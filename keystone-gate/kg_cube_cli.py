"""kg cube and kg neighbour commands."""
from substrate import Substrate


def cmd_cube_new(args):
    from kg_agent import create_cube
    from kg_entities import claim_link_error, link_claim
    s = Substrate()
    links = {"subjects": args.subject or [], "entities": args.entity or [], "evidence": args.evidence or []}
    if error := claim_link_error(s, **links):
        s.close()
        print(f"error: {error}")
        return
    result = create_cube(s, args.content, source=args.source, tags=args.tag or None)
    made = link_claim(s, result["cube_id"], **links) if "error" not in result else []
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"Created: {result['cube_id']}")
    for type_, target in made:
        print(f"  {type_}: {target}")
    print(f"  content: {args.content!r}")
    if args.source:
        print(f"  source: {args.source}")
    print()
    print("Empty cube. Fill lenses with: kg cube fill <id> <lens> \"<content>\"")
    print(f"Lenses: {', '.join(__import__('kg_agent').LENSES)}")


def cmd_cube_fill(args):
    from kg_agent import fill_face, LENSES
    lens = args.lens.upper()
    if lens not in LENSES:
        print(f"error: invalid lens {lens!r}; must be one of {LENSES}")
        return
    s = Substrate()
    result = fill_face(s, args.cube_id, lens, args.content,
                       confidence=args.confidence, filled_by="human")
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"Filled: {result['face_id']}")
    print(f"  {lens}: {args.content!r}")


def cmd_cube_validate(args):
    from kg_agent import validate
    s = Substrate()
    result = validate(s, args.cube_id, args.by, note=args.note)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"Validated: {args.cube_id}")
    print(f"  validator: {args.by}")
    if args.note:
        print(f"  note: {args.note}")


def cmd_cube_attest(args):
    from kg_agent import attest
    s = Substrate()
    result = attest(s, args.cube_id, args.by, note=args.note)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"Attested: {args.cube_id}")
    print(f"  by: {args.by}")


def cmd_cube_review(args):
    from kg_review import review
    s = Substrate()
    try:
        seen = review(s, args.by, cube_id=args.cube_id, tag=args.tag)
    except (EOFError, KeyboardInterrupt):
        seen = None
    s.close()
    print("\nStopped. Everything answered so far is saved." if seen is None
          else f"\nReviewed {seen} cube(s).")


def cmd_cube_view(args):
    import webbrowser
    from kg_view import write_view
    s = Substrate()
    result = write_view(s)
    s.close()
    print(f"Wrote {result['cubes']} cubes to {result['path']}")
    if not args.no_open:
        webbrowser.open(result["path"].as_uri())


def cmd_cube_snapshot(args):
    from kg_public import write_snapshot
    s = Substrate()
    try:
        result = write_snapshot(s)
    finally:
        s.close()
    print(f"Wrote {result['cubes']} public cubes to {result['path']} ({result['left_out']} left out)")


def cmd_repo_add(args):
    from kg_repos import add_repo, fetch_repo
    s = Substrate()
    for name in args.repos:
        repo = fetch_repo(name)
        result = add_repo(s, repo)
        where = "private, local model only" if repo["private"] else "public"
        print(f"{name} ({where}): {len(result['cubes'])} cubes by {result['by']}")
        for why in result["tried"]:
            print(f"  passed over {why}")
    s.close()


def cmd_overlaps(args):
    from kg_overlaps import THRESHOLD, find_overlaps, load_decisions
    from kg_view import collect
    s = Substrate()
    cubes = collect(s)
    found = find_overlaps(cubes, load_decisions(s), minimum=THRESHOLD if args.min is None else args.min)
    s.close()
    words = {c["id"]: c["content"] for c in cubes}
    for o in found:
        shared = ", ".join(f"{x['lens']}: {x['term']}" for x in o["shared"])
        print(f"λ {o['lambda']:.2f}{' confirmed' if o['confirmed'] else ''}  {shared}")
        print(f"  {words[o['a']]}\n  {words[o['b']]}")
    print(f"{len(found)} overlaps")


def cmd_cube_draft(args):
    from kg_fill import cubes_with_blanks, draft_cube
    s = Substrate()
    cubes = [args.cube_id] if args.cube_id else cubes_with_blanks(s)
    if not cubes:
        print("Every face is filled or has a draft waiting.")
    for cube_id in cubes:
        result = draft_cube(s, cube_id)
        if result["drafted"]:
            print(f"{cube_id}: {', '.join(result['drafted'])} drafted by {result['by']}")
        elif result["tried"]:
            print(f"{cube_id}: no draft. {'; '.join(result['tried'])}")
    s.close()
    print("Check them with: kg cube serve --by <name>, or kg cube proposals")


