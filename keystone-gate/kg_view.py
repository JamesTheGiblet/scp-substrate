"""See the cubes as a 3D field. Writes one self-contained HTML page.

The page is a snapshot: run `kg cube view` again after a review. It loads
nothing from the network.
"""
import json
from pathlib import Path

from kg_agent import LENSES, list_cubes, list_proposals, show_cube
from kg_lens_links import all_modes
from kg_overlaps import attach_overlaps, load_decisions
from store.trust import fused_trust


_here = Path(__file__).resolve().parent
VIEW = _here / "view"
TEMPLATE = VIEW / "view_template.html"
PARTS = {name: VIEW / file for name, file in {
    "/*STYLE*/": "view_style.css",
    "/*GRID*/": "view_grid.js",
    "/*BAR*/": "view_bar.js",
    "/*EDIT*/": "view_edit.js",
}.items()}
FIELD = [VIEW / f"view_field_{part}.js" for part in ("world", "hubs", "draw", "form", "time", "move")]
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
    """Suggested neighbour links waiting for you, and the reasons and connecting
    words behind ones you accepted, listed on both cubes."""
    drafts, reasons, words = {}, {}, {}
    for p in list_proposals(s, status="any"):
        if p.get("proposal_type") != "neighbour" or p.get("status") not in ("pending", "accepted"):
            continue
        for this, other in ((p["cube_id"], p["other_cube_id"]), (p["other_cube_id"], p["cube_id"])):
            if p["status"] == "pending":
                drafts.setdefault(this, []).append({"other": other, "proposal_id": p["id"],
                                                    "why": p.get("rationale") or "", "from": p["cube_id"]})
                continue
            if p.get("rationale"):
                reasons.setdefault(this, {})[other] = p["rationale"]
            if p.get("word"):
                words.setdefault(this, {})[other] = {"word": p["word"], "from": p["from"]}
    return drafts, reasons, words


def _you(s):
    """The person entity the store belongs to, or None."""
    row = s.get(user_name(s).lower())
    return row["id"] if row and row["foundation"] == "foundation:person" else None


GROUND_PINS = {"GND", "-", "IN-", "OUT-"}


def _name(s, cid):
    row = s.get(cid)
    return (row["state"].get("name") or cid) if row else cid


def hubs(s):
    """Entities other than you that use subjects: each with its parts, who is
    building it, and the nets its wiring claims join, for the overview panel."""
    from kg_wiring import nets
    you, out = _you(s), []
    for e in s.by_foundation("foundation:entity") + s.by_foundation("foundation:project"):
        parts = sorted(l["target"] for l in s.links_from(e["id"])
                       if l["type"] == "uses" and l["target"].startswith("subject/"))
        if e["id"] == you or not parts:
            continue
        notes = e["state"].get("parts") or {}
        joined = [{"ground": all(p.rsplit(":", 1)[1] in GROUND_PINS for p in n["pins"]),
                   "pins": [f"{_name(s, p.rsplit(':', 1)[0])} {p.rsplit(':', 1)[1]}" for p in n["pins"]]}
                  for n in nets(s, e["id"])]
        out.append({"id": e["id"], "name": e["state"].get("name", e["id"]), "kind": e["state"].get("kind"),
                    "builders": sorted(user_name(s) if l["source"] == you else _name(s, l["source"])
                                     for l in s.links_to(e["id"], "building")),
                    "parts": [{"id": p, "name": _name(s, p), **notes.get(p, {})} for p in parts],
                    "nets": joined})
    return sorted(out, key=lambda h: h["id"])


def things(s):
    """Every entity and subject, for their places in the grid. Claim counts are
    worked out on the page from each cube's own links."""
    from kg_entities import RELATIONS, list_entities
    from kg_subjects import list_subjects
    you = _you(s)
    name = lambda cid: user_name(s) if cid == you else _name(s, cid)
    entities = []
    unsorted = lambda cid: (s.get(f"proposal/sort/{cid}") or {"state": {}})["state"].get("status") == "pending"
    for e in [e for e in list_entities(s) if not unsorted(e["id"])]:
        out = [(l["type"], l["target"], True) for l in s.links_from(e["id"]) if l["type"] in RELATIONS]
        into = [(l["type"], l["source"], False) for l in s.links_to(e["id"]) if l["type"] in RELATIONS]
        entities.append({"id": e["id"], "name": name(e["id"]), "kind": e.get("kind") or e.get("role"),
                         "you": e["id"] == you,
                         "parts": sorted(t for kind, t, _ in out if kind == "uses" and t.startswith("subject/")),
                         "links": [{"word": kind, "other": name(o), "out": fwd} for kind, o, fwd in out + into
                                   if not (kind == "uses" and o.startswith("subject/"))]})
    subjects = [{"id": x["id"], "name": x.get("name", x["id"]), "kind": x.get("kind"),
                 "used_by": sorted(name(l["source"]) for l in s.links_to(x["id"], "uses"))}
                for x in list_subjects(s)]
    return {"entities": sorted(entities, key=lambda e: (not e["you"], e["name"].lower())),
            "subjects": sorted(subjects, key=lambda x: x["name"].lower())}


