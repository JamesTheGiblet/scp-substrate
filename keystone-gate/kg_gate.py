"""The gate. Binds a gated function to an sc capsule and refuses to pass
answers that violate compliance.

Structure-only compliance: the gate checks that any references in an answer
(capsule IDs, file paths, slugs, multi-word names) are grounded in the
substrate, that any numeric trust scores match the capsule's actual trust,
and that an affirmative answer came from a real intent. It does not judge
whether the answer is "correct" — only whether its references are real.

A bare single word ("bigfoot") cannot be told apart from ordinary English,
so it is out of reach of a structure-only check.

The gate reads its rules from an sc capsule (sc/symlm-answerer by default).
Adding a rule means adding a check function here and a `must` or `must_not`
entry in the sc capsule. Removing a rule means removing both.
"""
import json
import re

from substrate import Substrate


# A capsule ID or file path in text: one or more slash-separated segments
_ID_RE = re.compile(r"(?<![\w./-])[A-Za-z0-9_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]+)+")

# A hyphenated slug: santa-claus, everything-is-capsules
_SLUG_RE = re.compile(r"(?<![\w./-])[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+(?![\w/-])")

# A multi-word proper name: Santa Claus
_NAME_RE = re.compile(r"\b[A-Z][a-z]+(?: [A-Z][a-z]+)+\b")

# Trust score in text: "score = 0.98", "score: 1.0", "trust 1", "Posterior 0.5"
_TRUST_RE = re.compile(r"\b(?:score|trust|posterior)\s*(?:[=:]\s*)?(\d+(?:\.\d+)?)", re.IGNORECASE)

# Logged chat is what people typed, not what the substrate knows
_UNGROUNDED_KINDS = ("conversation-turn", "unparsed-input")


def load_sc(s, sc_id="sc/symlm-answerer"):
    """Load the sc capsule that defines the gate's contract. Returns state dict or None."""
    c = s.get(sc_id)
    if not c:
        return None
    return c["state"]


def _iter_text_fields(result):
    """Yield every text field from an ask.answer_question result."""
    if not result:
        return
    for key in ("summary", "detail"):
        v = result.get(key)
        if isinstance(v, str):
            yield v
    detail = result.get("detail")
    if isinstance(detail, dict):
        yield json.dumps(detail)


def _ids_in(text):
    return [m.group(0).rstrip(".,;:") for m in _ID_RE.finditer(text)]


def _names_in(text):
    slugs = [m.group(0) for m in _SLUG_RE.finditer(text)
             if re.search(r"[A-Za-z]", m.group(0))]
    return slugs + _NAME_RE.findall(text)


