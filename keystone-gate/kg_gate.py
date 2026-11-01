"""The gate. Binds a gated function to an sc capsule and refuses to pass
answers that violate compliance.

Structure-only compliance: the gate checks that any capsule IDs mentioned
in an answer exist in the substrate, and that any numeric trust scores
match the capsule's actual trust. It does not judge whether the answer is
"correct" — only whether its references are real.

The gate reads its rules from an sc capsule (sc/symlm-answerer by default).
Adding a rule means adding a check function here and a `must` entry in the
sc capsule. Removing a rule means removing both.
"""
import json
import re

from substrate import Substrate


# A capsule ID in text looks like: one or more slash-separated segments
_ID_RE = re.compile(r"\b[a-z0-9_][a-z0-9_.-]*(?:/[a-z0-9_.-]+)+\b")

# Trust score in text: "score = 0.XXXXXX", "score: 0.XXXXXX", or "score 0.XXXXXX"
_TRUST_RE = re.compile(r"(?:score|trust|posterior)\s*(?:[=:]\s*)?(0\.\d+)")


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


def _actual_trust_values(s, cid):
    """Return list of (source, value) plausibly rendered as trust for a capsule.

    The walker may render either trust_now.score (parameter trust) or
    fused_trust.posterior (combined). Accept both.
    """
    values = []
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
    """Every slashed ID mentioned must exist in the substrate.

    Also: if result["entity"] is set (walkers always set it), it must exist.
    """
    violations = []
    seen = set()

    # Check explicit entity first
    entity = result.get("entity")
    if entity and not s.get(entity):
        violations.append({
            "rule": "no_invented_ids",
            "detail": f"entity {entity!r} mentioned but not in substrate",
        })

    for text in _iter_text_fields(result):
        for match in _ID_RE.finditer(text):
            cid = match.group(0).rstrip(".,;:")
            if cid in seen:
                continue
            seen.add(cid)
            if not s.get(cid):
                violations.append({
                    "rule": "no_invented_ids",
                    "detail": f"{cid!r} mentioned but not in substrate",
                })
    return violations


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


_RULES = {
    "no_invented_ids": _check_no_invented_ids,
    "no_hallucinated_trust": _check_no_hallucinated_trust,
}


def check(s, proposed, sc=None):
    """Check a proposed answer against the sc capsule's `must` rules.

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
    for must in sc.get("must", []):
        rule_name = must.get("rule")
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
