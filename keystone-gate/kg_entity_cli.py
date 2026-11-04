"""kg entity commands. Imported by kg."""
from store.substrate import Substrate


def cmd_entity_list(args):
    from kg_entities import list_entities
    s = Substrate()
    rows = list_entities(s)
    s.close()
    if not rows:
        print("No entities yet.")
    for e in rows:
        print(f"  {e['id']:45} {e.get('kind') or '-':12} {e.get('name') or ''}")


def cmd_entity_show(args):
    s = Substrate()
    row = s.get(args.id)
    if not row:
        print(f"error: {args.id} not found")
        s.close()
        return
    print(f"{row['id']}  ({row['foundation'].replace('foundation:', '')})")
    for k in ("name", "kind", "status", "role"):
        if row["state"].get(k):
            print(f"  {k}: {row['state'][k]}")
    for l in sorted(row["links"], key=lambda l: (l["type"], l["target"])):
        print(f"  {l['type']:14} -> {l['target']}")
    for l in sorted(s.links_to(args.id), key=lambda l: (l["type"], l["source"])):
        print(f"  {l['type']:14} <- {l['source']}")
    s.close()


def cmd_entity_add(args):
    from kg_entities import add_entity
    s = Substrate()
    r = add_entity(s, args.name, args.kind, args.by)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"Created: {r['id']}")


def cmd_entity_link(args):
    from kg_entities import relate
    s = Substrate()
    r = relate(s, args.source, args.relation, args.target)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['source']} {r['relation']} {r['target']}")


def cmd_entity_proposals(args):
    from kg_entities import list_sort_proposals
    s = Substrate()
    rows = list_sort_proposals(s, status=args.status)
    s.close()
    if not rows:
        print(f"No {args.status} sort proposals.")
    for p in rows:
        what = {"entity": f"entity ({p.get('entity_kind')})", "subject": "subject",
                "merge": f"merge into {p.get('into')}", "drop": "drop",
                "describe": f"document describing {p.get('into')}"}[p["action"]]
        moved = f", as {p['new_id']}" if p.get("new_id") and p["new_id"] != p["target"] else ""
        print(f"\n{p['id']}  [{p['status']}]\n  {p['target']} -> {what}{moved}")
        if p.get("rationale"):
            print(f"  why: {p['rationale']}")


def cmd_entity_accept(args):
    from kg_entities import accept_sort
    s = Substrate()
    r = accept_sort(s, args.proposal_id, args.by, action=args.as_, entity_kind=args.kind,
                    new_id=args.id, name=args.name, into=args.into)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['action']}: {r['id']}")


def cmd_entity_reject(args):
    from kg_entities import reject_sort
    s = Substrate()
    r = reject_sort(s, args.proposal_id, args.by, reason=args.reason)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['proposal_id']} rejected")


def add_entity_parser(sub):
    from kg_entities import ACTIONS, RELATIONS
    sp = sub.add_parser("entity", help="entities: things that exist, and sorting old capsules")
    sp_sub = sp.add_subparsers(dest="entity_cmd", required=True)

    p = sp_sub.add_parser("list", help="list entities")
    p.set_defaults(func=cmd_entity_list)

    p = sp_sub.add_parser("show", help="an entity and its links")
    p.add_argument("id")
    p.set_defaults(func=cmd_entity_show)

    p = sp_sub.add_parser("add", help="create an entity")
    p.add_argument("name")
    p.add_argument("--kind", required=True, help="person, project, robot, organisation, place and so on")
    p.add_argument("--by", required=True)
    p.set_defaults(func=cmd_entity_add)

    p = sp_sub.add_parser("link", help="link an entity to an entity or subject")
    p.add_argument("source")
    p.add_argument("relation", choices=RELATIONS)
    p.add_argument("target")
    p.set_defaults(func=cmd_entity_link)

    p = sp_sub.add_parser("proposals", help="list sort proposals for old capsules")
    p.add_argument("--status", default="pending", choices=["pending", "accepted", "rejected", "any"])
    p.set_defaults(func=cmd_entity_proposals)

    p = sp_sub.add_parser("accept", help="apply a sort proposal, optionally corrected")
    p.add_argument("proposal_id")
    p.add_argument("--by", required=True)
    p.add_argument("--as", dest="as_", choices=ACTIONS, help="a different action")
    p.add_argument("--kind", help="a different entity or subject kind")
    p.add_argument("--id", help="a different new id")
    p.add_argument("--name", help="a different name")
    p.add_argument("--into", help="for merge or describe, the capsule to fold into")
    p.set_defaults(func=cmd_entity_accept)

    p = sp_sub.add_parser("reject", help="reject a sort proposal, leaving the capsule as it is")
    p.add_argument("proposal_id")
    p.add_argument("--by", required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_entity_reject)
