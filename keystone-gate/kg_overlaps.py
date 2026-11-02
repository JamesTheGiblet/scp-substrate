"""Flag where work overlaps, valued by a Leighton weight.

Two cubes from different sources overlap when the same lens on each shares
unusual words. That gives N0, the sum across lenses, capped at the top of the
λ range. λ then decays by Forge Theory, N(t) = N0 * e^(-kt), where t is the days
since either cube last changed, or since a person confirmed the overlap.

Below 0.60 an overlap is not shown. That is the stack's boundary for λ. Confirming adds
0.20 and restarts the clock, and dismissing hides it for good, which closes the
Leighton Loop: score, act, observe, update.

This measures shared vocabulary from accepted faces, not shared meaning, and k
is a chosen half-life, not calibrated against outcomes.
"""
import hashlib
import json
import math
from datetime import datetime, timezone

from kg_cube import _now
from kg_lens_links import LENSES, _similar, _vectors, _word


THRESHOLD = 0.60
LAMBDA_MAX = 2.00
CONFIRM_GAIN = 0.20
HALF_LIFE_DAYS = 60
K = math.log(2) / HALF_LIFE_DAYS


def _home(cube):
    return cube.get("repo") or cube.get("group")


def _accepted(cube):
    faces = {l: f for l, f in cube["faces"].items() if f and not f.get("pending")}
    return {**cube, "faces": faces}


def _stamps(cube):
    return [f.get("at") for f in cube["faces"].values() if f and not f.get("pending") and f.get("at")]


def _days_since(stamps, now):
    if not stamps:
        return 0.0
    latest = datetime.strptime(max(stamps), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return max(0.0, (now - latest).total_seconds() / 86400)


def _pair_id(a, b):
    return "overlap/" + hashlib.sha256("|".join(sorted((a, b))).encode("utf-8")).hexdigest()[:16]


def load_decisions(s):
    rows = s.conn.execute("SELECT id, state_json FROM capsules WHERE "
                          "json_extract(state_json, '$.kind') = 'overlap-decision'").fetchall()
    return {row["id"]: json.loads(row["state_json"]) for row in rows}


def decide(s, a, b, verdict, by):
    """Record a person's view of an overlap. Returns {overlap_id} or {error}."""
    if verdict not in ("confirmed", "dismissed"):
        return {"error": "verdict must be confirmed or dismissed"}
    if not s.get(a) or not s.get(b):
        return {"error": "cube not found"}
    overlap_id = _pair_id(a, b)
    s.write({"id": overlap_id, "foundation": "foundation:knowledge", "state": {
        "kind": "overlap-decision", "a": a, "b": b, "verdict": verdict, "by": by, "decided_at": _now(),
    }})
    return {"overlap_id": overlap_id}


def find_overlaps(cubes, decisions=None, now=None, minimum=THRESHOLD):
    """Overlaps at or above the minimum, strongest first."""
    decisions = decisions or {}
    now = now or datetime.now(timezone.utc)
    usable = [_accepted(c) for c in cubes]
    by_id = {c["id"]: c for c in usable}
    shared = {}
    for lens in LENSES:
        vectors = _vectors(usable, lens)
        ids = sorted(vectors)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                if _home(by_id[a]) == _home(by_id[b]):
                    continue
                weight, term = _similar(vectors[a], vectors[b])
                if weight > 0:
                    shared.setdefault((a, b), []).append((weight, lens, _word(term)))

    found = []
    for (a, b), lenses in shared.items():
        decision = decisions.get(_pair_id(a, b)) or {}
        if decision.get("verdict") == "dismissed":
            continue
        confirmed = decision.get("verdict") == "confirmed"
        n0 = min(LAMBDA_MAX, sum(w for w, _, _ in lenses) + (CONFIRM_GAIN if confirmed else 0))
        stamps = _stamps(by_id[a]) + _stamps(by_id[b]) + ([decision["decided_at"]] if confirmed else [])
        age = _days_since(stamps, now)
        value = n0 * math.exp(-K * age)
        if value >= minimum:
            strongest = sorted(lenses, key=lambda x: (-x[0], x[1]))
            found.append({"a": a, "b": b, "lambda": round(value, 2), "n0": round(n0, 2), "age_days": round(age, 1),
                          "confirmed": confirmed, "shared": [{"lens": l, "term": t} for _, l, t in strongest]})
    return sorted(found, key=lambda o: (-o["lambda"], o["a"], o["b"]))


def attach_overlaps(cubes, decisions=None, now=None):
    """Give each cube the overlaps it is part of, for the page."""
    for cube in cubes:
        cube["overlaps"] = []
    by_id = {c["id"]: c for c in cubes}
    for o in find_overlaps(cubes, decisions, now):
        for this, other in ((o["a"], o["b"]), (o["b"], o["a"])):
            by_id[this]["overlaps"].append({**{k: o[k] for k in ("lambda", "confirmed", "shared")}, "other": other})
    return cubes


def by_overlap(cubes):
    """Join overlapping cubes into boxes, for the page's Overlaps view."""
    root = {c["id"]: c["id"] for c in cubes}

    def find(x):
        while root[x] != x:
            x = root[x]
        return x
    pairs = {}
    for c in cubes:
        for o in c.get("overlaps", []):
            if c["id"] < o["other"]:
                pairs[(c["id"], o["other"])] = o
                root[find(c["id"])] = find(o["other"])
    boxes, alone = {}, []
    linked = {cid for pair in pairs for cid in pair}
    for c in sorted(cubes, key=lambda c: c["id"]):
        if c["id"] in linked:
            boxes.setdefault(find(c["id"]), []).append(c["id"])
        else:
            alone.append(c["id"])

    def name(members):
        terms = {}
        for (a, b), o in pairs.items():
            if a in members:
                for s in o["shared"][:2]:
                    terms[s["term"]] = terms.get(s["term"], 0) + o["lambda"]
        return " + ".join(sorted(terms, key=lambda t: (-terms[t], t))[:2])
    clusters = [{"name": name(m), "members": m} for m in boxes.values()]
    clusters.sort(key=lambda g: g["name"])
    if alone:
        clusters.append({"name": f"below {THRESHOLD:.2f}", "members": alone})
    links = [{"a": a, "b": b, "lens": o["shared"][0]["lens"], "term": o["shared"][0]["term"], "weight": o["lambda"]}
             for (a, b), o in sorted(pairs.items())]
    return {"clusters": clusters, "links": links}