def cmd_cube_notes(args):
    from kg_agent import list_cubes
    from kg_fill import suggest_note
    s = Substrate()
    made = 0
    for cube_id in [args.cube_id] if args.cube_id else [row["id"] for row in list_cubes(s)]:
        result = suggest_note(s, cube_id)
        made += bool(result["note"])
        if result["tried"] and not result["note"]:
            print(f"{cube_id}: no note. {'; '.join(result['tried'])}")
    s.close()
    print(f"Suggested {made} validation notes.")


def cmd_cube_password(args):
    import getpass
    from kg_lock import load_lock, make_lock, matches, save_lock
    lock = load_lock()
    if lock and not matches(getpass.getpass("Current password: "), lock):
        raise SystemExit("That is not the current password.")
    password = getpass.getpass("New password: ")
    if password != getpass.getpass("Same again: "):
        raise SystemExit("Those did not match. Nothing changed.")
    try:
        print(f"Saved to {save_lock(make_lock(password))}")
    except ValueError as e:
        raise SystemExit(f"Nothing changed: {e}.")


def cmd_cube_serve(args):
    import webbrowser
    from kg_lock import load_lock
    from kg_serve import make_server
    lock = load_lock()
    if not lock:
        raise SystemExit("Set an editing password first: python keystone-gate/kg cube password")
    server = make_server(args.by, lock, args.port, hosts=args.host)
    url = f"http://127.0.0.1:{server.server_address[1]}/"
    print(f"Cube Field at {url} (this machine only). Press Ctrl+C to stop.")
    if not args.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    server.server_close()


def cmd_cube_show(args):
    from kg_agent import show_cube, LENSES
    s = Substrate()
    data = show_cube(s, args.cube_id)
    if "error" in data:
        print(f"error: {data['error']}")
        return

    print(f"{data['cube_id']}")
    print(f"  content: {data['content']!r}")
    if data.get("source"):
        print(f"  source: {data['source']}")
    if data.get("tags"):
        print(f"  tags: {data['tags']}")
    print(f"  created: {data['created_at']}")
    if data.get("contradicts"):
        print(f"  contradicts: {data['contradicts']['other']} ({data['contradicts'].get('note') or 'no note'})")
    print()

    # Show evidence if linked
    from kg_evidence import get_evidence_for_claim
    ev_list = get_evidence_for_claim(s, args.cube_id)
    if ev_list:
        print("  Evidence:")
        for ev in ev_list:
            print(f"    [{ev['state'].get('evidence_kind')}] {ev['state'].get('title')} ({ev['id']})")
        print()

    print("  Faces:")
    for lens in LENSES:
        face = data["faces"].get(lens)
        if face:
            c = face.get("content", "")
            if len(c) > 60:
                c = c[:57] + "..."
            print(f"    [x] {lens:10} {c}")
        else:
            print(f"    [ ] {lens:10} (empty)")
    print()

    v = data.get("validation")
    if v:
        note = v.get("note") or ""
        if len(note) > 60:
            note = note[:57] + "..."
        label = "Validation STALE, was" if v.get("stale") else "Validated"
        print(f"  {label} by {v.get('validator')} at {v.get('validated_at')}")
        if v.get("stale"):
            print(f"    because: {v.get('stale_because')}")
        if note:
            print(f"    note: {note}")
    else:
        print("  Validation: (not yet validated)")
    print()

    a = data.get("attestation")
    if a:
        state = "RETRACTED, was attested" if a.get("retracted_because") else "Attested"
        print(f"  {state} by {a.get('source')} at {a.get('attested_at')}")
    comp = data["completeness"]
    print(f"  Completeness: {comp['score']:.2f} ({len(comp['filled_lenses'])}/5 lenses"
          f"{' + validated' if comp['validated'] else ''})")
    if comp["missing_lenses"]:
        print(f"  Missing lenses: {', '.join(comp['missing_lenses'])}")
    print(f"  Attestation eligible: {'YES' if comp['complete'] else 'NO'}")
    s.close()


