"""Extract vocabulary from substrate content and seed new lexical entries.

Sources:
  - docs/*.scp.json (SCP documents)
  - capsule state fields (knowledge, observation, principle, decision, session)
  - Python docstrings and comments

Filters:
  - >= 2 occurrences
  - >= 3 characters
  - not already in lexicon (lex/, alias/, typo/)

POS tagging: heuristic (context + morphology), flagged by confidence.
"""
import argparse
import ast
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from substrate import Substrate

ROOT = Path(__file__).parent

# Words that signal the *next* word's POS
DET = {"the", "a", "an", "this", "that", "these", "those", "my", "your",
       "our", "their", "his", "her", "its", "every", "each", "any", "some"}
PREP = {"in", "on", "at", "by", "with", "from", "to", "of", "for", "into",
        "onto", "under", "over", "near", "through", "across"}
ADJ_PREV = {"very", "quite", "really", "so", "too", "more", "most",
            "less", "least", "quite", "rather", "extremely"}
CONJ = {"and", "or", "but", "nor", "yet", "so"}

# Morphological suffixes
NOUN_SUFFIX = ("tion", "sion", "ment", "ness", "ity", "ance", "ence",
               "ship", "hood", "dom", "ism", "ist", "er", "or")
ADJ_SUFFIX  = ("ous", "ful", "ive", "able", "ible", "al", "ic", "ish",
               "less", "ary", "ory")
VERB_SUFFIX = ("ing", "ed", "ise", "ize")
ADV_SUFFIX  = ("ly",)

# Stop words (already in lexicon or too generic to be useful alone)
STOP = {"the", "a", "an", "and", "or", "but", "if", "is", "was", "were",
        "am", "are", "be", "been", "being", "have", "has", "had", "do",
        "does", "did", "will", "would", "could", "should", "may", "might",
        "must", "can", "i", "you", "he", "she", "it", "we", "they", "me",
        "him", "her", "us", "them", "this", "that", "these", "those",
        "my", "your", "his", "its", "our", "their", "to", "of", "in",
        "on", "at", "by", "with", "from", "for", "into", "onto", "as",
        "not", "no", "yes", "so", "than", "then", "there", "here", "when",
        "where", "why", "how", "what", "who", "which", "while", "because",
        "all", "any", "some", "each", "every", "more", "most", "less",
        "least", "very", "quite", "just", "also", "only", "even", "still",
        "yet", "already", "always", "never", "sometimes", "often"}


# --- source collection ---------------------------------------------------
def _walk_json_strings(obj):
    """Yield every string value in a JSON structure."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_json_strings(v)


def collect_sources(s):
    """Yield (label, text) tuples."""
    # 1. SCP documents
    for path in sorted((ROOT / "docs").glob("*.scp.json")):
        try:
            data = json.loads(path.read_text())
            text = " ".join(_walk_json_strings(data))
            yield f"docs/{path.name}", text
        except Exception as e:
            print(f"  warn: {path.name}: {e}")

    # 2. Substrate capsules with textual state
    for row in s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE foundation IN ('foundation:knowledge', 'foundation:observation',
                             'foundation:event', 'foundation:leighton-weight')
          AND is_meta = 0
    """):
        try:
            data = json.loads(row["state_json"])
            text = " ".join(_walk_json_strings(data))
            yield f"capsule:{row['id']}", text
        except Exception:
            pass

    # 3. Python docstrings + comments
    for path in sorted(ROOT.glob("*.py")):
        try:
            src = path.read_text()
            # Docstrings via ast
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.FunctionDef,
                                     ast.ClassDef, ast.AsyncFunctionDef)):
                    ds = ast.get_docstring(node)
                    if ds:
                        yield f"py:{path.name}:docstring", ds
            # Comments via regex
            comments = "\n".join(
                m.group(1) for m in re.finditer(r"^\s*#\s*(.+)$",
                                                src, re.MULTILINE)
            )
            if comments:
                yield f"py:{path.name}:comments", comments
        except Exception:
            pass


# --- tokenisation -------------------------------------------------------
WORD_RE = re.compile(r"[A-Za-z]+")


def tokenise(text):
    return [w.lower() for w in WORD_RE.findall(text)]


# --- POS heuristics -----------------------------------------------------
# Word itself is a known function word
WORD_IS_PREP = PREP - {"to"}  # 'to' handled separately as aux marker
WORD_IS_DET  = DET
WORD_IS_CONJ = CONJ

# Adverbs / auxiliary shapes that stand alone
KNOWN_ADV = {"not", "never", "always", "often", "sometimes", "already",
             "still", "just", "only", "even", "also", "very", "quite",
             "rather", "too", "so", "here", "there", "now", "then"}

KNOWN_AUX = {"is", "are", "was", "were", "am", "be", "been", "being",
             "have", "has", "had", "do", "does", "did", "will", "would",
             "could", "should", "may", "might", "must", "can"}