NO_PLACE = "No entity or subject"


def _place(s, cube_id, hub, you):
    """Where a claim belongs by entity and subject: its hub and part, else its
    entity and its most specific subject (the one with fewest claims)."""
    name = lambda cid: user_name(s) if cid == you else _name(s, cid)
    if hub:
        return " · ".join(name(x) for x in (hub["entity"], hub["part"]) if x)
    subjects = _links(s, cube_id, "about-subject")
    entities = [name(e) for e in _links(s, cube_id, "about-entity")]
    narrow = min(subjects, key=lambda x: (len(s.links_to(x, "about-subject")), x), default=None)
    return " · ".join(entities[:1] + ([name(narrow)] if narrow else [])) or NO_PLACE


def _hub_of(s, cube_id, places):
    """Where a claim sits on the page: by the first part it is about, else by
    the entity it is about. places maps part and entity ids to their hub."""
    subjects = _links(s, cube_id, "about-subject")
    entities = _links(s, cube_id, "about-entity")
    # A part two entities share sits with the entity the claim is about
    for hub, parts in sorted(places, key=lambda p: p[0] not in entities):
        part = next((p for p in parts if p in subjects), None)
        if part:
            return {"entity": hub, "part": part}
    hub = next((h for h, _ in places if h in entities), None)
    return {"entity": hub, "part": None} if hub else None


def collect(s):
    """Everything the page shows, one dict per cube. A cube with an about-entity
    link to you glows green on the page."""
    cubes = []
    you = _you(s)
    places = [(h["id"], [p["id"] for p in h["parts"]]) for h in hubs(s)]
    # A whole comes before its parts, so a claim about a part they share
    # sits with SCPBot, not with the chassis that is part of it
    inner = {h for h, _ in places for l in s.links_from(h) if l["type"] == "part-of"}
    places.sort(key=lambda p: p[0] in inner)
    link_drafts, link_reasons, link_words = _link_notes(s)
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
            "about_you": bool(you) and you in _links(s, cube["cube_id"], "about-entity"),
            "hub": (hub := _hub_of(s, cube["cube_id"], places)),
            "place": _place(s, cube["cube_id"], hub, you),
            "subjects": _links(s, cube["cube_id"], "about-subject"),
            "entities": _links(s, cube["cube_id"], "about-entity"),
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
            "link_words": link_words.get(cube["cube_id"], {}),
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


def render(cubes, api=None, user="You", hubs=(), things=None):
    """Fill the template. '<' is escaped so stored text cannot end the script."""
    data = _safe_json(cubes)
    page = TEMPLATE.read_text(encoding="utf-8")
    field = "\n".join(p.read_text(encoding="utf-8") for p in FIELD)
    page = page.replace("/*FIELD*/", "(() => {\n" + field + "})();")
    for marker, path in PARTS.items():
        page = page.replace(marker, path.read_text(encoding="utf-8"))
    page = page.replace("/*API*/null", _safe_json(api)).replace('/*USER*/"You"', _safe_json(user))
    page = page.replace("/*HUBS*/[]", _safe_json(list(hubs)))
    page = page.replace("/*THINGS*/{}", _safe_json(things or {"entities": [], "subjects": []}))
    modes = all_modes(cubes) if cubes and "faces" in cubes[0] else {}
    return page.replace("/*CUBES*/[]", data).replace("/*MODES*/{}", _safe_json(modes))


def write_view(s, path=OUTPUT):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cubes = collect(s)
    path.write_text(render(cubes, user=user_name(s), hubs=hubs(s), things=things(s)), encoding="utf-8")
    return {"path": path, "cubes": len(cubes)}
