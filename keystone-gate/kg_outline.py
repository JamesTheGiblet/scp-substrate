"""Build an entity, its subjects and its claims from a plain-text outline.

    # entity Replicant
    kind: project
    part-of: project/forge-stack

    ## subject Leighton Weight
    uses: yes

    ### claim Each agent's λ is computed from a ledger of decaying events.
    source: Replicant README
    from: repo/jamesthegiblet/replicant
    tags: needs-check
    FACT: The README says λ is computed on read, never stored.

Lines under a heading are `key: value`. Under an entity, a key from
RELATIONS links the entity to that id; `building: james` links the other way.
Under a subject, `uses: yes` says the entity uses it, and `kind:` names its
kind. A claim before any subject is about the entity as a whole. A lens line
is offered as a draft for the person to confirm, never as a filled face.
Imported by kg. See docs/VOCABULARY.md.
"""
import re

from substrate import Substrate

HEAD = re.compile(r"^(#{1,3})\s*(entity|subject|claim)\b[:\s]*(.*)$", re.I)
PAIR = re.compile(r"^([A-Za-z-]+):\s*(.*)$")


def parse(text):
    """The outline as [{name, kind, keys, subjects: [{name, keys, claims}], claims}]."""
    from kg_cube import LENSES
    entities, entity, subject, claim = [], None, None, None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("<!--"):
            continue
        head = HEAD.match(line)
        if head:
            what, name = head.group(2).lower(), head.group(3).strip()
            if not name:
                raise ValueError(f"line {n}: a {what} needs a name")
            if what == "entity":
                entity, subject, claim = {"name": name, "keys": {}, "subjects": [], "claims": []}, None, None
                entities.append(entity)
            elif entity is None:
                raise ValueError(f"line {n}: a {what} must come after an # entity")
            elif what == "subject":
                subject, claim = {"name": name, "keys": {}, "claims": []}, None
                entity["subjects"].append(subject)
            else:
                claim = {"text": name, "keys": {}, "lenses": {}}
                (subject or entity)["claims"].append(claim)
            continue
        pair = PAIR.match(line)
        if not pair or entity is None:
            raise ValueError(f"line {n}: expected a heading or key: value, got {line[:60]!r}")
        key, value = pair.group(1), pair.group(2).strip()
        if claim is not None and key.upper() in LENSES:
            claim["lenses"][key.upper()] = value
        else:
            (claim or subject or entity)["keys"][key.lower()] = value
    return entities


def plan(s, entities):
    """What importing would do: one line per thing, saying made or kept."""
    from kg_entities import entity_id
    from kg_subjects import _slug
    lines = []
    for e in entities:
        eid = e["keys"].get("id") or entity_id(e["name"], e["keys"].get("kind", "entity"))
        lines.append(f"{'keep' if s.get(eid) else 'make'} entity {eid}")
        for sub in e["subjects"]:
            sid = f"subject/{_slug(sub['name'])}"
            lines.append(f"  {'keep' if s.get(sid) else 'make'} subject {sid}")
            lines += [f"    claim: {c['text'][:70]}" for c in sub["claims"]]
        lines += [f"  claim about the whole: {c['text'][:70]}" for c in e["claims"]]
    return lines


def problems(s, entities):
    """Every id the outline points at that isn't in the store, checked before
    anything is written, so an outline goes in whole or not at all."""
    from kg_entities import RELATIONS
    out = []
    for e in entities:
        for key, value in e["keys"].items():
            if key in RELATIONS:
                out += [f"{e['name']}: {key} {v} not found" for v in _ids(value) if not s.get(v)]
        for c in e["claims"] + [c for sub in e["subjects"] for c in sub["claims"]]:
            out += [f"{c['text'][:40]!r}: evidence {v} not found" for v in _ids(c["keys"].get("from", ""))
                    if not s.get(v)]
    return out


def _ids(value):
    return [v.strip() for v in value.split(",") if v.strip()]


