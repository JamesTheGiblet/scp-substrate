"""Seed corpus sentences. Create-only. Edit capsules after first run."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import re
from store.substrate import Substrate

CORPUS_SENTENCES = [
    "the cat sat",
    "the dog sat",
    "the cat sits",
    "the dog sits",
    "a cat sat",
    "a dog sits",
    "the big cat sat",
    "the small dog sits",
    "the cat sat on the mat",
    "the cat sat in the mat",
    "the cat sat on a mat",
    "the dog sat on the mat",
    "the big cat sat on the small mat",
    "the small dog sits on the big mat",
    "a cat sat on the mat",
    "the cat chased the dog",
    "the dog chased the cat",
    "the dog sat in the house",
    "the cat chased the big dog",
    "a dog chased the small cat",
    "the cat chased the dog on the mat",
    "the dog sat in the house on the mat",
    "the big red cat sat",
    "the cat sat the dog",
]


def _slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def main():
    s = Substrate()
    new, skipped = 0, 0
    for text in CORPUS_SENTENCES:
        cid = f"corpus/{_slugify(text)}"
        if s.get(cid):
            skipped += 1
            continue
        s.write({
            "id": cid,
            "foundation": "foundation:knowledge",
            "state": {"kind": "corpus-sentence", "text": text},
        })
        new += 1
    print(f"corpus: {new} new, {skipped} already present (create-only)")
    s.close()


if __name__ == "__main__":
    main()
