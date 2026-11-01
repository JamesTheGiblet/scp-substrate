# Keystone Gate

A knowledge system built on top of the SCP substrate. Sibling to Replicant, sharing the same Forge tools.

The LLM is the interface only. It handles language, never truth. A rule-based layer defines what the LLM may produce, and a gate enforces it.

## Boundary

This directory and the substrate share **one database** (`../sc.db`). It does **not** add code to `src/substrate.py`, `src/rules.py`, `src/trust.py`, `src/queries.py`, or `schema.sql`. It calls `from substrate import Substrate` and writes via `Substrate.write()` and `Substrate.link()`.

**Substrate provides:**
- Four foundations: `foundation:cube`, `foundation:lens`, `foundation:cube-face`, `foundation:neighbour`
- `default-cube` capsule with the corrected 5-lens shape (16% per lens, 20% human validation = 100%)
- The `Substrate` class, event log, trust engine, crypto, everything the substrate already had

**Keystone Gate provides:**
- `sc` capsules defining gate contracts (`sc/symlm-answerer`)
- A gate that refuses answers violating a contract (`kg_gate.py`, `kg_hal.py`)
- A CLI (`kg`) that runs the gate end-to-end
- Statistics and listing for KG content (`kg_stats.py`, `kg_router.py`)
- Cubes: lens faces, human validation, weighted completeness, neighbours (`kg_agent.py`)
- Rules that propose face fills and neighbour links for a human to accept or reject (`kg_rules.py`)

**Not yet built** (see "Status" below):
- Neighbourhood-router (beyond listing)
- Attestation feeding trust (eligibility is computed but nothing consumes it)
- Real LLM interface (currently tests the substrate's own walker)

## The gate

The core idea: an LLM cannot be trusted with facts. It handles language only. The gate defines what it may produce - in an `sc` capsule - and refuses any answer that violates the contract.

An `sc` capsule is a data-defined contract:

```

sc/symlm-answerer
kind: sc
must:
- no_invented_ids:      every slashed ID or path must be a capsule or in stored content
- no_hallucinated_trust: every numeric trust score must match trust_now, fused_trust or the stored score
must_not:
- no_llm_prior:         an affirmative answer must carry the real intent that produced it
- no_hallucinated_entities: slugs and multi-word names must be capsules or in stored content
test_cases:
- {input: "who is james", expect_pass: true}
- {input: "who is santa claus", expect_pass: true}
- {input: "why is scp-claim trusted", expect_pass: true}
- {input: "where is parse_sentence", expect_pass: true}

```

The gate checks the contract. Every answer that comes through `kg ask "..."` is:

1. Produced by the substrate's walker (`ask.answer_question`) or, later, by any LLM
2. Checked against `sc/symlm-answerer`'s `must` and `must_not` rules
3. **Shown only if compliance passes** - otherwise withheld and the violations printed

The gate is structure-only by design. It checks that any references in the answer are real. It does not judge whether the reasoning is correct - that's the human's job (the 20% validation in the DataCube model). The gate is the mechanism that makes the human's judgment *trustworthy by construction*: if the gate passed, you know the answer isn't hallucinating references.

What it cannot catch: a bare single invented word ("bigfoot") looks like English, and `no_llm_prior` proves an answer came from a real intent, not that the words follow from the walk. A rule in the contract with no checker fails closed.

Adding a rule = adding a `must` or `must_not` entry to the sc capsule + a checker function in `kg_gate.py`'s `_RULES` dict. Removing a rule = removing both. There's no configuration file, no plugin system. The contract is data; the enforcement is a function.

## Layout

```

keystone-gate/
├── README.md          this file
├── kg                 CLI entry point (executable)
├── kg_stats.py        count KG capsules in substrate
├── kg_router.py       list neighbours (no routing logic yet)
├── kg_agent.py        cubes: faces, validation, neighbours, proposals
├── kg_rules.py        rules that propose fills and neighbours
├── kg_gate.py         the gate - rules, checks, refusal
├── kg_hal.py          HAL - asks the substrate, gates the answer
├── seed_sc.py         seed sc capsules (create-or-update)
└── test_kg.py         boundary + gate tests

```

## CLI

```

kg stats                            # count cubes, lenses, cube-faces, neighbour pairs
kg route list                       # list all neighbours
kg ask "<question>"                 # ask substrate, gated - refuses if compliance fails
kg gate check "<question>"          # show rules + pass/reject with violations
kg gate test                        # run sc capsule's own test_cases
kg cube new "<content>"             # create a cube (--source, --tag)
kg cube fill <id> <lens> "<text>"   # fill one lens face
kg cube validate <id> --by <name>   # record human validation
kg cube show <id>                   # faces, validation, completeness
kg cube list                        # all cubes with scores
kg cube contradicts <id> <other>    # flag a contradiction
kg cube tick [id]                   # run rules, creating proposals
kg cube proposals [id]              # list proposals (--status)
kg cube accept <proposal> --by <n>  # apply a proposal
kg cube reject <proposal> --by <n>  # reject it; sticks unless the content or rationale changes
kg neighbour link <a> <b>           # link two cubes both ways
kg neighbour list <id>              # list a cube's neighbours

```

## Usage

```bash
cd ~/scp-substrate

# See the boundary works
./keystone-gate/kg stats
./keystone-gate/kg route list

# Run the gate's own tests
./keystone-gate/kg gate test

# Ask gated
./keystone-gate/kg ask "who is james"

# Inspect a gate decision
./keystone-gate/kg gate check "why is scp-claim trusted"
```

Tests

```bash
python keystone-gate/test_kg.py
```

57 tests covering:

· Boundary: foundations exist, boundary imports work, stats counts content, route list runs
· DataCube: corrected to 5 lenses + contradicts field
· Gate: every rule in both directions, fail-closed on unknown rules, logged chat is not grounding
· Cubes: completeness, attestation, validation going stale, every edit event-logged
· Proposals and rules: accept, reject, rejections sticking, decision matching

Boundary and gate tests read a temporary copy of sc.db, so the live database is never written to.

Status

Boundary proven. Four foundations in sc.json, projected into sc.db. kg stats and kg route list cross the boundary cleanly.

Gate working. sc/symlm-answerer defines the contract. kg_gate.py checks it. kg_hal.py refuses to render answers that fail. kg gate test runs the contract's own test cases (4/4 pass). 57 KG tests pass. 70 substrate tests pass - untouched.

Cubes working. There are 3 cubes in the substrate, all complete. Completeness is computed and decides attestation eligibility. Changing a face after validation marks the validation stale, so the cube drops out of eligibility until a human validates it again. Nothing consumes eligibility yet.

Behaviour working. kg cube tick runs five rules that propose fills and neighbours. Nothing applies without a human accept, and rejections stick.

Design decisions, stated

· Single DB, separate program. Keystone Gate shares sc.db with the substrate but never modifies substrate code. This preserves the substrate's stability through another ~15 capability layers. If the boundary breaks, we find out in kg stats before any logic is built.
· Contract as data, enforcement as code. The sc capsule holds the rules; kg_gate.py holds the checkers. Neither alone can enforce. Both must agree.
· Structure-only gate. The gate does not judge reasoning. It judges references. That's the correct scope - an automated judge of reasoning is a bigger problem than the one Keystone Gate solves.
· Four foundations, no schema change. foundation:cube, foundation:lens, foundation:cube-face, foundation:neighbour are capsules in sc.json. schema.sql is unchanged. The gate can be dropped entirely by removing those four rows and the keystone-gate/ directory.
  