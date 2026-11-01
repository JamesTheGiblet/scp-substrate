"""Cube walker: what james has examined, and where he stands on it."""
import json
import re

from trust import fused_trust


_ASKING = {"what", "believe", "think", "about", "trust", "should", "does", "view",
           "opinion", "stand", "cube", "cubes", "claim", "claims", "james", "know",
           "the", "and", "for", "how", "where", "with", "use", "are", "you", "not"}


def _stem(word):
    """Drop a common ending, so signing meets signed and signal stays apart."""
    for ending in ("ing", "ed", "es", "s"):
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


def _stems(text):
    words = re.findall(r"[a-z][a-z0-9]{2,}", text.lower())
    return {_stem(w) for w in words if w not in _ASKING}


def _status(s, cube_id):
    attestation = s.get(f"{cube_id}/attestation")
    if attestation and not attestation["state"].get("retracted_because"):
        return f"attested by {attestation['state'].get('source')}"
    if attestation:
        return "attestation retracted"
    validation = s.get(f"{cube_id}/face/human-validation")
    if validation and not validation["state"].get("stale"):
        return "validated, not attested"
    return "not yet validated"


def _face(s, cube_id, lens):
    face = s.get(f"{cube_id}/face/{lens}")
    return face["state"].get("content") if face else None


def _render(s, cube_id, content):
    standing = fused_trust(s, cube_id).get("posterior", 0.5)
    lines = [f"  {cube_id}", f"    {content}",
             f"    {_status(s, cube_id)}, standing {standing:.2f}"]
    for label, lens in (("view", "OPINION"), ("against", "COUNTER")):
        text = _face(s, cube_id, lens)
        lines.append(f"    {label}: {text or '(not written yet)'}")
    return lines


def _cubes(s):
    return [(r["id"], json.loads(r["state_json"])) for r in s.conn.execute(
        "SELECT id, state_json FROM capsules "
        "WHERE foundation = 'foundation:cube' AND is_meta = 0 ORDER BY id")]


def walk_what_believe(s, entity_id, text):
    """Find cubes on a topic. With no topic, list the attested ones."""
    # Code names such as kg_agent are subjects, not topic words
    topic = _stems(re.sub(r"\w+_\w+", " ", text))
    cubes = _cubes(s)
    if not topic:
        found = [(cid, st) for cid, st in cubes if s.get(f"{cid}/attestation")
                 and not s.get(f"{cid}/attestation")["state"].get("retracted_because")]
        if not found:
            return {"ok": True, "summary": "No cubes are attested yet.", "detail": None}
        lines = [f"  {cid}: {st.get('content')}" for cid, st in found]
        return {"ok": True, "summary": f"{len(found)} attested cube(s):",
                "detail": "\n".join(lines)}

    scored = []
    for cid, st in cubes:
        about = f"{cid} {st.get('content', '')} {' '.join(st.get('tags') or [])}"
        overlap = len(topic & _stems(about))
        if overlap:
            scored.append((overlap, cid, st))
    if not scored:
        return {"ok": True, "summary": "No cube covers that yet.", "detail": None}

    # Cubes a person has examined come first among equals
    scored.sort(key=lambda row: (-row[0], not s.get(f"{row[1]}/face/human-validation"), row[1]))
    best = scored[:3]
    lines = []
    for _, cid, st in best:
        lines += _render(s, cid, st.get("content"))
    return {"ok": True, "summary": f"{len(scored)} cube(s) match, closest {len(best)}:",
            "detail": "\n".join(lines)}
