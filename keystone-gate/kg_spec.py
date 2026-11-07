"""Spec a project from what the store knows, and say plainly what it doesn't.

    kg spec "Desk Arm" --uses "servos, m5stick, battery, camera"

Each word in --uses, and any subject or entity the brief names, is matched to
subjects and entities by name or alias. A match reaches what an ask would:
a subject's narrower and broader kinds, an entity's parts and what it uses.
The claims on those come back in two groups, validated and not yet, each
saying which other project it came from. Anything with no claims behind it
is a question, never an answer. Claims that protect or limit one in the
spec come too, under Safety, though nothing named them. No model is asked, so nothing is made up.

With --out, the questions go on a sheet: write a claim on a row and import
it, and the project and its subjects are made. A row left blank is skipped.
"""
import csv
import io
import re

from answer.walk_cubes import _about, _named, _reach, _stem, _stems, _status
from kg_cube import LENSES
from store.claim_links import relations
from store.kinds import broader

SHEET = ["entity", "entity_kind", "subject", "uses", "question", "claim", "tags", *LENSES]


def _key(word):
    word = re.sub(r"ies$", "y", word)
    return _stem(word)


def _words(text):
    return {_key(w) for w in re.findall(r"[a-z0-9][a-z0-9]+", text.lower())}


def _near(a, b):
    """One word starts the other, so m5stick meets m5stickc and servo servos."""
    return a == b or (min(len(a), len(b)) >= 4 and (a.startswith(b) or b.startswith(a)))


def _covers(these, those):
    return all(any(_near(a, b) for b in those) for a in these)


def matches(s, term):
    """Every subject and entity a term could mean, as {id: (name, close)}.
    close means every word of a name or alias is in the term, so "servo"
    is close to Servos; the others only hold the term's words, as "servo
    driver" does, and are worth offering but not choosing for you."""
    from answer.walk_cubes import THINGS, _names
    words, found = _words(term), {}
    for foundation in THINGS:
        for row in s.by_foundation(foundation):
            if row["id"] == "person":
                continue
            fits = [(_covers(have, words), _covers(words, have))
                    for have in map(_words, _names(row["state"])) if words and have]
            if any(close or loose for close, loose in fits):
                found[row["id"]] = (row["state"].get("name", row["id"]), any(c for c, _ in fits))
    return found


def _match(s, term):
    """What a term names: the close matches if there are any, else every match."""
    found = matches(s, term)
    close = {i: n for i, (n, c) in found.items() if c}
    return close or {i: n for i, (n, _) in found.items()}


def _name(s, tid):
    row = s.get(tid)
    return (row["state"].get("name") if row else None) or tid


def spec(s, name, uses=(), brief="", picked=None):
    """{entity, exists, terms: [(term, {id: name})], known, unvalidated, safety, unknown}.
    known and unvalidated are [(claim_id, text, about, from)]; unknown is
    [(term, question)]. picked maps a term to the ids you chose for it, when
    it matched more than one thing or should match nothing."""
    from kg_entities import entity_id
    eid = entity_id(name, "project")
    exists = next((r["id"] for r in (s.get(eid), s.get(entity_id(name, "entity"))) if r), None)
    picked = picked or {}
    terms = [(t, {i: _name(s, i) for i in picked[t] if s.get(i)} if t in picked else _match(s, t))
             for t in uses if t.strip()]
    named = _named(s, _stems(brief)) if brief else {}
    seen = set().union(*(m for _, m in terms)) if terms else set()
    terms += [(n["name"], {tid: n["name"]}) for tid, n in named.items() if tid not in seen]
    if exists:
        # What the project already uses is part of its spec
        for l in s.links_from(exists):
            if l["type"] == "uses" and l["target"] not in seen | set(named):
                terms.append((_name(s, l["target"]), {l["target"]: _name(s, l["target"])}))
    reach = _reach(s, [tid for _, m in terms for tid in m])
    for tid in list(reach):
        if tid.startswith("subject/"):
            # What holds for any servo holds for the MG90S this project names
            reach[tid] |= broader(s, tid)
    out = {"entity": exists or eid, "exists": bool(exists), "terms": terms,
           "known": [], "unvalidated": [], "unknown": []}
    taken = set()
    for term, matched in terms:
        if not matched:
            out["unknown"].append((term, f"{term}: nothing in the store. Which one, what does it need, "
                                         f"and how does it join the rest?"))
            continue
        hits = 0
        for row in s.by_foundation("foundation:cube"):
            cid = row["id"]
            about = _about(s, cid)
            on = sorted(about & set().union(*(reach[t] for t in matched)))
            if not on:
                continue
            hits += 1
            if cid in taken:
                continue
            taken.add(cid)
            others = sorted(_name(s, a) for a in about
                            if not a.startswith("subject/") and a != out["entity"])
            status = _status(s, cid)
            group = "known" if status.startswith(("validated", "attested")) else "unvalidated"
            out[group].append((cid, row["state"].get("content"), [_name(s, a) for a in on], others))
        if not hits:
            names = ", ".join(matched.values())
            out["unknown"].append((term, f"{term}: the store has {names}, but no claims on it yet. "
                                         f"What do you know about it?"))
    out["safety"] = _safety(s, taken)
    return out


