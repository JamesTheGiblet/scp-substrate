#!/usr/bin/env python3
"""Seed 11 useful capsules + 19 links. Idempotent — re-running writes nothing new."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import json
from store.substrate import Substrate

CAPSULES = [
    # --- personal context (from james-gilbert-v1 declaration) ---------------
    {"id": "claude", "foundation": "foundation:knowledge", "state": {
        "kind": "tool",
        "name": "Claude",
        "vendor": "Anthropic",
        "use": "rigorous specs, architectural review, code review",
        "note": "Claude for thinking; code gets written elsewhere",
    }},
    {"id": "esp32", "foundation": "foundation:knowledge", "state": {
        "kind": "tool",
        "name": "ESP32",
        "category": "microcontroller",
        "use": "embedded systems, robotics",
        "family": "also M5StickC for prototyping",
    }},
    {"id": "carpentry", "foundation": "foundation:knowledge", "state": {
        "kind": "skill",
        "name": "Carpentry",
        "origin": "chisels and hammers; self-employed with routers and jigs",
        "note": "first trade; still operates at Giblets Forge",
    }},
    {"id": "forge-stack", "foundation": "foundation:knowledge", "state": {
        "kind": "concept",
        "name": "Forge Stack",
        "members": ["SC-OS", "canon", "JIG", "LLLM", "SCP"],
        "note": "umbrella architecture; SCP substrate is one project under it",
    }},
    {"id": "malvern", "foundation": "foundation:knowledge", "state": {
        "kind": "place",
        "name": "Malvern",
        "region": "Worcestershire, UK",
        "note": "home of QinetiQ's site",
    }},
    {"id": "qinetiq", "foundation": "foundation:knowledge", "state": {
        "kind": "organisation",
        "name": "QinetiQ",
        "role": "defence and security technology company",
        "site": "Malvern",
    }},

    # --- substrate meta (principles, decisions, open questions) ------------
    {"id": "signed-not-trusted", "foundation": "foundation:knowledge", "state": {
        "kind": "principle",
        "name": "signed-not-trusted",
        "statement": "Signed means provenance, not trust.",
        "rationale": "A signature proves who signed a document. It does not assert the document is true, useful, or trusted.",
        "applies_to": ["giblets-scp", "substrate-trust"],
        "origin": "lens_note on james-gilbert-v1",
    }},
    {"id": "phase-0", "foundation": "foundation:knowledge", "state": {
        "kind": "principle",
        "name": "Phase 0",
        "statement": "Phase 0 is always documentation.",
        "rationale": "Document fully before building. Ideas parked for years, documented; not started until they fit.",
        "source": "first of james's build_rules",
    }},
    {"id": "chose-sqlite", "foundation": "foundation:knowledge", "state": {
        "kind": "decision",
        "name": "chose-sqlite",
        "question": "Which database for the SCP substrate?",
        "decision": "SQLite, single file, WAL mode",
        "rationale": "One writer, many readers, no network. Schema fixed at migration; no migrations since.",
        "alternatives_considered": [
            "Postgres (overkill for one user)",
            "DuckDB (analytics not transactions)",
            "Filesystem JSON (no queries)",
        ],
        "decided_by": "james",
        "date": "2026-10-25",
    }},
    {"id": "adaptive-fusion", "foundation": "foundation:knowledge", "state": {
        "kind": "question",
        "name": "adaptive-fusion",
        "question": "How to calibrate the fusion likelihood function?",
        "context": "Current sigmoid is fixed; unknown whether it matches actual evidence quality.",
        "status": "open",
        "blocked_by": "need ground-truth observations (did the claim turn out true?)",
        "raised": "2026-10-31",
    }},

    # --- session event ----------------------------------------------------
    {"id": "session-2026-10-31", "foundation": "foundation:event", "state": {
        "kind": "session",
        "date": "2026-10-31",
        "outcome": "canonical james-gilbert key bootstrapped; declared=signed closed; both SCP docs re-signed and re-verified",
        "capsules_added": 11,
        "schema_changes": 0,
        "tests": "19/19",
    }},
]

LINKS = [
    # James ↔ tools / skills / concepts
    ("james",              "uses",           "claude"),
    ("james",              "uses",           "esp32"),
    ("james",              "can",            "carpentry"),
    ("james",              "building",       "forge-stack"),
    # James ↔ work location
    ("james",              "at",             "malvern"),
    ("james",              "works-at",       "qinetiq"),
    ("malvern",            "hosts",          "qinetiq"),
    # SCP ↔ principles / concepts / questions
    ("scp",                "guided-by",      "signed-not-trusted"),
    ("scp",                "follows",        "phase-0"),
    ("scp",                "open-question",  "adaptive-fusion"),
    ("scp",                "part-of",        "forge-stack"),
    # Decision about the substrate (both directions)
    ("chose-sqlite",       "about",          "giblets-forge/project/scp-substrate-v1"),
    ("chose-sqlite",       "decided-by",     "james"),
    ("giblets-forge/project/scp-substrate-v1", "has-decision", "chose-sqlite"),
    # Session history
    ("session-2026-10-31", "touched",        "giblets-forge/author/james-gilbert-v1"),
    ("session-2026-10-31", "touched",        "giblets-forge/project/scp-substrate-v1"),
    ("session-2026-10-31", "touched",        "chose-sqlite"),
    ("session-2026-10-31", "touched",        "signed-not-trusted"),
    ("session-2026-10-31", "touched",        "phase-0"),
]


def main():
    s = Substrate()
    new_caps, existing_caps = 0, 0
    new_links, existing_links = 0, 0

    for c in CAPSULES:
        if s.get(c["id"]):
            existing_caps += 1
            continue
        s.write(c)
        new_caps += 1

    for src, type_, tgt in LINKS:
        row = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type=? AND target=?",
            (src, type_, tgt)
        ).fetchone()
        if row:
            existing_links += 1
            continue
        s.link(src, type_, tgt)
        new_links += 1

    print(f"capsules: {new_caps} new, {existing_caps} already present")
    print(f"links:    {new_links} new, {existing_links} already present")

    counts = dict(s.conn.execute("""
        SELECT 'capsules' k, COUNT(*) v FROM capsules
        UNION ALL SELECT 'links',    COUNT(*) FROM links
        UNION ALL SELECT 'events',   COUNT(*) FROM events
    """).fetchall())
    print("totals:", counts)
    s.close()


if __name__ == "__main__":
    main()
