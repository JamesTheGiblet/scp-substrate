"""kg evidence commands: add a piece of evidence, cite it from claims, and
list what each claim rests on. The evidence itself is in src/store/evidence.py.
Imported by kg."""
from store.evidence import KINDS, add_evidence, cite, evidence_of
from store.substrate import Substrate


def cmd_evidence_list(args):
    s = Substrate()
    rows = s.by_foundation("foundation:evidence")
    for e in sorted(rows, key=lambda e: e["id"]):
        n = len(s.links_to(e["id"], "derived-from"))
        print(f"  {e['id']:50} {e['state'].get('kind'):12} {n:3} claim(s)  {e['state'].get('title', '')}")
    s.close()
    if not rows:
        print("No evidence yet.")


def cmd_evidence_show(args):
    s = Substrate()
    row = s.get(args.id)
    if not row:
        s.close()
        raise SystemExit(f"error: {args.id} not found")
    print(row["id"])
    for k in ("kind", "title", "url", "path", "repo", "note", "by", "added_at"):
        if row["state"].get(k):
            print(f"  {k}: {row['state'][k]}")
    claims = sorted(l["source"] for l in s.links_to(args.id, "derived-from"))
    print(f"  backs {len(claims)} claim(s):")
    for c in claims:
        print(f"    {c}")
    s.close()


def cmd_evidence_add(args):
    s = Substrate()
    r = add_evidence(s, args.slug, args.kind, args.title, args.by,
                     url=args.url, path=args.path, repo=args.repo, note=args.note)
    s.close()
    if "error" in r:
        raise SystemExit(f"error: {r['error']}")
    print(f"{'Created' if r['status'] == 'created' else 'Already there'}: {r['id']}")


def cmd_evidence_cite(args):
    s = Substrate()
    for eid in args.evidence:
        r = cite(s, args.claim, eid)
        print(f"error: {r['error']}" if "error" in r else f"{r['claim']} is derived from {r['evidence']}")
    s.close()


def cmd_evidence_of(args):
    s = Substrate()
    found = evidence_of(s, args.claim)
    s.close()
    if not found:
        print(f"{args.claim} rests on no evidence: your word only.")
    for e in found:
        print(f"  {e['id']:50} {e['kind']:16} +{e['weight']:.2f}  {e['title']}")


def add_evidence_parser(sub):
    sp = sub.add_parser("evidence", help="evidence: what claims rest on")
    sp_sub = sp.add_subparsers(dest="evidence_cmd", required=True)

    p = sp_sub.add_parser("list", help="every piece of evidence and how many claims it backs")
    p.set_defaults(func=cmd_evidence_list)

    p = sp_sub.add_parser("show", help="one piece of evidence and the claims it backs")
    p.add_argument("id")
    p.set_defaults(func=cmd_evidence_show)

    p = sp_sub.add_parser("add", help="add a piece of evidence")
    p.add_argument("slug", help="becomes evidence/<slug>")
    p.add_argument("--kind", required=True, choices=list(KINDS))
    p.add_argument("--title", required=True)
    p.add_argument("--url")
    p.add_argument("--path")
    p.add_argument("--repo")
    p.add_argument("--note")
    p.add_argument("--by", default="james")
    p.set_defaults(func=cmd_evidence_add)

    p = sp_sub.add_parser("cite", help="say a claim is derived from evidence")
    p.add_argument("claim")
    p.add_argument("evidence", nargs="+")
    p.set_defaults(func=cmd_evidence_cite)

    p = sp_sub.add_parser("of", help="what one claim rests on")
    p.add_argument("claim")
    p.set_defaults(func=cmd_evidence_of)
