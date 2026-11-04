"""Import sc_version 1.2 person documents with evidence-discipline fields.

Maps a person document to:
  - One person capsule (full document in state_json)
  - Links to each routine in `routine_links` (via `follows`)
  - Link to the short-hand `james` capsule if present (bidirectional `same-as`)
  - Placeholder capsules for each `extends` target, linked via `extends`
  - Question capsules for each `open_items` entry (via `open-question`)

Evidence discipline: `stated` vs `observed` vs `inferred` are preserved as
fields. `inferred_unconfirmed` items with confidence values are stored as
state, NOT as trust instances — the document is explicit that these are
Claude's reads from conversation, unconfirmed, not substrate-derived
truth. Promoting them to trust would over-formalise the model.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import argparse
import json
from datetime import datetime, timezone

from substrate import Substrate
from signing import verify


KIND = "person"


def _slug_from_doc_id(doc_id):
    return doc_id.replace(".", "/")


def _find_capsule_by_field(s, kind, field, value):
    """Find a capsule whose state has kind=<kind> and state[field]=<value>."""
    row = s.conn.execute(
        f"SELECT id FROM capsules WHERE "
        f"json_extract(state_json, '$.kind') = ? AND "
        f"json_extract(state_json, '$.{field}') = ?",
        (kind, value),
    ).fetchone()
    return row["id"] if row else None


def import_person(s, doc, source_path=None, signed_path=None):
    doc_id = doc.get("id")
    if not doc_id:
        return {"error": "document has no id"}

    person_id = _slug_from_doc_id(doc_id)

    sig = doc.get("signature")
    sig_verified = None
    if signed_path:
        result = verify(doc)
        sig_verified = result
        if not result.get("valid"):
            return {"error": f"signature invalid: {result.get('reason')}"}

    # --- 1. Person capsule ---
    person_state = {
        "kind": KIND,
        "sc_version": doc.get("sc_version"),
        "document_id": doc_id,
        "title": doc.get("title"),
        "owner": doc.get("owner"),
        "status": doc.get("status"),
        "tags": doc.get("tags"),
        "evidence_rule": doc.get("evidence_rule"),
        "core": doc.get("core"),
        "identity": doc.get("identity"),
        "self_description": doc.get("self_description"),
        "neurodivergence": doc.get("neurodivergence"),
        "how_he_works": doc.get("how_he_works"),
        "communication_needs": doc.get("communication_needs"),
        "regulation": doc.get("regulation"),
        "priorities": doc.get("priorities"),
        "routine_links": doc.get("routine_links"),
        "inferred_unconfirmed": doc.get("inferred_unconfirmed"),
        "open_items": doc.get("open_items"),
        "source_path": source_path,
        "signed_path": signed_path,
        "signature": sig if isinstance(sig, dict) else {"value": sig},
        "signature_verified": bool(sig_verified and sig_verified.get("valid")),
        "last_absorbed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    existing = s.get(person_id)
    if existing:
        s.write({"id": person_id, "foundation": "foundation:knowledge", "state": person_state})
    else:
        s.write({
            "id": person_id,
            "foundation": "foundation:knowledge",
            "state": person_state,
        })

    # --- 2. Link to shorthand capsule (james) if present ---
    shorthand_link = None
    if s.get("james"):
        if not s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='same-as' AND target='james'",
            (person_id,)
        ).fetchone():
            s.link(person_id, "same-as", "james")
        if not s.conn.execute(
            "SELECT 1 FROM links WHERE source='james' AND type='same-as' AND target=?",
            (person_id,)
        ).fetchone():
            s.link("james", "same-as", person_id)
        shorthand_link = "james"

    # --- 3. Link to routines via routine_links ---
    routine_links = []
    for routine_doc_id in doc.get("routine_links", []):
        target = _find_capsule_by_field(s, "routine", "document_id", routine_doc_id)
        if target:
            routine_links.append(target)
            if not s.conn.execute(
                "SELECT 1 FROM links WHERE source=? AND type='follows' AND target=?",
                (person_id, target)
            ).fetchone():
                s.link(person_id, "follows", target)

    # --- 4. Placeholder capsules for `extends` targets ---
    extends_links = []
    for parent in doc.get("extends", []):
        parent_id = parent if "/" in parent else parent
        if not s.get(parent_id):
            # Create a placeholder
            s.write({
                "id": parent_id,
                "foundation": "foundation:knowledge",
                "state": {
                    "kind": "person-schema",
                    "name": parent,
                    "description": f"Placeholder for {parent}; not yet authored.",
                },
            })
        if not s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='extends' AND target=?",
            (person_id, parent_id)
        ).fetchone():
            s.link(person_id, "extends", parent_id)
        extends_links.append(parent_id)

    # --- 5. Question capsules for open_items ---
    questions_created = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i, q in enumerate(doc.get("open_items", [])):
        qid = f"{person_id}/open/{i+1}"
        if s.get(qid):
            continue
        s.write({
            "id": qid,
            "foundation": "foundation:knowledge",
            "state": {
                "kind": "question",
                "question": q,
                "status": "open",
                "raised": today,
                "context": f"from {person_id}",
            },
        })
        s.link(person_id, "open-question", qid)
        questions_created += 1

    return {
        "person_id": person_id,
        "document_id": doc_id,
        "shorthand_link": shorthand_link,
        "routine_links": routine_links,
        "extends_links": extends_links,
        "questions_created": questions_created,
        "signature_verified": bool(sig_verified and sig_verified.get("valid")),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path")
    ap.add_argument("--signed", action="store_true")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        sys.exit(f"not found: {p}")

    doc = json.loads(p.read_text(encoding="utf-8"))
    if not doc.get("id", "").startswith("person."):
        sys.exit("not a person document (id must start with 'person.')")

    s = Substrate()
    result = import_person(
        s, doc,
        source_path=str(p),
        signed_path=str(p) if args.signed else None,
    )
    s.close()

    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
