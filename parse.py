"""Rule-based parser: tokenise, reduce via sequence rules, display."""
import json
import re
import uuid

from substrate import Substrate
from rules import evaluate_rules


def _lookup_entry(s, word):
    """Return lexical entry state; falls back to alias/ or typo/."""
    for kind in ("lexical-entry", "alias", "typo"):
        row = s.conn.execute("""
            SELECT state_json FROM capsules
            WHERE foundation = 'foundation:knowledge'
              AND json_extract(state_json, '$.kind') = ?
              AND json_extract(state_json, '$.text') = ?
            LIMIT 1
        """, (kind, word)).fetchone()
        if row:
            return json.loads(row["state_json"])
    return None


def lookup_pos(s, word):
    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.pos') AS pos
        FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'lexical-entry'
          AND json_extract(state_json, '$.text') = ?
    """, (word,)).fetchone()
    return row["pos"] if row else None


def tokenise(s, text, session_id):
    words = re.findall(r"[a-zA-Z]+", text.lower())
    token_ids = []
    for i, word in enumerate(words):
        entry = _lookup_entry(s, word)
        if entry is None:
            raise ValueError(f"unknown word: {word!r}")
        tok_id = f"parse/{session_id}/tok-{i}"
        s.write({
            "id": tok_id,
            "foundation": "foundation:token",
            "state": {
                "text": word,
                "pos": entry["pos"],
                "index": i,
                "features": entry.get("features", {}),
            },
        })
        token_ids.append(tok_id)
    return token_ids


def parse_sentence(s, text, max_iter=50):
    session_id = uuid.uuid4().hex[:8]
    try:
        tokens = tokenise(s, text, session_id)
    except ValueError as e:
        return {"error": str(e), "session": session_id}

    if not tokens:
        return {"error": "no tokens in input", "session": session_id}

    n = len(tokens)
    scope = set(tokens)

    for _ in range(max_iter):
        fired, _ = evaluate_rules(s, scope=scope, only_types={"sequence"})
        if not fired:
            break
        for f in fired:
            scope.add(f[3])

    scope_list = list(scope)
    placeholders = ",".join("?" * len(scope_list))
    rows = s.conn.execute(f"""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:sentence'
          AND id IN ({placeholders})
    """, scope_list).fetchall()

    full = None
    for r in rows:
        state = json.loads(r["state_json"])
        if state.get("start") == 0 and state.get("end") == n - 1:
            full = r["id"]
            break

    return {
        "session":  session_id,
        "tokens":   tokens,
        "sentence": full,
        "n_tokens": n,
    }


def display_parse(s, root_id, prefix="", is_last=None):
    c = s.get(root_id)
    if not c:
        return
    state = c["state"]
    foundation = c["foundation"].replace("foundation:", "")

    if foundation == "token":
        label = f"{state.get('pos', '?')} \"{state.get('text', '?')}\" [{state.get('index')}]"
    elif foundation == "phrase":
        label = f"{state.get('category', '?')} [{state.get('start')}-{state.get('end')}]"
    elif foundation == "sentence":
        label = f"S [{state.get('start')}-{state.get('end')}]"
    else:
        label = foundation

    if is_last is None:
        print(label)
        child_prefix = ""
    else:
        connector = "└─ " if is_last else "├─ "
        print(f"{prefix}{connector}{label}")
        child_prefix = prefix + ("   " if is_last else "│  ")

    children = s.conn.execute("""
        SELECT target FROM links
        WHERE source = ? AND type = 'has-child'
        ORDER BY json_extract(metadata, '$.position')
    """, (root_id,)).fetchall()

    for i, child in enumerate(children):
        display_parse(s, child["target"], child_prefix, i == len(children) - 1)


def cleanup_session(s, session_id):
    prefix = f"parse/{session_id}/%"
    with s.conn:
        s.conn.execute(
            "DELETE FROM links WHERE source LIKE ? OR target LIKE ?",
            (prefix, prefix)
        )
        s.conn.execute("DELETE FROM capsules WHERE id LIKE ?", (prefix,))
        s.conn.execute(
            "INSERT INTO events (event_type, payload) VALUES ('parse.cleaned', ?)",
            (json.dumps({"session": session_id}),)
        )