def apply(s, entities, by):
    """Make what the outline names. Existing entities and subjects are reused,
    and a claim whose id exists is skipped. Returns what was made."""
    from kg_entities import RELATIONS, add_entity, entity_id, relate
    from kg_proposals import propose_face
    from kg_subjects import _slug, accept_subject, propose_subject
    if missing := problems(s, entities):
        raise ValueError("; ".join(missing))
    made = {"entities": [], "subjects": [], "claims": [], "drafts": 0, "skipped": []}
    for e in entities:
        kind = e["keys"].get("kind", "entity")
        eid = e["keys"].get("id") or entity_id(e["name"], kind)
        if not s.get(eid):
            add_entity(s, e["name"], kind, by, **{k: v for k, v in e["keys"].items()
                                                  if k not in RELATIONS and k not in ("kind", "id")})
            made["entities"].append(eid)
        for key, value in e["keys"].items():
            if key in RELATIONS:
                for other in _ids(value):
                    relate(s, other, key, eid) if key == "building" else relate(s, eid, key, other)
        groups = [(None, e["claims"])]
        for sub in e["subjects"]:
            sid = f"subject/{_slug(sub['name'])}"
            if not s.get(sid):
                pid = propose_subject(s, sub["name"], [], by, kind=sub["keys"].get("kind"),
                                      rationale=f"From an outline imported by {by}")["proposal_id"]
                accept_subject(s, pid, by)
                made["subjects"].append(sid)
            if sub["keys"].get("uses", "").lower() in ("yes", "true"):
                relate(s, eid, "uses", sid)
            groups.append((sid, sub["claims"]))
        for sid, claims in groups:
            for c in claims:
                made_claim = _claim(s, c, eid, sid, by, made)
                if made_claim:
                    for lens, text in c["lenses"].items():
                        propose_face(s, made_claim, lens, text, f"outline:{by}", rationale="from the outline")
                        made["drafts"] += 1
    return made


def _claim(s, c, eid, sid, by, made):
    from kg_agent import create_cube
    from kg_entities import claim_link_error, link_claim
    keys = c["keys"]
    cid = keys.get("id") or f"cube/{'-'.join(re.findall(r'[a-z0-9]+', c['text'].lower())[:8])}"
    if s.get(cid):
        made["skipped"].append(cid)
        return None
    evidence = _ids(keys.get("from", ""))
    if error := claim_link_error(s, subjects=[sid] if sid else [], entities=[eid], evidence=evidence):
        raise ValueError(f"{c['text'][:50]!r}: {error}")
    tags = _ids(keys.get("tags", ""))
    create_cube(s, c["text"], source=keys.get("source") or f"From an outline imported by {by}",
                tags=tags, cube_id=cid)
    link_claim(s, cid, subjects=[sid] if sid else [], entities=[eid], evidence=evidence)
    made["claims"].append(cid)
    return cid


def cmd_import(args):
    with open(args.path, encoding="utf-8") as f:
        try:
            entities = parse(f.read())
        except ValueError as e:
            print(f"error: {e}")
            return
    s = Substrate()
    try:
        if not args.write:
            print("\n".join(plan(s, entities) + [f"problem: {p}" for p in problems(s, entities)]))
            print("\nNothing written. Run again with --write to make these.")
            return
        made = apply(s, entities, args.by)
    except ValueError as e:
        print(f"error: {e}")
        return
    finally:
        s.close()
    print(f"made {len(made['entities'])} entities, {len(made['subjects'])} subjects, {len(made['claims'])} claims "
          f"and {made['drafts']} lens drafts; skipped {len(made['skipped'])} claims that exist")


def add_outline_parser(sub):
    p = sub.add_parser("import", help="build an entity, its subjects and claims from an outline file")
    p.add_argument("path")
    p.add_argument("--by", default="james")
    p.add_argument("--write", action="store_true", help="make them; without it, only show what would be made")
    p.set_defaults(func=cmd_import)
