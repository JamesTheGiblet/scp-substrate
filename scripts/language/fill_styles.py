"""Promote the three inherits placeholders to real content.

Content comes from the declaration blob itself — no invention.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from substrate import Substrate

FOUNDATION = "foundation:knowledge"
SOURCE_DOC = "giblets-forge/author/james-gilbert-v1"


def promote(s, capsule_id, state):
    """Replace placeholder state with real content."""
    existing = s.get(capsule_id)
    if not existing:
        raise SystemExit(f"missing {capsule_id} — run import_scp.py first")
    if not existing["state"].get("placeholder"):
        print(f"  {capsule_id}: already filled, skipping")
        return False
    with s.conn:
        s.conn.execute(
            "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
            (__import__("json").dumps(state), capsule_id)
        )
        s.conn.execute(
            "INSERT INTO events (event_type, capsule_id, payload) VALUES ('capsule.filled', ?, ?)",
            (capsule_id, __import__("json").dumps({"from": "placeholder"}))
        )
    print(f"  {capsule_id}: filled")
    return True


s = Substrate()

# --- james-voice --------------------------------------------------------
promote(s, "giblets-forge/style/james-voice", {
    "kind": "style",
    "inherited_by": [SOURCE_DOC],
    "voice": {
        "register":    "direct and informal",
        "sign_off":    "Giblet out",
        "posture":     "honest pushback over flattery, always",
        "format":      "bullets over block text",
        "spelling":    "British English everywhere, identifiers included",
        "correction":  "writes fast: flag and correct spelling",
        "learning":    "learns by doing, not by instruction",
    },
    "interface": {
        "for_agents": [
            "Direct and informal",
            "Honest pushback over flattery, always",
            "Bullets over block text",
            "Writes fast: flag and correct spelling",
            "Learns by doing, not by instruction",
            "Use Claude for rigorous specs; code gets written elsewhere",
        ],
        "public_channel": "LinkedIn",
    },
    "note": "Self-declaration of voice. Cube under OPINION/CONTEXT.",
})

# --- james-style --------------------------------------------------------
promote(s, "giblets-forge/style/james-style", {
    "kind": "style",
    "inherited_by": [SOURCE_DOC],
    "build_rules": [
        "Phase 0 is always documentation",
        "Build then test; everything earns a test",
        "Log everything; fail loud and public; fix first",
        "Lean dependencies",
        "Split files over 400 lines; modular",
        "camelCase in JS/C++; no prefix habits",
        "Node.js or Python for tooling",
        "Good/Bad/Ugly CHANGELOG on every repo",
        "British English everywhere, identifiers included",
    ],
    "rhythm": {
        "rebuild": "Finds a better way -> starts from scratch rather than patch.",
        "focus":   "Pointed at a task, finishes it. Left alone, wanders.",
        "fuel":    "Being told no, or that it can't be done.",
    },
    "note": "Self-declaration of build style. Cube under OPINION/CONTEXT.",
})

# --- visual-identity ----------------------------------------------------
promote(s, "giblets-forge/style/visual-identity", {
    "kind": "style",
    "inherited_by": [SOURCE_DOC],
    "identity": {
        "forge_name": "Giblets Forge",
        "structure":  "sole trader",
        "motto":      "I wanted it. So I forged it. Now forge yours.",
        "licence":    "MSL-1.0",
        "handle":     "JamesTheGiblet",
        "goes_by":    "James",
    },
    "domains": [
        "sovereign AI architecture (Forge Stack -> SC-OS, canon, JIG, LLLM)",
        "embedded systems (ESP32, M5StickC)",
        "robotics",
        "3D printing (built a 1.5m2 printer with four independent heated beds)",
        "interactive fiction and games",
        "simulation and emergence",
    ],
    "note": "Self-declaration of visual/brand identity. Cube under OPINION/CONTEXT.",
})

s.close()