def cmd_cube_list(args):
    from kg_agent import list_cubes
    s = Substrate()
    cubes = list_cubes(s)
    s.close()
    if not cubes:
        print("No cubes yet.")
        return
    for c in cubes:
        marker = "[complete]" if c["complete"] else "[incomplete]"
        print(f"  {c['id']:45} {c['score']:.2f} {marker}")


def cmd_cube_contradicts(args):
    from kg_agent import set_contradicts
    s = Substrate()
    result = set_contradicts(s, args.cube_id, args.other_id, note=args.note)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"{result['cube_id']} contradicts {result['contradicts']}")


def cmd_neighbour_link(args):
    from kg_agent import link_neighbour
    s = Substrate()
    result = link_neighbour(s, args.cube_a, args.cube_b, note=args.note)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    print(f"Linked: {result['cube_a']} <-> {result['cube_b']}")
    if args.note:
        print(f"  note: {args.note}")


def cmd_neighbour_list(args):
    from kg_agent import list_neighbours
    s = Substrate()
    result = list_neighbours(s, args.cube_id)
    s.close()
    if "error" in result:
        print(f"error: {result['error']}")
        return
    if not result["neighbours"]:
        print(f"{result['cube']} has no neighbours.")
    else:
        print(f"{result['cube']} neighbours:")
        for n in result["neighbours"]:
            print(f"  -> {n}")


def cmd_cube_proposals(args):
    from kg_agent import list_proposals
    s = Substrate()
    props = list_proposals(s, cube_id=args.cube_id, status=args.status)
    s.close()
    if not props:
        scope = f" (cube {args.cube_id})" if args.cube_id else ""
        print(f"No {args.status} proposals.{scope}")
        return
    for p in props:
        ptype = p.get("proposal_type", "?")
        if ptype == "face":
            content = p.get("content", "")
            if len(content) > 60:
                content = content[:57] + "..."
            print(f"  {p['id']}")
            print(f"    face    [{p['lens']}] {content}")
        elif ptype == "neighbour":
            print(f"  {p['id']}")
            print(f"    neigh   -> {p.get('other_cube_id')}")
        print(f"    by      {p.get('proposed_by', '?')}")
        if p.get("rationale"):
            r = p["rationale"]
            if len(r) > 70:
                r = r[:67] + "..."
            print(f"    reason  {r}")
        print(f"    status  {p.get('status')}")
        print()


def cmd_cube_accept(args):
    from kg_agent import accept_proposal
    s = Substrate()
    r = accept_proposal(s, args.proposal_id, accepted_by=args.by, word=args.word, reverse=args.reverse)
    s.close()
    if "error" in r:
        print(f"error: {r['error']}")
        return
    print(f"Accepted: {r['proposal_id']}")


def cmd_cube_reject(args):
    from kg_agent import reject_proposal
    s = Substrate()
    r = reject_proposal(s, args.proposal_id, rejected_by=args.by, reason=args.reason)
    s.close()
    if "error" in r:
        print(f"error: {r['error']}")
        return
    print(f"Rejected: {r['proposal_id']}")
    if args.reason:
        print(f"  reason: {args.reason}")


def cmd_cube_tick(args):
    from kg_agent import list_cubes
    from kg_rules import run_rules
    s = Substrate()
    cubes = list_cubes(s)
    if args.cube_id:
        cubes = [c for c in cubes if c["id"] == args.cube_id]
    if not cubes:
        print("No cubes to tick.")
        s.close()
        return

    total_new = total_updated = total_skipped = 0
    for c in cubes:
        results = run_rules(s, c["id"])
        created = [r for r in results if r.get("status") == "created"]
        updated = [r for r in results if r.get("status") == "updated"]
        skipped = [r for r in results if r.get("skipped")]
        errored = [r for r in results if "error" in r]
        total_new += len(created)
        total_updated += len(updated)
        total_skipped += len(skipped)
        if not (created or updated or errored):
            continue
        print(f"{c['id']} (completeness {c['score']:.2f})")
        for r in created:
            print(f"  [new] {r.get('rule','?')} -> {r.get('lens') or r.get('other_cube_id')}")
        for r in updated:
            print(f"  [upd] {r.get('rule','?')} -> {r.get('lens') or r.get('other_cube_id')}")
        for r in errored:
            print(f"  [err] {r.get('rule','?')}: {r['error']}")
        print()

    s.close()
    print(f"Tick complete: {total_new} new, {total_updated} updated, {total_skipped} skipped")
