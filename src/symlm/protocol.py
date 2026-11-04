"""Classify input against the Social Protocol Stack. Respond at matched layer."""
import random
import re

from symlm.parse import parse_sentence, cleanup_session


def _classifiers(s):
    """Return classifier capsules ordered by id (01 first)."""
    rows = s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'input-classifier'
        ORDER BY id
    """).fetchall()
    import json
    return [(r["id"], json.loads(r["state_json"])) for r in rows]


def _word_boundary_match(pattern, text_lower):
    """Pattern appears as a whole word/phrase."""
    # Escape pattern, add word boundaries
    p = re.escape(pattern.lower())
    return re.search(r'\b' + p + r'\b', text_lower) is not None


def _can_parse(s, text):
    r = parse_sentence(s, text)
    ok = r.get("sentence") is not None
    if r.get("session"):
        cleanup_session(s, r["session"])
    return ok


def classify(s, text):
    """Return {layer, kind, classifier_id, response_templates, name} or fallback."""
    text_lower = text.strip().lower()
    for cid, state in _classifiers(s):
        mode = state.get("match_mode")
        patterns = state.get("patterns", [])

        matched = False
        if mode == "exact":
            matched = text_lower in (p.lower() for p in patterns)
        elif mode == "contains":
            matched = any(_word_boundary_match(p, text_lower) for p in patterns)
        elif mode == "endswith":
            matched = any(text.strip().lower().endswith(p.lower()) for p in patterns)
        elif mode == "startswith":
            matched = any(text_lower.startswith(p.lower()) for p in patterns)
        elif mode == "parses":
            matched = _can_parse(s, text)

        if matched:
            return {
                "layer":       state.get("layer"),
                "kind":        state.get("name"),
                "classifier":  cid,
                "response_templates": state.get("response_templates", []),
            }

    return {"layer": 0, "kind": "unknown", "classifier": None, "response_templates": []}


def ack_response(classification):
    """Pick a template from the matched classifier."""
    templates = classification.get("response_templates") or ["ok"]
    return random.choice(templates)


def error_response(s, text):
    """Brief recovery. Name the failure mode precisely."""
    words = re.findall(r"[a-z]+", text.lower())
    unknown = [w for w in words if not s.get(f"lex/{w}")]
    if unknown:
        return f"I don't know: {', '.join(unknown)}."
    if len(words) == 1:
        return f"I know {words[0]!r} but can't parse it on its own."
    return "I know those words but can't parse that."
