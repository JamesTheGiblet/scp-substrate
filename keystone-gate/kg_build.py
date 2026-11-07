"""The page's Build panel: say what a project uses in your own words, see what
the store knows about it, and answer what it doesn't.

check() is read-only: it matches your words to parts and returns the spec
from kg_spec. save() writes only what you confirmed: the project, a uses link
for each part, a count where you gave one, a new subject for a part the store
has never heard of, and a claim for each question you answered. alias() adds
another name to a subject or entity, so the same words find it next time.
"""
import re

from kg_spec import _match, _name, spec

MAX_ALIAS = 60


def _terms(text):
    return [t.strip() for t in re.split(r"[,;\n]", text or "") if t.strip()]


def check(s, name, uses, picked=None):
    """What the words match and what the store knows, as JSON for the page."""
    terms = _terms(uses)
    r = spec(s, name, terms, picked=picked)
    every = {t: _match(s, t) for t in terms}
    return {
        "entity": r["entity"], "exists": r["exists"],
        "parts": [{"term": term, "picked": sorted(matched),
                   "matches": [{"id": i, "name": n} for i, n in sorted({**every.get(term, {}), **matched}.items())]}
                  for term, matched in r["terms"]],
        "known": [_claim(c) for c in r["known"]],
        "unvalidated": [_claim(c) for c in r["unvalidated"]],
        "safety": [{"id": cid, "text": text, "word": word, "other": other, "validated": done}
                   for cid, text, word, other, done in r["safety"]],
        "unknown": [{"term": t, "question": q} for t, q in r["unknown"]],
    }


def _claim(c):
    cid, text, on, others = c
    return {"id": cid, "text": text, "on": on, "from": others}


def _subject(s, name, by):
    """An existing subject id, or a new subject made from the part's name."""
    from kg_subjects import _slug, accept_subject, propose_subject
    sid = f"subject/{_slug(name)}"
    if not s.get(sid):
        pid = propose_subject(s, name[:1].upper() + name[1:], [], by,
                              rationale=f"Named by {by} in the build panel")["proposal_id"]
        accept_subject(s, pid, by)
    return sid


def save(s, data, by):
    """Write what was confirmed. parts: [{term, ids, count}], with ids empty
    for a new part; answers: [{term, claim}]."""
    from kg_agent import create_cube
    from kg_cube import _update_state
    from kg_entities import add_entity, entity_id, link_claim, relate
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("name the project first")
    eid = next((i for i in (entity_id(name, "project"), entity_id(name, "entity")) if s.get(i)), None)
    made = {"project": None, "parts": 0, "subjects": [], "claims": []}
    if not eid:
        eid = add_entity(s, name, "project", by)["id"]
        made["project"] = eid
    notes = dict(s.get(eid)["state"].get("parts") or {})
    of_term = {}
    for part in data.get("parts") or []:
        term = str(part.get("term") or "").strip()
        ids = [i for i in part.get("ids") or [] if isinstance(i, str)]
        if not term:
            continue
        if not ids:
            ids = [_subject(s, term, by)]
            made["subjects"].append(ids[0])
        for i in ids:
            row = s.get(i)
            if not row or row["foundation"] == "foundation:cube" or i == eid:
                raise ValueError(f"{i} is not a part")
            relate(s, eid, "uses", i)
            made["parts"] += 1
            count = part.get("count")
            if isinstance(count, int) and count > 0:
                notes[i] = {**notes.get(i, {}), "count": count}
        of_term[term] = ids
    if notes != (s.get(eid)["state"].get("parts") or {}):
        _update_state(s, eid, {**s.get(eid)["state"], "parts": notes})
    for answer in data.get("answers") or []:
        text = str(answer.get("claim") or "").strip()
        if not text:
            continue
        term = str(answer.get("term") or "").strip()
        subjects = [i for i in of_term.get(term) or [_subject(s, term, by)] if i.startswith("subject/")]
        result = create_cube(s, text, source=f"written by {by} in the build panel", tags=["needs-check"])
        if "error" in result:
            raise ValueError(result["error"])
        link_claim(s, result["cube_id"], subjects=subjects, entities=[eid])
        made["claims"].append(result["cube_id"])
    return {**made, "entity": eid}


def alias(s, data, by):
    """Another name for a subject or entity."""
    from kg_cube import _update_state
    tid, word = (data.get("id") or "").strip(), " ".join(str(data.get("alias") or "").split())
    row = s.get(tid)
    if not row or row["foundation"] not in ("foundation:subject", "foundation:entity", "foundation:project"):
        raise ValueError(f"{tid} is not a subject or entity")
    if not word or len(word) > MAX_ALIAS:
        raise ValueError(f"an alias is 1 to {MAX_ALIAS} characters")
    old = row["state"].get("aliases") or []
    if isinstance(old, str):
        old = [a.strip() for a in old.split(",") if a.strip()]
    if word.lower() in {a.lower() for a in old} | {(row["state"].get("name") or "").lower()}:
        return {"id": tid, "alias": word, "already": True}
    _update_state(s, tid, {**row["state"], "aliases": old + [word]})
    return {"id": tid, "alias": word, "name": _name(s, tid)}
