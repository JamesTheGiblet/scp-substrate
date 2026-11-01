"""Import sc_version 1.2 circadian routine documents.

Maps a routine document to:
  - One routine capsule (full document in state_json)
  - One routine-block capsule per sequence item (linked via `contains`)
  - One question capsule per open_item (linked via `open-question`)
  - `james --follows--> routine` (if james exists)

Usage:
  python import_circadian.py <file.scp.json> [--signed]

The --signed flag expects a signed document; verifies before importing.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from substrate import Substrate
from signing import verify


KIND = "routine"
BLOCK_KIND = "routine-block"


def _slug_from_doc_id(doc_id):
    """Convert 'circadian.morning.weekday' → 'circadian/morning/weekday'."""
    return doc_id.replace(".", "/")


def import_circadian(s, doc, source_path=None, signed_path=None):
    """Absorb one circadian routine document."""
    doc_id = doc.get("id") or doc.get("scp_id")
    if not doc_id:
        return {"error": "document has no id"}

    routine_id = _slug_from_doc_id(doc_id)

    # Signature handling
    sig = doc.get("signature")
    sig_verified = None
    if signed_path:
        result = verify(doc)
        sig_verified = result
        if not result.get("valid"):
            return {"error": f"signature invalid: {result.get('reason')}"}

    # --- 1. Main routine capsule ---
    routine_state = {
        "kind": KIND,
        "sc_version": doc.get("sc_version"),
        "document_id": doc_id,
        "title": doc.get("title"),
        "owner": doc.get("owner"),
        "status": doc.get("status"),
        "applies": doc.get("applies"),
        "anchors": doc.get("anchors"),
        "flex_rule": doc.get("flex_rule"),
        "resolved_timelines": doc.get("resolved_timelines"),
        "source_path": source_path,
        "signed_path": signed_path,
        "signature": sig if isinstance(sig, dict) else {"value": sig},
        "signature_verified": bool(sig_verified and sig_verified.get("valid")),
        "last_absorbed": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    existing = s.get(routine_id)
    if existing:
        with s.conn:
            s.conn.execute(
                "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(routine_state), routine_id),
            )
    else:
        s.write({
            "id": routine_id,
            "foundation": "foundation:knowledge",
            "state": routine_state,
        })

    # --- 2. Block capsules ---
    blocks_created = 0
    for i, block in enumerate(doc.get("sequence", [])):
        bid = f"{routine_id}/block/{block['id']}"
        if s.get(bid):
            continue
        s.write({
            "id": bid,
            "foundation": "foundation:knowledge",
            "state": {
                "kind": BLOCK_KIND,
                "block_id": block["id"],
                "minutes": block.get("minutes"),
                "fixed": block.get("fixed"),
                "start": block.get("start"),
                "end": block.get("end"),
                "ends_at": block.get("ends_at"),
                "at": block.get("at"),
                "desc": block.get("desc"),
                "position": i,
                "routine_id": routine_id,
            },
        })
        s.link(routine_id, "contains", bid)
        blocks_created += 1

    # --- 3. Question capsules for open_items ---
    questions_created = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for i, q in enumerate(doc.get("open_items", [])):
        qid = f"{routine_id}/open/{i+1}"
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
                "context": f"from {routine_id}",
            },
        })
        s.link(routine_id, "open-question", qid)
        questions_created += 1

    # --- 4. Link owner to routine ---
    owner_link = None
    owner = doc.get("owner")
    if owner and owner.lower() == "james gilbert" and s.get("james"):
        # Idempotent
        existing = s.conn.execute(
            "SELECT 1 FROM links WHERE source='james' AND type='follows' AND target=?",
            (routine_id,)
        ).fetchone()
        if not existing:
            s.link("james", "follows", routine_id)
        owner_link = "james"

    return {
        "routine_id": routine_id,
        "document_id": doc_id,
        "blocks_created": blocks_created,
        "questions_created": questions_created,
        "signature_verified": bool(sig_verified and sig_verified.get("valid")),
        "owner_link": owner_link,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", help="path to sc_version 1.2 circadian document")
    ap.add_argument("--signed", action="store_true",
                    help="document is signed; verify before absorbing")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        sys.exit(f"not found: {p}")

    doc = json.loads(p.read_text())
    if doc.get("sc_version") is None and doc.get("id", "").startswith("circadian") is False:
        sys.exit("not a circadian sc_version document (missing sc_version or id)")

    s = Substrate()
    result = import_circadian(
        s, doc,
        source_path=str(p),
        signed_path=str(p) if args.signed else None,
    )
    s.close()

    print(json.dumps(result, indent=2))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