SAFETY = ("protects", "limits")


def _safety(s, taken):
    """Claims that protect or limit one already in the spec, and those that
    protect or limit them, though no word named them: a fuse on the pack,
    the wire gauge on the servo leads. [(claim_id, text, word, other, validated)]."""
    found, todo = [], sorted(taken)
    while todo:
        cid = todo.pop(0)
        for word, other, outward in relations(s, cid):
            if word in SAFETY and not outward and other not in taken:
                taken.add(other)
                todo.append(other)
                done = _status(s, other).startswith(("validated", "attested"))
                found.append((other, s.get(other)["state"].get("content"), word, cid, done))
    return found


def render(result, brief=""):
    lines = [f"Spec for {result['entity']}" + ("" if result["exists"] else " (not in the store yet)")]
    if brief:
        lines.append(f"Brief: {brief}")
    lines.append("\nWhat your words matched:")
    for term, matched in result["terms"]:
        lines.append(f"  {term} -> {', '.join(matched.values()) or 'nothing'}")
    for group, title in (("known", "Known (validated)"), ("unvalidated", "Known, but not validated yet")):
        lines.append(f"\n{title}: {len(result[group])}")
        for cid, text, on, others in result[group]:
            where = f" (from {', '.join(others)})" if others else " (general)"
            lines.append(f"  - {text}{where}\n      {cid}, on {', '.join(on)}")
    lines.append(f"\nSafety, what protects or limits the above: {len(result['safety'])}")
    for cid, text, word, other, done in result["safety"]:
        lines.append(f"  - {text}{'' if done else ' (not validated yet)'}\n      {cid} {word} {other}")
    lines.append(f"\nNot known: {len(result['unknown'])}")
    lines += [f"  - {q}" for _, q in result["unknown"]]
    return "\n".join(lines)


def sheet(name, result):
    """The questions as a claims CSV: one row per unknown, claim left blank."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(SHEET)
    for term, question in result["unknown"]:
        w.writerow([name, "project", term, "yes", question, "", "needs-check", *[""] * len(LENSES)])
    return buf.getvalue()


def cmd_spec(args):
    from store.substrate import Substrate
    s = Substrate()
    try:
        uses = [u.strip() for u in re.split(r"[,;]", args.uses or "") if u.strip()]
        result = spec(s, args.name, uses, args.brief or "")
    finally:
        s.close()
    print(render(result, args.brief))
    if args.out and result["unknown"]:
        with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
            f.write(sheet(args.name, result))
        print(f"\nWrote {len(result['unknown'])} questions to {args.out}. Write a claim on each row you can, then:")
        print(f"  python keystone-gate/kg import {args.out}           # check it")
        print(f"  python keystone-gate/kg import {args.out} --write   # make the project and its claims")


def add_spec_parser(sub):
    p = sub.add_parser("spec", help="spec a project from what the store knows, with what it doesn't as questions")
    p.add_argument("name", help="the project, new or existing")
    p.add_argument("--uses", help="parts and topics it will use, separated by commas")
    p.add_argument("--brief", help="a line on what it is; subjects it names are matched too")
    p.add_argument("--out", help="write the questions to this CSV, to fill and import")
    p.set_defaults(func=cmd_spec)
