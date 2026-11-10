"""Evidence management. First-class capsules for datasheets, guides, logs, etc."""
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent))
sys.path.insert(0, str(_here))

from substrate import Substrate

def _slugify(text):
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')

def add_evidence(s, title, kind="guide", url=None, path=None):
    """Create a new evidence capsule."""
    slug = _slugify(title)[:40]
    eid = f"evidence/{slug}"
    
    existing = s.get(eid)
    if existing:
        return {"error": f"evidence {eid} already exists"}

    s.write({
        "id": eid,
        "foundation": "foundation:knowledge",
        "state": {
            "kind": "evidence",
            "evidence_kind": kind,
            "title": title,
            "url": url,
            "path": path,
            "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        }
    })
    return {"evidence_id": eid}

def link_evidence(s, claim_id, evidence_id):
    """Link a claim to a piece of evidence."""
    if not s.get(claim_id):
        return {"error": f"claim {claim_id} not found"}
    if not s.get(evidence_id):
        return {"error": f"evidence {evidence_id} not found"}
        
    existing = s.conn.execute(
        "SELECT 1 FROM links WHERE source=? AND type='derived-from' AND target=?",
        (claim_id, evidence_id)
    ).fetchone()
    
    if existing:
        return {"status": "skipped", "reason": "link already exists"}
        
    s.link(claim_id, "derived-from", evidence_id)
    return {"status": "created", "link": f"{claim_id} -> {evidence_id}"}

def get_evidence_for_claim(s, claim_id):
    """Return list of evidence linked to a claim."""
    rows = s.conn.execute("""
        SELECT target FROM links WHERE source=? AND type='derived-from'
    """, (claim_id,)).fetchall()
    
    out = []
    for r in rows:
        ev = s.get(r["target"])
        if ev:
            out.append(ev)
    return out
