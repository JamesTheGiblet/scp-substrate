Structure

What's here, why, and how it fits.

---

Directory

```
~/scp-substrate/
├── README.md              entry point
├── scps                   CLI
├── schema.sql             DDL — the shape
├── sc.json                foundations — the constitution
├── sc.db                  instances, links, events — the world
│
├── src/                   everything importable
│   ├── substrate.py       Substrate class, DB access, decay UDF
│   ├── ed25519.py         Ed25519 primitive (own, RFC 8032)
│   ├── signing.py         sign / verify / canonicalise / did:key
│   ├── rules.py           rule engine (4 condition types), rules_sequence.py
│   ├── trust.py           trust engine (parameter, evidence, fusion)
│   ├── queries.py         read-only queries
│   ├── why.py             backward reasoning (why is X trusted?)
│   ├── explain.py         forward reasoning (what is X?)
│   └── parse, generate, corpus, analysis, protocol,
│       feedback, talk, ask   SymLM language layer
│
├── scripts/               run by hand
│   ├── bootstrap.py       project sc.json into sc.db
│   ├── keygen.py          generate Ed25519 keypair
│   ├── sign_doc.py        sign an SCP document
│   ├── import_scp.py      SCP document ingest (also import_person, import_circadian)
│   ├── absorb_repo.py     index a local repo (also absorb_github)
│   └── fill_styles.py, extract_vocab.py, learn_frequencies.py
│
├── seeds/                 create-only capsule seeds, reconcile_seeds.py
├── tests/                 run.py, test_substrate_N.py, test_house_rules.py
│
├── docs/                  SPEC, STRUCTURE, REASONING, SCP documents (*.scp.json)
├── keystone-gate/         Keystone Gate - sibling app, shares sc.db
│   ├── kg                 CLI entry point
│   ├── kg_stats.py        count KG capsules
│   ├── kg_router.py       neighbour listing
│   ├── kg_agent.py        public face of kg_cube.py and kg_proposals.py
│   ├── kg_cube_cli.py     kg cube and kg neighbour commands
│   ├── kg_rules.py        rules that propose fills and neighbours
│   ├── kg_gate.py         gate: rules, checks, refusal
│   ├── kg_hal.py          HAL: ask substrate, gate the answer
│   ├── kg_llm.py          Claude rewords answers, gated, falls back to the walker
│   ├── kg_review.py       guided review of cubes for a person
│   ├── seed_sc.py         seed sc capsules
│   ├── seed_cubes.py      real claims as cubes, lenses as proposals
│   └── test_kg_N.py       boundary, gate, cube and proposal tests
└── legacy/                pre-SQLite JSON archive (excluded from git)
```

---

Layers

```
┌─────────────────────────────────────────────────────────────┐
│ interface      scps                                         │
├─────────────────────────────────────────────────────────────┤
│ reasoning      why.py    explain.py                         │
├─────────────────────────────────────────────────────────────┤
│ engines        rules.py  trust.py  queries.py               │
├─────────────────────────────────────────────────────────────┤
│ crypto         ed25519.py  signing.py                       │
├─────────────────────────────────────────────────────────────┤
│ substrate      substrate.py                                 │
├─────────────────────────────────────────────────────────────┤
│ storage        schema.sql  sc.db                            │
├─────────────────────────────────────────────────────────────┤
│ constitution   sc.json                                      │
└─────────────────────────────────────────────────────────────┘
```

Each layer only imports from layers below it. No layer imports from above. The substrate layer imports nothing from any engine or reasoning module.

---

Files

File What it does Imports from
substrate.py Substrate class — SQLite access, UDF, write/link/supersede stdlib
ed25519.py Ed25519 primitive — publickey, sign, checkvalid hashlib
signing.py sign, verify, canonicalise, did:key encoding ed25519, stdlib
rules.py evaluate_rules — dispatch on condition type substrate
trust.py compute_all, trust_from_evidence, sigmoid, fuse, fused_trust substrate
queries.py why_trusted, trust_now, verified, latest, observations, etc. substrate
why.py why_trusted, print_chain — backward narrative substrate, queries, trust
explain.py explain — forward narrative substrate
import_scp.py import_scp — SCP document ingest substrate
fill_styles.py one-shot: fill SCP inherits placeholders substrate
seed_capsules.py one-shot: 11 context capsules substrate
keygen.py CLI: generate keypair signing
sign_doc.py CLI: sign a document signing
bootstrap.py CLI: project sc.json into sc.db stdlib
scps CLI all of the above
tests/run.py runs every test file

