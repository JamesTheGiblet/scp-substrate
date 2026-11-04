"""Conversational REPL. Parses input, responds from grammar + substrate,
logs every turn as a capsule."""
import json
import re
import uuid

from substrate import Substrate
from parse import parse_sentence, cleanup_session, display_parse
from generate import generate_sentence


def _extract_semantic(s, root_id, session_id):
    """Extract subject, verb, verb_tense, object from a parse tree."""
    rows = s.conn.execute("""
        SELECT json_extract(state_json, '$.text') AS text,
               json_extract(state_json, '$.pos') AS pos,
               json_extract(state_json, '$.features') AS features,
               json_extract(state_json, '$.index') AS idx
        FROM capsules
        WHERE id LIKE ? AND foundation = 'foundation:token'
        ORDER BY json_extract(state_json, '$.index')
    """, (f"parse/{session_id}/tok-%",)).fetchall()

    tokens = [dict(r) for r in rows]  # Row -> dict so .get() works

    nouns = [t for t in tokens if t["pos"] == "noun"]
    verbs = [t for t in tokens if t["pos"] == "verb"]
    verb = verbs[0] if verbs else None

    verb_features = {}
    if verb and verb.get("features"):
        f = verb["features"]
        if isinstance(f, str):
            try:
                verb_features = json.loads(f)
            except json.JSONDecodeError:
                # Features are optional; a bad blob means none
                verb_features = {}
        elif isinstance(f, dict):
            verb_features = f

    return {
        "subject":    nouns[0]["text"] if nouns else None,
        "verb":       verb["text"] if verb else None,
        "verb_tense": verb_features.get("tense"),
        "object":     nouns[-1]["text"] if len(nouns) > 1 else None,
    }


def _discourse_state(s, session_id):
    """Return the previous turn's subject and tense for this session."""
    row = s.conn.execute("""
        SELECT json_extract(state_json, '$.subject') AS subject,
               json_extract(state_json, '$.verb_tense') AS tense
        FROM capsules
        WHERE id LIKE ? AND json_extract(state_json, '$.kind') = 'conversation-turn'
        ORDER BY id DESC LIMIT 1
    """, (f"conversation/{session_id}/%",)).fetchone()
    return {"subject": row["subject"] if row else None,
            "tense":   row["tense"] if row else None}


def _is_question(text):
    """Question-shaped? ends with '?' or starts with wh-word."""
    t = text.strip().lower()
    if t.endswith("?"):
        return True
    for w in ("what", "who", "where", "when", "why", "how", "which"):
        if t.startswith(w + " ") or t == w:
            return True
    return False


def _log_turn(s, session_id, turn, user_text, response, parsed, semantic=None, classification=None):
    cid = f"conversation/{session_id}/{turn:03d}"
    state = {
        "kind": "conversation-turn",
        "session": session_id,
        "turn": turn,
        "input": user_text,
        "output": response,
        "parsed": parsed,
    }
    if semantic:
        state.update({
            "subject":    semantic.get("subject"),
            "verb":       semantic.get("verb"),
            "verb_tense": semantic.get("verb_tense"),
            "object":     semantic.get("object"),
        })
    if classification:
        state.update({
            "layer":      classification.get("layer"),
            "kind_class": classification.get("kind"),
        })
    with s.conn:
        s.write({
            "id": cid,
            "foundation": "foundation:observation",
            "state": state,
        })
    return cid


