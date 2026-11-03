"""See the cubes as a 3D field. Writes one self-contained HTML page.

The page is a snapshot: run `kg cube view` again after a review. It loads
nothing from the network.
"""
import json
from pathlib import Path

from kg_agent import LENSES, list_cubes, list_proposals, show_cube
from kg_lens_links import all_modes
from kg_overlaps import attach_overlaps, load_decisions
from trust import fused_trust


_here = Path(__file__).resolve().parent
TEMPLATE = _here / "view_template.html"
PARTS = {name: _here / file for name, file in {
    "/*STYLE*/": "view_style.css",
    "/*GRID*/": "view_grid.js",
    "/*BAR*/": "view_bar.js",
    "/*EDIT*/": "view_edit.js",
}.items()}
FIELD = [_here / f"view_field_{part}.js" for part in ("world", "draw", "form", "time", "move")]
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
        "at": face.get("filled_at"),
    }


def _faces(s, cube):
    """Filled faces, plus pending drafts marked so they never count as filled."""
    faces = {lens: _face(cube["faces"].get(lens)) for lens in LENSES}
    for p in list_proposals(s, cube_id=cube["cube_id"], status="pending"):
        if p.get("lens") in faces and not faces[p["lens"]]:
            faces[p["lens"]] = {"content": p["content"], "filled_by": "draft", "at": p.get("proposed_at"),
                                "unread": True, "pending": True, "proposal_id": p["id"],
                                "drafted_by": (p.get("proposed_by") or "").removeprefix("model-draft:").removesuffix("-draft-opinion")}
    return faces


def _links(s, cube_id, link_type):
    return [l["target"] for l in s.links_from(cube_id) if l["type"] == link_type]


def _group(s, cube_id):
    for source_id in _links(s, cube_id, "derived-from"):
        source = s.get(source_id)
        if source:
            return source["state"].get("name") or source["state"].get("owner") or source_id
    return "Project claims"


def _repo(s, cube_id):
    for source_id in _links(s, cube_id, "derived-from"):
        if source_id.startswith("repo/"):
            return s.get(source_id)["state"].get("name", source_id)
    return None


def _link_notes(s):
    """Suggested neighbour links waiting for you, and the reasons behind ones you
    accepted, listed on both cubes."""
    drafts, reasons = {}, {}
    for p in list_proposals(s, status="any"):
        if p.get("proposal_type") != "neighbour" or p.get("status") not in ("pending", "accepted"):
            continue
        for this, other in ((p["cube_id"], p["other_cube_id"]), (p["other_cube_id"], p["cube_id"])):
            if p["status"] == "pending":
                drafts.setdefault(this, []).append({"other": other, "proposal_id": p["id"], "why": p.get("rationale") or ""})
            elif p.get("rationale"):
                reasons.setdefault(this, {})[other] = p["rationale"]
    return drafts, reasons


def collect(s):
    """Everything the page shows, one dict per cube."""
    cubes = []
    link_drafts, link_reasons = _link_notes(s)
    for row in list_cubes(s):
        cube = show_cube(s, row["id"])
        validation = cube["validation"]
        attestation = cube["attestation"]
        cubes.append({
            "id": cube["cube_id"],
            "created_at": cube.get("created_at", ""),
            "content": cube["content"],
            "created": s.get(cube["cube_id"])["state"].get("created_at"),
            "source": cube["source"],
            "tags": cube["tags"] or [],
            "group": _group(s, cube["cube_id"]),
            "repo": _repo(s, cube["cube_id"]),
            "score": cube["completeness"]["score"],
            "status": _status(cube),
            "standing": round(fused_trust(s, cube["cube_id"]).get("posterior", 0.5), 2),
            "faces": _faces(s, cube),
            "validation": validation and {
                "validator": validation.get("validator"),
                "note": validation.get("note"),
                "stale": bool(validation.get("stale")),
                "at": validation.get("validated_at"),
            },
            "attestation": attestation and {
                "source": attestation.get("source"),
                "note": attestation.get("note"),
                "retracted": attestation.get("retracted_because"),
                "at": attestation.get("attested_at"),
            },
            "note_draft": (s.get(f"{cube['cube_id']}/validation-draft") or {"state": {}})["state"].get("content"),
            "neighbours": _links(s, cube["cube_id"], "neighbour"),
            "link_drafts": link_drafts.get(cube["cube_id"], []),
            "link_reasons": link_reasons.get(cube["cube_id"], {}),
            "contradicts": (cube["contradicts"] or {}).get("other"),
        })
    return attach_overlaps(cubes, load_decisions(s))


def _safe_json(value):
    return json.dumps(value, ensure_ascii=False).replace("<", "\\u003c")


def user_name(s):
    """The first name of the person this store belongs to."""
    row = s.conn.execute("SELECT json_extract(state_json, '$.owner') AS owner FROM capsules "
                         "WHERE json_extract(state_json, '$.kind') = 'person' LIMIT 1").fetchone()
    return row["owner"].split()[0] if row and row["owner"] else "You"


def render(cubes, api=None, user="You"):
    """Fill the template. '<' is escaped so stored text cannot end the script."""
    data = _safe_json(cubes)
    page = TEMPLATE.read_text(encoding="utf-8")
    field = "\n".join(p.read_text(encoding="utf-8") for p in FIELD)
    page = page.replace("/*FIELD*/", "(() => {\n" + field + "})();")
    for marker, path in PARTS.items():
        page = page.replace(marker, path.read_text(encoding="utf-8"))
    page = page.replace("/*API*/null", _safe_json(api)).replace('/*USER*/"You"', _safe_json(user))
    modes = all_modes(cubes) if cubes and "faces" in cubes[0] else {}
    return page.replace("/*CUBES*/[]", data).replace("/*MODES*/{}", _safe_json(modes))


def write_view(s, path=OUTPUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cubes = collect(s)
    path.write_text(render(cubes, user=user_name(s)), encoding="utf-8")
    return {"path": path, "cubes": len(cubes)}