def _strings_in(value):
    """Yield every string nested inside a JSON value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings_in(v)
    elif isinstance(value, list):
        for v in value:
            yield from _strings_in(v)


def _grounded_terms(s):
    """Every reference that appears in stored content, lowercased.

    Tokenised the same way as answers, so a match is the whole term and not
    a fragment of a longer one. Covers file paths, which are not capsule IDs.
    """
    terms = {r["type"].lower() for r in s.conn.execute("SELECT DISTINCT type FROM links")}
    terms.update(r["kind"].lower() for r in s.conn.execute(
        "SELECT DISTINCT json_extract(state_json, '$.kind') AS kind FROM capsules "
        "WHERE json_extract(state_json, '$.kind') IS NOT NULL"
    ))
    placeholders = ",".join("?" for _ in _UNGROUNDED_KINDS)
    for r in s.conn.execute(
        "SELECT state_json FROM capsules "
        f"WHERE COALESCE(json_extract(state_json, '$.kind'), '') NOT IN ({placeholders})",
        _UNGROUNDED_KINDS,
    ):
        for text in _strings_in(json.loads(r["state_json"])):
            terms.update(t.lower() for t in _ids_in(text))
            terms.update(t.lower() for t in _names_in(text))
    return terms


def _ungrounded(s, terms):
    """Return the terms that are neither capsules nor in stored content."""
    missing = [t for t in dict.fromkeys(terms) if not s.get(t)]
    if not missing:
        return []
    grounded = _grounded_terms(s)
    return [t for t in missing if t.lower() not in grounded]


def _actual_trust_values(s, cid):
    """Return list of (source, value) plausibly rendered as trust for a capsule.

    The walker may render either trust_now.score (parameter trust) or
    fused_trust.posterior (combined), or an observation's own stored score.
    Accept all three.
    """
    values = []
    capsule = s.get(cid)
    stored = capsule["state"].get("score") if capsule else None
    if isinstance(stored, (int, float)) and not isinstance(stored, bool):
        values.append(("stored_score", float(stored)))
    try:
        from queries import trust_now
        tn = trust_now(s, cid)
        if tn and tn.get("score") is not None:
            values.append(("trust_now", float(tn["score"])))
    except Exception:
        pass
    try:
        from trust import fused_trust
        ft = fused_trust(s, cid)
        if ft and ft.get("posterior") is not None:
            values.append(("fused_trust", float(ft["posterior"])))
    except Exception:
        pass
    return values


def _check_no_invented_ids(s, result):
    """Every slashed ID or path mentioned must be grounded in the substrate.

    Also: if result["entity"] is set (walkers always set it), it must exist.
    """
    violations = []

    # Check explicit entity first
    entity = result.get("entity")
    if entity and not s.get(entity):
        violations.append({
            "rule": "no_invented_ids",
            "detail": f"entity {entity!r} mentioned but not in substrate",
        })

    terms = [t for text in _iter_text_fields(result) for t in _ids_in(text)]
    for cid in _ungrounded(s, terms):
        violations.append({
            "rule": "no_invented_ids",
            "detail": f"{cid!r} mentioned but not in substrate",
        })
    return violations


def _check_no_hallucinated_entities(s, result):
    """Every slug or multi-word name mentioned must be grounded in the substrate."""
    terms = [t for text in _iter_text_fields(result) for t in _names_in(text)]
    return [{
        "rule": "no_hallucinated_entities",
        "detail": f"{term!r} mentioned but not in substrate",
    } for term in _ungrounded(s, terms)]


def _check_no_llm_prior(s, result):
    """An affirmative answer must come from a real intent's walk.

    Provenance only: an explicit refusal (ok=False) claims nothing, so it
    passes. Whether the words follow from the walk is the human's job.
    """
    if result.get("ok") is False:
        return []
    intent = result.get("intent")
    capsule = s.get(intent) if intent else None
    if not capsule or capsule["state"].get("kind") != "input-intent":
        return [{
            "rule": "no_llm_prior",
            "detail": f"answer has no substrate provenance (intent={intent!r})",
        }]
    return []


def _check_no_hallucinated_trust(s, result):
    """Any numeric trust score must match the actual trust for the named capsule.

    Primary ID source: result["entity"] — walkers set this explicitly.
    Fallback: nearest slashed ID in the text.
    """
    violations = []
    primary = result.get("entity") if isinstance(result, dict) else None

    for text in _iter_text_fields(result):
        for match in _TRUST_RE.finditer(text):
            claimed = float(match.group(1))

            cid = primary
            if cid is None:
                # fallback: nearest slashed ID before the score
                start = max(0, match.start() - 300)
                window = text[start:match.start()]
                id_matches = list(_ID_RE.finditer(window))
                if id_matches:
                    cid = id_matches[-1].group(0).rstrip(".,;:")

            if cid is None:
                violations.append({
                    "rule": "no_hallucinated_trust",
                    "detail": f"trust value {claimed:.4f} with no identifiable capsule",
                })
                continue

            actuals = _actual_trust_values(s, cid)
            if not actuals:
                violations.append({
                    "rule": "no_hallucinated_trust",
                    "detail": f"claimed {claimed:.4f} for {cid!r} but no trust record exists",
                })
                continue

            # Accept if claimed matches ANY plausible value within tolerance
            matched = None
            for source, val in actuals:
                if abs(val - claimed) <= 0.02:
                    matched = (source, val)
                    break

            if matched is None:
                summary = ", ".join(f"{src}={val:.4f}" for src, val in actuals)
                violations.append({
                    "rule": "no_hallucinated_trust",
                    "detail": f"claimed {claimed:.4f} for {cid!r}; actual: {summary}",
                })
    return violations


def _normalised(text):
    return " ".join(text.split())


def _check_claims_quote_evidence(s, result):
    """Every claim must quote, verbatim, the walker evidence it rests on."""
    claims = result.get("claims") or []
    if not claims:
        return [{"rule": "claims_quote_evidence", "detail": "answer has no claims"}]
    evidence = _normalised(result.get("evidence") or "")
    return [{
        "rule": "claims_quote_evidence",
        "detail": f"quote not found in evidence: {claim.get('evidence')!r}",
    } for claim in claims
        if not claim.get("evidence")
        or _normalised(claim["evidence"]) not in evidence]


def _check_no_unsourced_terms(s, result):
    """Numbers and capitalised words must come from the evidence or the question.

    The first word of a sentence is capitalised anyway, so it proves nothing.
    """
    source = f"{result.get('evidence') or ''} {result.get('question') or ''}".lower()
    known = set(re.findall(r"\w+(?:\.\d+)?", source))
    violations = []
    for claim in result.get("claims") or []:
        terms = re.findall(r"\b\d+(?:\.\d+)?\b", claim.get("text", ""))
        for sentence in re.split(r"[.!?:]\s+", claim.get("text", "")):
            terms += re.findall(r"\b[A-Z][A-Za-z]+\b", sentence)
            first = re.match(r"\W*([A-Z][A-Za-z]+)\b", sentence)
            if first:
                terms.remove(first.group(1))
        for term in dict.fromkeys(terms):
            if term.lower() not in known:
                violations.append({
                    "rule": "no_unsourced_terms",
                    "detail": f"{term!r} is not in the evidence or the question",
                })
    return violations


_RULES = {
    "no_invented_ids": _check_no_invented_ids,
    "no_hallucinated_trust": _check_no_hallucinated_trust,
    "no_hallucinated_entities": _check_no_hallucinated_entities,
    "no_llm_prior": _check_no_llm_prior,
    "claims_quote_evidence": _check_claims_quote_evidence,
    "no_unsourced_terms": _check_no_unsourced_terms,
}


def check(s, proposed, sc=None):
    """Check a proposed answer against the sc capsule's `must` and `must_not` rules.

    proposed = {"input": str, "result": dict}  (result is ask.answer_question's output)
    sc = optional pre-loaded sc state; if None, loads sc/symlm-answerer

    Returns {"ok": bool, "violations": [{"rule", "detail"}], "sc_id": str}
    """
    if sc is None:
        sc = load_sc(s)
    if sc is None:
        return {
            "ok": False,
            "sc_id": None,
            "violations": [{"rule": "missing_sc", "detail": "no sc capsule loaded"}],
        }

    result = proposed.get("result")
    if result is None:
        # No answer produced — nothing to gate. Empty answer is trivially compliant.
        return {"ok": True, "sc_id": sc.get("name"), "violations": []}

    all_violations = []
    for entry in sc.get("must", []) + sc.get("must_not", []):
        rule_name = entry.get("rule")
        checker = _RULES.get(rule_name)
        if not checker:
            all_violations.append({
                "rule": rule_name or "unknown",
                "detail": "no checker implemented for this rule",
            })
            continue
        all_violations.extend(checker(s, result))

    return {
        "ok": not all_violations,
        "sc_id": sc.get("name"),
        "violations": all_violations,
    }
