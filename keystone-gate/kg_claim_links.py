"""kg cube relate and kg cube contradicts: link one claim to another with a
connecting word. The words and links themselves are in src/store/claim_links.py.

kg cube words: your own words on a claim, for linking. Tags say where a claim
came from (needs-check, seller); words say what it is about in your terms
(stall, brownout, current-draw). Two claims sharing a word get a suggested
link, whatever their subjects, and kg ask matches the words too.
"""
import re

from store.claim_links import relate


def _word(w):
    return "-".join(re.findall(r"[a-z0-9]+", w.lower()))


def set_words(s, cube_id, add=(), remove=(), by="james"):
    """Add and remove a claim's words, then suggest links to claims sharing one."""
    from kg_cube import _update_state
    from kg_rules import run_rules
    row = s.get(cube_id)
    if not row or row["foundation"] != "foundation:cube":
        return {"error": f"claim {cube_id} not found"}
    words = (set(row["state"].get("words") or []) | {_word(w) for w in add}) - {_word(w) for w in remove}
    words = sorted(w for w in words if w)
    if words != (row["state"].get("words") or []):
        _update_state(s, cube_id, {**row["state"], "words": words})
    made = [r for r in run_rules(s, cube_id, only_rules=["neighbour_by_words"]) if r.get("status") == "created"]
    return {"cube_id": cube_id, "words": words, "suggested": len(made)}


def cmd_cube_words(args):
    from store.substrate import Substrate
    s = Substrate()
    result = set_words(s, args.cube_id, add=args.words, remove=args.remove or (), by=args.by)
    s.close()
    if "error" in result:
        raise SystemExit(f"error: {result['error']}")
    print(f"{result['cube_id']}: {', '.join(result['words']) or 'no words yet'}")
    if result["suggested"]:
        print(f"  {result['suggested']} new suggested link(s); see kg cube proposals {result['cube_id']}")


def cmd_cube_contradicts(args):
    from kg_agent import set_contradicts
    from store.substrate import Substrate
    s = Substrate()
    result = set_contradicts(s, args.cube_id, args.other_id, note=args.note)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"{result['cube_id']} contradicts {result['contradicts']}")


def cmd_cube_relate(args):
    from store.substrate import Substrate
    s = Substrate()
    result = relate(s, args.cube_id, args.word, args.other_id, args.by, note=args.note)
    s.close()
    if "error" in result:
        raise SystemExit(f"error: {result['error']}")
    print(f"{result['from']} {result['word']} {result['to']}")
