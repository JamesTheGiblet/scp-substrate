"""Suggested links from the foundational cubes to related cubes in other clusters.

Each one is a pending proposal, so it counts for nothing until James accepts it
in the grid. The reasons are Claude's, written from the cubes' claims.
Run: python seeds/claims/before-pivot/seed_links_foundations.py
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import propose_neighbour


BY = "model-draft:claude"

NEIGHBOURS = [
    # Security, out to how the system is built
    ("keep-dependencies-to-one", "own-ed25519-for-local-signing", "signing in pure Python avoids a crypto dependency"),
    ("keep-dependencies-to-one", "sqlite-single-file-wal-mode-chosen", "SQLite ships with Python"),
    ("password-hash-meets-owasp-cost", "keep-dependencies-to-one", "scrypt comes from the standard library"),
    ("never-commit-secrets", "keys-need-a-backup-and-a-rotation-plan", "both are about handling keys"),
    ("rotate-a-leaked-key-immediately", "keys-need-a-backup-and-a-rotation-plan", "rotation needs a plan before a leak"),
    ("outside-text-is-data-not-instructions", "treat-retrieved-text-as-data", "the same rule, general and local"),
    ("outside-text-is-data-not-instructions", "quoting-sources-reduces-hallucination", "quotes tie model output back to the text"),
    ("models-word-people-decide", "agent-proposes-humans-decide", "the same principle"),
    ("models-word-people-decide", "llm-handles-language-not-truth", "models word answers but do not decide truth"),
    ("foundational-cubes-are-rigid", "contract-as-data-enforcement-as-code", "the rules are enforced in code"),
    ("sc-db-needs-real-backups", "sqlite-single-file-wal-mode-chosen", "one file holds everything"),
    ("sc-db-needs-real-backups", "binary-database-in-git", "git history is not a tested backup"),
    ("this-repo-stays-private", "binary-database-in-git", "sc.db is tracked in the repo"),
    ("writes-need-token-and-unlock", "every-write-goes-through-substrate", "both guard how writes happen"),
    # Hardware safety, out to the parts it protects
    ("pca9685-oe-pin-disables-outputs", "emergency-stop-cuts-power", "OE stops the signals, not the power"),
    ("pca9685-oe-pin-disables-outputs", "robots-can-move-without-warning", "outputs can be held off at start-up"),
    ("pca9685-oe-pin-disables-outputs", "pca9685-wiring-for-controllers", "OE is one more line to wire"),
    ("set-software-joint-limits", "inverse-kinematics-maps-position-to-angles", "inverse kinematics can ask for angles past a limit"),
    ("set-software-joint-limits", "pca9685-calibrate-before-trusting-angles", "limits rest on calibrated angles"),
    ("set-software-joint-limits", "mg996r-travel-is-120-degrees", "travel varies by servo"),
    ("static-can-kill-parts-silently", "first-power-on-checks", "static damage can show at first power-on"),
    ("static-can-kill-parts-silently", "esp32-gpio-input-and-current-limits", "bare ESP32 pins have little margin"),
    ("first-power-on-checks", "pca9685-servo-plug-orientation", "plug orientation is worth checking first"),
    ("emergency-stop-and-gravity", "arm-base-joint-carries-the-most-torque", "cutting power drops the load the base joint was holding"),
]


def seed(s):
    made = []
    for a, b, why in NEIGHBOURS:
        if s.get(f"cube/{a}") and s.get(f"cube/{b}"):
            result = propose_neighbour(s, f"cube/{a}", f"cube/{b}", BY, rationale=why)
            if result.get("status") == "created":
                made.append((a, b))
        else:
            print(f"skipped {a} -> {b}: a cube is missing")
    return made


if __name__ == "__main__":
    s = Substrate()
    print(f"Suggested {len(seed(s))} links, waiting for you in the grid.")
    s.close()
