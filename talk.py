"""Conversational REPL. Parses input, responds from grammar + substrate,
logs every turn as a capsule."""
import re
import uuid

from substrate import Substrate
from parse import parse_sentence, cleanup_session, display_parse
from generate import generate_sentence


def _known_words(s, text):
    words = re.findall(r"[a-z]+", text.lower())
    out = []
    for w in words:
        c = s.get(f"lex/{w}")
        if c:
            st = c["state"]
            out.append({"word": w, "pos": st["pos"],
                        "features": st.get("features", {})})
    return out


def _log_turn(s, session_id, turn, user_text, response, parsed):
    cid = f"conversation/{session_id}/{turn:03d}"
    with s.conn:
        s.write({
            "id": cid,
            "foundation": "foundation:observation",
            "state": {
                "kind": "conversation-turn",
                "session": session_id,
                "turn": turn,
                "input": user_text,
                "output": response,
                "parsed": parsed,
            },
        })
    return cid


def respond(s, text, turn, session_id):
    parts = []
    parsed = False

    # 1. Try to parse
    r = parse_sentence(s, text)
    if "error" in r:
        # unknown word — say which one
        parts.append(f"I don't know: {r['error']}")
    else:
        parsed = r.get("sentence") is not None
        if parsed:
            parts.append("I understand.")
        else:
            parts.append("I can't parse that.")
        cleanup_session(s, r["session"])

    # 2. Which words do I recognise?
    known = _known_words(s, text)
    if known:
        words = ", ".join(f"{k['word']} ({k['pos']})" for k in known)
        parts.append(f"Words I know: {words}.")
    elif not parts:
        parts.append("I don't recognise any of those words.")

    # 3. If parsed, respond in kind
    if parsed:
        g = generate_sentence(s)
        if "error" not in g:
            parts.append(f"So: {g['text']}.")
            cleanup_session(s, g["session"])

    response = " ".join(parts)
    _log_turn(s, session_id, turn, text, response, parsed)
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
    print(f"SCP talk — session {session_id}")
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
