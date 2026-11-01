"""The project's own principles, checked. Run: python tests/run.py"""
import re

from support_substrate import *

CODE = ([ROOT / "scps", ROOT / "keystone-gate" / "kg"]
        + sorted(ROOT.glob("src/*.py")) + sorted(ROOT.glob("scripts/*.py"))
        + sorted(ROOT.glob("seeds/*.py")) + sorted(ROOT.glob("tests/*.py"))
        + sorted(ROOT.glob("keystone-gate/*.py")))


def test_no_file_over_400_lines():
    """principle/split-400-lines"""
    over = {p.name: n for p in CODE
            if (n := len(p.read_text(encoding="utf-8").splitlines())) > 400}
    assert not over, over


def test_no_silent_exception_handlers():
    """principle/fail-loud-public"""
    pattern = re.compile(r"except( Exception)?( as \w+)?:\s*\n\s*pass\b")
    silent = [p.name for p in CODE if p.name != "test_house_rules.py"
              and pattern.search(p.read_text(encoding="utf-8"))]
    assert not silent, silent


if __name__ == "__main__":
    run_tests(globals())
