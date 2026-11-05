"""Claims, subjects and entities from a CSV. Run: python tests/run.py"""
from support_kg import *


def _store():
    s = _fresh_kg_substrate()
    with s.conn:
        for fid in ("foundation:subject", "foundation:entity", "foundation:person", "foundation:project"):
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                           "VALUES (?, 'foundation:foundation', '{}', 1)", (fid,))
    s.write({"id": "james", "foundation": "foundation:person", "state": {"name": "James"}})
    s.write({"id": "entity/scpbot", "foundation": "foundation:entity", "state": {"name": "SCPBot", "aliases": ["SCP bot"]}})
    s.write({"id": "subject/mg90s", "foundation": "foundation:subject", "state": {"name": "MG90S"}})
    return s


CSV = """﻿Entity,Subject,Uses,Claim,ID,Tags,FACT,Supports
scp bot,mg90s,yes,The MG90S stalls at about 700 mA.,cube/mg90s-stalls-700ma,"needs-check; measured",Read on the bench supply.,
SCPBot,UBEC,yes,"The UBEC gives 5 V, steady under load.",cube/ubec-steady,,,cube/mg90s-stalls-700ma
Rover,Wheel motor,,A wheel motor needs a driver board.,,needs-check,,
"""


def test_a_csv_fills_claims_subjects_and_entities():
    from kg_csv import write
    s = _store()
    try:
        made = write(s, CSV, "james")
        # SCPBot and the MG90S are found by alias and name; Rover, UBEC and the wheel motor are new
        assert made["entities"] == ["entity/rover"], made
        assert sorted(made["subjects"]) == ["subject/ubec", "subject/wheel-motor"], made
        assert len(made["claims"]) == 3 and made["links"] == 1 and made["drafts"] == 1, made
        uses = {l["target"] for l in s.links_from("entity/scpbot") if l["type"] == "uses"}
        assert uses == {"subject/mg90s", "subject/ubec"}
        assert ("about-subject", "subject/mg90s") in [(l["type"], l["target"]) for l in s.links_from("cube/mg90s-stalls-700ma")]
        assert s.get("cube/mg90s-stalls-700ma")["state"]["tags"] == ["needs-check", "measured"]
        assert s.get("cube/ubec-steady")["state"]["source"] == "From a CSV imported by james"
        assert ("supports", "cube/mg90s-stalls-700ma") in [(l["type"], l["target"]) for l in s.links_from("cube/ubec-steady")]
        # Importing again skips what exists
        assert write(s, CSV, "james")["claims"] == []
    finally:
        s.close()


def test_a_preview_writes_nothing():
    from kg_csv import preview
    s = _store()
    try:
        lines, problems = preview(s, CSV)
        assert problems == [] and "keep entity entity/scpbot" in lines and "make entity entity/rover" in lines, lines
        assert not s.get("entity/rover") and not s.get("cube/ubec-steady")
    finally:
        s.close()


def test_a_bad_file_says_which_row_and_writes_nothing():
    from kg_csv import parse, write
    s = _store()
    try:
        for text, said in (("entity,claim\nSCPBot,\n", "row 2: needs both"),
                           ("subject,claim\nMG90S,It stalls.\n", "at least entity and claim"),
                           ("entity,claim\nentity/nobody,It stalls.\n", "row 2: no entity has the id entity/nobody"),
                           ("entity,claim\nSCPBot,It stalls,at 700 mA\n", "row 2: more cells than columns")):
            try:
                parse(s, text)
                raise AssertionError(f"expected {said!r}")
            except ValueError as e:
                assert said in str(e), e
        # A missing evidence id stops the whole file
        try:
            write(s, "entity,claim,from\nRover,It rolls.,evidence/none\nRover,It turns.,\n", "james")
            raise AssertionError("expected a problem")
        except ValueError as e:
            assert "evidence evidence/none not found" in str(e), e
        assert not s.get("entity/rover")
    finally:
        s.close()


def test_the_page_previews_then_imports():
    from kg_serve import apply_action
    s = _store()
    try:
        shown = apply_action(s, {"action": "import", "csv": CSV}, "james")
        assert shown["problems"] == [] and not s.get("entity/rover"), shown
        done = apply_action(s, {"action": "import", "csv": CSV, "write": True}, "james")
        assert done["made"].startswith("made 1 entities, 2 subjects, 3 claims"), done
    finally:
        s.close()


def test_a_words_column_suggests_links():
    from kg_agent import list_proposals
    from kg_csv import write
    s = _store()
    try:
        made = write(s, "entity,subject,claim,words
SCPBot,MG90S,The MG90S stalls.,stall
"
                        "Rover,Wheel motor,The wheel motor stalls on carpet.,stall; carpet
", "james")
        assert made["suggested"] == 1, made
        sug = [p for p in list_proposals(s, status="pending") if p.get("proposed_by") == "neighbour_by_words"]
        assert {sug[0]["cube_id"], sug[0]["other_cube_id"]} == set(made["claims"]), sug
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
