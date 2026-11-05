"""Claims with lenses still to write, as a CSV you fill in elsewhere.

kg cube gaps lists every claim with a face not yet filled; with --out it
writes them as a sheet, one row per claim:

    claim_id, entity, subject, claim, missing, tags, FACT, COUNTER, OPINION, FICTION, CONTEXT

Write the missing lenses in their columns and import the same file through
kg import or the page's Import CSV. Each text goes in as a draft to confirm,
replacing any model draft waiting for that lens, so it then shows on the
next kg cube sheet. A lens already filled is left alone. The tags column
shows the claim's tags; any you add there are added to the claim.
"""
import csv
import io

from kg_cube import LENSES
from kg_proposals import propose_face

HEAD = ["claim_id", "entity", "subject", "claim", "missing", "tags", *LENSES]


def _names(s, cube_id, type_):
    return ", ".join((s.get(l["target"]) or {"state": {}})["state"].get("name") or l["target"]
                     for l in s.links_from(cube_id) if l["type"] == type_)


def gaps(s):
    """[(claim row, [missing lenses])], by claim id."""
    out = []
    for r in sorted(s.by_foundation("foundation:cube"), key=lambda r: r["id"]):
        missing = [l for l in LENSES if not s.get(f"{r['id']}/face/{l}")]
        if missing:
            out.append((r, missing))
    return out


def export(s, limit=None):
    from kg_entities import ABOUT_ENTITY
    from kg_subjects import ABOUT
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(HEAD)
    found = gaps(s)[:limit]
    for r, missing in found:
        writer.writerow([r["id"], _names(s, r["id"], ABOUT_ENTITY), _names(s, r["id"], ABOUT),
                         r["state"].get("content", ""), " ".join(missing),
                         ", ".join(r["state"].get("tags") or [])] + [""] * len(LENSES))
    return out.getvalue(), len(found)


def is_gaps(text):
    head = {h.strip().lower() for h in next(csv.reader(io.StringIO(text.lstrip("﻿"))), [])}
    return "claim_id" in head and "proposal_id" not in head and bool(head & {l.lower() for l in LENSES})


def _rows(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    reader.fieldnames = [(f or "").strip().upper() for f in reader.fieldnames or []]
    return list(enumerate(reader, 2))


def _tags(r):
    return [t.strip().lower() for t in (r.get("TAGS") or "").replace(";", ",").split(",") if t.strip()]


def _texts(text):
    """[(row number, claim id, lens, text)] for every lens cell written in."""
    return [(n, (r.get("CLAIM_ID") or "").strip(), lens, (r.get(lens) or "").strip())
            for n, r in _rows(text) for lens in LENSES if (r.get(lens) or "").strip()]


def preview(s, text):
    lines, problems = [], []
    for n, cid, lens, _ in _texts(text):
        if not s.get(cid) or s.get(cid)["foundation"] != "foundation:cube":
            problems.append(f"row {n}: {cid or 'no claim_id'} is not a claim")
        elif s.get(f"{cid}/face/{lens}"):
            lines.append(f"keep   {lens:8} {cid} (already filled)")
        else:
            lines.append(f"draft  {lens:8} {cid}")
    for n, r in _rows(text):
        cid = (r.get("CLAIM_ID") or "").strip()
        row = s.get(cid)
        new = row and [t for t in _tags(r) if t not in (row["state"].get("tags") or [])]
        if new and row["foundation"] == "foundation:cube":
            lines.append(f"tags   {cid}: {', '.join(new)}")
    return list(dict.fromkeys(lines)), problems


def write(s, text, by):
    if problems := preview(s, text)[1]:
        raise ValueError("; ".join(problems))
    from kg_cube import _update_state
    drafted = replaced = tagged = 0
    for _, r in _rows(text):
        row = s.get((r.get("CLAIM_ID") or "").strip())
        old = (row["state"].get("tags") or []) if row else []
        if row and (new := [t for t in _tags(r) if t not in old]):
            _update_state(s, row["id"], {**row["state"], "tags": old + new})
            tagged += 1
    for _, cid, lens, content in _texts(text):
        if s.get(f"{cid}/face/{lens}"):
            continue
        status = propose_face(s, cid, lens, content, f"sheet:{by}", rationale="from a gaps sheet").get("status")
        drafted += status == "created"
        replaced += status == "updated"
    return (f"added {drafted} drafts and rewrote {replaced} model drafts with your text, "
            f"tagged {tagged} claims; "
            f"review them with kg cube sheet")


def cmd_cube_gaps(args):
    from store.substrate import Substrate
    s = Substrate()
    try:
        if not args.out:
            found = gaps(s)
            for r, missing in found:
                print(f"{r['id']}  needs {' '.join(missing)}")
            print(f"\n{len(found)} claims have lenses to write. Add --out sheets/gaps.csv for a sheet.")
            return
        text, rows = export(s, args.limit)
    finally:
        s.close()
    if not rows:
        print("Every claim has all its lenses filled.")
        return
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    print(f"Wrote {rows} claims to {args.out}. Write the missing lenses in their columns, then:")
    print(f"  python keystone-gate/kg import {args.out}           # check it")
    print(f"  python keystone-gate/kg import {args.out} --write   # add them as drafts")
