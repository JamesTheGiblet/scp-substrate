"""Seed lexical entries with semantic features. Idempotent."""
from substrate import Substrate

LEXICON = {
    "the":    ("det",  {}),
    "a":      ("det",  {}),
    "big":    ("adj",  {}),
    "red":    ("adj",  {}),
    "small":  ("adj",  {}),
    "cat":    ("noun", {"physical": True, "animacy": "animal", "location": False}),
    "dog":    ("noun", {"physical": True, "animacy": "animal", "location": False}),
    "mat":    ("noun", {"physical": True, "animacy": "object", "location": True}),
    "house":  ("noun", {"physical": True, "animacy": "object", "location": True}),
    "sat":    ("verb", {"transitive": False}),
    "sits":   ("verb", {"transitive": False}),
    "chased": ("verb", {"transitive": True}),
    "on":     ("prep", {"requires_location": True}),
    "in":     ("prep", {"requires_location": True}),
}


def main():
    import json
    s = Substrate()
    new, updated = 0, 0
    for word, (pos, features) in LEXICON.items():
        cid = f"lex/{word}"
        state = {"kind": "lexical-entry", "text": word, "pos": pos, "features": features}
        if s.get(cid):
            with s.conn:
                s.conn.execute(
                    "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                    (json.dumps(state), cid)
                )
            updated += 1
        else:
            s.write({"id": cid, "foundation": "foundation:knowledge", "state": state})
            new += 1
    print(f"lexicon: {new} new, {updated} updated")
    s.close()


if __name__ == "__main__":
    main()
