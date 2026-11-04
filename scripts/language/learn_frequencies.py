"""Parse every corpus sentence, count token occurrences, seed trust."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from collections import Counter

from store.substrate import Substrate
from symlm.parse import parse_sentence, cleanup_session
from symlm.corpus import load_corpus


def main():
    s = Substrate()
    word_counts = Counter()
    failed = []

    corpus = load_corpus(s)
    for item in corpus:
        text = item["text"]
        r = parse_sentence(s, text)
        if "error" in r:
            failed.append((text, r["error"]))
            continue
        if not r["sentence"]:
            failed.append((text, "no full parse"))
            cleanup_session(s, r["session"])
            continue

        # Walk down from sentence to collect token texts
        stack = [r["sentence"]]
        seen = set()
        while stack:
            cid = stack.pop()
            if cid in seen:
                continue
            seen.add(cid)
            c = s.get(cid)
            if not c:
                continue
            if c["foundation"] == "foundation:token":
                word_counts[c["state"]["text"]] += 1
            for l in s.links_from(cid):
                if l["type"] == "has-child":
                    stack.append(l["target"])

        cleanup_session(s, r["session"])

    if failed:
        print(f"corpus: {len(failed)} failures")
        for text, err in failed:
            print(f"  {text!r}: {err}")

    print(f"corpus: {len(corpus) - len(failed)}/{len(corpus)} parsed")
    print(f"words observed: {sum(word_counts.values())}, vocabulary: {len(word_counts)}")

    # Write trust instance per word
    new = 0
    for word, count in word_counts.items():
        tid = f"trust/freq/{word}"
        state = {"n0": count, "k": 0, "count": count, "word": word}
        existing = s.get(tid)
        if existing and existing["state"] == state:
            continue
        s.write({
            "id": tid,
            "foundation": "foundation:leighton-weight",
            "state": state,
        })
        if not existing:
            s.link(tid, "about", f"lex/{word}")
            new += 1

    print(f"trust instances: {new} new, {len(word_counts) - new} updated")
    s.close()


if __name__ == "__main__":
    main()
