"""One-shot: read current capsule state, rewrite seed scripts to match."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import json
from store.substrate import Substrate


def fmt_lexicon(lexicon):
    lines = ['"""Seed lexical entries. Create-only (capsules authoritative)."""',
             'from store.substrate import Substrate', '',
             'LEXICON = {']
    for word, (pos, features) in sorted(lexicon.items()):
        lines.append(f'    {word!r}: ({pos!r}, {features!r}),')
    lines.append('}')
    return '\n'.join(lines)


def fmt_grammar(grammar):
    lines = ['"""Seed grammar rules. Create-only (capsules authoritative)."""',
             'from store.substrate import Substrate', '',
             'GRAMMAR = [']
    for rule_id, state in grammar:
        cond = state.get("condition", {})
        eff = state.get("effect", {})
        lines.append(f'    {{"id": {rule_id!r},')
        lines.append( '     "state": {')
        lines.append( '         "condition": {')
        lines.append(f'             "type": {cond.get("type", "sequence")!r},')
        if "number_agree" in cond:
            lines.append(f'             "number_agree": {cond["number_agree"]},')
        lines.append( '             "match": [')
        for m in cond.get("match", []):
            parts = []
            if "foundation" in m:
                parts.append(f'"foundation": {m["foundation"]!r}')
            if "state" in m:
                parts.append(f'"state": {m["state"]!r}')
            if "features" in m:
                parts.append(f'"features": {m["features"]!r}')
            lines.append(f'                 {{{", ".join(parts)}}},')
        lines.append( '             ],')
        lines.append( '         },')
        lines.append( '         "effect": {')
        lines.append(f'             "foundation": {eff.get("foundation")!r},')
        if "state" in eff:
            lines.append(f'             "state": {eff["state"]!r},')
        lines.append( '         },')
        lines.append( '     }},')
    lines.append(']')
    return '\n'.join(lines)


def extract_block(src, name):
    """Extract everything from `name = ` to the matching close brace/bracket."""
    idx = src.find(f"{name} = ")
    if idx < 0:
        raise ValueError(f"{name} not found")
    start = src.find('{', idx)
    if start < 0:
        start = src.find('[', idx)
    opener = src[start]
    closer = '}' if opener == '{' else ']'
    depth = 0
    for i in range(start, len(src)):
        if src[i] == opener:
            depth += 1
        elif src[i] == closer:
            depth -= 1
            if depth == 0:
                return src[idx:i+1]
    raise ValueError("unbalanced block")


def extract_main(src):
    idx = src.find("def main():")
    if idx < 0:
        raise ValueError("main() not found")
    return src[idx:]


def main():
    s = Substrate()

    # Read lexicon from DB
    lexicon = {}
    for r in s.conn.execute("""
        SELECT state_json FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'lexical-entry'
        ORDER BY id
    """):
        st = json.loads(r["state_json"])
        lexicon[st["text"]] = (st["pos"], st.get("features", {}))

    # Read grammar from DB
    grammar = []
    for r in s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation = 'foundation:rule'
          AND json_extract(state_json, '$.condition.type') = 'sequence'
        ORDER BY id
    """):
        grammar.append((r["id"], json.loads(r["state_json"])))

    s.close()

    print(f"capsules found: {len(lexicon)} lexical, {len(grammar)} grammar")

    # Preserve the original main() bodies, only swap the data block
    import os
    os.chdir(Path(__file__).resolve().parent)
    if not os.path.exists("seed_lexicon.py.bak"):
        os.rename("seed_lexicon.py", "seed_lexicon.py.bak")
        os.rename("seed_grammar.py", "seed_grammar.py.bak")

    lex_old = open("seed_lexicon.py.bak").read()
    lex_new = fmt_lexicon(lexicon) + "\n\n\n" + extract_main(lex_old) + "\n"
    open("seed_lexicon.py", "w").write(lex_new)

    gram_old = open("seed_grammar.py.bak").read()
    gram_new = fmt_grammar(grammar) + "\n\n\n" + extract_main(gram_old) + "\n"
    open("seed_grammar.py", "w").write(gram_new)

    print(f"wrote seed_lexicon.py ({len(lexicon)} entries)")
    print(f"wrote seed_grammar.py ({len(grammar)} rules)")


if __name__ == "__main__":
    main()
