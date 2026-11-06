"""One subject as a kind of another: MG90S is a Servo, a UBEC is a Voltage
regulator. The link is `is-a`, from the narrower subject to the broader.

It lets general knowledge reach particular things: a claim about servos counts
for every entity that uses an MG90S, and a question about servos finds the
claims about the MG90S. A person says it; nothing infers it.
"""
from datetime import datetime, timezone

IS_A = "is-a"


def _subject(s, sid):
    return (s.get(sid) or {}).get("foundation") == "foundation:subject"


def _follow(s, start, up):
    found, todo = set(), [start]
    while todo:
        here = todo.pop()
        nxt = ([l["target"] for l in s.links_from(here) if l["type"] == IS_A] if up
               else [l["source"] for l in s.links_to(here, IS_A)])
        for n in nxt:
            if n not in found and n != start:
                found.add(n)
                todo.append(n)
    return found


def broader(s, sid):
    """Every subject sid is a kind of, all the way up."""
    return _follow(s, sid, up=True)


def narrower(s, sid):
    """Every subject that is a kind of sid, all the way down."""
    return _follow(s, sid, up=False)


def is_a(s, sid, broader_id, by):
    """Say sid is a kind of broader_id. Refuses a loop."""
    for x in (sid, broader_id):
        if not _subject(s, x):
            return {"error": f"subject {x} not found"}
    if sid == broader_id or sid in broader(s, broader_id):
        return {"error": f"{broader_id} is already a kind of {sid}"}
    s.link(sid, IS_A, broader_id, metadata={"by": by, "at": datetime.now(timezone.utc).isoformat()})
    return {"subject": sid, "is_a": broader_id}
