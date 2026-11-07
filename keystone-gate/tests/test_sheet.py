"""Reviewing drafts on a spreadsheet. Run: python tests/run.py"""
import csv
import io

from support_kg import *


def _store():
    from kg_agent import create_cube, propose_face
    s = _fresh_kg_substrate()
    for n in range(3):
        cid = create_cube(s, f"Claim number {n} holds.", cube_id=f"cube/claim-{n}")["cube_id"]
        for lens in ("FACT", "COUNTER"):
            propose_face(s, cid, lens, f"{lens} draft for claim {n}", "model-draft:test")
    return s


def _filled(text, decisions):
    rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
    for row, (decision, mine, words) in zip(rows, decisions):
        row.update(decision=decision, your_text=mine, words=words)
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=rows[0].keys())
    w.writeheader()
    w.writerows(rows)
    return out.getvalue()


def test_a_sheet_keeps_whole_claims_together():
    from kg_sheet import export
    s = _store()
    try:
        text, rows = export(s, limit=5)
        # Three drafts would split a claim, so it stops at two claims' four
        assert rows == 4 and text.count("cube/claim-2") == 0, text
    finally:
        s.close()


def test_a_filled_sheet_accepts_rejects_and_rewrites():
    from kg_csv import preview, write
    s = _store()
    try:
        text, _ = __import__("kg_sheet").export(s, limit=50)
        filled = _filled(text, [("accept", "", "stall"), ("Reject", "", ""), ("edit", "My own fact.", ""),
                                ("", "", ""), ("", "", ""), ("", "", "")])
        lines, problems = preview(s, filled)
        assert problems == [] and len(lines) == 4, lines
        assert write(s, filled, "james") == "accepted 1, rejected 1 and rewrote 1 drafts; set words on 1 claims"
        assert s.get("cube/claim-0/face/COUNTER")["state"]["content"] == "COUNTER draft for claim 0"
        assert not s.get("cube/claim-0/face/FACT")
        assert s.get("cube/claim-1/face/COUNTER")["state"]["content"] == "My own fact."
        assert s.get("cube/claim-0")["state"]["words"] == ["stall"]
    finally:
        s.close()


def test_a_bad_row_stops_the_sheet():
    from kg_csv import write
    s = _store()
    try:
        text, _ = __import__("kg_sheet").export(s, limit=50)
        for decisions, said in (([("accept", "", ""), ("maybe", "", "")], "row 3: decision must be"),
                                ([("edit", "", "")], "row 2: edit needs your_text")):
            try:
                write(s, _filled(text, decisions), "james")
                raise AssertionError(f"expected {said!r}")
            except ValueError as e:
                assert said in str(e), e
        assert not s.get("cube/claim-0/face/COUNTER")
    finally:
        s.close()


def test_a_draft_that_is_not_a_lens_is_a_problem_not_an_accept():
    from kg_sheet import export, preview
    s = _store()
    try:
        # Written straight to the store, as a tool outside kg might
        s.write({"id": "cube/claim-0/proposal/9", "foundation": "foundation:knowledge", "state": {
            "kind": "cube-proposal", "proposal_type": "face", "cube_id": "cube/claim-0",
            "lens": "HUMAN_VALIDATION", "content": "Holds.", "status": "pending"}})
        text, _ = export(s, limit=50)
        rows = list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))
        decisions = [("accept", "", "")] * len(rows)
        _, problems = preview(s, _filled(text, decisions))
        assert len(problems) == 1 and "'HUMAN_VALIDATION' is not a lens" in problems[0], problems
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
