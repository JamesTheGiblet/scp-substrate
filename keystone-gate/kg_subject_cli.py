"""kg subject commands. Imported by kg."""
from store.substrate import Substrate


def _members(text):
    return [m if m.startswith("cube/") else f"cube/{m}" for m in text.split(",") if m.strip()] if text else None


def cmd_subject_proposals(args):
    from kg_subjects import list_subject_proposals
    s = Substrate()
    rows = list_subject_proposals(s, status=args.status)
    s.close()
    if not rows:
        print(f"No {args.status} subject proposals.")
    for p in rows:
        print(f"\n{p['id']}  [{p['status']}]  {p['name']}" + (f"  ({p['subject_kind']})" if p.get("subject_kind") else ""))
        if p.get("rationale"):
            print(f"  why: {p['rationale']}")
        for m in p["members"]:
            print(f"    {m}")


def cmd_subject_accept(args):
    from kg_subjects import accept_subject
    s = Substrate()
    r = accept_subject(s, args.proposal_id, args.by, name=args.name, members=_members(args.only))
    s.close()
    if "error" in r:
        print(f"error: {r['error']}")
        return
    print(f"{r['subject_id']}: {len(r['members'])} claims")


def cmd_subject_reject(args):
    from kg_subjects import reject_subject
    s = Substrate()
    r = reject_subject(s, args.proposal_id, args.by, reason=args.reason)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['proposal_id']} rejected")


def cmd_subject_add(args):
    from kg_subjects import add_claim
    s = Substrate()
    r = add_claim(s, _members(args.cube_id)[0], args.subject_id)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['cube_id']} is about {r['subject_id']}")


def cmd_subject_list(args):
    from kg_subjects import list_subjects
    s = Substrate()
    rows = list_subjects(s)
    s.close()
    if not rows:
        print("No subjects yet. See kg subject proposals.")
    for subj in rows:
        kinds = "".join(f"  is a {b}" for b in subj.get("is_a", []))
        print(f"\n{subj['id']}  {subj['name']}  ({len(subj['claims'])} claims){kinds}")
        for c in subj["claims"]:
            print(f"    {c}")


def cmd_subject_is_a(args):
    from kg_subjects import kind_of
    s = Substrate()
    r = kind_of(s, args.subject_id, args.broader, args.by)
    s.close()
    print(f"error: {r['error']}" if "error" in r else f"{r['subject']} is a {r['is_a']}")


def add_subject_parser(sub):
    sp = sub.add_parser("subject", help="subjects: what claims are about")
    sp_sub = sp.add_subparsers(dest="subject_cmd", required=True)

    p = sp_sub.add_parser("proposals", help="list subject proposals")
    p.add_argument("--status", default="pending", choices=["pending", "accepted", "rejected", "any"])
    p.set_defaults(func=cmd_subject_proposals)

    p = sp_sub.add_parser("accept", help="create the subject and link its claims")
    p.add_argument("proposal_id")
    p.add_argument("--by", required=True)
    p.add_argument("--name", help="a different name for the subject")
    p.add_argument("--only", help="comma-separated claims to keep, from the proposal")
    p.set_defaults(func=cmd_subject_accept)

    p = sp_sub.add_parser("reject", help="reject a subject proposal")
    p.add_argument("proposal_id")
    p.add_argument("--by", required=True)
    p.add_argument("--reason")
    p.set_defaults(func=cmd_subject_reject)

    p = sp_sub.add_parser("add", help="say a claim is about an existing subject")
    p.add_argument("cube_id")
    p.add_argument("subject_id")
    p.set_defaults(func=cmd_subject_add)

    p = sp_sub.add_parser("list", help="list subjects and their claims")
    p.set_defaults(func=cmd_subject_list)

    p = sp_sub.add_parser("is-a", help="say one subject is a kind of another: subject/mg90s subject/servos")
    p.add_argument("subject_id")
    p.add_argument("broader", help="the broader subject; a name makes it if it doesn't exist")
    p.add_argument("--by", default="james")
    p.set_defaults(func=cmd_subject_is_a)