def respond(s, text, turn, session_id):
    """Classify input, respond at matched layer."""
    import protocol as _p

    prev = _discourse_state(s, session_id)
    classification = _p.classify(s, text)
    layer = classification["layer"]

    response = ""
    semantic = {}

    if 2 <= layer <= 6:
        # Ack mode: any non-semantic layer (2-6) gets a Layer-matched response.
        # Only Layer 7 (Application) is genuine semantic content.
        response = _p.ack_response(classification)

    elif layer == 7 or (layer == 3 and _is_question(text)):
        # First try querying the substrate for an answer
        from ask import answer_question, render as _ask_render
        q = answer_question(s, text)
        if q is not None:
            response = _ask_render(q)
        else:
            # Fall back to grammar parse + generate (for statements)
            resolved = text
            if prev["subject"]:
                resolved = re.sub(r'\bit\b', prev["subject"], text, flags=re.IGNORECASE)
            prefix = f"(it → {prev['subject']}) " if resolved != text else ""

            r = parse_sentence(s, resolved)
            if "error" in r or not r.get("sentence"):
                if r.get("session"):
                    cleanup_session(s, r["session"])
                response = prefix + _p.error_response(s, resolved)
            else:
                semantic = _extract_semantic(s, r["sentence"], r["session"])
                cleanup_session(s, r["session"])
                g = generate_sentence(s, prefer_tense=semantic.get("verb_tense"))
                if "error" in g:
                    response = prefix + "I didn't follow."
                else:
                    response = prefix + f"So: {g['text']}."
                    cleanup_session(s, g["session"])

    else:
        # Error mode: brief, no word dump
        response = _p.error_response(s, text)
        # Log unparsed for later grammar induction
        import uuid as _uuid
        uid = _uuid.uuid4().hex[:8]
        s.write({
            "id": f"unparsed/{session_id}/{turn:03d}-{uid}",
            "foundation": "foundation:observation",
            "state": {
                "kind": "unparsed-input",
                "session": session_id,
                "turn": turn,
                "text": text,
            },
        })

    _log_turn(s, session_id, turn, text, response,
              parsed=(layer == 7),
              semantic=semantic,
              classification=classification)
    return response


def help_text():
    return (
        "Commands:\n"
        "  help    this message\n"
        "  quit    exit\n"
        "  words   list known words\n"
        "  <text>  say something (any English using known words)\n"
        "\n"
        "Known grammar: S → NP VP. NP → det [adj] noun. "
        "VP → verb | verb NP | verb PP | verb NP PP. PP → prep NP."
    )


def cmd_words(s):
    rows = s.conn.execute("""
        SELECT json_extract(state_json, '$.text') AS text,
               json_extract(state_json, '$.pos') AS pos
        FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'lexical-entry'
        ORDER BY pos, text
    """).fetchall()
    by_pos = {}
    for r in rows:
        by_pos.setdefault(r["pos"], []).append(r["text"])
    for pos in sorted(by_pos):
        print(f"  {pos:6}: {', '.join(by_pos[pos])}")


def repl():
    s = Substrate()
    session_id = uuid.uuid4().hex[:8]
    # Banner reads live counts from the substrate
    n_lex = s.conn.execute("""
        SELECT COUNT(*) FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') IN ('lexical-entry', 'alias', 'typo')
    """).fetchone()[0]
    n_rules = s.conn.execute("""
        SELECT COUNT(*) FROM capsules
        WHERE foundation = 'foundation:rule'
          AND json_extract(state_json, '$.condition.type') = 'sequence'
    """).fetchone()[0]
    n_class = s.conn.execute("""
        SELECT COUNT(*) FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'input-classifier'
    """).fetchone()[0]

    print(f"SCP talk — session {session_id}")
    print(f"SymLM (Symbolic Language Model). {n_lex} words, {n_rules} grammar rules, {n_class} classifiers.")
    print("Every answer is a graph walk. Not a chatbot.")
    print("Type 'help' for commands, 'quit' to exit.\n")
    turn = 0
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in ("quit", "exit", "q"):
            break
        if line.lower() == "help":
            print(help_text())
            continue
        if line.lower() == "words":
            cmd_words(s)
            continue
        turn += 1
        print(respond(s, line, turn, session_id))
    print(f"\nSession {session_id} ended. {turn} turns logged as capsules.")
    s.close()


if __name__ == "__main__":
    repl()
