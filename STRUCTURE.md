STRUCTURE.md

Here it is, verbatim:

---

Structure

What's here, why, and how it fits.

---

Directory

```
~/scp-substrate/
├── README.md              entry point
├── SPEC.md                substrate specification (this repo's)
├── STRUCTURE.md           this file
├── REASONING.md           how rules / trust / why / explain work
│
├── schema.sql             DDL — the shape
├── sc.json                foundations — the constitution
├── sc.db                  instances, links, events — the world
│
├── substrate.py           Substrate class, DB access, decay UDF
├── ed25519.py             Ed25519 primitive (own, RFC 8032)
├── signing.py             sign / verify / canonicalise / did:key
│
├── rules.py               rule engine (3 condition types)
├── trust.py               trust engine (parameter, evidence, fusion)
├── queries.py             read-only queries
│
├── why.py                 backward reasoning (why is X trusted?)
├── explain.py             forward reasoning (what is X?)
│
├── import_scp.py          SCP document ingest
├── fill_styles.py         SCP inherits placeholder resolution
├── seed_capsules.py       one-shot seed of 11 context capsules
├── keygen.py              generate Ed25519 keypair
├── sign_doc.py            sign an SCP document
├── bootstrap.py           project sc.json into sc.db
│
├── scps                   CLI (10 subcommands)
├── test_substrate.py      21 tests, in-memory fixtures
│
├── docs/                  SCP source documents (*.scp.json)
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
scps CLI: 10 subcommands all of the above
test_substrate.py 21 tests all of the above

---

Schema

Six tables.

```sql
capsules(id PK, foundation, state_json, is_meta, created_at, updated_at)
links(id PK, source FK, type, target FK, metadata, created_at)
     UNIQUE(source, type, target)
events(seq PK, event_type, capsule_id, payload, occurred_at)
rules(id PK FK, trigger_on, condition, action, enabled)          -- unused
trust_scores(capsule_id FK, model_id FK, score, computed_at)      -- PK(capsule_id, model_id)
schema_version(version)
```

The rules table is unused. Rules are stored as capsules with foundation:rule; the engine queries capsules directly. The table is a leftover from the migration and should be dropped in a future schema change or documented as deprecated. Do not populate it.

Indexes:

```
idx_capsules_foundation    ON capsules(foundation)
idx_capsules_is_meta       ON capsules(is_meta) WHERE is_meta=1
idx_links_source           ON links(source, type)
idx_links_target           ON links(target, type)
idx_links_type             ON links(type)
idx_events_capsule         ON events(capsule_id, occurred_at)
idx_events_type            ON events(event_type, occurred_at)
idx_rules_trigger          ON rules(trigger_on) WHERE enabled=1   -- unused
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

Nothing outside substrate.py opens a write transaction. Every engine, every CLI command, every script calls into Substrate. This is the discipline that keeps event logging consistent.

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

A schema change — the hard one. Requires a numbered migration script, updating schema.sql, bumping schema_version, and re-running bootstrap.py (which will skip DDL creation on existing DBs, so migration must be applied separately). Not attempted in the current codebase.

---

Test coverage

test_substrate.py runs 21 tests against :memory: SQLite databases. Each test builds a minimal substrate fixture:

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

Coverage by area:

Area Tests
Crypto test_ed25519_rfc_vector_1, test_sign_verify_roundtrip, test_tamper_detection, test_canonicalise_deterministic
Substrate test_get, test_write_and_link, test_foundation_protection, test_supersede, test_supersede_rejects_missing_old
Rules test_rules_idempotent, test_rules_malformed_warns, test_kind_and_age_rule, test_kind_and_age_skips_young_question
Trust test_trust_parameter, test_trust_from_evidence, test_sigmoid, test_fuse_no_evidence, test_fuse_mid_prior_strong_evidence, test_fuse_disagreement_moves, test_fuse_clamping, test_fused_trust_integration

Not covered: why.py, explain.py, import_scp.py, bootstrap.py, scps itself. These are exercised only through manual use.

---

The rules table — a known wart

The rules table in schema.sql was created during the initial migration when rules were imagined as a first-class substrate concept. By the time the rule engine was implemented, rules had been modelled as capsules with foundation:rule, which fit the substrate's "everything is a capsule" model better. The table was never populated.

It remains in schema.sql. Dropping it requires a schema change. Until then:

· Do not populate it.
· idx_rules_trigger is dead weight.
