"""Evidence: what a claim rests on. A README, a changelog, a datasheet, the
seller's listing, one customer's review, a measurement on the real thing.

Each piece exists once, as evidence/<slug>, and every claim drawn from it
links to it with derived-from. Its kind says how much it can carry, and
standing (store/trust.py) adds that up. James's word on its own, and a
model's general knowledge, are not evidence: a claim resting only on them
stands at 0.5 until something backs it. See docs/VOCABULARY.md, Evidence.

Evidence that cites a file in an indexed repo records the version it was
checked against. When re-indexing finds the file changed or gone, the
evidence counts half until someone checks it again.
"""
from datetime import datetime, timezone

# What each kind of evidence adds to a claim's standing score. Validation
# by a person adds 1.0, so one measurement counts as much as a validation.
KINDS = {
    "measurement": 1.0,      # measured or tested on the real thing
    "datasheet": 0.75,       # the maker's own figures
    "code": 0.75,            # a file in a repo, read on a date
    "doc": 0.75,             # a README, guide or written doc from the source
    "person-document": 0.5,  # James's own signed statement about himself
    "listing": 0.25,         # a seller's copy or images
    "review": 0.25,          # one customer's report
}


# What changed evidence still counts for, until it is checked again
CHANGED = 0.5


def kind_of(row):
    """The evidence kind of a capsule a claim is derived from, or None when it
    is not evidence, such as a whole repo the claim is only about."""
    if row["foundation"] == "foundation:evidence":
        return row["state"].get("kind")
    # James's signed person document, imported as knowledge of kind person
    if row["foundation"] == "foundation:person" or row["state"].get("kind") == "person":
        return "person-document"
    return None


def add_evidence(s, slug, kind, title, by, url=None, path=None, repo=None, note=None):
    """Make evidence/<slug>. Making it again with the same id is a no-op."""
    if kind not in KINDS:
        return {"error": f"kind must be one of: {', '.join(KINDS)}"}
    eid = slug if slug.startswith("evidence/") else f"evidence/{slug}"
    if s.get(eid):
        return {"id": eid, "status": "exists"}
    state = {"kind": kind, "title": title, "by": by,
             "added_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    state.update({k: v for k, v in (("url", url), ("path", path), ("repo", repo), ("note", note)) if v})
    s.write({"id": eid, "foundation": "foundation:evidence", "state": state})
    return {"id": eid, "status": "created"}


def cite(s, claim_id, evidence_id):
    """Say a claim is derived from a piece of evidence."""
    claim, evidence = s.get(claim_id), s.get(evidence_id)
    if not claim or claim["foundation"] != "foundation:cube":
        return {"error": f"claim {claim_id} not found"}
    if not evidence or not kind_of(evidence):
        return {"error": f"evidence {evidence_id} not found"}
    s.link(claim_id, "derived-from", evidence_id)
    return {"claim": claim_id, "evidence": evidence_id}


def file_of(s, row):
    """The indexed file a piece of evidence cites, file/<repo>/<path>, or None."""
    repo, path = row["state"].get("repo"), row["state"].get("path")
    if not (repo and path and repo.startswith("repo/")):
        return None
    return s.get(f"file/{repo[len('repo/'):]}/{path}")


def _version(f):
    # A local repo's index keeps sha256; a GitHub one keeps the git sha
    return f["state"].get("sha256") or f["state"].get("sha")


def checked(s, evidence_id, by):
    """Record that the file a piece of evidence cites was checked as it is now."""
    row = s.get(evidence_id)
    f = row and file_of(s, row)
    if not f:
        return {"error": f"{evidence_id} cites no file in an indexed repo"}
    state = dict(row["state"], checked_version=_version(f), checked_by=by,
                 checked_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    s.write({"id": evidence_id, "foundation": row["foundation"], "state": state})
    s.link(evidence_id, "cites-file", f["id"])
    return {"id": evidence_id, "file": f["id"], "version": state["checked_version"]}


def changed(s, row):
    """True when the file a piece of evidence was checked against has changed
    since, or is gone from the index. Evidence never checked is not changed."""
    version = row["state"].get("checked_version")
    if not version:
        return False
    f = file_of(s, row)
    return f is None or _version(f) != version


def evidence_of(s, claim_id):
    """The evidence a claim rests on: [{id, kind, title, weight, changed}]."""
    out = []
    for l in s.links_from(claim_id):
        row = s.get(l["target"]) if l["type"] == "derived-from" else None
        kind = row and kind_of(row)
        if kind:
            moved = changed(s, row)
            out.append({"id": row["id"], "kind": kind, "changed": moved,
                        "weight": KINDS.get(kind, 0.0) * (CHANGED if moved else 1.0),
                        "title": row["state"].get("title") or row["state"].get("name") or row["id"]})
    return sorted(out, key=lambda e: (-e["weight"], e["id"]))
