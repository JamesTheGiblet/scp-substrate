"""Rule-based generator: expand grammar rules into a valid sentence.

The mirror of parse.py:
  parse:    tokens -> reduce via sequence rules -> S
  generate: S -> expand via sequence rules -> tokens

Both directions write the same kind of capsules (tokens, phrases, sentences)
with the same links (has-child, position-ordered) and the same event types
(rule.fired). A generated sentence can be re-parsed to the same tree.
"""
import json
import random
import uuid

from substrate import Substrate
from rules import _sv_agree, _object_semantic_check, _subject_semantic_check, _leaf_features


class ExpansionError(Exception):
    pass


def _rollback_subtree(s, capsule_id, session_id):
    """Delete a capsule and its descendants within a parse session."""
    to_delete = set()
    stack = [capsule_id]
    while stack:
        cid = stack.pop()
        if cid in to_delete:
            continue
        to_delete.add(cid)
        for l in s.links_from(cid):
            if l["type"] == "has-child":
                stack.append(l["target"])
    with s.conn:
        for cid in to_delete:
            s.conn.execute("DELETE FROM links WHERE source=? OR target=?", (cid, cid))
            s.conn.execute("DELETE FROM capsules WHERE id=?", (cid,))
        import json as _j
        s.conn.execute(
            "INSERT INTO events (event_type, capsule_id, payload) VALUES ('parse.rolled-back', ?, ?)",
            (capsule_id, _j.dumps({"session": session_id, "reason": "semantic"}))
        )


def _semantic_check_pp(s, prep_cid, np_cid):
    """PP -> prep NP. If prep requires location, every noun in the NP must be location=true."""
    prep = s.get(prep_cid)
    if not prep:
        return True
    pf = prep["state"].get("features", {})
    if not pf.get("requires_location"):
        return True
    np_leaves = _leaf_features(s, np_cid)
    nouns = [l for l in np_leaves if l["pos"] == "noun"]
    if not nouns:
        return False
    return all(n["features"].get("location") for n in nouns)


def _number_agree(s, children):
    """All leaves with a `number` feature must agree."""
    nums = set()
    for cid in children:
        for leaf in _leaf_features(s, cid):
            n = leaf.get("features", {}).get("number")
            if n:
                nums.add(n)
    return len(nums) <= 1


def _rule_weight(s, rule_id):
    """Trust weight for a rule (default 1 if no feedback yet)."""
    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.n0') AS n0
        FROM capsules
        WHERE foundation = 'foundation:leighton-weight'
          AND json_extract(state_json, '$.rule') = ?
        LIMIT 1
    """, (rule_id,)).fetchone()
    if row and row["n0"]:
        return max(0.1, float(row["n0"]))
    return 1.0


def _find_rules_producing(s, foundation, state_filter):
    rows = s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:rule'
          AND json_extract(state_json, '$.condition.type') = 'sequence'
    """).fetchall()
    out = []
    for r in rows:
        rule = json.loads(r["state_json"])
        effect = rule.get("effect", {})
        eff_f = effect.get("foundation", "")
        if not eff_f.startswith("foundation:"):
            eff_f = f"foundation:{eff_f}"
        if eff_f != foundation:
            continue
        eff_state = effect.get("state", {})
        if all(eff_state.get(k) == v for k, v in state_filter.items()):
            out.append({"id": r["id"], "rule": rule})
    return out


