"""Tag nouns with animacy. Create-or-update. Idempotent."""
import json
from substrate import Substrate

ANIMACY = {
    # Humans
    "james": "human", "person": "human", "user": "human",
    "author": "human", "builder": "human", "programmer": "human",
    "developer": "human", "giblet": "human", "giblets": "human",

    # Animals
    "cat": "animal", "cats": "animal", "dog": "animal", "dogs": "animal",
    "bird": "animal", "birds": "animal", "horse": "animal",
    "fish": "animal", "mouse": "animal",

    # Physical objects (non-animate)
    "mat": "object", "mats": "object",
    "house": "object", "houses": "object",
    "table": "object", "chair": "object", "door": "object",
    "tree": "object", "book": "object", "car": "object",
    "capsule": "object", "capsules": "object", "cube": "object",
    "printer": "object", "robot": "object",
    "tool": "object", "tools": "object",
    "forge": "object", "token": "object", "tokens": "object",
    "phrase": "object", "phrases": "object", "span": "object",

    # Abstract nouns
    "substrate": "abstract", "trust": "abstract",
    "foundation": "abstract", "foundations": "abstract",
    "sentence": "abstract", "sentences": "abstract",
    "evidence": "abstract", "corpus": "abstract",
    "conversation": "abstract",
    "verb": "abstract", "noun": "abstract", "nouns": "abstract",
    "rule": "abstract", "rules": "abstract",
    "idea": "abstract", "concept": "abstract",
    "question": "abstract", "decision": "abstract",
    "principle": "abstract", "session": "abstract",
    "framework": "abstract", "project": "abstract",
    "theory": "abstract", "mechanism": "abstract",
    "model": "abstract", "algorithm": "abstract",
    "knowledge": "abstract", "observation": "abstract",
    "meaning": "abstract", "structure": "abstract",
    "context": "abstract", "layer": "abstract",
    "network": "abstract", "protocol": "abstract",
    "classifier": "abstract", "grammar": "abstract",
    "lexicon": "abstract", "system": "abstract",
    "input": "abstract", "output": "abstract",
    "response": "abstract", "request": "abstract",
    "term": "abstract", "word": "abstract", "words": "abstract",
    "scp": "abstract", "entry": "abstract",
    "turn": "abstract", "key": "abstract",
    "parse": "abstract", "parser": "abstract",
    "language": "abstract", "lexical": "abstract",
    "value": "abstract", "field": "abstract",
}


def main():
    s = Substrate()
    created = updated = skipped = 0
    for word, animacy in ANIMACY.items():
        cid = f"lex/{word}"
        c = s.get(cid)
        if not c:
            s.write({
                "id": cid,
                "foundation": "foundation:knowledge",
                "state": {
                    "kind": "lexical-entry",
                    "text": word,
                    "pos": "noun",
                    "features": {"animacy": animacy},
                    "source": "feature-tagged",
                },
            })
            created += 1
            continue
        features = dict(c["state"].get("features", {}))
        if features.get("animacy") == animacy:
            skipped += 1
            continue
        features["animacy"] = animacy
        state = dict(c["state"])
        state["features"] = features
        with s.conn:
            s.conn.execute(
                "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(state), cid),
            )
        updated += 1
    print(f"animacy tags: {created} created, {updated} updated, {skipped} skipped")
    s.close()


if __name__ == "__main__":
    main()
