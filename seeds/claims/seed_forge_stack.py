#!/usr/bin/env python3
"""The Forge Stack as an entity, its five layers as subjects, and the details as claims.

James set this out on 2026-11-03: the stack is the foundation everything else
is built on. The layers and claims come from the stack's own frozen, signed
docs (the-full-stack-reclone-20260808-1438/docs), so each claim names the doc
it came from. The old forge-stack capsule is sorted into project/forge-stack
by accepting its pending sort proposal. Leighton Weight is the trust score λ,
so the earlier subject/trust folds into it. Faces are left blank.
Create-only: anything whose id exists is skipped.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[2] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from store.substrate import Substrate
from kg_agent import create_cube
from kg_cube import _update_state
from kg_entities import accept_sort, link_claim, merge, relate
from kg_subjects import accept_subject, propose_subject

STACK = "project/forge-stack"
DOCS = "the-full-stack-reclone-20260808-1438/docs"
SOURCE = "The Forge Stack's frozen, signed docs, {}/{}; checked on 2026-11-03"

# slug -> (name, stage, artefact), in spine order
LAYERS = {
    "scp": ("SCP", "Declare", "sc"), "datacube": ("DataCube", "Classify", "cube"),
    "leighton-weight": ("Leighton Weight", "Trust-score", "λ"),
    "chronoscribe": ("ChronoSCRIBE", "Audit", "ledger"), "hal": ("HAL", "Act", "seal"),
}

# (slug, claim, layer or None for the stack as a whole, doc)
CLAIMS = [
    ("forge-stack-five-stage-spine", "The Forge Stack is a five-stage spine: Declare (SCP), Classify (DataCube), "
     "Trust-score (Leighton Weight), Audit (ChronoSCRIBE) and Act (HAL).", None, "glossary.md"),
    ("forge-stack-system-artefact-pairs", "Each Forge Stack stage pairs a named system with a lowercase artefact: "
     "SCP makes an sc, DataCube a cube, ChronoSCRIBE a ledger and HAL a seal, while Leighton Weight's output is "
     "the number λ.", None, "glossary.md"),
    ("forge-stack-v1-frozen-signed", "Forge Stack v1 is frozen, signed and witnessed: eleven capsules signed with "
     "James's own did:key, and nineteen genesis entries in the ledger.", None, "forge-stack-state-of-the-build.md"),
    ("forge-stack-gate-pattern", "The Forge Stack is enforced at runtime by the gate pattern: ingress gates "
     "protect state, and egress gates protect the world.", None, "forge-stack-state-of-the-build.md"),
    ("forge-stack-terms-defined-once", "Forge Stack terms are defined once, in its glossary, and a change to the "
     "glossary makes a new capsule identity rather than an edit.", None, "glossary.md"),
    ("forge-stack-axiom-and-mimir-retired", "AXIOM and Mimir are no longer part of the Forge Stack spine.", None,
     "glossary.md"),
    ("scp-produces-sc", "SCP, the Semantic Capsule Protocol, produces, validates and consumes sc artefacts, "
     "always lowercase, with the extension .sc.json.", "scp", "glossary.md"),
    ("every-sc-is-signed", "Every sc must be signed, SCP Lite capsules included.", "scp", "glossary.md"),
    ("datacube-six-lenses", "DataCube classifies through six lenses, FACT, COUNTER, OPINION, FICTION, CONTEXT "
     "and UNKNOWN, and a cube is complete only when all six are filled.", "datacube", "glossary.md"),
    ("datacube-keeps-a-store", "DataCube keeps an append-only store, never called a ledger, because that word "
     "belongs to ChronoSCRIBE.", "datacube", "glossary.md"),
    ("datacube-integrity-grades", "DataCube grades a cube's completeness: CRYSTALLINE at 90% or more, COHERENT "
     "70–89%, FORMING 40–69% and SPARSE under 40%.", "datacube", "glossary.md"),
    ("empty-counter-is-a-signal", "An empty COUNTER lens signals that disconfirming evidence hasn't been sought.",
     "datacube", "glossary.md"),
    ("leighton-weight-range", "Leighton Weight (λ) is held per entity, ranges from 0.00 to 2.00, and means "
     "quarantine below 0.60.", "leighton-weight", "glossary.md"),
    ("forge-theory-decay", "Forge Theory's decay formula N(t) = N₀·e^(−kt) belongs to the whole stack, and its "
     "decay constant k is calibrated per domain and doesn't transfer between domains.", "leighton-weight",
     "glossary.md"),
    ("leighton-loop", "The Leighton Loop is the stack's pattern of scoring, observing outcomes and updating "
     "scores.", "leighton-weight", "glossary.md"),
    ("chronoscribe-keeps-the-ledger", "ChronoSCRIBE keeps the authoritative ledger: time-ordered, hash-chained and "
     "signed, holding every document and capsule hash and every HAL seal.", "chronoscribe", "chronoscribe.md"),
    ("chronoscribe-makes-the-spine-honest", "Without ChronoSCRIBE, decay values and trust scores are assertions; "
     "with it, they are verifiable history.", "chronoscribe", "chronoscribe.md"),
    ("hal-humans-hold-lambda", "HAL, the Human Accountability Layer, is where humans hold λ and act as "
     "validators, with authority that decay can revoke.", "hal", "glossary.md"),
    ("hal-five-tiers", "HAL has five tiers of authorisation mapped to λ, from Tier 1 (0.60–0.89, easily "
     "reversible actions) to Tier 5 (1.80–2.00, root council).", "hal", "hal.md"),
    ("hal-two-roles", "HAL's two core roles are the Fact Validator, who verifies input data, and the Consequence "
     "Authoriser, who seals actions by λ threshold.", "hal", "glossary.md"),
    ("hal-seal", "A HAL seal is the signed record of an authorisation decision and who made it, appended to the "
     "ledger.", "hal", "glossary.md"),
]


def main():
    s = Substrate()
    proposal = s.get("proposal/sort/forge-stack")
    if proposal and proposal["state"]["status"] == "pending":
        print(f"  sorted forge-stack: {accept_sort(s, 'proposal/sort/forge-stack', 'james', name='Forge Stack')}")
    for order, (slug, (name, stage, artefact)) in enumerate(LAYERS.items(), 1):
        sid = f"subject/{slug}"
        if s.get(sid) is None:
            pid = propose_subject(s, name, [], "james", kind="layer",
                                  rationale="A layer of the Forge Stack; set out by James on 2026-11-03")
            accept_subject(s, pid["proposal_id"], "james")
        _update_state(s, sid, {**s.get(sid)["state"], "name": name, "kind": "layer", "stage": stage,
                               "artefact": artefact, "order": order})
        relate(s, STACK, "uses", sid)
    if s.get("subject/trust"):
        print(f"  folded subject/trust into Leighton Weight: {merge(s, 'subject/trust', 'subject/leighton-weight')}")
    made = 0
    for slug, claim, layer, doc in CLAIMS:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        create_cube(s, claim, source=SOURCE.format(DOCS, doc), tags=["forge-stack"], cube_id=cid)
        link_claim(s, cid, subjects=[f"subject/{layer}"] if layer else [], entities=[STACK])
        made += 1
    print(f"{made} claims made")
    s.close()


if __name__ == "__main__":
    main()
