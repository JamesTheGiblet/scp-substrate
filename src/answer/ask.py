"""Natural language queries against the substrate.

Flow:
  question → intent classifier → entity extraction → walker → render → answer
"""
import json
import re

from store.substrate import Substrate
from answer.walkers import WALKERS, extract_kind


# --- intent classification ----------------------------------------------
def _intents(s):
    rows = s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'input-intent'
        ORDER BY id
    """).fetchall()
    return [(r["id"], json.loads(r["state_json"])) for r in rows]


def classify_intent(s, text):
    """Return intent dict or None."""
    text_lower = " ".join(text.lower().split())
    for cid, state in _intents(s):
        for phrase in state.get("phrases", []):
            if phrase.lower() in text_lower:
                return _intent_match(cid, state)
        for pattern in state.get("patterns", []):
            if re.search(pattern, text_lower):
                return _intent_match(cid, state)
    return None


def _intent_match(cid, state):
    return {
        "id": cid,
        "walker": state["walker"],
        "requires_entity": state.get("requires_entity", False),
    }


# --- entity extraction ---------------------------------------------------
def extract_entity(s, text, intent):
    """Find the most likely substrate ID the question is about."""
    # Direct ID match first — handles paths like repo/owner/name, file/owner/name/path.py
    for word in re.findall(r"[a-z0-9_./-]+", text.lower()):
        if "/" in word and len(word) >= 5 and s.get(word):
            return word

    # A hyphenated word may be the last segment of one namespaced ID:
    # james-gilbert-v1 -> giblets-forge/author/james-gilbert-v1
    for word in re.findall(r"[a-z0-9_.-]+", text.lower()):
        if "-" in word and not s.get(word):
            rows = s.conn.execute(
                "SELECT id FROM capsules WHERE substr(id, -?) = ?",
                (len(word) + 1, "/" + word),
            ).fetchall()
            if len(rows) == 1:
                return rows[0]["id"]

    tokens = [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 2]

    SKIP_PREFIXES = ("lex/", "typo/", "alias/", "corpus/")

    def _usable(cid):
        return not any(cid.startswith(p) for p in SKIP_PREFIXES)

    # 3-, 2-, 1-word compound slugs, scanning left-to-right
    for n in (3, 2, 1):
        for i in range(len(tokens) - n + 1):
            candidate = "-".join(tokens[i:i + n])
            if _usable(candidate) and s.get(candidate):
                return candidate

    # Any token as a direct ID
    for t in tokens:
        if len(t) >= 3 and _usable(t) and s.get(t):
            return t

    # Match against state.text or state.name
    for t in tokens:
        if len(t) < 3:
            continue
        row = s.conn.execute("""
            SELECT id FROM capsules
            WHERE foundation IN ('foundation:knowledge', 'foundation:entity', 'foundation:person',
                                 'foundation:project', 'foundation:subject')
              AND is_meta = 0
              AND (lower(json_extract(state_json, '$.text')) = ?
                   OR lower(json_extract(state_json, '$.name')) = ?)
            LIMIT 1
        """, (t, t)).fetchone()
        if row and _usable(row["id"]):
            return row["id"]

    # Intent-specific defaults
    if intent["walker"] in ("what_uses", "what_building"):
        return "james"
    if intent["walker"] == "what_decided":
        return None  # search across all decisions
    if intent["walker"] == "list_kind":
        return None  # kind extracted from text

    return None




# --- entry point --------------------------------------------------------
def answer_question(s, text):
    """Try to answer a question against the substrate. Returns dict or None."""
    intent = classify_intent(s, text)
    if not intent:
        return None

    entity = extract_entity(s, text, intent)

    if intent["requires_entity"] and not entity:
        return {"ok": False,
                "summary": f"I understood the question ({intent['id']}) "
                           f"but couldn't identify what you're asking about.",
                "detail": None}

    walker = WALKERS.get(intent["walker"])
    if not walker:
        return {"ok": False,
                "summary": f"Intent '{intent['id']}' has no walker — bug.",
                "detail": None}

    result = walker(s, entity, text)
    result["intent"] = intent["id"]
    result["entity"] = entity
    return result


def render(result):
    """Turn a result dict into printable text."""
    if result is None:
        return None
    text = result.get("summary", "")
    detail = result.get("detail")
    if detail:
        text += "\n" + detail
    return text
