"""Links between claims that say how they connect.

A link reads as a sentence from one claim to another: "the inline fuse"
protects "the UBEC feed", "a separate servo supply" solves "the brownout". The connecting
word is the link's type, so anything reading the store sees what the link
means, not only that two claims touch. Only the words in WORDS are allowed,
so each one means the same every time. See docs/VOCABULARY.md, Relationship.
"""
import json
from datetime import datetime, timezone

# Connecting word -> link type
WORDS = {
    "supports": "supports",
    "goes against": "goes-against",
    "needs": "needs",
    "protects": "protects",
    "limits": "limits",
    "causes": "causes",
    "risks": "risks",
    "solves": "solves",
    "works with": "works-with",
    "replaces": "replaces",
    "is a case of": "is-a-case-of",
}
_WORD_OF = {t: w for w, t in WORDS.items()}
# Older words, still read from sheets and outlines written before the change
OLD = {"depends on": "needs", "is an example of": "is a case of"}
# Sheet columns and outline keys: each word's link type, and the older ones
KEYS = {**{t: w for w, t in WORDS.items()}, **{o.replace(" ", "-"): n for o, n in OLD.items()}}
# What each word means, for the page and the help
MEANS = {
    "supports": "more reason to believe it",
    "goes against": "less reason to believe it",
    "needs": "won't work without it",
    "protects": "stops it failing",
    "limits": "sets a ceiling on it",
    "causes": "makes it happen",
    "risks": "could make it fail",
    "solves": "is the fix for it",
    "works with": "the two are halves of one design",
    "replaces": "is newer, so the other is out of date",
    "is a case of": "is one case of a general rule",
}


def word_of(text):
    """The connecting word for "works with" or "works-with", else None. An
    older word gives the one that took its place."""
    text = " ".join((text or "").lower().replace("-", " ").split())
    text = OLD.get(text, text)
    return text if text in WORDS else None


def _is_claim(s, cid):
    row = s.get(cid)
    return bool(row) and row["foundation"] == "foundation:cube"


def relate(s, a, word, b, by, note=None):
    """Link claim a to claim b with a connecting word. Linking twice is a no-op."""
    w = word_of(word)
    if not w:
        return {"error": f"connecting word must be one of: {', '.join(WORDS)}"}
    for cid in (a, b):
        if not _is_claim(s, cid):
            return {"error": f"claim {cid} not found"}
    if a == b:
        return {"error": "a claim can't link to itself"}
    at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    s.link(a, WORDS[w], b, metadata={"by": by, "note": note, "at": at})
    return {"from": a, "word": w, "to": b}


def unrelate(s, a, word, b, by, reason=None):
    """Take a connecting-word link off, logging who and why."""
    w = word_of(word)
    if not w:
        return {"error": f"connecting word must be one of: {', '.join(WORDS)}"}
    with s.conn:
        cur = s.conn.execute("DELETE FROM links WHERE source = ? AND type = ? AND target = ?", (a, WORDS[w], b))
        if not cur.rowcount:
            return {"error": f"{a} doesn't {w} {b}"}
        s.conn.execute("INSERT INTO events (event_type, capsule_id, payload) VALUES ('link.removed', ?, ?)",
                       (a, json.dumps({"type": WORDS[w], "target": b, "by": by, "reason": reason})))
    return {"from": a, "word": w, "to": b, "removed": True}


def relations(s, cube_id):
    """Every connecting-word link on a claim, as (word, other claim, out), with
    out True when the sentence starts from this claim."""
    out = [(_WORD_OF[l["type"]], l["target"], True) for l in s.links_from(cube_id) if l["type"] in _WORD_OF]
    into = [(_WORD_OF[l["type"]], l["source"], False) for l in s.links_to(cube_id) if l["type"] in _WORD_OF]
    return sorted(out + into)
