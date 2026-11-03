#!/usr/bin/env python3
"""Suggested subjects for the 44 claims kept after the archive, grouped by Claude.

Each is a proposal and changes nothing until accepted with `kg subject accept`.
The cubes about James are left out: James is an entity, not a subject.
Re-running updates pending proposals and leaves rejected ones alone.
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_subjects import propose_subject

# (name, kind, rationale, claims)
SUBJECTS = [
    ("Li-ion packs", "component", "Each says how to charge, protect, spot trouble in, or get rid of a Li-ion pack.",
     ["do-not-charge-li-ion-unattended", "li-ion-warning-signs", "li-ion-fire-get-out-and-call-999",
      "li-ion-disposal", "protection-cannot-stop-internal-faults", "fuse-the-battery-positive-near-the-pack",
      "prevent-reversed-battery"]),
    ("Emergency stops", "practice", "What stopping a powered robot does and does not do.",
     ["emergency-stop-cuts-power", "emergency-stop-and-gravity", "robots-can-move-without-warning",
      "set-software-joint-limits"]),
    ("Bench work", "practice", "Hazards at the bench while building, before anything moves.",
     ["first-power-on-checks", "static-can-kill-parts-silently", "solder-fume-is-a-real-hazard",
      "mains-work-is-for-competent-people"]),
    ("PCA9685", "component", "The servo driver board.", ["pca9685-oe-pin-disables-outputs"]),
    ("VL53L0X", "component", "The laser distance sensor.", ["vl53l0x-laser-is-class-1"]),
    ("Cube page", "system", "How the editing page is reached and who can write through it.",
     ["the-page-is-never-public", "writes-need-token-and-unlock", "password-hash-meets-owasp-cost"]),
    ("Secrets and private data", "practice", "Where keys and private text may and may not go.",
     ["never-commit-secrets", "rotate-a-leaked-key-immediately", "private-text-stays-on-this-machine",
      "this-repo-stays-private", "sc-db-needs-real-backups"]),
    ("Models and people", "practice", "What a model may do and what only a person decides.",
     ["models-word-people-decide", "outside-text-is-data-not-instructions", "foundational-cubes-are-rigid"]),
    ("Code style", "practice", "How the code and docs are written.",
     ["british-english-everywhere", "split-files-over-400-lines", "python-for-these-tools",
      "keep-dependencies-to-one", "plain-words-in-docs"]),
    ("Working method", "practice", "How James runs the work, apart from the code itself.",
     ["phase-0-is-documentation", "log-everything-fail-loud", "compress-in-uncertain-channels"]),
    ("Signing", "topic", "What a signature does and does not show.", ["signed-means-provenance-not-trust"]),
]


def main():
    s = Substrate()
    for name, kind, why, claims in SUBJECTS:
        r = propose_subject(s, name, [f"cube/{c}" for c in claims], "claude", kind=kind, rationale=why)
        print(f"  {name}: {r.get('status') or r.get('reason') or r.get('error')}")
    s.close()


if __name__ == "__main__":
    main()
