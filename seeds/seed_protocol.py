"""Seed the Social Protocol Stack as capsules. Create-only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from substrate import Substrate

CAPSULES = [
    # --- layers ----------------------------------------------------------
    {"id": "layer-1-physical", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 1, "name": "Physical",
        "description": "Tone, posture, expression."}},
    {"id": "layer-2-link", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 2, "name": "Link",
        "description": "Ritual phrases, greetings, handshakes. Daily use."}},
    {"id": "layer-3-network", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 3, "name": "Network",
        "description": "Routing social intent, in-group signals, warmth."}},
    {"id": "layer-4-transport", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 4, "name": "Transport",
        "description": "Small talk, flow control."}},
    {"id": "layer-5-session", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 5, "name": "Session",
        "description": "Ongoing relationship state; continuity."}},
    {"id": "layer-6-presentation", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 6, "name": "Presentation",
        "description": "Framing, tone matching."}},
    {"id": "layer-7-application", "foundation": "foundation:knowledge", "state": {
        "kind": "protocol-layer", "layer": 7, "name": "Application",
        "description": "Actual semantic content and meaning. Rare in passing interaction."}},

    # --- overview + concepts --------------------------------------------
    {"id": "protocol-stack", "foundation": "foundation:knowledge", "state": {
        "kind": "framework",
        "name": "Social Protocol Stack",
        "description": "Human interaction as a deterministic protocol stack.",
        "origin": "James, Giblets Forge",
        "layers": [1, 2, 3, 4, 5, 6, 7],
    }},
    {"id": "handshake-protocol", "foundation": "foundation:knowledge", "state": {
        "kind": "concept",
        "description": "Layer 2 ritual greeting. Not a request for factual data.",
        "example": "How are you?",
        "correct_response_layer": 2,
    }},
    {"id": "bandwidth-mismatch", "foundation": "foundation:knowledge", "state": {
        "kind": "concept",
        "description": "High-bandwidth semantic packet sent into a low-bandwidth channel.",
        "symptoms": ["frozen smiles", "quick subject changes", "social distancing"],
    }},
    {"id": "minimum-viable-packet", "foundation": "foundation:knowledge", "state": {
        "kind": "principle",
        "statement": "Default to compression in uncertain channels.",
    }},
    {"id": "recovery-sequence", "foundation": "foundation:knowledge", "state": {
        "kind": "procedure",
        "steps": ["acknowledge lightly", "hand back the channel", "return to public mode"],
    }},
    {"id": "dual-mode-interface", "foundation": "foundation:knowledge", "state": {
        "kind": "concept",
        "public_mode": "Low-bandwidth protocol matching; minimum viable packets.",
        "private_mode": "High-bandwidth semantic exchange; safe channels only.",
    }},
    {"id": "high-bandwidth-thinker", "foundation": "foundation:knowledge", "state": {
        "kind": "persona",
        "traits": ["high pattern recognition", "fast associative processing", "literal interpretation"],
        "risks": ["masking fatigue", "social error states"],
    }},

    # --- input classifiers ----------------------------------------------
    {"id": "classifier/01-wellbeing", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "wellbeing-question",
        "match_mode": "contains",
        "patterns": ["how are you", "how's it going", "you ok", "how do you do", "alright"],
        "response_templates": ["good thanks", "not bad", "alright, you?", "fine thanks"],
    }},
    {"id": "classifier/02-greeting", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "greeting",
        "match_mode": "exact",
        "patterns": ["hi", "hello", "hey", "morning", "good morning", "afternoon",
                     "evening", "yo", "hiya"],
        "response_templates": ["hi", "hello", "hey", "morning"],
    }},
    {"id": "classifier/03-smalltalk", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 4, "name": "smalltalk",
        "match_mode": "contains",
        "patterns": ["weather", "nice day", "rain", "freezing", "boiling"],
        "response_templates": ["mm", "yeah", "suppose so"],
    }},
    {"id": "classifier/04-semantic", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 7, "name": "semantic",
        "match_mode": "parses",
        "response_templates": [],
    }},
]

LINKS = [
    ("protocol-stack", "guided-by", "high-bandwidth-thinker"),
    ("scp", "guided-by", "protocol-stack"),
    ("handshake-protocol", "part-of", "layer-2-link"),
    ("bandwidth-mismatch", "part-of", "layer-7-application"),
    ("minimum-viable-packet", "part-of", "recovery-sequence"),
    ("dual-mode-interface", "part-of", "protocol-stack"),
    ("layer-1-physical", "part-of", "protocol-stack"),
    ("layer-2-link", "part-of", "protocol-stack"),
    ("layer-3-network", "part-of", "protocol-stack"),
    ("layer-4-transport", "part-of", "protocol-stack"),
    ("layer-5-session", "part-of", "protocol-stack"),
    ("layer-6-presentation", "part-of", "protocol-stack"),
    ("layer-7-application", "part-of", "protocol-stack"),
]


def main():
    s = Substrate()
    new_caps, skip_caps = 0, 0
    for c in CAPSULES:
        if s.get(c["id"]):
            skip_caps += 1
            continue
        s.write(c)
        new_caps += 1
    new_links, skip_links = 0, 0
    for src, typ, tgt in LINKS:
        row = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type=? AND target=?",
            (src, typ, tgt)
        ).fetchone()
        if row:
            skip_links += 1
            continue
        s.link(src, typ, tgt)
        new_links += 1
    print(f"protocol: {new_caps} new capsules, {skip_caps} present")
    print(f"          {new_links} new links, {skip_links} present")
    s.close()


if __name__ == "__main__":
    main()
