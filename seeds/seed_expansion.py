"""All expansion capsules from the '20 candidates' list. Create-only."""
from substrate import Substrate

CAPSULES = [
    # --- A: vocabulary (14) ---------------------------------------------
    {"id": "lex/yes",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "yes",  "pos": "ack",  "features": {}}},
    {"id": "lex/no",   "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "no",   "pos": "ack",  "features": {}}},
    {"id": "lex/ok",   "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "ok",   "pos": "ack",  "features": {}}},
    {"id": "lex/yeah", "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "yeah", "pos": "ack",  "features": {}}},
    {"id": "lex/not",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "not",  "pos": "neg",  "features": {}}},
    {"id": "lex/is",   "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "is",   "pos": "aux",  "features": {"tense": "present"}}},
    {"id": "lex/was",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "was",  "pos": "aux",  "features": {"tense": "past"}}},
    {"id": "lex/will", "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "will", "pos": "aux",  "features": {"tense": "future"}}},
    {"id": "lex/who",   "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "who",   "pos": "wh", "features": {}}},
    {"id": "lex/what",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "what",  "pos": "wh", "features": {}}},
    {"id": "lex/where", "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "where", "pos": "wh", "features": {}}},
    {"id": "lex/when",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "when",  "pos": "wh", "features": {}}},
    {"id": "lex/and",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "and",  "pos": "conj", "features": {}}},
    {"id": "lex/but",  "foundation": "foundation:knowledge", "state": {"kind": "lexical-entry", "text": "but",  "pos": "conj", "features": {}}},

    # --- B: classifiers (6) ---------------------------------------------
    {"id": "classifier/05-farewell", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "farewell",
        "match_mode": "contains",
        "patterns": ["bye", "goodbye", "see you", "later", "cheers", "night"],
        "response_templates": ["bye", "see you", "later", "cheers"]}},
    {"id": "classifier/06-thanks", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "thanks",
        "match_mode": "contains",
        "patterns": ["thanks", "thank you", "ta", "cheers"],
        "response_templates": ["no worries", "cheers", "anytime"]}},
    {"id": "classifier/07-apology", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "apology",
        "match_mode": "contains",
        "patterns": ["sorry", "my bad", "oops", "apologies"],
        "response_templates": ["no worries", "fine", "don't worry"]}},
    {"id": "classifier/08-request", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 3, "name": "request",
        "match_mode": "contains",
        "patterns": ["please", "could you", "would you", "can you"],
        "response_templates": ["sure", "ok", "alright"]}},
    {"id": "classifier/09-question-mark", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 3, "name": "question-mark",
        "match_mode": "endswith", "patterns": ["?"],
        "response_templates": ["dunno", "not sure", "maybe"]}},
    {"id": "classifier/10-ack", "foundation": "foundation:knowledge", "state": {
        "kind": "input-classifier", "layer": 2, "name": "ack",
        "match_mode": "exact", "patterns": ["yes", "no", "ok", "yeah", "yep", "nope"],
        "response_templates": ["ok", "right", "mm"]}},

    # --- C: personal content (16) ---------------------------------------
    {"id": "forge", "foundation": "foundation:knowledge", "state": {
        "kind": "identity", "name": "Giblets Forge", "structure": "sole trader",
        "motto": "I wanted it. So I forged it. Now forge yours.",
        "licence": "MSL-1.0"}},

    {"id": "tool/chisels", "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "chisels", "category": "hand-tool"}},
    {"id": "tool/router",  "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "router", "category": "power-tool"}},
    {"id": "tool/jig",     "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "jig", "category": "workholding"}},
    {"id": "tool/printer", "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "3D printer", "category": "additive", "spec": "1.5m2, four independent heated beds"}},
    {"id": "tool/claude",  "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "Claude", "category": "llm", "vendor": "Anthropic"}},
    {"id": "tool/esp32",   "foundation": "foundation:knowledge", "state": {"kind": "tool", "name": "ESP32", "category": "microcontroller"}},

    {"id": "project/robot-arm",       "foundation": "foundation:knowledge", "state": {"kind": "project", "name": "robot-arm", "status": "active", "domain": "robotics"}},
    {"id": "project/3d-printer-build","foundation": "foundation:knowledge", "state": {"kind": "project", "name": "3d-printer-build", "status": "active", "domain": "hardware"}},
    {"id": "project/if-game",         "foundation": "foundation:knowledge", "state": {"kind": "project", "name": "if-game", "status": "active", "domain": "interactive-fiction"}},
    {"id": "project/sim-emergence",   "foundation": "foundation:knowledge", "state": {"kind": "project", "name": "sim-emergence", "status": "active", "domain": "simulation"}},

    {"id": "parked/canon", "foundation": "foundation:knowledge", "state": {"kind": "parked-idea", "name": "canon", "status": "parked", "domain": "sovereign-ai"}},
    {"id": "parked/jig",   "foundation": "foundation:knowledge", "state": {"kind": "parked-idea", "name": "JIG",   "status": "parked", "domain": "sovereign-ai"}},
    {"id": "parked/lllm",  "foundation": "foundation:knowledge", "state": {"kind": "parked-idea", "name": "LLLM",  "status": "parked", "domain": "sovereign-ai"}},

    {"id": "principle/fail-loud-public",       "foundation": "foundation:knowledge", "state": {"kind": "principle", "statement": "Log everything; fail loud and public; fix first."}},
    {"id": "principle/split-400-lines",        "foundation": "foundation:knowledge", "state": {"kind": "principle", "statement": "Split files over 400 lines; modular."}},
    {"id": "principle/british-english-everywhere", "foundation": "foundation:knowledge", "state": {"kind": "principle", "statement": "British English everywhere, identifiers included."}},

    # --- D: meta (6) ---------------------------------------------------
    {"id": "alias/an",   "foundation": "foundation:knowledge", "state": {"kind": "alias", "alias_for": "a", "text": "an", "pos": "det", "features": {}}},
    {"id": "alias/js",   "foundation": "foundation:knowledge", "state": {"kind": "alias", "alias_for": "james", "text": "js", "pos": "noun", "features": {}}},
    {"id": "alias/scps", "foundation": "foundation:knowledge", "state": {"kind": "alias", "alias_for": "scp", "text": "scps", "pos": "noun", "features": {}}},

    {"id": "typo/todau", "foundation": "foundation:knowledge", "state": {"kind": "typo", "alias_for": "today", "text": "todau", "pos": "noun", "features": {}}},
    {"id": "typo/teh",   "foundation": "foundation:knowledge", "state": {"kind": "typo", "alias_for": "the",   "text": "teh",   "pos": "det", "features": {}}},
    {"id": "typo/adn",   "foundation": "foundation:knowledge", "state": {"kind": "typo", "alias_for": "and",   "text": "adn",   "pos": "conj", "features": {}}},
]

LINKS = [
    # james ↔ forge
    ("james", "owns", "forge"),
    ("forge", "owned-by", "james"),
    # james ↔ tools
    ("james", "uses", "tool/chisels"),
    ("james", "uses", "tool/router"),
    ("james", "uses", "tool/jig"),
    ("james", "uses", "tool/printer"),
    ("james", "uses", "tool/claude"),
    ("james", "uses", "tool/esp32"),
    # james ↔ projects
    ("james", "building", "project/robot-arm"),
    ("james", "building", "project/3d-printer-build"),
    ("james", "building", "project/if-game"),
    ("james", "building", "project/sim-emergence"),
    # tools → projects
    ("tool/printer", "used-in", "project/3d-printer-build"),
    ("tool/router",  "used-in", "forge"),
    ("tool/esp32",   "used-in", "project/robot-arm"),
    ("tool/claude",  "used-in", "scp"),
    # projects ↔ forge-stack
    ("scp", "part-of", "forge-stack"),
    ("project/sim-emergence", "part-of", "forge-stack"),
    ("parked/canon", "part-of", "forge-stack"),
    ("parked/jig",   "part-of", "forge-stack"),
    ("parked/lllm",  "part-of", "forge-stack"),
    # parked ideas owned by james
    ("parked/canon", "owned-by", "james"),
    ("parked/jig",   "owned-by", "james"),
    ("parked/lllm",  "owned-by", "james"),
    # principles
    ("principle/fail-loud-public",         "applies-to", "james"),
    ("principle/split-400-lines",          "applies-to", "scp"),
    ("principle/british-english-everywhere","applies-to", "james"),
]


def main():
    s = Substrate()
    nc, sc = 0, 0
    for c in CAPSULES:
        if s.get(c["id"]):
            sc += 1
            continue
        s.write(c)
        nc += 1
    nl, sl = 0, 0
    for src, typ, tgt in LINKS:
        if s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type=? AND target=?",
            (src, typ, tgt)
        ).fetchone():
            sl += 1
            continue
        if not s.get(tgt):
            print(f"  SKIP (missing target): {src} --{typ}--> {tgt}")
            continue
        s.link(src, typ, tgt)
        nl += 1
    print(f"capsules: {nc} new, {sc} present")
    print(f"links:    {nl} new, {sl} present")
    s.close()


if __name__ == "__main__":
    main()
