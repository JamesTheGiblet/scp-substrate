"""Cubes. The base unit of Keystone Gate.

A cube is a record whose six faces are filled by lenses and validated by
humans. Five lenses at 16% each plus human validation at 20% = 100%.
Completeness gates attestation: no trust until a cube is complete.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))

from store.substrate import Substrate


LENSES = ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"]
LENS_WEIGHT = 0.16
HUMAN_VALIDATION_WEIGHT = 0.20
TOTAL_WEIGHT = LENS_WEIGHT * len(LENSES) + HUMAN_VALIDATION_WEIGHT


def _shape(s):
    """Weights and rules from default-cube, the constants if it has none."""
    capsule = s.get("default-cube")
    state = capsule["state"] if capsule else {}
    weighting = state.get("weighting", {})
    return {
        "per_lens": weighting.get("per_lens", LENS_WEIGHT),
        "human_validation": weighting.get("human_validation", HUMAN_VALIDATION_WEIGHT),
        "minimum_lenses": state.get("rules", {}).get("minimum_lenses", 0),
    }


def _slugify(text):
    """First few words, alphanumerics only, for a stable cube id."""
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "unnamed"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _update_state(s, capsule_id, state):
    """Replace a capsule's state through Substrate.write, so the event is logged."""
    s.write({
        "id": capsule_id,
        "foundation": s.get(capsule_id)["foundation"],
        "state": state,
    })


def create_cube(s, content, source=None, tags=None, cube_id=None):
    """Create a new cube capsule. Returns {cube_id} or {error}."""
    if not cube_id:
        base = _slugify(content)
        candidate = f"cube/{base}"
        i = 2
        while s.get(candidate):
            candidate = f"cube/{base}-{i}"
            i += 1
        cube_id = candidate

    if s.get(cube_id):
        return {"error": f"cube {cube_id} already exists"}

    s.write({
        "id": cube_id,
        "foundation": "foundation:cube",
        "state": {
            "kind": "cube",
            "content": content,
            "source": source,
            "tags": tags or [],
            "contradicts": None,
            "created_at": _now(),
        },
    })
    if s.get("default-cube"):
        s.link(cube_id, "classified-by", "default-cube")
    return {"cube_id": cube_id}


FOUNDATIONAL = "foundational"


def is_foundational(s, cube_id):
    """Safety and security cubes. Their rules are enforced here, not left to habit."""
    cube = s.get(cube_id)
    return bool(cube) and FOUNDATIONAL in (cube["state"].get("tags") or [])


def fill_face(s, cube_id, lens, content, confidence=None, filled_by="human"):
    """Fill one lens face of a cube. Returns {face_id, lens} or {error}."""
    if lens not in LENSES:
        return {"error": f"invalid lens {lens!r}; must be one of {LENSES}"}
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    if "bulk accept" in filled_by and is_foundational(s, cube_id):
        return {"error": f"{cube_id} is foundational, so each face must be read and accepted on its own"}

    face_id = f"{cube_id}/face/{lens}"
    state = {
        "kind": "cube-face",
        "cube_id": cube_id,
        "lens": lens,
        "content": content,
        "confidence": confidence,
        "filled_by": filled_by,
        "filled_at": _now(),
    }
    existing = s.get(face_id)
    if existing:
        _update_state(s, face_id, state)
        if existing["state"].get("content") != content:
            _mark_validation_stale(s, cube_id, lens)
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "lens": lens}


def _mark_validation_stale(s, cube_id, lens):
    """A human validated what the cube said then. Changing a face voids that."""
    face_id = f"{cube_id}/face/human-validation"
    face = s.get(face_id)
    if face:
        _update_state(s, face_id, {**face["state"], "stale": True,
                                   "stale_because": f"{lens} changed at {_now()}"})
    attestation = s.get(f"{cube_id}/attestation")
    if attestation:
        _update_state(s, attestation["id"], {**attestation["state"], "score": 0.0,
                                             "retracted_because": f"{lens} changed at {_now()}"})


