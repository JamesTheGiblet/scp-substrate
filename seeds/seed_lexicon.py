"""Seed lexical entries. Create-only (capsules authoritative)."""
from substrate import Substrate

LEXICON = {
    'a': ('det', {'number': 'sg'}),
    'big': ('adj', {}),
    'cat': ('noun', {'physical': True, 'animacy': 'animal', 'location': False, 'number': 'sg'}),
    'cats': ('noun', {'physical': True, 'animacy': 'animal', 'location': False, 'number': 'pl'}),
    'chases': ('verb', {'transitive': True, 'object_must_be_animate': True, 'tense': 'present'}),
    'chased': ('verb', {'transitive': True, 'object_must_be_animate': True, 'tense': 'past'}),
    'dog': ('noun', {'physical': True, 'animacy': 'animal', 'location': False, 'number': 'sg'}),
    'dogs': ('noun', {'physical': True, 'animacy': 'animal', 'location': False, 'number': 'pl'}),
    'house': ('noun', {'physical': True, 'animacy': 'object', 'location': True, 'number': 'sg'}),
    'houses': ('noun', {'physical': True, 'animacy': 'object', 'location': True, 'number': 'pl'}),
    'in': ('prep', {'requires_location': True}),
    'mat': ('noun', {'physical': True, 'animacy': 'object', 'location': True, 'number': 'sg'}),
    'mats': ('noun', {'physical': True, 'animacy': 'object', 'location': True, 'number': 'pl'}),
    'on': ('prep', {'requires_location': True}),
    'red': ('adj', {}),
    'sat': ('verb', {'transitive': False, 'tense': 'past'}),
    'sits': ('verb', {'transitive': False, 'number': 'sg', 'tense': 'present'}),
    'small': ('adj', {}),
    'the': ('det', {}),
}


def main():
    import json
    s = Substrate()
    new, skipped = 0, 0
    for word, (pos, features) in LEXICON.items():
        cid = f"lex/{word}"
        state = {"kind": "lexical-entry", "text": word, "pos": pos, "features": features}
        if s.get(cid):
            # Create-only: capsule is the source of truth after first seed.
            # To change an entry, edit the capsule directly. Re-running this
            # script will not overwrite it.
            skipped += 1
            continue
        s.write({"id": cid, "foundation": "foundation:knowledge", "state": state})
        new += 1
    print(f"lexicon: {new} new, {skipped} already present (create-only)")
    s.close()


if __name__ == "__main__":
    main()

