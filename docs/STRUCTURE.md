Structure

What's here and how it fits together.

---

Directory

```
scp-substrate/
├── README.md              entry point
├── scps                   CLI
├── schema.sql             DDL
├── sc.json                foundations
├── sc.db                  instances, links, events
│
├── src/                   everything importable, in three packages
│   ├── store/             substrate (Substrate class, DB access, decay), rules,
│   │                      rules_sequence (grammar rules), trust (parameter and
│   │                      evidence trust, fusion), queries (read-only),
│   │                      signing (sign, verify, did:key), ed25519 (pure Python),
│   │                      evidence (what claims rest on, and its weights),
│   │                      claim_links (supports, goes-against and the other words)
│   ├── answer/            ask (intent matching), walkers (one per kind of question),
│   │                      walk_cubes (answers from cubes), explain, why
│   └── symlm/             the SymLM language layer: parse, generate, corpus,
│                          analysis, protocol, feedback, talk
│
├── scripts/               run by hand
│   ├── bootstrap.py       copy sc.json into sc.db
│   ├── archive_cubes.py   move capsules, their links and events into archive/
│   ├── evidence_from_sources.py  make evidence from each claim's source line
│   ├── readme_shots.py    take the README's screenshots
│   ├── scp/               keygen, sign_doc, import_scp (also import_person, import_circadian)
│   ├── repos/             absorb_repo, absorb_github: index a repo; repo_symbols: its functions and imports
│   └── language/          extract_vocab, fill_styles, learn_frequencies: the SymLM vocabulary
│
├── seeds/                 scripts that create starting capsules
│   ├── substrate/         the substrate's own: lexicon, grammar, corpus, intents, protocol
│   └── claims/            claims, entities and subjects; before-pivot/ holds the old cube seeds
├── tests/                 run.py, test_substrate_N.py, test_house_rules.py, support_substrate.py
├── docs/                  README (what each doc is for), VOCABULARY, SPEC, OUTLINE, STARTUP, PHONE, FAQ, REASONING, STRUCTURE
│   └── scp/               signed SCP documents (*.scp.json) imported into the store
├── archive/               archived capsules, links and events, one sc-archive-<date>.db per archive, and old README screenshots in images-<date>/
├── outlines/              outlines that kg import built entities from, kept as the record
├── images/                screenshots used in the README, taken by scripts/readme_shots.py
├── build/                 cubes.html, the generated page, tracked in git
│   └── public/            the public snapshot, its own repo (JamesTheGiblet/cubes), ignored here
├── keystone-gate/         the kg modules; tests/ and view/ (the page) in folders. Its seeds are in seeds/claims/. See keystone-gate/README.md
└── legacy/                pre-SQLite JSON archive, ignored by git
```

---

Layers

```
┌─────────────────────────────────────────────────────────────┐
│ interface      scps                                         │
├─────────────────────────────────────────────────────────────┤
│ language       ask  walkers  walk_cubes  parse  generate    │
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
│ foundations    sc.json                                      │
└─────────────────────────────────────────────────────────────┘
```

Layers import from layers below them, and `substrate.py` imports no engine or reasoning module. `keystone-gate/` sits beside `scps` at the top and imports from `src/`.

---

Files

The directory list above says what each file does. `keystone-gate/README.md` covers that folder.

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

Reads are not transactional. They see committed state. There is no snapshot isolation across multiple queries in a single user operation — a script reading trust_scores then reading links could see a change in between if another process wrote concurrently. This matters only with concurrent writers, which are not supported.

---

Extension points

Adding to the substrate, in order of difficulty:

A capsule of an existing foundation — Substrate.write({...}). No code change.

A new foundation — edit sc.json, run bootstrap.py. No code change. The foundation exists and instances can reference it. Nothing enforces its state.schema yet.

A new query — add a function to queries.py. To make it askable, add a walker to WALKERS in walkers.py and an intent capsule.

A new rule condition type — add an _eval_X() function to rules.py, extend the if/elif in evaluate_rules, add a capsule of foundation:rule with condition.type = "X". No changes to substrate.py or schema.sql.

A new trust signal — add a function to trust.py and a subcommand to scps. The convention is: writes go through Substrate, reads use queries.

A new CLI command — add cmd_X(a) and a subparser in scps.

A new SCP document format — write a new importer modelled on import_scp.py. It must accept a JSON dict and produce capsule writes through Substrate.

A schema change — the hardest. Requires a numbered migration script, updating schema.sql, bumping schema_version, and re-running bootstrap.py (which will skip DDL creation on existing DBs, so migration must be applied separately). Done once so far: the unused rules table was dropped, logged as a schema.migration event.

---

Test coverage

python tests/run.py runs everything.

- The test_substrate_N.py files use :memory: SQLite databases with small fixtures.
- The keystone-gate tests use :memory: fixtures and a temporary copy of sc.db, so they cannot write to the live one.
- test_house_rules.py fails if a code or page file passes 400 lines, or a Python exception is silently swallowed.

The test files split by size, so numbered files are not grouped by topic.

Not covered: bootstrap.py, most scps subcommands, the live paths in absorb_github.py, the live model APIs, and browser behaviour. The page has been checked by hand and with scripted runs in Edge.
