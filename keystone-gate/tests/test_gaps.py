"""Claims with lenses to write, out to a CSV and back. Run: python tests/run.py"""
from support_kg import *


def _store():
    from kg_agent import create_cube, fill_face
    from kg_proposals import propose_face
    s = _fresh_kg_substrate()
    create_cube(s, "The MG90S stalls at about 700 mA.", cube_id="cube/mg90s-stalls")
    create_cube(s, "The UBEC gives 5 V.", cube_id="cube/ubec-5v")
    for lens in ("FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"):
        fill_face(s, "cube/ubec-5v", lens, f"{lens} text", filled_by="james")
    fill_face(s, "cube/mg90s-stalls", "FACT", "Measured on the bench.", filled_by="james")
    propose_face(s, "cube/mg90s-stalls", "COUNTER", "A model's guess.", "model")
    return s


def test_only_claims_with_lenses_to_write_go_on_the_sheet():
    from kg_gaps import export, gaps
    s = _store()
    try:
        assert [(r["id"], m) for r, m in gaps(s)] == [("cube/mg90s-stalls", ["COUNTER", "OPINION", "FICTION", "CONTEXT"])]
        text, rows = export(s)
        assert rows == 1 and "cube/ubec-5v" not in text and "COUNTER OPINION FICTION CONTEXT" in text, text
    finally:
        s.close()


def test_a_filled_gaps_sheet_goes_in_as_drafts():
    from kg_agent import list_proposals
    from kg_csv import preview, write
    s = _store()
    try:
        sheet = ("claim_id,claim,missing,tags,FACT,COUNTER,OPINION\n"
                 'cube/mg90s-stalls,The MG90S stalls.,,"needs-check, Measured",Overwritten?,Below 6 V it may not.,Worth a fuse.\n')
        lines, problems = preview(s, sheet)
        assert problems == [] and any("keep" in l and "FACT" in l for l in lines), lines
        assert write(s, sheet, "james").startswith("added 1 drafts and rewrote 1 model drafts with your text, tagged 1"), "write"
        drafts = {p["lens"]: p["content"] for p in list_proposals(s, cube_id="cube/mg90s-stalls")}
        assert drafts == {"COUNTER": "Below 6 V it may not.", "OPINION": "Worth a fuse."}, drafts
        assert s.get("cube/mg90s-stalls")["state"]["tags"] == ["needs-check", "measured"]
        # The filled face is left alone
        assert s.get("cube/mg90s-stalls/face/FACT")["state"]["content"] == "Measured on the bench."
        assert preview(s, "claim_id,FACT\ncube/nothing,Hello.\n")[1] == ["row 2: cube/nothing is not a claim"]
    finally:
        s.close()


def test_a_new_claim_on_a_gaps_sheet_is_made():
    from kg_agent import list_proposals
    from kg_csv import preview, write
    s = _store()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    try:
        sheet = ("claim_id,entity,subject,claim,missing,tags,FACT,COUNTER\n"
                 "cube/caps-are-polarised,Parts,Capacitors,Electrolytics are polarised.,,needs-check,A stripe marks the negative.,Ceramics aren't.\n"
                 "cube/nothing,,,,,,Hello.,\n")
        lines, problems = preview(s, sheet)
        assert "make entity entity/parts" in lines and problems == ["row 3: cube/nothing is not a claim"], (lines, problems)
        assert write(s, sheet.splitlines(True)[0] + sheet.splitlines(True)[1], "james").startswith(
            "made 1 claims, 1 entities and 1 subjects with 2 lens drafts"), "write"
        drafts = {p["lens"] for p in list_proposals(s, cube_id="cube/caps-are-polarised")}
        assert drafts == {"FACT", "COUNTER"} and s.get("cube/caps-are-polarised")["state"]["tags"] == ["needs-check"]
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
