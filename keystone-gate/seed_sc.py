"""Seed sc capsules (gated LLM contracts). Create-or-update."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent))

from substrate import Substrate


SC_CAPSULES = [
    {
        "id": "sc/symlm-answerer",
        "state": {
            "kind": "sc",
            "name": "symlm-answerer",
            "purpose": "Answer natural language questions about the SCP substrate",
            "must": [
                {"rule": "no_invented_ids",
                 "description": "Every capsule ID mentioned in the answer must exist in the substrate"},
                {"rule": "no_hallucinated_trust",
                 "description": "Any numeric trust score in the answer must match fused_trust(id).posterior for the named capsule"},
            ],
            "must_not": [
                {"rule": "no_llm_prior",
                 "description": "Must not claim knowledge not present in the substrate"},
                {"rule": "no_hallucinated_entities",
                 "description": "Must not invent capsule IDs, entity names, or file paths"},
            ],
            "test_cases": [
                {"input": "who is james", "expect_pass": True,
                 "reason": "james exists in substrate"},
                {"input": "who is santa claus", "expect_pass": True,
                 "reason": "answer is 'not in substrate' — no invented IDs, so it passes"},
                {"input": "why is scp-claim trusted", "expect_pass": True,
                 "reason": "trust score must match fused_trust"},
            ],
            "boundary": "The gate checks structure, not semantics. It does not verify that a walker gave the 'right' answer — only that the answer's references are real.",
            "version": "1.0",
        },
    },
]


def main():
    s = Substrate()
    new = updated = 0
    for sc in SC_CAPSULES:
        existing = s.get(sc["id"])
        if existing:
            if existing["state"] != sc["state"]:
                with s.conn:
                    s.conn.execute(
                        "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                        (json.dumps(sc["state"]), sc["id"]),
                    )
                updated += 1
        else:
            s.write({
                "id": sc["id"],
                "foundation": "foundation:knowledge",
                "state": sc["state"],
            })
            new += 1
    print(f"sc capsules: {new} new, {updated} updated")
    s.close()


if __name__ == "__main__":
    main()
