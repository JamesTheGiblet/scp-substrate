"""Read a misspelt word in a question as the word the store uses.

A word the store has never seen is checked against the typo entries first
(typo/teh is "the"). A word in SymLM's lexicon (lex/<word>) is real English
and is left alone, so "tell" never becomes "tall". Anything else is matched
against every word in the claims and in the names of subjects and entities:
the closest within one edit, or two for a word of eight letters or more,
starting with the same letter, is used when only one word is that close. Swapping two letters next to each other is one edit, so
"ubce" reads as "ubec". The answer says what it read each word as, so a
wrong guess is easy to spot.
"""
import re

_WORD = re.compile(r"[a-z][a-z0-9]{2,}")
THINGS = ("foundation:subject", "foundation:entity", "foundation:project")


def _stem(word):
    for ending in ("ing", "ed", "es", "s"):
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def _distance(a, b, limit):
    """Edits from a to b, counting a swap of two neighbouring letters as one,
    or limit + 1 once it is sure to pass limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    before, row = None, list(range(len(b) + 1))
    for i in range(1, len(a) + 1):
        now = [i] + [0] * len(b)
        for j in range(1, len(b) + 1):
            now[j] = min(row[j] + 1, now[j - 1] + 1, row[j - 1] + (a[i - 1] != b[j - 1]))
            if before and i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                now[j] = min(now[j], before[j - 2] + 1)
        before, row = row, now
        if min(row) > limit:
            return limit + 1
    return row[-1]


def known_words(s):
    """Every word in the claims, their tags, and subject and entity names."""
    texts = [r[0] for r in s.conn.execute(
        "SELECT json_extract(state_json, '$.content') || ' ' || COALESCE(json_extract(state_json, '$.tags'), '') "
        "FROM capsules WHERE foundation = 'foundation:cube' AND is_meta = 0")]
    for foundation in THINGS:
        texts += [f"{r['state'].get('name', '')} {r['state'].get('aliases') or ''}" for r in s.by_foundation(foundation)]
    return set(_WORD.findall(" ".join(t or "" for t in texts).lower()))


def correct(s, text, skip=()):
    """The question with misspelt words replaced, and [(written, read as)]."""
    words = known_words(s)
    stems = {_stem(w) for w in words}
    fixes = []
    for w in dict.fromkeys(_WORD.findall(text.lower())):
        typo = s.get(f"typo/{w}")
        if typo and typo["state"].get("alias_for"):
            fixes.append((w, typo["state"]["alias_for"]))
            continue
        if len(w) < 4 or w in skip or w in words or _stem(w) in stems or s.get(f"lex/{w}"):
            continue
        # Slips keep the first letter, so "magnets" is never read as "agents"
        limit = 1 if len(w) < 8 else 2
        near = sorted((_distance(w, k, limit), k) for k in words
                      if k[0] == w[0] and abs(len(k) - len(w)) <= limit)
        near = [(d, k) for d, k in near if d <= limit]
        # Only when one word is closest; two equally close is a guess
        if near and (len(near) == 1 or near[0][0] < near[1][0]):
            fixes.append((w, near[0][1]))
    for wrong, right in fixes:
        text = re.sub(rf"\b{re.escape(wrong)}\b", right, text, flags=re.I)
    return text, fixes
