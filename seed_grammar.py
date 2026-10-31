"""Seed grammar rules. Idempotent."""
from substrate import Substrate

GRAMMAR = [
    {"id": "grammar/np-det-noun",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "det"}},
             {"foundation": "token", "state": {"pos": "noun"}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "NP"}},
     }},
    {"id": "grammar/np-det-adj-noun",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "det"}},
             {"foundation": "token", "state": {"pos": "adj"}},
             {"foundation": "token", "state": {"pos": "noun"}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "NP"}},
     }},
    {"id": "grammar/pp-prep-np",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token",  "state": {"pos": "prep"}},
             {"foundation": "phrase", "state": {"category": "NP"}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "PP"}},
     }},
    {"id": "grammar/vp-verb",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token", "state": {"pos": "verb"},
              "features": {"transitive": False}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "VP"}},
     }},

    {"id": "grammar/vp-verb-np",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token",  "state": {"pos": "verb"},
              "features": {"transitive": True}},
             {"foundation": "phrase", "state": {"category": "NP"}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "VP"}},
     }},
    {"id": "grammar/vp-verb-pp",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "token",  "state": {"pos": "verb"},
              "features": {"transitive": False}},
             {"foundation": "phrase", "state": {"category": "PP"}},
         ]},
         "effect": {"foundation": "phrase", "state": {"category": "VP"}},
     }},
    {"id": "grammar/s-np-vp",
     "state": {
         "condition": {"type": "sequence", "match": [
             {"foundation": "phrase", "state": {"category": "NP"}},
             {"foundation": "phrase", "state": {"category": "VP"}},
         ]},
         "effect": {"foundation": "sentence", "state": {"category": "S"}},
     }},
]


def main():
    s = Substrate()
    new = 0
    for g in GRAMMAR:
        if s.get(g["id"]):
            continue
        s.write({"id": g["id"], "foundation": "foundation:rule", "state": g["state"]})
        new += 1
    print(f"grammar: {new} new, {len(GRAMMAR) - new} already present")
    s.close()


if __name__ == "__main__":
    main()
