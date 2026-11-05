"""Claims from a CSV file: one row per claim, with its entity and subject
made if they don't exist yet.

The rows are turned into the same shape an outline makes (kg_outline.py),
and go in through the same checks: every id is looked up before anything is
written, so a file goes in whole or not at all.

Columns, in any order and any case. Only entity and claim are needed:

    entity        what the claim is about: a name such as SCPBot, or an id
    entity_kind   for a new entity: robot, project, person and so on
    subject       the part or topic it is about, by name or id
    subject_kind  for a new subject: component, topic and so on
    uses          yes when the entity uses the subject
    claim         the claim, one sentence
    id            the claim's id; made from the claim's words if left out
    source        where it comes from, in words
    tags          labels, such as needs-check
    words         your own words for linking claims; claims sharing one get a suggested link
    from          evidence ids it is derived from
    also          more subject ids it is about
    FACT, COUNTER, OPINION, FICTION, CONTEXT   drafts to confirm later
    supports, goes-against, depends-on and the other connecting words
                  claim ids this one links to

Names are matched against existing entities and subjects, and their aliases,
ignoring case, so "scpbot" finds entity/scpbot. A cell can hold several
values separated by commas or semicolons.
"""
import csv
import io

from kg_outline import apply, plan, problems

ENTITIES = ("foundation:entity", "foundation:project", "foundation:person")


def _names(state):
    aliases = state.get("aliases") or []
    if isinstance(aliases, str):
        aliases = aliases.split(",")
    return {n.strip().lower() for n in [state.get("name"), *aliases] if n and n.strip()}


def _find(s, foundations, value):
    """An existing capsule named or identified by value, or None."""
    row = s.get(value)
    if row and row["foundation"] in foundations:
        return row
    for foundation in foundations:
        for r in s.by_foundation(foundation):
            if value.lower() in _names(r["state"]):
                return r
    return None


def _list(value):
    return ", ".join(v.strip() for v in value.replace(";", ",").split(",") if v.strip())


def parse(s, text):
    """The CSV as outline entities. Raises ValueError naming the bad row."""
    from kg_cube import LENSES
    rows = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    if not rows.fieldnames:
        raise ValueError("the file is empty")
    rows.fieldnames = [(f or "").strip() for f in rows.fieldnames]
    heads = {f.lower() for f in rows.fieldnames}
    if not {"entity", "claim"} <= heads:
        raise ValueError("the first row must name the columns, with at least entity and claim")
    entities = {}
    for n, raw in enumerate(rows, 2):
        row = {}
        for k, v in raw.items():
            if k is None:
                raise ValueError(f"row {n}: more cells than columns; put a cell with commas in quotes")
            row[k.upper() if k.upper() in LENSES else k.lower()] = (v or "").strip()
        if not any(row.values()):
            continue
        if not row.get("entity") or not row.get("claim"):
            raise ValueError(f"row {n}: needs both an entity and a claim")
        e = _entity(s, entities, row, n)
        claim = {"text": row["claim"], "lenses": {l: row[l] for l in LENSES if row.get(l)},
                 "keys": {k: (_list(v) if k in _LISTS else v) for k, v in row.items()
                          if v and k not in _ROW_ONLY and k not in LENSES}}
        if row.get("subject"):
            _subject(s, e, row)["claims"].append(claim)
        else:
            e["claims"].append(claim)
    if not entities:
        raise ValueError("no rows with a claim")
    return list(entities.values())


# Columns that describe the row's entity or subject, not the claim
_ROW_ONLY = {"entity", "entity_kind", "subject", "subject_kind", "uses", "claim"}
_LISTS = {"tags", "words", "from", "also", "supports", "goes-against", "protects", "limits",
          "depends-on", "causes", "is-part-of", "is-an-example-of"}


def _entity(s, entities, row, n):
    found = _find(s, ENTITIES, row["entity"])
    if found:
        key = found["id"]
        if key not in entities:
            entities[key] = {"name": found["state"].get("name") or found["id"], "keys": {"id": found["id"]},
                             "subjects": [], "claims": []}
    else:
        if "/" in row["entity"]:
            raise ValueError(f"row {n}: no entity has the id {row['entity']}; give a name to make a new one")
        key = row["entity"].lower()
        if key not in entities:
            entities[key] = {"name": row["entity"], "keys": {"kind": row.get("entity_kind") or "entity"},
                             "subjects": [], "claims": []}
    return entities[key]


def _subject(s, e, row):
    found = _find(s, ("foundation:subject",), row["subject"])
    name = found["state"].get("name", found["id"]) if found else row["subject"]
    for sub in e["subjects"]:
        if sub["name"].lower() == name.lower():
            break
    else:
        sub = {"name": name, "keys": {"id": found["id"]} if found else {}, "claims": []}
        if not found and row.get("subject_kind"):
            sub["keys"]["kind"] = row["subject_kind"]
        e["subjects"].append(sub)
    if row.get("uses", "").lower() in ("yes", "true", "y", "1"):
        sub["keys"]["uses"] = "yes"
    return sub


def preview(s, text):
    """What importing would make, and anything that stops it: (lines, problems).
    A review sheet from kg cube sheet goes to kg_sheet instead."""
    import kg_sheet
    if kg_sheet.is_sheet(text):
        return kg_sheet.preview(s, text)
    entities = parse(s, text)
    return plan(s, entities), problems(s, entities)


def write(s, text, by):
    """Import it. Returns what was made, or for a review sheet what was done."""
    import kg_sheet
    if kg_sheet.is_sheet(text):
        return kg_sheet.write(s, text, by)
    return apply(s, parse(s, text), by, via="a CSV")


def summary(made):
    return (f"made {len(made['entities'])} entities, {len(made['subjects'])} subjects, {len(made['claims'])} claims "
            f"and {made['drafts']} lens drafts, linked {made['links']} pairs of claims, suggested {made['suggested']} links "
            f"from your words; skipped {len(made['skipped'])} claims that exist")
