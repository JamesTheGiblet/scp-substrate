"""Run every test file. Usage: python tests/run.py"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
files = sorted(ROOT.glob("tests/test_*.py")) + sorted(ROOT.glob("keystone-gate/tests/test_*.py"))

passed = failed = 0
for f in files:
    r = subprocess.run([sys.executable, str(f)], capture_output=True, text=True, encoding="utf-8")
    counts = re.search(r"(\d+) passed, (\d+) failed", r.stdout)
    if not counts:
        print(f"{f.name}: did not finish\n{r.stderr}")
        failed += 1
        continue
    passed += int(counts[1])
    failed += int(counts[2])
    print(f"{f.name}: {counts[0]}")
    for line in r.stdout.splitlines():
        if "\u2717" in line:
            print(line)

print(f"\n{passed} passed, {failed} failed")
sys.exit(0 if failed == 0 else 1)