---

Schema

Five tables.

```sql
capsules(id PK, foundation, state_json, is_meta, created_at, updated_at)
links(id PK, source FK, type, target FK, metadata, created_at)
     UNIQUE(source, type, target)
events(seq PK, event_type, capsule_id, payload, occurred_at)
trust_scores(capsule_id FK, model_id FK, score, computed_at)      -- PK(capsule_id, model_id)
schema_version(version)
```

Rules are stored as capsules with foundation:rule; the engine queries capsules directly.

Indexes:

```
idx_capsules_foundation    ON capsules(foundation)
idx_capsules_is_meta       ON capsules(is_meta) WHERE is_meta=1
idx_links_source           ON links(source, type)
idx_links_target           ON links(target, type)
idx_links_type             ON links(type)
idx_events_capsule         ON events(capsule_id, occurred_at)
idx_events_type            ON events(event_type, occurred_at)
```

---

Data flow

Write path

```
caller
  → Substrate.write / link / supersede
    → transaction:
      → INSERT/UPDATE capsules or links
      → INSERT events (one per write)
    → commit
```

Capsule writes go through Substrate. Engines that need a change and its event to be atomic (trust.py, rules.py, feedback.py, parse.py, generate.py, scps, fill_styles.py) write SQL directly and log their own event in the same transaction. Those events can be summaries, so the log is an audit trail, not a row-by-row record.

Read path

```
caller
  → Substrate.get / links_from / by_foundation   (substrate-level)
  → queries.*                                    (query-level)
  → why.* / explain.*                            (reasoning-level)
  → scps <command>                               (CLI-level)
```

Reads are not transactional. They see committed state. There is no snapshot isolation across multiple queries in a single user operation — a script reading trust_scores then reading links could see a change in between if another process wrote concurrently. For a single-user substrate, this has not been an issue. For multi-writer, it would need addressing.

---

Extension points

Adding to the substrate, in order of difficulty:

A capsule of an existing foundation — Substrate.write({...}). No code change.

A new foundation — edit sc.json, run bootstrap.py. No code change. The foundation exists and instances can reference it. Nothing enforces its state.schema yet.

A new query — add a function to queries.py. It can be as simple as a SQL SELECT, or a composition of Substrate calls.

A new rule condition type — add an _eval_X() function to rules.py, extend the if/elif in evaluate_rules, add a capsule of foundation:rule with condition.type = "X". No changes to substrate.py or schema.sql.

A new trust signal — add a function to trust.py and a subcommand to scps. The convention is: writes go through Substrate, reads use queries.

A new CLI command — add cmd_X(a) and a subparser in scps. That's it.

A new SCP document format — write a new importer modelled on import_scp.py. It must accept a JSON dict and produce capsule writes through Substrate.

A schema change — the hard one. Requires a numbered migration script, updating schema.sql, bumping schema_version, and re-running bootstrap.py (which will skip DDL creation on existing DBs, so migration must be applied separately). Done once so far: the unused rules table was dropped, logged as a schema.migration event.

---

Test coverage

python tests/run.py runs everything. The test_substrate_N.py files use :memory: SQLite databases. The keystone-gate test files use :memory: fixtures and a temporary copy of sc.db. test_house_rules.py fails if a file passes 400 lines or an exception is silently swallowed. Each test builds a minimal substrate fixture:

```
foundation:foundation
foundation:knowledge
foundation:observation
foundation:rule
foundation:leighton-weight
alice               (knowledge)
obs-1               (observation, observes alice)
model-1             (leighton-weight)
```

Tests never touch sc.db. They can run while the substrate is live, in parallel, without risk.

Tests cover crypto, the substrate, rules, trust, SymLM, the gate, cubes and proposals. The test files are the authoritative list.

Not covered: bootstrap.py and most scps subcommands, which are exercised through manual use. Live paths in absorb_github.py need network access and are not tested.