def _find_lexical_entries(s, pos, features=None, tense_pref=None):
    """Return list of {text, pos, features, weight} for a given pos, optionally filtered by features."""
    rows = s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'lexical-entry'
          AND json_extract(state_json, '$.pos') = ?
    """, (pos,)).fetchall()
    out = []
    for r in rows:
        state = json.loads(r["state_json"])
        if features:
            cf = state.get("features", {})
            if not all(cf.get(k) == v for k, v in features.items()):
                continue
        # Weight from trust/freq/<word> if present
        w = s.conn.execute("""
            SELECT json_extract(state_json, '$.n0') AS n0
            FROM capsules
            WHERE foundation = 'foundation:leighton-weight'
              AND json_extract(state_json, '$.word') = ?
            LIMIT 1
        """, (state["text"],)).fetchone()
        weight = float(w["n0"]) if (w and w["n0"]) else 1.0
        # Bias by tense preference (don't block; just nudge)
        if tense_pref:
            t = state.get("features", {}).get("tense")
            if t == tense_pref:
                weight *= 10.0
            elif t is not None:
                weight *= 0.1
        state["weight"] = weight
        state["features"] = state.get("features", {})
        out.append(state)
    return out


def _expand(s, spec, rng, session_id, next_idx, depth=0, tense_pref=None):
    """Expand a spec into tokens. Returns (texts, next_idx, capsule_id)."""
    if depth > 20:
        raise ExpansionError("depth limit")

    foundation = spec.get("foundation", "token")
    if not foundation.startswith("foundation:"):
        foundation = f"foundation:{foundation}"
    state_filter = spec.get("state", {})

    # Base case: leaf token
    if foundation == "foundation:token":
        pos = state_filter.get("pos")
        if not pos:
            raise ExpansionError("token spec missing 'pos'")
        features = spec.get("features")
        choices = _find_lexical_entries(s, pos, features=features, tense_pref=tense_pref)
        if not choices:
            hint = f" pos={pos!r}" + (f" features={features!r}" if features else "")
            raise ExpansionError(f"no lexical entries for{hint}")
        weights = [c["weight"] for c in choices]
        word = rng.choices(choices, weights=weights, k=1)[0]
        tok_id = f"parse/{session_id}/tok-{next_idx}"
        s.write({
            "id": tok_id,
            "foundation": "foundation:token",
            "state": {
                "text": word.get("text"), "pos": pos, "index": next_idx,
                "features": word.get("features", {}),
            },
        })
        return [word["text"]], next_idx + 1, tok_id

    # Phrase / sentence: find rules that produce this category
    rules = _find_rules_producing(s, foundation, state_filter)
    if not rules:
        raise ExpansionError(f"no rules producing {foundation} {state_filter}")
    # Weighted by rule trust (feedback-informed)
    rule_weights = [_rule_weight(s, r["id"]) for r in rules]
    chosen = rng.choices(rules, weights=rule_weights, k=1)[0]
    rules = [chosen] + [r for r in rules if r is not chosen]

    last_err = None
    for r in rules:
        try:
            texts = []
            cur = next_idx
            children = []
            for child_spec in r["rule"]["condition"].get("match", []):
                sub_texts, cur, cid = _expand(s, child_spec, rng, session_id, cur, depth + 1, tense_pref=tense_pref)
                texts.extend(sub_texts)
                children.append(cid)

            # Semantic check for PP -> prep NP
            if (foundation == "foundation:phrase"
                    and state_filter.get("category") == "PP"
                    and len(children) == 2):
                if not _semantic_check_pp(s, children[0], children[1]):
                    for cid in children:
                        _rollback_subtree(s, cid, session_id)
                    raise ExpansionError("semantic: requires location")

            # Number agreement for NP
            if (foundation == "foundation:phrase"
                    and state_filter.get("category") == "NP"):
                if not _number_agree(s, children):
                    for cid in children:
                        _rollback_subtree(s, cid, session_id)
                    raise ExpansionError("number disagreement in NP")

            # Subject-verb agreement (opt-in on rule)
            if (foundation == "foundation:sentence"
                    and r["rule"]["condition"].get("subject_verb_agree")
                    and len(children) == 2):
                if not _sv_agree(s, children[0], children[1]):
                    for cid in children:
                        _rollback_subtree(s, cid, session_id)
                    raise ExpansionError("subject-verb disagreement")

                # Subject animacy
                vp_children = s.conn.execute(
                    "SELECT target FROM links WHERE source=? AND type='has-child' "
                    "ORDER BY json_extract(metadata, '$.position')",
                    (children[1],)
                ).fetchall()
                if vp_children:
                    verb_cid = vp_children[0]["target"]
                    verb = s.get(verb_cid)
                    if (verb and verb["foundation"] == "foundation:token"
                            and not _subject_semantic_check(s, verb_cid, children[0])):
                        for cid in children:
                            _rollback_subtree(s, cid, session_id)
                        raise ExpansionError("subject must be animate")

            # Object semantic check for VP -> verb NP
            if (foundation == "foundation:phrase"
                    and state_filter.get("category") == "VP"
                    and len(children) >= 2):
                child0 = s.get(children[0])
                child1 = s.get(children[1])
                if (child0 and child1
                        and child0["foundation"] == "foundation:token"
                        and child1["foundation"] == "foundation:phrase"
                        and child1["state"].get("category") == "NP"):
                    if not _object_semantic_check(s, children[0], children[1]):
                        for cid in children:
                            _rollback_subtree(s, cid, session_id)
                        raise ExpansionError("object must be animate")

            rule_short = r["id"].split("/")[-1]
            new_id = f"parse/{session_id}/{rule_short}/{next_idx}-{cur-1}"
            new_state = dict(r["rule"]["effect"].get("state", {}))
            new_state["start"] = next_idx
            new_state["end"] = cur - 1

            s.write({"id": new_id, "foundation": foundation, "state": new_state})
            with s.conn:
                for i, cid in enumerate(children):
                    s.conn.execute(
                        "INSERT OR IGNORE INTO links (source, type, target, metadata) "
                        "VALUES (?, 'has-child', ?, ?)",
                        (new_id, cid, json.dumps({"position": i, "derived_by": r["id"]}))
                    )
                s.conn.execute(
                    "INSERT INTO events (event_type, capsule_id, payload) "
                    "VALUES ('rule.fired', ?, ?)",
                    (r["id"], json.dumps({"derived": new_id, "direction": "generate"}))
                )
            return texts, cur, new_id
        except ExpansionError as e:
            last_err = e
            continue

    raise ExpansionError(f"all rules failed for {foundation} {state_filter}: {last_err}")


_START_FOUNDATIONS = {
    "S":  ("foundation:sentence", {"category": "S"}),
    "NP": ("foundation:phrase",   {"category": "NP"}),
    "VP": ("foundation:phrase",   {"category": "VP"}),
    "PP": ("foundation:phrase",   {"category": "PP"}),
}


def generate_sentence(s, start="S", seed=None, prefer_tense=None):
    """Generate a sentence (or sub-category) by rule expansion."""
    if start not in _START_FOUNDATIONS:
        return {"error": f"unknown start category {start!r}; use one of {list(_START_FOUNDATIONS)}"}
    if seed is None:
        seed = random.randrange(2**32)
    rng = random.Random(seed)
    session_id = uuid.uuid4().hex[:8]
    foundation, state_filter = _START_FOUNDATIONS[start]

    # Retry: SV/object checks may reject the first pick; different random choices
    # on retry often succeed. Preserves determinism (same rng state → same result).
    last_err = None
    texts = end = root = None
    for _attempt in range(8):
        try:
            texts, end, root = _expand(
                s, {"foundation": foundation, "state": state_filter},
                rng, session_id, 0, tense_pref=prefer_tense
            )
            break
        except ExpansionError as e:
            last_err = e
            # Clear any leftover partial capsules from failed attempts
            from parse import cleanup_session
            cleanup_session(s, session_id)
            continue

    if texts is None:
        return {"error": str(last_err or "expansion failed"),
                "session": session_id, "seed": seed}

    return {
        "session": session_id,
        "seed":    seed,
        "start":   start,
        "text":    " ".join(texts),
        "tokens":  texts,
        "root":    root,
    }
