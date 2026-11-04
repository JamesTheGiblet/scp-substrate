"""Seed sc capsules (gated LLM contracts). Create-or-update."""
import sys
from pathlib import Path

# keystone-gate, 1 folder up
_here = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_here.parent / "src"))

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
                 "description": "An affirmative answer must carry the real input-intent that produced it; provenance only, not semantic entailment"},
                {"rule": "no_hallucinated_entities",
                 "description": "Slugs and multi-word names must be capsules or appear in stored content. Bare single words are out of reach"},
            ],
            "test_cases": [
                {"input": "who is james", "expect_pass": True,
                 "reason": "james exists in substrate"},
                {"input": "who is santa claus", "expect_pass": True,
                 "reason": "answer is 'not in substrate' — no invented IDs, so it passes"},
                {"input": "why is scp-claim trusted", "expect_pass": True,
                 "reason": "trust score must match fused_trust"},
                {"input": "where is parse_sentence", "expect_pass": True,
                 "reason": "file paths in stored content are grounded, not invented IDs"},
            ],
            "boundary": "The gate checks structure, not semantics. It does not verify that a walker gave the 'right' answer — only that the answer's references are real.",
            "version": "1.1",
        },
    },
    {
        "id": "sc/claude-answerer",
        "state": {
            "kind": "sc",
            "name": "claude-answerer",
            "purpose": "Reword a walker's answer in natural language through Claude",
            "must": [
                {"rule": "no_invented_ids",
                 "description": "Every capsule ID mentioned in the answer must exist in the substrate"},
                {"rule": "no_hallucinated_trust",
                 "description": "Any numeric trust score must match the capsule's actual trust"},
                {"rule": "claims_quote_evidence",
                 "description": "Every claim must quote, verbatim, the walker evidence it rests on"},
                {"rule": "no_unsourced_terms",
                 "description": "Numbers and capitalised words must come from the evidence or the question"},
            ],
            "must_not": [
                {"rule": "no_llm_prior",
                 "description": "An affirmative answer must carry the real input-intent that produced it"},
                {"rule": "no_hallucinated_entities",
                 "description": "Slugs and multi-word names must be capsules or appear in stored content"},
            ],
            "test_cases": [],
            "boundary": "Checks that claims are anchored to evidence and carry no new names or numbers. It does not prove a paraphrase means what its quote means. A refused answer falls back to the walker.",
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
                s.write({
                    "id": sc["id"],
                    "foundation": "foundation:knowledge",
                    "state": sc["state"],
                })
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
