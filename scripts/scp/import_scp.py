"""Import Giblets Forge SCP documents (v1.x) as substrate capsules.

Hybrid: declaration → state_json, inherits → links, SCP-specific fields
quarantined under state.source_format for later promotion.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import json

from substrate import Substrate

# Authored declaration = a claim. Uses existing foundation:knowledge.
FOUNDATION = "foundation:knowledge"


def import_scp(s: Substrate, doc: dict, *, source_path: str = None) -> dict:
    scp_id = doc["scp_id"]
    decl   = doc.get("declaration", {})
    entity = decl.get("entity", {})

    state = {
        # The payload — the actual declaration, queryable via json_extract
        "declaration": decl,
        # Document metadata, preserved but quarantined
        "source_format": {
            "format":           "giblets-scp",
            "version":          doc.get("scp_version"),
            "canonicalisation": doc.get("canonicalisation"),
            "licence":          doc.get("licence"),
            "signature":        doc.get("signature"),
            "declared_at":      doc.get("created"),
            "source_path":      source_path,
        },
    }

    # 1. The document itself
    s.write({"id": scp_id, "foundation": FOUNDATION, "state": state})

    # 2. Inherits targets (create placeholders if missing)
    inherits_created, inherits_existing = [], []
    for target in doc.get("inherits", []):
        if s.get(target):
            inherits_existing.append(target)
        else:
            s.write({
                "id":         target,
                "foundation": FOUNDATION,
                "state": {
                    "placeholder": True,
                    "kind":        "inherit-target",
                    "note":        f"Referenced by {scp_id}; body not yet imported",
                },
            })
            inherits_created.append(target)
        s.link(scp_id, "inherits", target)

    # 3. Declares: explicit entity.capsule wins, else handle match (backward compat)
    declared_subject = None
    candidate = entity.get("capsule")
    if not candidate and entity.get("handle") == "JamesTheGiblet" and s.get("james"):
        candidate = "james"
    if candidate and s.get(candidate):
        s.link(scp_id, "declares", candidate)
        s.link(candidate, "declared-by", scp_id)
        declared_subject = candidate

    return {
        "scp_id":             scp_id,
        "inherits_created":   inherits_created,
        "inherits_existing":  inherits_existing,
        "declares":           declared_subject,
        "signed":             bool(doc.get("signature", {}).get("value")),
    }


def main():
    usage = "usage: python scripts/scp/import_scp.py <file.scp.json>"
    if len(sys.argv) < 2:
        sys.exit(usage)
    if sys.argv[1] in ("-h", "--help"):
        print(usage)
        return
    path = Path(sys.argv[1])
    if not path.exists():
        sys.exit(f"file not found: {path}")

    doc = json.loads(path.read_text(encoding="utf-8"))
    if "scp_id" not in doc or "declaration" not in doc:
        sys.exit("not an SCP document (missing scp_id or declaration)")

    s = Substrate()
    result = import_scp(s, doc, source_path=str(path))
    print(json.dumps(result, indent=2))
    s.close()


if __name__ == "__main__":
    main()
