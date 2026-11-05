"""kg cube relate and kg cube contradicts: link one claim to another with a
connecting word. The words and links themselves are in src/store/claim_links.py."""
from store.claim_links import relate


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
