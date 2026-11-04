"""Wiring claims, and the nets traced from them. Run: python tests/run.py"""
from support_kg import *


def _claim(s, cid, wires, entity="entity/bot"):
    s.write({"id": cid, "foundation": "foundation:cube", "state": {"kind": "cube", "content": cid,
                                                                   "wires": wires}})
    s.link(cid, "about-entity", entity)
    s.link(cid, "about-subject", "subject/wiring")


def test_a_common_ground_forms_from_the_wires():
    from kg_wiring import nets
    s = _fresh_kg_substrate()
    try:
        for cid in ("entity/bot", "entity/other", "subject/wiring"):
            s.write({"id": cid, "foundation": "foundation:knowledge", "state": {}})
        _claim(s, "cube/a", [[["m5", "GND"], ["pca", "GND"]], [["m5", "G32"], ["pca", "SDA"]]])
        _claim(s, "cube/b", [[["ubec", "OUT-"], ["pca", "GND"]]])
        _claim(s, "cube/c", [[["x", "GND"], ["pca", "GND"]]], entity="entity/other")
        found = nets(s, "entity/bot")
        assert found[0]["parts"] == ["m5", "pca", "ubec"] and found[0]["claims"] == ["cube/a", "cube/b"]
        assert found[1]["pins"] == ["m5:G32", "pca:SDA"]
        assert len(found) == 2
    finally:
        s.close()


if __name__ == "__main__":
    run_tests(globals())
