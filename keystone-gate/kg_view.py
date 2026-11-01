"""See the cubes as a 3D field. Writes one self-contained HTML page.

The page is a snapshot: run `kg cube view` again after a review. It loads
nothing from the network, and build/ is ignored by git because the page holds
your opinions.
"""
import json
from pathlib import Path

from kg_agent import LENSES, list_cubes, list_proposals, show_cube
from kg_lens_links import all_modes
from trust import fused_trust


_here = Path(__file__).resolve().parent
TEMPLATE = _here / "view_template.html"
FIELD = _here / "view_field.js"
EDIT = _here / "view_edit.js"
OUTPUT = _here.parent / "build" / "cubes.html"


def _status(cube):
    attestation = cube["attestation"]
    if attestation and not attestation.get("retracted_because"):
        return "attested"
    if attestation:
        return "retracted"
    validation = cube["validation"]
    if validation and validation.get("stale"):
        return "stale"
    if cube["completeness"]["complete"]:
        return "validated"
    return "draft"


def _face(face):
    if not face:
        return None
    filled_by = face.get("filled_by") or ""
    return {
        "content": face.get("content"),
        "filled_by": filled_by,
        "unread": "bulk accept" in filled_by,
    }


def _faces(s, cube):
    """Filled faces, plus pending drafts marked so they never count as filled."""
    faces = {lens: _face(cube["faces"].get(lens)) for lens in LENSES}
    for p in list_proposals(s, cube_id=cube["cube_id"], status="pending"):
        if p.get("lens") in faces and not faces[p["lens"]]:
            faces[p["lens"]] = {"content": p["content"], "filled_by": "draft",
                                "unread": True, "pending": True, "proposal_id": p["id"]}
    return faces


def _links(s, cube_id, link_type):
    return [l["target"] for l in s.links_from(cube_id) if l["type"] == link_type]


def _group(s, cube_id):
    for source_id in _links(s, cube_id, "derived-from"):
        source = s.get(source_id)
        if source:
            return source["state"].get("name", source_id)
    return "Project claims"


def collect(s):
    """Everything the page shows, one dict per cube."""
    cubes = []
    for row in list_cubes(s):
        cube = show_cube(s, row["id"])
        validation = cube["validation"]
        attestation = cube["attestation"]
        cubes.append({
            "id": cube["cube_id"],
            "content": cube["content"],
            "source": cube["source"],
            "tags": cube["tags"] or [],
            "group": _group(s, cube["cube_id"]),
            "score": cube["completeness"]["score"],
            "status": _status(cube),
            "standing": round(fused_trust(s, cube["cube_id"]).get("posterior", 0.5), 2),
            "faces": _faces(s, cube),
            "validation": validation and {
                "validator": validation.get("validator"),
                "note": validation.get("note"),
                "stale": bool(validation.get("stale")),
            },
            "attestation": attestation and {
                "source": attestation.get("source"),
                "note": attestation.get("note"),
                "retracted": attestation.get("retracted_because"),
            },
            "neighbours": _links(s, cube["cube_id"], "neighbour"),
            "contradicts": (cube["contradicts"] or {}).get("other"),
        })
    return cubes


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def render(cubes, api=None):
    """Fill the template. '<' is escaped so stored text cannot end the script."""
    data = _safe_json(cubes)
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*FIELD*/", FIELD.read_text(encoding="utf-8"))
    page = page.replace("/*EDIT*/", EDIT.read_text(encoding="utf-8"))
    page = page.replace("/*API*/null", _safe_json(api))
    modes = all_modes(cubes) if cubes and "faces" in cubes[0] else {}
    return page.replace("/*CUBES*/[]", data).replace("/*MODES*/{}", _safe_json(modes))


def write_view(s, path=OUTPUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cubes = collect(s)
    path.write_text(render(cubes), encoding="utf-8")
    return {"path": path, "cubes": len(cubes)}
