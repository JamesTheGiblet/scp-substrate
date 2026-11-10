"""Export sc.db events to a Canon-format JSONL ledger for independent verification."""
import json
import hashlib
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))

from substrate import Substrate

def _hash_record(record):
    # Canon requires a 16-hex (64-bit) prefix for the record hash
    b = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')
    return hashlib.sha256(b).hexdigest()[:16]

def main(out_path="build/ledger.jsonl"):
    s = Substrate()
    events = s.conn.execute("SELECT seq, event_type, capsule_id, payload, occurred_at FROM events ORDER BY seq").fetchall()
    
    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    
    prev_hash = "0" * 16
    with out_file.open("w") as f:
        for i, ev in enumerate(events):
            record = {
                "seq": i + 1,
                "prev": prev_hash,
                "event_type": ev["event_type"],
                "capsule_id": ev["capsule_id"],
                "payload": json.loads(ev["payload"]) if ev["payload"] else {},
                "occurred_at": ev["occurred_at"]
            }
            h = _hash_record(record)
            record["hash"] = h
            # Note: We sign with a placeholder here. To make this fully Canon-compliant,
            # you would run this through record.py to add the Ed25519 signature.
            record["signature"] = "PENDING_CANON_SIGNATURE"
            record["signer"] = "did:key:PENDING"
            
            f.write(json.dumps(record, sort_keys=True, separators=(',', ':')) + "\n")
            prev_hash = h
            
    print(f"Exported {len(events)} events to {out_file}")
    print("Note: Run this through canon-verify's record.py to sign and verify the chain.")
    s.close()

if __name__ == "__main__":
    main()