def guess_pos(word, contexts):
    """Return (pos, confidence) where confidence is 'high'|'low'|'none'."""
    # Direct word check — overrides everything
    if word in WORD_IS_DET:
        return "det", "high"
    if word in WORD_IS_PREP:
        return "prep", "high"
    if word in WORD_IS_CONJ:
        return "conj", "high"
    if word in KNOWN_ADV:
        return "adv", "high"
    if word in KNOWN_AUX:
        return "aux", "high"

    votes = Counter()

    # Context votes
    for prev in contexts:
        if prev in DET:
            votes["noun"] += 3
        elif prev in PREP and prev != "to":
            votes["noun"] += 2
        elif prev == "to":
            votes["verb"] += 3
        elif prev in ADJ_PREV:
            votes["adj"] += 3
        elif prev in CONJ:
            pass  # ambiguous

    # Morphological votes
    for suf in NOUN_SUFFIX:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            votes["noun"] += 2
            break
    for suf in ADJ_SUFFIX:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            votes["adj"] += 2
            break
    for suf in VERB_SUFFIX:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            votes["verb"] += 1
            break
    for suf in ADV_SUFFIX:
        if word.endswith(suf) and len(word) > len(suf) + 1:
            votes["adv"] += 3
            break
    if word.endswith("s") and len(word) > 3:
        votes["noun"] += 1  # plural heuristic

    if not votes:
        return "unknown", "none"

    pos, top_votes = votes.most_common(1)[0]
    second_votes = votes.most_common(2)[1][1] if len(votes) > 1 else 0
    margin = top_votes - second_votes

    if margin >= 2 and top_votes >= 2:
        return pos, "high"
    return pos, "low"


# --- main ----------------------------------------------------------------
def extract(s, dry_run=False):
    print("Vocabulary extraction")
    print("=" * 60)
    print()

    # Collect sources
    sources = list(collect_sources(s))
    print(f"Sources read: {len(sources)}")

    # Count frequencies + record first-seen source per word
    freq = Counter()
    first_seen = {}
    contexts = defaultdict(list)  # word -> list of previous words

    for label, text in sources:
        words = tokenise(text)
        for i, w in enumerate(words):
            freq[w] += 1
            if w not in first_seen:
                first_seen[w] = label
            if i > 0:
                contexts[w].append(words[i - 1])

    print(f"Total tokens scanned: {sum(freq.values())}")
    print(f"Unique tokens: {len(freq)}")

    # Existing lexicon
    existing = set()
    for row in s.conn.execute("""
        SELECT json_extract(state_json, '$.text') AS text
        FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') IN
              ('lexical-entry', 'alias', 'typo')
    """):
        if row["text"]:
            existing.add(row["text"].lower())

    # Filter
    candidates = {}
    rejected_count = 0
    rejected_stop = 0
    for word, count in freq.items():
        if count < 2:
            rejected_count += 1
            continue
        if len(word) < 3:
            rejected_count += 1
            continue
        if word in existing:
            continue
        if word in STOP:
            rejected_stop += 1
            continue
        candidates[word] = count

    print(f"Filtered (>= 2 occurrences, >= 3 chars): {len(candidates)}")
    print(f"  dropped as rare/short: {rejected_count}")
    print(f"  dropped as stop words: {rejected_stop}")
    print(f"  already in lexicon: {len(existing)}")
    print()

    # POS tag
    tagged_high, tagged_low, tagged_none = {}, {}, {}
    for word in candidates:
        pos, conf = guess_pos(word, contexts[word])
        if conf == "high":
            tagged_high[word] = pos
        elif conf == "low":
            tagged_low[word] = pos
        else:
            tagged_none[word] = "unknown"

    total = len(candidates)
    n_high = len(tagged_high)
    n_low = len(tagged_low)
    n_none = len(tagged_none)

    print(f"POS tagging:")
    print(f"  high confidence: {n_high} ({100*n_high//total}%)")
    print(f"  low confidence:  {n_low} ({100*n_low//total}%)")
    print(f"  unknown:         {n_none} ({100*n_none//total}%)")
    print()

    # Top 20 by frequency
    print("Top 20 new words by frequency:")
    for word, count in sorted(candidates.items(), key=lambda x: -x[1])[:20]:
        pos = tagged_high.get(word) or tagged_low.get(word) or "unknown"
        conf = "H" if word in tagged_high else ("L" if word in tagged_low else "·")
        print(f"  [{conf}] {word:20} x{count:3}  pos={pos}")
    print()

    if dry_run:
        print("(dry-run — no capsules written)")
        print()
        print("Re-run with --write to seed these as lexical entries.")
        return {"total": total, "high": n_high, "low": n_low, "unknown": n_none}

    # Write
    written = 0
    for word, count in candidates.items():
        pos = tagged_high.get(word) or tagged_low.get(word) or "unknown"
        conf = ("high" if word in tagged_high
                else "low" if word in tagged_low
                else "unknown")
        cid = f"lex/{word}"
        if s.get(cid):
            continue
        s.write({
            "id": cid,
            "foundation": "foundation:knowledge",
            "state": {
                "kind": "lexical-entry",
                "text": word,
                "pos": pos,
                "features": {},
                "source": "extracted",
                "confidence": conf,
                "occurrences": count,
                "first_seen": first_seen[word],
            },
        })
        written += 1

    print(f"Wrote {written} new lexical entries.")
    return {"total": total, "written": written,
            "high": n_high, "low": n_low, "unknown": n_none}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="show report, don't write capsules")
    ap.add_argument("--write", action="store_true",
                    help="write capsules (default if neither flag)")
    args = ap.parse_args()

    dry = args.dry_run and not args.write
    s = Substrate()
    extract(s, dry_run=dry)
    s.close()


if __name__ == "__main__":
    main()
