"""Review drafts on a spreadsheet. kg cube sheet writes the waiting face drafts,
whole claims at a time, to a CSV; you fill in what to do with each, and the
same file goes back in through kg import or the page's Import CSV.

Columns written: proposal_id, claim_id, claim, lens, draft, decision,
your_text, words. Fill in, per row:

    decision    accept, reject or edit. Left blank, the row is skipped
    your_text   with edit, the words to use instead of the draft
    words       your words for linking the claim, on any of its rows

Accepting fills the face with the draft; edit fills it with your text and
rejects the draft. Every row is checked before anything is written.
"""
import csv
import io

from kg_agent import accept_proposal, fill_face, list_proposals, reject_proposal

COLUMNS = ["proposal_id", "claim_id", "claim", "lens", "draft", "decision", "your_text", "words"]
DECISIONS = ("accept", "reject", "edit")


def export(s, limit=50):
    """The next waiting face drafts as CSV text, never splitting a claim."""
    by_claim = {}
    for p in list_proposals(s, status="pending"):
        if p.get("proposal_type") == "face":
            by_claim.setdefault(p["cube_id"], []).append(p)
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(COLUMNS)
    rows = 0
    for cube_id in sorted(by_claim):
        drafts = sorted(by_claim[cube_id], key=lambda p: p["lens"])
        if rows and rows + len(drafts) > limit:
            break
        claim = (s.get(cube_id) or {"state": {}})["state"]
        for p in drafts:
            writer.writerow([p["id"], cube_id, claim.get("content", ""), p["lens"], p.get("content", ""),
                             "", "", ", ".join(claim.get("words") or [])])
        rows += len(drafts)
    return out.getvalue(), rows


def is_sheet(text):
    head = next(csv.reader(io.StringIO(text.lstrip("﻿"))), [])
    return {"proposal_id", "decision"} <= {h.strip().lower() for h in head}


def _rows(text):
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    reader.fieldnames = [(f or "").strip().lower() for f in reader.fieldnames or []]
    return [(n, {k: (v or "").strip() for k, v in r.items() if k}) for n, r in enumerate(reader, 2)]


def preview(s, text):
    """What the sheet would do, and anything that stops it: (lines, problems)."""
    lines, problems = [], []
    for n, r in _rows(text):
        decision = r.get("decision", "").lower()
        p = s.get(r.get("proposal_id", ""))
        if not decision and not r.get("words"):
            continue
        if decision and decision not in DECISIONS:
            problems.append(f"row {n}: decision must be accept, reject or edit, not {r['decision']!r}")
        elif decision and (not p or p["state"].get("status") != "pending"):
            problems.append(f"row {n}: {r.get('proposal_id') or 'no proposal_id'} is not a waiting draft")
        elif decision == "edit" and not r.get("your_text"):
            problems.append(f"row {n}: edit needs your_text")
        elif decision:
            lines.append(f"{decision:6} {p['state']['lens']:8} {p['state']['cube_id']}")
        if r.get("words"):
            lines.append(f"words  {r.get('claim_id')}: {r['words']}")
    return list(dict.fromkeys(lines)), problems


def write(s, text, by):
    from kg_claim_links import set_words
    if problems := preview(s, text)[1]:
        raise ValueError("; ".join(problems))
    done = {"accept": 0, "reject": 0, "edit": 0, "worded": set()}
    for _, r in _rows(text):
        decision = r.get("decision", "").lower()
        if decision == "accept":
            accept_proposal(s, r["proposal_id"], accepted_by=by)
        elif decision == "reject":
            reject_proposal(s, r["proposal_id"], rejected_by=by, reason="rejected on a review sheet")
        elif decision == "edit":
            st = s.get(r["proposal_id"])["state"]
            fill_face(s, st["cube_id"], st["lens"], r["your_text"], filled_by=by)
            reject_proposal(s, r["proposal_id"], rejected_by=by, reason="replaced by hand")
        if decision:
            done[decision] += 1
        if r.get("words") and r.get("claim_id") and r["claim_id"] not in done["worded"]:
            set_words(s, r["claim_id"], add=r["words"].replace(";", ",").split(","), by=by)
            done["worded"].add(r["claim_id"])
    return (f"accepted {done['accept']}, rejected {done['reject']} and rewrote {done['edit']} drafts; "
            f"set words on {len(done['worded'])} claims")


def cmd_cube_sheet(args):
    from store.substrate import Substrate
    s = Substrate()
    text, rows = export(s, args.limit)
    s.close()
    if not rows:
        print("No drafts are waiting.")
        return
    with open(args.out, "w", encoding="utf-8-sig", newline="") as f:
        f.write(text)
    print(f"Wrote {rows} drafts to {args.out}. Fill in decision (accept, reject or edit), then:")
    print(f"  python keystone-gate/kg import {args.out}           # check it")
    print(f"  python keystone-gate/kg import {args.out} --write   # apply it")
