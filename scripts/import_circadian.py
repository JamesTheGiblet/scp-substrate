"""Import sc_version 1.2 circadian routine documents.

Maps a routine document to:
  - One routine capsule (full document in state_json)
  - One routine-block capsule per sequence item (linked via `contains`)
  - One routine-phase capsule per phase (linked via `contains`)
  - One question capsule per open_item and per phase.unresolved (linked via `open-question`)
  - `james --follows--> routine` (if james exists)
  - `routine --follows--> <previous routine>` and inverse `precedes` (if follows_doc_id given)

Usage:
  python import_circadian.py <file.scp.json> [--signed]

The --signed flag expects a signed document; verifies before importing.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from substrate import Substrate
from signing import verify


KIND = "routine"
BLOCK_KIND = "routine-block"
PHASE_KIND = "routine-phase"


def _slug_from_doc_id(doc_id):
    """Convert 'circadian.morning.weekday' -> 'circadian/morning/weekday'."""
    return doc_id.replace(".", "/")


def _find_routine_by_doc_id(s, doc_id):
    """Find a routine capsule's id by its document_id field."""
    row = s.conn.execute(
        "SELECT id FROM capsules "
        "WHERE json_extract(state_json, '$.kind') = 'routine' "
        "  AND json_extract(state_json, '$.document_id') = ?",
        (doc_id,),
    ).fetchone()
    return row["id"] if row else None


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
        "follows_doc_id": doc.get("follows"),
        "branches": doc.get("branches"),
        "enforcement": doc.get("enforcement"),
        "rules": doc.get("rules"),
        "open_items": doc.get("open_items"),
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

    # --- 2. Block capsules (create-or-update) ---
    blocks_created = 0
    blocks_updated = 0
    for i, block in enumerate(doc.get("sequence", [])):
        bid = f"{routine_id}/block/{block['id']}"
        block_state = {
            "kind": BLOCK_KIND,
            "block_id": block["id"],
            "minutes": block.get("minutes"),
            "fixed": block.get("fixed"),
            "start": block.get("start"),
            "end": block.get("end"),
            "ends_at": block.get("ends_at"),
            "at": block.get("at"),
            "desc": block.get("desc"),
            "branch": block.get("branch"),
            "excludes": block.get("excludes"),
            "allows": block.get("allows"),
            "position": i,
            "routine_id": routine_id,
        }
        existing_block = s.get(bid)
        if existing_block:
            if existing_block["state"] != block_state:
                with s.conn:
                    s.conn.execute(
                        "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                        (json.dumps(block_state), bid),
                    )
                blocks_updated += 1
        else:
            s.write({"id": bid, "foundation": "foundation:knowledge", "state": block_state})
            s.link(routine_id, "contains", bid)
            blocks_created += 1

    # --- 2b. Phase capsules (for routines with `phases` instead of `sequence`) ---
    phases_created = 0
    phases = doc.get("phases")
    if phases:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        for phase_id, phase_data in phases.items():
            pid = f"{routine_id}/phase/{phase_id}"
            phase_state = {
                "kind": PHASE_KIND,
                "phase_id": phase_id,
                "routine_id": routine_id,
                "window": phase_data.get("window"),
                "structure": phase_data.get("structure"),
                "bedtime": phase_data.get("bedtime"),
                "desc": phase_data.get("desc"),
                "blocks": phase_data.get("blocks"),
                "unresolved": phase_data.get("unresolved"),
            }
            existing_phase = s.get(pid)
            if existing_phase:
                if existing_phase["state"] != phase_state:
                    with s.conn:
                        s.conn.execute(
                            "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                            (json.dumps(phase_state), pid),
                        )
            else:
                s.write({"id": pid, "foundation": "foundation:knowledge", "state": phase_state})
                s.link(routine_id, "contains", pid)
                phases_created += 1

            # Unresolved items inside a phase become open questions under that phase
            for j, unresolved_text in enumerate(phase_data.get("unresolved") or []):
                qid = f"{pid}/open/{j+1}"
                if s.get(qid):
                    continue
                s.write({
                    "id": qid,
                    "foundation": "foundation:knowledge",
                    "state": {
                        "kind": "question",
                        "question": unresolved_text,
                        "status": "open",
                        "raised": today,
                        "context": f"from {pid}",
                    },
                })
                s.link(pid, "open-question", qid)

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

    # --- 3b. follows / precedes links (cross-routine) ---
    follows_target = None
    follows_doc_id = doc.get("follows")
    if follows_doc_id:
        follows_target = _find_routine_by_doc_id(s, follows_doc_id)
        if follows_target:
            if not s.conn.execute(
                "SELECT 1 FROM links WHERE source=? AND type='follows' AND target=?",
                (routine_id, follows_target),
            ).fetchone():
                s.link(routine_id, "follows", follows_target)
            if not s.conn.execute(
                "SELECT 1 FROM links WHERE source=? AND type='precedes' AND target=?",
                (follows_target, routine_id),
            ).fetchone():
                s.link(follows_target, "precedes", routine_id)

    # --- 4. Link owner to routine ---
    owner_link = None
    owner = doc.get("owner")
    if owner and owner.lower() == "james gilbert" and s.get("james"):
        existing = s.conn.execute(
            "SELECT 1 FROM links WHERE source='james' AND type='follows' AND target=?",
            (routine_id,),
        ).fetchone()
        if not existing:
            s.link("james", "follows", routine_id)
        owner_link = "james"

    return {
        "routine_id": routine_id,
        "document_id": doc_id,
        "blocks_created": blocks_created,
        "blocks_updated": blocks_updated,
        "phases_created": phases_created,
        "questions_created": questions_created,
        "signature_verified": bool(sig_verified and sig_verified.get("valid")),
        "owner_link": owner_link,
        "follows": follows_target,
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
