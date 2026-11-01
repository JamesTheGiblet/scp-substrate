"""Cube-as-agent. The base unit of Keystone Gate.

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
sys.path.insert(0, str(_here.parent))

from substrate import Substrate


LENSES = ["FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT"]
LENS_WEIGHT = 0.16
HUMAN_VALIDATION_WEIGHT = 0.20
TOTAL_WEIGHT = LENS_WEIGHT * len(LENSES) + HUMAN_VALIDATION_WEIGHT


def _slugify(text):
    """First few words, alphanumerics only, for a stable cube id."""
    words = re.findall(r"[a-z0-9]+", text.lower())[:6]
    return "-".join(words) or "unnamed"


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    try:
        s.link(cube_id, "classified-by", "default-cube")
    except Exception:
        pass
    return {"cube_id": cube_id}


def fill_face(s, cube_id, lens, content, confidence=None, filled_by="human"):
    """Fill one lens face of a cube. Returns {face_id, lens} or {error}."""
    if lens not in LENSES:
        return {"error": f"invalid lens {lens!r}; must be one of {LENSES}"}
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

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
        with s.conn:
            s.conn.execute(
                "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(state), face_id),
            )
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "lens": lens}


def validate(s, cube_id, validator, note=None):
    """Record human validation of a cube. Returns {face_id, validator} or {error}."""
    if not s.get(cube_id):
        return {"error": f"cube {cube_id} not found"}

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
        with s.conn:
            s.conn.execute(
                "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(state), face_id),
            )
    else:
        s.write({
            "id": face_id,
            "foundation": "foundation:cube-face",
            "state": state,
        })
        s.link(cube_id, "has-face", face_id)
        s.link(face_id, "about", cube_id)
    return {"face_id": face_id, "validator": validator}


def set_contradicts(s, cube_id, other_cube_id, note=None):
    """Flag that this cube contradicts another."""
    c = s.get(cube_id)
    if not c:
        return {"error": f"cube {cube_id} not found"}
    if not s.get(other_cube_id):
        return {"error": f"other cube {other_cube_id} not found"}
    new_state = dict(c["state"])
    new_state["contradicts"] = {"other": other_cube_id, "note": note, "set_at": _now()}
    with s.conn:
        s.conn.execute(
            "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
            (json.dumps(new_state), cube_id),
        )
    if not s.conn.execute(
        "SELECT 1 FROM links WHERE source=? AND type='contradicts' AND target=?",
        (cube_id, other_cube_id),
    ).fetchone():
        s.link(cube_id, "contradicts", other_cube_id)
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
            validated = True
        elif lens in LENSES:
            filled.append(lens)

    missing = [l for l in LENSES if l not in filled]
    score = len(filled) * LENS_WEIGHT + (HUMAN_VALIDATION_WEIGHT if validated else 0)

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
