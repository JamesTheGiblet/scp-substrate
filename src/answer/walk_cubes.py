"""Cube walker: what james has examined, and where he stands on it."""
import json
import re

from answer.spelling import correct
from store.claim_links import relations
from store.evidence import evidence_of
from store.kinds import broader, narrower
from store.trust import fused_trust


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
    found = evidence_of(s, cube_id)
    # Kinds in plain words: person-document is a label, not a name the gate can find
    rests = "; ".join(f"{e['title']} ({e['kind'].replace('-', ' ')}{', changed since checked' if e['changed'] else ''})"
                      for e in found) or "nothing yet, your word only"
    lines = [f"  {cube_id}", f"    {content}",
             f"    {_status(s, cube_id)}, standing {standing:.2f}", f"    rests on: {rests}"]
    for label, lens in (("view", "OPINION"), ("against", "COUNTER")):
        text = _face(s, cube_id, lens)
        lines.append(f"    {label}: {text or '(not written yet)'}")
    # How it connects to other claims, as sentences
    lines += [f"    link: this {word} {other}" if out else f"    link: {other} {word} this"
              for word, other, out in relations(s, cube_id)]
    return lines


def _cubes(s):
    return [(r["id"], json.loads(r["state_json"])) for r in s.conn.execute(
        "SELECT id, state_json FROM capsules "
        "WHERE foundation = 'foundation:cube' AND is_meta = 0 ORDER BY id")]


THINGS = ("foundation:subject", "foundation:entity", "foundation:project", "foundation:person")


def _names(state):
    aliases = state.get("aliases") or []
    if isinstance(aliases, str):
        aliases = aliases.split(",")
    return [n for n in [state.get("name"), *aliases] if n and n.strip()]


def _named(s, topic):
    """The subjects and entities the question names: every word of a name or
    alias is in it. James is in _ASKING, so he is never named this way."""
    found = {}
    for foundation in THINGS:
        for row in s.by_foundation(foundation):
            for name in _names(row["state"]):
                words = _stems(name)
                if words and words <= topic:
                    found[row["id"]] = {"name": row["state"].get("name", row["id"]), "words": words}
                    break
    return found


def _about(s, cube_id):
    return {l["target"] for l in s.links_from(cube_id) if l["type"] in ("about-subject", "about-entity")}


def _wholes_parts(s, tid):
    """An entity and every entity that is part of it, all the way down. SCPBot
    reaches its chassis, and the Forge Stack its projects."""
    found, todo = {tid}, [tid]
    while todo:
        for l in s.links_to(todo.pop(), "part-of"):
            if l["source"] not in found:
                found.add(l["source"])
                todo.append(l["source"])
    return found


def _reach(s, named):
    """What a claim may be about to count as on a named thing: the thing, and
    for an entity, its own parts and the parts of what it is made of, and the
    broader kinds of those parts. SCPBot reaches its MG90S, servos in general,
    and its chassis's legs. A subject reaches its narrower kinds."""
    reach = {}
    for tid in named:
        reach[tid] = {tid}
        if tid.startswith("subject/"):
            # A question about servos finds the claims about the MG90S
            reach[tid] |= narrower(s, tid)
            continue
        for eid in _wholes_parts(s, tid):
            used = {l["target"] for l in s.links_from(eid) if l["type"] == "uses"}
            # SCPBot uses an MG90S, so what holds for any servo holds for SCPBot
            reach[tid] |= {eid} | used | {b for u in used for b in broader(s, u)}
    return reach


def walk_what_believe(s, entity_id, text):
    """Find cubes on a topic. With no topic, list the attested ones. A claim
    about a subject or entity the question names ranks above a word match."""
    # Code names such as kg_agent are subjects, not topic words
    text, fixes = correct(s, re.sub(r"\w+_\w+", " ", text), skip=_ASKING)
    read_as = " ".join(f'Read "{a}" as "{b}".' for a, b in fixes)
    topic = _stems(text)
    cubes = _cubes(s)
    if not topic:
        found = [(cid, st) for cid, st in cubes if s.get(f"{cid}/attestation")
                 and not s.get(f"{cid}/attestation")["state"].get("retracted_because")]
        if not found:
            return {"ok": True, "summary": "No cubes are attested yet.", "detail": None}
        lines = [f"  {cid}: {st.get('content')}" for cid, st in found]
        return {"ok": True, "summary": f"{len(found)} attested cube(s):",
                "detail": "\n".join(lines)}

    named = _named(s, topic)
    reach = _reach(s, named)
    scored = []
    for cid, st in cubes:
        # Your own words for linking count as the claim's words too
        words = f"{cid} {st.get('content', '')} {' '.join(st.get('tags') or [])} {' '.join(st.get('words') or []).replace('-', ' ')}"
        about = _about(s, cid)
        on_things = [tid for tid, parts in reach.items() if parts & about]
        # A named thing's name is counted by the link to it, not again as a
        # word, so "SCPBot's legs" ranks by legs among the claims on SCPBot.
        # A claim that says the name without the link still gets the word.
        rest = topic - set().union(*(named[t]["words"] for t in on_things))
        overlap = len(rest & _stems(words))
        # Each named thing the claim is on counts as much as a shared word,
        # and wins a tie, so a link adds to the words but can't drown them
        on = len(on_things)
        if overlap or on:
            scored.append((overlap + on, on, cid, st))
    if not scored:
        return {"ok": True, "summary": f"{read_as} No cube covers that yet.".strip(), "detail": None}

    # Cubes a person has examined come first among equals
    scored.sort(key=lambda row: (-row[0], -row[1], not s.get(f"{row[2]}/face/human-validation"), row[2]))
    best = scored[:3]
    lines = []
    for _, _, cid, st in best:
        shown = _render(s, cid, st.get("content"))
        if about := sorted(_name(s, t) for t in _about(s, cid)):
            shown.insert(4, f"    about: {', '.join(about)}")
        lines += shown
    on = f" on {', '.join(sorted(n['name'] for n in named.values()))}" if named else ""
    return {"ok": True, "summary": f"{read_as} {len(scored)} cube(s) match{on}, closest {len(best)}:".strip(),
            "detail": "\n".join(lines)}


def _name(s, capsule_id):
    row = s.get(capsule_id)
    return (row["state"].get("name") if row else None) or capsule_id
