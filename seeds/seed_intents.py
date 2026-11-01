"""Seed input-intent classifiers. Create-only."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from substrate import Substrate

INTENTS = [
    # Order matters — more specific first
    {"id": "intent/why-trusted",
     "walker": "why_trusted",
     "phrases": ["why is", "why is it", "why trusted", "how trusted", "why trust"],
     "requires_entity": True,
     "description": "Explain why a capsule is trusted"},
    {"id": "intent/verified",
     "walker": "verified",
     "phrases": ["is it verified", "is it signed", "is it authentic", "who signed"],
     "patterns": [r"^is \S+ (signed|verified|authentic)\??$"],
     "requires_entity": True,
     "description": "Show verification records"},
    {"id": "intent/what-decided",
     "walker": "what_decided",
     "phrases": ["what did i decide", "what was decided", "decision about",
                 "why did we choose", "why did i choose", "decide about"],
     "requires_entity": False,
     "description": "Find a decision and its rationale"},
    {"id": "intent/what-believe",
     "walker": "what_believe",
     "phrases": ['what do i know', 'what do i believe', 'what do i think', 'what do i trust', 'do i trust', 'my view on', 'my opinion on', 'where do i stand', 'should i'],
     "requires_entity": False,
     "description": "Find cubes on a topic, with your view and the case against"},
    {"id": "intent/what-uses",
     "walker": "what_uses",
     "phrases": ["what do i use", "what tools", "which tools", "what does james use"],
     "requires_entity": False,
     "description": "List tools a person uses"},
    {"id": "intent/what-building",
     "walker": "what_building",
     "phrases": ["what am i building", "what is james building", "current projects",
                 "what projects"],
     "requires_entity": False,
     "description": "List projects a person is building"},
    {"id": "intent/what-supports",
     "walker": "what_supports",
     "phrases": ["what supports", "supporting evidence", "evidence for"],
     "requires_entity": True,
     "description": "Find supporting evidence for a claim"},
    {"id": "intent/list-kind",
     "walker": "list_kind",
     "phrases": ["list all", "show me all", "list every", "all the"],
     "requires_entity": False,
     "description": "List capsules of a given kind"},
    {"id": "intent/what-happened",
     "walker": "what_happened",
     "phrases": ["what happened", "what was done", "session on", "on the"],
     "requires_entity": False,
     "description": "Show session or date activity"},
    {"id": "intent/where-is",
     "walker": "where_is",
     "phrases": ["where is", "where's", "find function", "find class",
                 "where is function", "where is class", "locate"],
     "requires_entity": False,
     "description": "Find a symbol or file by name"},
    {"id": "intent/what-files",
     "walker": "what_files",
     "phrases": ["what files", "files in", "contents of repo", "list files in"],
     "requires_entity": True,
     "description": "List files contained in a repo"},
    {"id": "intent/who-is",
     "walker": "who_is",
     "phrases": ["who is", "who's"],
     "requires_entity": True,
     "description": "Describe a person or entity"},
    {"id": "intent/what-is",
     "walker": "what_is",
     "phrases": ["what is", "what are", "describe"],
     "requires_entity": True,
     "description": "Describe any capsule"},
]


def main():
    s = Substrate()
    new = 0
    for it in INTENTS:
        if s.get(it["id"]):
            continue
        s.write({
            "id": it["id"],
            "foundation": "foundation:knowledge",
            "state": {
                "kind": "input-intent",
                "walker": it["walker"],
                "match_mode": "any_phrase",
                "phrases": it["phrases"],
                "patterns": it.get("patterns", []),
                "requires_entity": it["requires_entity"],
                "description": it["description"],
            },
        })
        new += 1
    print(f"intents: {new} new")
    s.close()


if __name__ == "__main__":
    main()