def validate(s, cube_id, validator, note=None):
    """Record human validation of a cube. Returns {face_id, validator} or {error}."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    minimum = _shape(s)["minimum_lenses"]
    if len(completeness(s, cube_id)["filled_lenses"]) < minimum:
        return {"error": f"{cube_id} needs at least {minimum} lenses before validation"}
    if is_foundational(s, cube_id):
        if len(completeness(s, cube_id)["filled_lenses"]) < len(LENSES):
            return {"error": f"{cube_id} is foundational, so all five faces must be accepted first"}
        said = " ".join((note or "").lower().split())
        draft = s.get(f"{cube_id}/validation-draft")
        if not said or (draft and said == " ".join(draft["state"]["content"].lower().split())):
            return {"error": f"{cube_id} is foundational, so the note must be in your own words"}

    face_id = f"{cube_id}/face/human-validation"
    state = {
        "kind": "cube-face",
        "cube_id": cube_id,
        "lens": "HUMAN_VALIDATION",
        "validator": validator,
        "note": note,
        "validated_at": _now(),
    }
    existing = s.get(face_id)
    if existing:
        _update_state(s, face_id, state)
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "validator": validator}


def set_contradicts(s, cube_id, other_cube_id, note=None, by="james"):
    """Flag that this cube contradicts another: it goes against the other."""
    from store.claim_links import relate
    c = s.get(cube_id)
    if not c:
        return {"error": f"cube {cube_id} not found"}
    if not s.get(other_cube_id):
        return {"error": f"other cube {other_cube_id} not found"}
    new_state = dict(c["state"])
    new_state["contradicts"] = {"other": other_cube_id, "note": note, "set_at": _now()}
    _update_state(s, cube_id, new_state)
    relate(s, cube_id, "goes against", other_cube_id, by, note=note)
    return {"cube_id": cube_id, "contradicts": other_cube_id}


def completeness(s, cube_id):
    """Return completeness score and face state."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules "
        "WHERE foundation = 'foundation:cube-face' "
        "  AND json_extract(state_json, '$.cube_id') = ?",
        (cube_id,),
    ).fetchall()

    filled = []
    validated = False
    for r in rows:
        st = json.loads(r["state_json"])
        lens = st.get("lens")
        if lens == "HUMAN_VALIDATION":
            validated = not st.get("stale")
        elif lens in LENSES:
            filled.append(lens)

    missing = [l for l in LENSES if l not in filled]
    shape = _shape(s)
    score = len(filled) * shape["per_lens"] + (shape["human_validation"] if validated else 0)

    return {
        "cube_id": cube_id,
        "score": round(score, 4),
        "filled_lenses": filled,
        "missing_lenses": missing,
        "validated": validated,
        "complete": score >= 0.9999,
    }


def attestation_eligible(s, cube_id):
    """True only if completeness == 1.0. Completeness gates attestation."""
    c = completeness(s, cube_id)
    if "error" in c:
        return False
    return c["complete"]


def attest(s, cube_id, attested_by, note=None):
    """A human vouches for a complete cube. Returns {attestation_id} or {error}.

    Completeness gates attestation, and attestation is what reaches trust:
    it is an observation of the cube, so fused_trust counts it as evidence.
    Changing a face retracts it, and a new attestation can then replace it.
    """
    if not attestation_eligible(s, cube_id):
        return {"error": f"{cube_id} is not complete, so it cannot be attested"}
    attestation_id = f"{cube_id}/attestation"
    s.write({
        "id": attestation_id,
        "foundation": "foundation:observation",
        "state": {
            "kind": "attestation",
            "target": cube_id,
            "score": 1.0,
            "source": attested_by,
            "note": note,
            "attested_at": _now(),
        },
    })
    s.link(attestation_id, "observes", cube_id)
    return {"attestation_id": attestation_id}


def show_cube(s, cube_id):
    """Return full cube data for rendering."""
    c = s.get(cube_id)
    if not c:
        return {"error": f"cube {cube_id} not found"}
    comp = completeness(s, cube_id)

    faces = {}
    for lens in LENSES:
        fid = f"{cube_id}/face/{lens}"
        f = s.get(fid)
        faces[lens] = f["state"] if f else None

    vfid = f"{cube_id}/face/human-validation"
    vf = s.get(vfid)
    validation = vf["state"] if vf else None

    return {
        "cube_id": cube_id,
        "content": c["state"].get("content"),
        "source": c["state"].get("source"),
        "tags": c["state"].get("tags"),
        "contradicts": c["state"].get("contradicts"),
        "created_at": c["state"].get("created_at"),
        "faces": faces,
        "validation": validation,
        "attestation": (s.get(f"{cube_id}/attestation") or {}).get("state"),
        "completeness": comp,
    }


def list_cubes(s):
    rows = s.conn.execute(
        "SELECT id FROM capsules WHERE foundation = 'foundation:cube' AND is_meta = 0 ORDER BY id"
    ).fetchall()
    out = []
    for r in rows:
        comp = completeness(s, r["id"])
        out.append({
            "id": r["id"],
            "score": comp["score"] if "score" in comp else 0,
            "complete": comp.get("complete", False),
        })
    return out


def link_neighbour(s, cube_a, cube_b, note=None):
    """Create a bidirectional neighbour relationship between two cubes.

    Neighbours know only IDs; they query the ledger for detail. That's why
    we only link — we don't copy state. The relationship is stored as
    two directed `neighbour` links (a->b and b->a) so traversal works
    from either end without special-casing direction.
    """
    for cid in (cube_a, cube_b):
        if not s.get(cid):
            return {"error": f"cube {cid} not found"}

    if cube_a == cube_b:
        return {"error": "cannot link a cube to itself"}

    for src, tgt in ((cube_a, cube_b), (cube_b, cube_a)):
        existing = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='neighbour' AND target=?",
            (src, tgt),
        ).fetchone()
        if not existing:
            s.link(src, "neighbour", tgt)

    return {"cube_a": cube_a, "cube_b": cube_b, "note": note}


def list_neighbours(s, cube_id):
    """Return cube IDs directly neighboured to a cube."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}
    rows = s.conn.execute(
        "SELECT target FROM links WHERE source=? AND type='neighbour' ORDER BY target",
        (cube_id,),
    ).fetchall()
    return {"cube": cube_id, "neighbours": [r["target"] for r in rows]}
