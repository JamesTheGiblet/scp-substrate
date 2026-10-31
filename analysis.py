"""Gap analysis: where does the corpus fail to parse?

Two failure modes reported:
  1. Gap — contiguous tokens that don't reduce to anything.
  2. Composition gap — everything covers, but no top-level sentence.
"""
import json
import re

from substrate import Substrate
from parse import parse_sentence, cleanup_session, lookup_pos


def find_gap_spans(s, text):
    """Parse text, return a structured diagnosis if it fails to reach S."""
    words = re.findall(r"[a-zA-Z]+", text.lower())
    pos_seq = []
    for w in words:
        pos = lookup_pos(s, w)
        if pos is None:
            return {"error": f"unknown word: {w}", "n": len(words), "pos_so_far": pos_seq}
        pos_seq.append(pos)

    r = parse_sentence(s, text)
    if "error" in r:
        return {"error": r["error"], "n": len(words), "pos": pos_seq}

    session = r["session"]
    if r["sentence"]:
        cleanup_session(s, session)
        return {"ok": True, "n": len(words), "pos": pos_seq}

    # Parse failed. Find every phrase/sentence capsule in the session.
    n = len(words)
    rows = s.conn.execute("""
        SELECT id, foundation, state_json FROM capsules
        WHERE id LIKE ? AND (foundation='foundation:phrase' OR foundation='foundation:sentence')
    """, (f"parse/{session}/%",)).fetchall()

    spans = []
    for row in rows:
        st = json.loads(row["state_json"])
        a, b = st.get("start"), st.get("end")
        if a is None or b is None:
            continue
        spans.append({"a": a, "b": b,
                      "foundation": row["foundation"].replace("foundation:", "")})

    # Maximal: not strictly contained in another span
    maximal = [
        sp for sp in spans
        if not any(
            (other["a"], other["b"]) != (sp["a"], sp["b"])
            and other["a"] <= sp["a"] and sp["b"] <= other["b"]
            for other in spans
        )
    ]
    maximal.sort(key=lambda x: x["a"])

    # Gaps: token indices not covered by any maximal span
    covered = set()
    for sp in maximal:
        covered.update(range(sp["a"], sp["b"] + 1))

    gaps = []
    i = 0
    while i < n:
        if i not in covered:
            j = i
            while j < n and j not in covered:
                j += 1
            gaps.append((i, j - 1, pos_seq[i:j]))
            i = j
        else:
            i += 1

    cleanup_session(s, session)

    return {
        "ok": False,
        "n": n,
        "pos": pos_seq,
        "maximal": [(sp["a"], sp["b"], sp["foundation"]) for sp in maximal],
        "gaps": gaps,
    }


def propose_rule_for_gap(gap):
    """Proposal for a raw token gap: 'a sequence rule matching this POS pattern.'"""
    a, b, pos_seq = gap
    return {
        "match": [{"foundation": "token", "state": {"pos": p}} for p in pos_seq],
        "note": "category unknown — caller must choose (NP, VP, PP, ...)",
    }


def analyse_corpus(s, corpus):
    """Run gap analysis over a corpus. Prints a report. Returns summary dict."""
    ok, failed_unknown, failed_gap = 0, 0, 0
    for item in corpus:
        text = item["text"] if isinstance(item, dict) else item
        r = find_gap_spans(s, text)
        if "error" in r:
            print(f"  [error] {text!r}")
            print(f"          {r['error']}")
            failed_unknown += 1
            continue
        if r["ok"]:
            ok += 1
            continue
        failed_gap += 1
        print(f"  [gap] {text!r}")
        print(f"        tokens: {' '.join(r['pos'])}")
        if r["gaps"]:
            for g in r["gaps"]:
                a, b, seq = g
                print(f"        unreduced tokens [{a}-{b}]: {' '.join(seq)}")
                proposal = propose_rule_for_gap(g)
                match_str = " ".join(p["state"]["pos"] for p in proposal["match"])
                print(f"        proposal: rule matching [{match_str}] → ?")
        if r["maximal"] and not r["gaps"]:
            names = [f"[{a}-{b}] {kind}" for a, b, kind in r["maximal"]]
            print(f"        all tokens covered, but no full S")
            print(f"        top-level spans: {', '.join(names)}")
            print(f"        diagnosis: no rule composes these into a sentence")
        print()

    print(f"summary: {ok} ok, {failed_gap} gaps, {failed_unknown} errors")
    return {"ok": ok, "gaps": failed_gap, "errors": failed_unknown}
