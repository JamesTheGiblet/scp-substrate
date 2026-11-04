"""Subjects: proposed, then accepted by a person. Run: python tests/run.py"""
from support_kg import *


def _store():
    from kg_agent import create_cube
    s = _fresh_kg_substrate()
    with s.conn:
        s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) "
                       "VALUES ('foundation:subject', 'foundation:foundation', '{}', 1)")
    a = create_cube(s, "Do not charge Li-ion unattended")["cube_id"]
    b = create_cube(s, "Fuse the battery positive near the pack")["cube_id"]
    c = create_cube(s, "British English everywhere")["cube_id"]
    return s, a, b, c


def test_a_proposal_changes_nothing_until_accepted():
    from kg_subjects import list_subjects, propose_subject
    s, a, b, _ = _store()
    try:
        r = propose_subject(s, "Li-ion packs", [a, b], "claude", kind="component")
        assert r["status"] == "pending"
        assert list_subjects(s) == [] and s.get("subject/li-ion-packs") is None
    finally:
        s.close()


def test_accepting_links_the_claims_once():
    from kg_subjects import accept_subject, list_subjects, propose_subject, subjects_of
    s, a, b, _ = _store()
    try:
        pid = propose_subject(s, "Li-ion packs", [a, b], "claude")["proposal_id"]
        assert accept_subject(s, pid, "james")["subject_id"] == "subject/li-ion-packs"
        [subj] = list_subjects(s)
        assert subj["claims"] == sorted([a, b]) and subj["created_by"] == "james"
        assert subjects_of(s, a) == ["subject/li-ion-packs"]
        assert "error" in accept_subject(s, pid, "james")
    finally:
        s.close()


def test_a_person_can_rename_and_narrow_but_not_widen():
    from kg_subjects import accept_subject, propose_subject
    s, a, b, c = _store()
    try:
        pid = propose_subject(s, "Batteries", [a, b], "claude")["proposal_id"]
        assert "error" in accept_subject(s, pid, "james", members=[a, c])
        r = accept_subject(s, pid, "james", name="Li-ion packs", members=[a])
        assert r == {"subject_id": "subject/li-ion-packs", "members": [a]}
    finally:
        s.close()


def test_a_rejection_sticks_unless_the_proposal_changes():
    from kg_subjects import propose_subject, reject_subject
    s, a, b, _ = _store()
    try:
        pid = propose_subject(s, "Batteries", [a, b], "claude")["proposal_id"]
        reject_subject(s, pid, "james", reason="too broad")
        assert propose_subject(s, "Batteries", [a, b], "claude")["skipped"]
        assert propose_subject(s, "Batteries", [a], "claude")["status"] == "pending"
    finally:
        s.close()


def test_a_subject_link_leaves_trust_alone():
    # trust.py reads a plain `about` link as a trust record, so subjects use their own
    from kg_subjects import accept_subject, propose_subject
    from trust import trust_from_evidence
    s, a, b, _ = _store()
    try:
        pid = propose_subject(s, "Li-ion packs", [a], "claude")["proposal_id"]
        accept_subject(s, pid, "james")
        assert "error" not in trust_from_evidence(s, a)
    finally:
        s.close()


def test_claims_must_exist():
    from kg_subjects import add_claim, propose_subject
    s, a, _, _ = _store()
    try:
        assert "error" in propose_subject(s, "Ghosts", ["cube/nope"], "claude")
        assert "error" in add_claim(s, a, "subject/nope")
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
