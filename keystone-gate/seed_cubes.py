"""Seed cubes for real decisions and claims. Create-only.

Lenses arrive as proposals from `claude-draft`, not as faces: nothing counts
until a human accepts it. OPINION is left empty because it is the human's own
judgement, and so are validation and attestation. Work through the result
with `kg cube review --by <name>`.
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_agent import create_cube, propose_face


DRAFTED_BY = "claude-draft"

CUBES = [
    {
        "id": "cube/phase-0-is-documentation",
        "content": "Phase 0 is always documentation.",
        "source": "phase-0 principle",
        "tags": ["principle", "process"],
        "FACT": "Recorded as the first of james's build rules: document fully before building.",
        "COUNTER": "Docs can lag once building starts. At 2026-11-01 keystone-gate/README.md still called kg_agent.py empty when it held 526 lines, and STRUCTURE.md listed 21 tests when there were 70.",
        "FICTION": "If building came first, ideas would start before they fit, and the reasons for them would live only in memory.",
        "CONTEXT": "From phase-0: ideas parked for years, documented, not started until they fit. The scp project links to it with follows.",
    },
    {
        "id": "cube/log-everything-fail-loud",
        "content": "Log everything; fail loud and public; fix first.",
        "source": "principle/fail-loud-public",
        "tags": ["principle", "process"],
        "FACT": "Recorded as a principle. The gate follows it: a rule with no checker is a violation, and a refused answer is withheld.",
        "COUNTER": "The code does not always follow it. At 2026-11-01 there were 9 places that catch Exception and pass silently, including create_cube in kg_agent.py.",
        "FICTION": "If failures stayed quiet, a broken gate would look exactly like a healthy one.",
        "CONTEXT": "Sits behind the event log and the gate's fail-closed behaviour.",
    },
    {
        "id": "cube/split-files-over-400-lines",
        "content": "Split files over 400 lines; modular.",
        "source": "principle/split-400-lines",
        "tags": ["principle", "code"],
        "FACT": "Recorded as a principle.",
        "COUNTER": "The repo breaks it. At 2026-11-01 these were over 400 lines: src/ask.py, src/rules.py, scripts/absorb_repo.py, keystone-gate/kg_agent.py, keystone-gate/kg and both test files.",
        "FICTION": "If every file stayed under 400 lines, kg_agent.py would already be split into cubes and proposals.",
        "CONTEXT": "No check enforces it. Either the rule needs one or it should be read as a guideline.",
    },
    {
        "id": "cube/british-english-everywhere",
        "content": "British English everywhere, identifiers included.",
        "source": "principle/british-english-everywhere",
        "tags": ["principle", "code"],
        "FACT": "Recorded as a principle. Code uses canonicalise and neighbour, and a grep at 2026-11-01 for common American spellings in code found none.",
        "COUNTER": "Third-party names stay American, such as sqlite3.Row and the ast module, so identifiers can never be fully consistent.",
        "FICTION": "With American spelling, a search for neighbour would miss half the code.",
        "CONTEXT": "One spelling keeps grep and capsule IDs predictable.",
    },
    {
        "id": "cube/compress-in-uncertain-channels",
        "content": "Default to compression in uncertain channels.",
        "source": "minimum-viable-packet principle",
        "tags": ["principle", "communication"],
        "FACT": "Recorded as the minimum-viable-packet principle.",
        "COUNTER": "Compression can lose what matters. If the channel was in fact safe, a short packet undersells the idea.",
        "FICTION": "Sending the full packet every time would mean more misunderstandings in low-bandwidth channels.",
        "CONTEXT": "Linked in spirit to the bandwidth-mismatch and dual-mode-interface concepts.",
    },
    {
        "id": "cube/everything-is-capsules",
        "content": "Everything can be represented as capsules.",
        "source": "everything-is-capsules claim",
        "tags": ["substrate"],
        "FACT": "Recorded as a claim. Foundations, rules, grammar, intents, contracts and cubes are all capsules, and the claim is the about target of scp-claim.",
        "COUNTER": "SPEC section 1 names four primitives. Links and events are not capsules, and trust_scores is a separate table.",
        "FICTION": "If links were capsules too, every traversal would cost more and the schema would be a single table.",
        "CONTEXT": "The founding idea of the substrate. Backed by obs-001, a score of 1.8 from james.",
    },
    {
        "id": "cube/two-layer-rule",
        "content": "Foundations live in sc.json; instances live in sc.db.",
        "source": "README two-layer rule; SPEC section 6",
        "tags": ["substrate"],
        "FACT": "bootstrap.py projects sc.json into sc.db, and Substrate.write rejects foundation IDs.",
        "COUNTER": "A foundation's schema is not enforced: SPEC section 2 says no engine validates state against it, so foundations describe rather than constrain.",
        "FICTION": "If foundations were editable in the DB, nothing could say which kinds of capsule were meant to exist.",
        "CONTEXT": "Each artifact has one writer. Adding a foundation is a versioned edit to one file.",
    },
    {
        "id": "cube/every-write-goes-through-substrate",
        "content": "Every write goes through Substrate, so every write is logged.",
        "source": "STRUCTURE write path; SPEC section 5",
        "tags": ["substrate", "ledger"],
        "FACT": "Stated in docs/STRUCTURE.md: nothing outside substrate.py opens a write transaction.",
        "COUNTER": "Not fully true. At 2026-11-01 src/trust.py, rules.py, feedback.py, parse.py, generate.py, scps and scripts/fill_styles.py still write SQL directly. Some log their own events and some do not.",
        "FICTION": "With every write in one place, the event log would be a complete record.",
        "CONTEXT": "Direct updates were removed from kg_agent.py and the importers on 2026-11-01. The statement in STRUCTURE.md still overclaims.",
    },
    {
        "id": "cube/events-are-audit-not-replay",
        "content": "Events are for audit, not for replay.",
        "source": "SPEC section 5",
        "tags": ["substrate", "ledger"],
        "FACT": "SPEC section 5: nothing reconstructs state from events, by deliberate choice. Replay is a v2 concern.",
        "COUNTER": "It limits recovery. capsule.written records only the foundation, not the state, so the log cannot rebuild a lost capsule.",
        "FICTION": "With full state in every event, sc.db could be rebuilt from the log, at the cost of a much larger ledger.",
        "CONTEXT": "sc.db is tracked in git, which is the recovery path today.",
    },
    {
        "id": "cube/schema-changes-are-rare-and-logged",
        "content": "schema.sql changes only by reviewed, logged migration.",
        "source": "SPEC section 7 and section 11",
        "tags": ["substrate"],
        "FACT": "One change since migration: the unused rules table was dropped and logged as a schema.migration event.",
        "COUNTER": "There is no migration framework. Changes are manual, so the rule depends on discipline.",
        "FICTION": "If every feature had added tables, the substrate would not have survived fifteen layers unchanged.",
        "CONTEXT": "All other growth has been additive in state_json. This is the project's main proof of design.",
    },
    {
        "id": "cube/own-ed25519-for-local-signing",
        "content": "A pure-Python Ed25519 is enough for signing your own documents on your own device.",
        "source": "README limits; SPEC section 9",
        "tags": ["crypto"],
        "FACT": "ed25519.py is a pure-Python RFC 8032 implementation tested against RFC section 7.1 vectors.",
        "COUNTER": "It is not constant-time, so it is unsafe in adversarial contexts or when signing for others.",
        "FICTION": "If this ever signed for other people, it would need replacing with an audited library.",
        "CONTEXT": "Keeps the substrate free of dependencies. Canonicalisation is also a local convention, not RFC 8785.",
    },
    {
        "id": "cube/symlm-has-no-weights",
        "content": "SymLM is symbolic: no weights, no training, every output traceable.",
        "source": "SPEC section 12",
        "tags": ["language"],
        "FACT": "Grammar, lexicon, classifiers and intents are capsules. Behaviour changes only when a human edits one.",
        "COUNTER": "It covers little: 12 grammar rules and 478 words. Since 2026-11-01 kg ask --claude adds a statistical model beside it for phrasing, outside SymLM.",
        "FICTION": "If SymLM could phrase freely, it would need the weights it was built to avoid.",
        "CONTEXT": "SPEC section 12 calls it a different mechanism from an LLM, not a smaller one.",
    },
    {
        "id": "cube/trust-is-shown-not-claimed",
        "content": "Trust the substrate can show counts for more than trust a capsule claims.",
        "source": "src/trust.py evidence section",
        "tags": ["trust"],
        "FACT": "trust_from_evidence walks observations and verifications instead of reading a capsule's own numbers. fused_trust combines both.",
        "COUNTER": "Evidence is thin and hand-scored: obs-001 is 1.8 from james, and the sigmoid is uncalibrated. Fusion treats prior and evidence equally, so the headline claim is not implemented as a preference.",
        "FICTION": "With ground-truth outcomes, the fusion could be calibrated. That is the open adaptive-fusion question.",
        "CONTEXT": "One materialised trust score exists. scp-claim sets age_days to 0, so recomputing resets its decay.",
    },
    {
        "id": "cube/repos-store-metadata-not-bytes",
        "content": "Repo capsules store metadata and symbols, not file contents.",
        "source": "README limits; SPEC section 13",
        "tags": ["substrate", "ingestion"],
        "FACT": "Absorption stores hashes, sizes, imports and symbol names. grep on disk stays the tool for content.",
        "COUNTER": "So open questions such as what does this code do cannot be answered, and the index goes stale until re-absorbed.",
        "FICTION": "Storing bytes would make sc.db a slow second copy of git.",
        "CONTEXT": "absorb_repo.py --prune, added 2026-11-01, removes capsules for files that have gone.",
    },
    {
        "id": "cube/llm-handles-language-not-truth",
        "content": "The LLM handles language, never truth.",
        "source": "keystone-gate/README.md",
        "tags": ["gate"],
        "FACT": "The walker finds the facts and Claude only rewords them. Any failure or refusal shows the walker's answer.",
        "COUNTER": "Rewording can still change meaning. The gate proves each claim quotes evidence, not that the sentence means the same as its quote.",
        "FICTION": "If the LLM could answer from its own knowledge, the gate would have nothing to check against.",
        "CONTEXT": "The core rule of Keystone Gate, enforced by sc/claude-answerer in kg_llm.py. No live call had been made at 2026-11-01.",
    },
    {
        "id": "cube/gate-checks-structure-not-reasoning",
        "content": "The gate judges references, not reasoning.",
        "source": "keystone-gate/README.md design decisions",
        "tags": ["gate"],
        "FACT": "The checkers test IDs, names, numbers, quotes and provenance. Whether the reasoning is right is left to the human.",
        "COUNTER": "A lowercase invented word can pass, and a true-looking answer can be wrong. Passing the gate can read as more assurance than it gives.",
        "FICTION": "An automatic judge of reasoning would be a harder problem than the one the gate solves, and would itself need gating.",
        "CONTEXT": "The human validation face, worth 20 percent, is where reasoning gets judged.",
    },
    {
        "id": "cube/contract-as-data-enforcement-as-code",
        "content": "The contract is data; enforcement is code.",
        "source": "keystone-gate/README.md design decisions; SPEC section 15",
        "tags": ["gate"],
        "FACT": "sc capsules list the rules and kg_gate.py holds the checkers. A rule with no checker fails closed.",
        "COUNTER": "So a contract edit alone adds nothing, and a new rule always needs code. The data is a list of names, not a language.",
        "FICTION": "With rules written in the capsule itself, the gate would need an interpreter for them.",
        "CONTEXT": "Until 2026-11-01 must_not rules were listed but never checked, which shows the two halves can drift.",
    },
    {
        "id": "cube/keystone-gate-shares-one-database",
        "content": "Keystone Gate is a separate program sharing one database.",
        "source": "keystone-gate/README.md design decisions",
        "tags": ["gate", "substrate"],
        "FACT": "It imports Substrate and adds no code to the substrate. All of its data is capsules in sc.db.",
        "COUNTER": "The shared DB means cube data mixes with substrate data, and a bad write by either affects both.",
        "FICTION": "With its own database, it could not check answers against the substrate without a second connection and a sync problem.",
        "CONTEXT": "Removing it means dropping the keystone-gate folder, four foundations and its capsules.",
    },
    {
        "id": "cube/completeness-gates-attestation",
        "content": "Completeness gates attestation; trust does not run in parallel.",
        "source": "default-cube weighting rule",
        "tags": ["gate", "trust"],
        "FACT": "kg cube attest refuses a cube that is not at 100 percent, and changing a face retracts the attestation.",
        "COUNTER": "The weights are hard-coded in kg_agent.py, not read from default-cube, and its minimum_lenses rule is ignored. Empty-feeling faces also count the same as strong ones.",
        "FICTION": "If attestation ignored completeness, a one-lens cube could carry the same trust as a fully examined one.",
        "CONTEXT": "Five lenses at 16 percent plus human validation at 20 percent. Attestation reaches trust as an observation.",
    },
    {
        "id": "cube/agent-proposes-humans-decide",
        "content": "The agent proposes; humans decide.",
        "source": "kg_agent.py proposal mechanism",
        "tags": ["gate", "process"],
        "FACT": "Rules create proposals, and nothing changes a cube until a human accepts. Rejections stick unless the content or rationale changes.",
        "COUNTER": "It costs attention. These 21 cubes alone create 84 proposals, and fatigue can turn accept into a rubber stamp.",
        "FICTION": "If proposals applied themselves, cubes would fill fast and mean little.",
        "CONTEXT": "kg cube fill is still open to a human directly, and that path skips proposals.",
    },
    {
        "id": "cube/refused-answers-are-withheld",
        "content": "A refused answer is withheld, not shown with a warning.",
        "source": "SPEC section 15",
        "tags": ["gate"],
        "FACT": "kg_hal.py returns no answer when the gate refuses. kg ask --claude replaces a refused answer with the walker's gated one.",
        "COUNTER": "A false refusal hides a good answer, and a person has no view of it except kg gate check. For Claude, the refused text is not shown at all.",
        "FICTION": "With warnings instead, people would learn to skim past them, and the gate would become decoration.",
        "CONTEXT": "On 2026-11-01 a sweep of about 4,000 walker answers found 13 false refusals, since fixed.",
    },
]

LENSES = ("FACT", "COUNTER", "FICTION", "CONTEXT")


def main():
    s = Substrate()
    created = proposed = 0
    for cube in CUBES:
        if s.get(cube["id"]):
            continue
        r = create_cube(s, cube["content"], source=cube["source"],
                        tags=cube["tags"], cube_id=cube["id"])
        if "error" in r:
            print(f"{cube['id']}: {r['error']}")
            continue
        created += 1
        for lens in LENSES:
            propose_face(s, cube["id"], lens, cube[lens], proposed_by=DRAFTED_BY,
                         rationale=f"drafted from {cube['source']}")
            proposed += 1
    print(f"cubes: {created} new, {proposed} proposals, {len(CUBES) - created} already present")
    s.close()


if __name__ == "__main__":
    main()
