# SCP Substrate Specification

Version 0.1.0. Describes what is implemented today. Not what is intended.

---

## 1. Primitives

A substrate has four kinds of things:

| Primitive | Where | Meaning |
|---|---|---|
| **Capsule** | row in `capsules` | a thing |
| **Foundation** | a capsule with `is_meta=1` | a kind of thing |
| **Link** | row in `links` | a typed edge between capsules |
| **Event** | row in `events` | a record of something that happened |

Every stored fact is one of these four. The `trust_scores` table is a stored copy of a computed value, not a fact in its own right.

---

## 2. Capsule

```sql
CREATE TABLE capsules (
    id          TEXT PRIMARY KEY,
    foundation  TEXT NOT NULL,
    state_json  TEXT NOT NULL DEFAULT '{}',
    is_meta     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

A capsule is:

· Identified by a stable string id (a namespaced key, e.g. james, giblets-forge/author/james-gilbert-v1, foundation:knowledge)
· Typed by foundation, which names the foundation capsule that defines what shape its state may have
· Bodied by state_json, an arbitrary JSON object
· Classified by is_meta — 1 for foundation capsules, 0 for instances

The substrate does not enforce the shape of state_json. That is the caller's responsibility. A foundation describes its expected shape in its own state.schema field, but no engine currently validates against it.

Capsules are written by Substrate.write() and Substrate.supersede(). Foundation capsules are written only by bootstrap.py from sc.json. write() raises ValueError if id.startswith("foundation:") or is_meta is truthy.

---

3. Foundation

A foundation is a capsule with:

· id prefixed foundation:
· is_meta = 1
· foundation = "foundation:foundation" (self-hosting)
· state containing at least name; optionally description, schema, allowed_links

The 19 foundations loaded at v0.1.0:

```
foundation:foundation
foundation:datacube
foundation:entity
foundation:event
foundation:knowledge
foundation:ledger
foundation:leighton-weight
foundation:observation
foundation:person
foundation:project
foundation:rule
foundation:token
foundation:phrase
foundation:sentence
foundation:cube
foundation:lens
foundation:cube-face
foundation:neighbour
foundation:subject
```

Foundations are the invariant of the system. Adding one is a versioned edit to sc.json; removing one soft-deprecates it (state.deprecated = true) but does not delete it, since instances may still reference it.

---

4. Link

```sql
CREATE TABLE links (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    target     TEXT NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    metadata   TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, type, target)
);
```

A link is a directed, typed, unique triple (source, type, target). type is a freeform string but by convention is a lowercase verb phrase: contributes-to, observes, about, verifies, supersedes, guided-by, uses, touched, inherits, declares, open-question.

Both source and target must be existing capsules. Foreign keys are on. Inserting a link to a missing target fails. This is deliberate: the graph is closed.

metadata is a JSON blob for edge-level annotations. Engines use it to record derivation: rule.fired writes {"derived_by": "<rule_id>", ...}; a trust-derived link writes {"derived_by": "...", "trust": 0.87}.

UNIQUE(source, type, target) makes link creation idempotent by construction.

---

5. Event

```sql
CREATE TABLE events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    capsule_id  TEXT,
    payload     TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Append-only. Never updated, never deleted, except by archiving: `scripts/archive_cubes.py` moves the events of the capsules it archives into `archive/sc-archive-<date>.db` and logs an `archive.moved` event in their place. The ledger is sc.db and its archives together. Every write through Substrate.write(), link(), supersede() and every engine fire logs an event.

Event types in use:

event_type capsule_id payload
capsule.written the capsule {"foundation": "..."}
capsule.imported the capsule {"source": "<path>"}
capsule.superseded the old capsule {"new_id": "<id>"}
capsule.renamed the capsule {"from": "<old id>"}
capsule.reclassified the capsule {"foundation": "..."}, from kg entity accept
capsule.merged the kept capsule {"from": "<old id>", "state": {...}}
capsule.deleted the capsule {"reason": "..."}, from absorb_repo.py --prune
capsule.filled the capsule {"from": "placeholder"}
link.added the source {"type": "...", "target": "..."}
link.retyped the source {"target": "...", "new_type": "..."}
rule.fired the rule {"source": "...", "type": "...", "target": "..."}
trust.computed the instance {"model": "...", "score": 0.87, "prev": null}
foundation.reloaded NULL {"version": "0.1.0", "hash": "...", "count": 11}
archive.moved NULL {"archive": "archive/sc-archive-2026-11-03.db", "kept_tags": [...], "counts": {...}}

Events are the ledger. Nothing in the system reconstructs state from events; the events are for audit, not for replay. This is a deliberate choice — replay is a v2 concern.

---

6. Two-layer invariant

The substrate has two artifacts that must stay in sync:

· sc.json — the foundations. Human-authored, versioned, single source of truth for foundations.
· sc.db — the world. Derived from sc.json at startup, plus instances accumulated by user writes.

bootstrap.py is the projection. It is idempotent: run it a hundred times, the DB reaches the same state. It checks for capsules table existence before writing DDL, so it's safe against an existing DB.

sc.json is never written by the substrate. sc.db is never edited by hand. Each has a single writer:

Artifact Writer
sc.json humans, via text editor
sc.db's capsules where is_meta=1 bootstrap.py, from sc.json
sc.db's capsules where is_meta=0 Substrate.write() and callers
sc.db's links Substrate.link(), Substrate.supersede(), engines

Breaking this rule — e.g. editing sc.db directly, or hand-writing a foundation into the DB — collapses the invariant.

---

7. Schema stability

schema.sql has changed once since the initial JSON → SQLite migration: the never-populated rules table was dropped, logged as a schema.migration event. These layers were added on top without any other change:

1. Rule engine
2. Trust engine
3. Composition (rule fires on trust)
4. SCP document import
5. Ed25519 signing
6. Verification capsules
7. CLI
8. Seed capsules, versioning, fusion, third rule condition

Any change to schema.sql is a schema change and requires a numbered migration. There is currently no migration framework; the expectation is that schema changes will be manual, rare, and reviewed.

---

8. Trust model

Two independent trust signals per capsule:

Parameter trust — from the capsule's own state:

```
score(t) = n0 * e^(-k * t_days)
```

where n0, k are in the capsule's state, and t_days is either state.age_days (if numeric) or elapsed from created_at. Materialized into trust_scores by compute_all().

Evidence trust — from the substrate graph:

```
score = Σ (observation.score * e^(-k * obs_age))
      + Σ (verification_weight * e^(-k * ver_age))
```

where a valid verification contributes +1.0, invalid -1.0. Parameter k is taken from the trust instance's state if the capsule has an about link; if not, k=0 and evidence is undecayed.

Fusion — Bayesian combination:

```
L = sigmoid(evidence_score)
posterior = (prior * L) / (prior * L + (1 - prior) * (1 - L))
```

with both prior and L clamped to [1e-3, 1-1e-3] to avoid degenerate 0/1 cases. When prior is missing, prior=0.5 is used and source reports evidence-only.

All three are exposed: scps trust <id> (parameter + evidence), scps fused <id> (posterior).

---

9. Signature format

Signed documents are JSON with a signature object:

```json
{
  "signature": {
    "key_id":    "did:key:z6Mk...",
    "algorithm": "Ed25519",
    "value":     "<base64 of 64-byte Ed25519 signature>"
  }
}
```

Canonicalisation (signing.canonicalise):

1. Deep-copy the document
2. Set signature.value = null (so the signature is not signing itself)
3. json.dumps(sort_keys=True, separators=(",", ":"), ensure_ascii=False)
4. Encode as UTF-8

This is a local convention, not JCS / RFC 8785. Interop requires agreement.

Signing: Ed25519 over the canonical bytes, using the 32-byte seed.
Verification: checkvalid(sig, canonicalise(doc), public_key_from_did_key(key_id)).
Malleability: rejected by S >= l check.
Constant-time: no. The pure-Python ed25519.py is not constant-time. Safe for local signing, not for adversarial contexts.

---

10. SCP document format (giblets-scp v1.x)

The substrate ingests documents with scp_id, declaration, inherits, signature. Import via import_scp.import_scp(s, doc):

· scp_id → capsule id
· declaration → capsule state.declaration
· Document metadata (scp_version, canonicalisation, signature, licence) → state.source_format
· inherits[] → links of type inherits from the document to each target (creating placeholder capsules if missing)
· declaration.entity.capsule (or entity.handle) → declares link from the document to the named capsule; symmetric declared-by link back

The document's foundation is foundation:knowledge, because a declaration is a claim. This is a policy decision, not enforced by the substrate.

---

11. Invariants

1. schema.sql changes only by reviewed, logged migration
2. Foundations are written only by bootstrap.py; Substrate.write() rejects foundation:* IDs
3. Foundation removal is soft (deprecation), never hard delete
4. Links are unique triples; UNIQUE(source, type, target) enforces
5. Events are append-only; no UPDATE or DELETE against events
6. Substrate engines are consumers, not mutators, of capsule shape
7. sc.db and sc.json each have a single writer

Any change that breaks one of these is a design change, not a bug fix.

---

## 12. SymLM — the symbolic language layer

The language layer is a **bounded symbolic language model** named SymLM. It sits on top of the substrate; it does not modify it.

### Definition

A SymLM is a language model where:

- the grammar is stored as capsules (sequence rules),
- the lexicon is stored as capsules (lexical entries with POS and features),
- the input classifiers are stored as capsules (protocol layers, query intents),
- changes are made by humans editing capsules, not by gradient updates,
- every answer is a graph walk ending in a rendered response.

There are no weights. There is no training loop. There is no probability distribution over tokens. Generation is rule expansion under feature constraints and corpus frequency. Parsing is rule reduction over a fixed grammar.

### Bounds at v0.1

| Dimension | Count | Where |
|---|---|---|
| Grammar rules | 12 | `grammar/*` capsules |
| Lexicon | 478 | `lex/*` capsules |
| Feature-tagged nouns | 97 | `lex/*` capsules with `features.animacy` |
| Input classifiers | 11 | `classifier/*` capsules |
| Query intents | 13 | `intent/*` capsules |
| Corpus sentences | 24 | `corpus/*` capsules |

The system is enumerable. Every rule, every word, every classifier, every intent can be listed with `scps list -f knowledge`. Nothing is hidden in a blob.

### Properties

- **Symbolic** — representation is symbols (capsules), not dense vectors.
- **Bounded** — grammar and lexicon are fixed at any given time and listed in the substrate.
- **Local** — no network, no external model, one file.
- **Traceable** — every parse is a tree of `has-child` links; every query is a walk.
- **Grounded** — answers are built from substrate content by walkers, not from statistics.
- **Deliberate** — grammar and intents change when a capsule is edited. Word and rule trust also move with `scps confirm` and `scps reject`.

### Distinguished from a large language model

A large language model produces text from a distribution over tokens, which makes it fluent and broad but hard to trace to a cause. SymLM builds text from rules that can be listed, so an output can be traced to the rules and capsules behind it.

SymLM covers far less. It fails visibly when it cannot parse or match a question, though a walker can still give a wrong answer if a capsule is wrong or an entity is misidentified. The substrate can hold both kinds of system: `kg ask --claude` adds Claude for wording, outside SymLM.

---

## 13. Repos and symbols

The substrate holds a small inventory of local and remote repositories, plus symbol extraction over source files. This is data — no new tables.

### Repo capsule

```
repo/<owner>/<repo>      (GitHub-absorbed)
repo/<repo>              (locally-absorbed)
foundation: knowledge
state:
kind: repo
source: github | local
full_name, owner, name, description
default_branch, tree_sha, git_branch, git_head
language, languages, primary_language
file_count, size_bytes, total_size_bytes
stars, forks, open_issues, license, topics
html_url, clone_url
created_at, updated_at, pushed_at, last_absorbed

```

### File capsule

```

file/<owner>/<repo>/<rel-path>   (GitHub)
file/<repo>/<rel-path>           (local)
foundation: knowledge
state:
kind: source-file
source, repo, repo_id, path, abs_path (local only)
language, size_bytes, sha (github) or sha256 (local)
lines (local only — content read)
imports (local, Python/JS only)
last_modified, last_absorbed

```

Repos link to their files via `contains`. One repo → many files. On re-absorption, the file is updated only if its hash changed; unchanged files are skipped.

### Symbol capsule

```

symbol/<repo>/<path-slug>/<name>
foundation: knowledge
state:
kind: symbol
name, symbol_kind (function | class | method)
line, docstring
repo, file, file_id, language

```

Each file with symbols links to its symbols via `defines`. Symbol extraction is content-based for local absorption:

- **Python**: `ast.parse`, top-level `FunctionDef`/`AsyncFunctionDef`/`ClassDef`, class methods as `<Class>.<method>`, imports from `Import`/`ImportFrom`
- **JavaScript / TypeScript**: regex on function declarations, class declarations, `const x = () => {}` patterns, `import ... from '...'`

Symbols are **not** extracted for GitHub-absorbed repos. The GitHub API gives tree SHAs, not file contents. To get symbols, clone the repo locally and run `absorb_repo.py`.

### Idempotence

Both `absorb_repo.py` and `absorb_github.py` are idempotent:
- File capsule updated only if hash changed
- Symbol capsule created only if absent (path + name + file is the identity)
- Imports updated in place if changed

---

## 14. Natural language query interface

`scps ask "<question>"` and `scps talk` (REPL) route natural language to the substrate via intent classification. Same substrate, no new tables.

### Flow

```

question → intent classification → entity extraction → walker → render → answer

```

### Intents

Intents are capsules of `kind: input-intent` under `foundation:knowledge`:

```

intent/why-trusted       → walker=why_trusted    (backward reasoning)
intent/verified          → walker=verified       (signature records)
intent/what-decided      → walker=what_decided   (decisions + rationale)
intent/what-believe      → walker=what_believe   (cubes on a topic, or attested cubes)
intent/what-uses         → walker=what_uses      (tools)
intent/what-building     → walker=what_building  (projects)
intent/what-supports     → walker=what_supports  (evidence)
intent/list-kind         → walker=list_kind      (filter by state.kind)
intent/what-happened     → walker=what_happened  (sessions)
intent/who-is            → walker=who_is
intent/what-is           → walker=what_is
intent/where-is          → walker=where_is       (symbols/files by name)
intent/what-files        → walker=what_files     (files in a repo)

```

Each intent has a `phrases` list. Classification does substring matching on `phrases` (`any_phrase` mode), then tries any regexes in the optional `patterns` list. Order matters: intents are sorted by id, and earlier ids win on ambiguity.

### Entity extraction

`extract_entity` finds the substrate ID the question is *about*:
1. Direct ID match: any token that contains `/` and exists in the substrate (`repo/owner/name`, `file/owner/name/path`)
   A hyphenated token that is the last segment of exactly one ID also matches (`james-gilbert-v1`)
2. 3-, 2-, 1-word compound slugs scanning left-to-right
3. `state.text` or `state.name` match across lexical entries
4. Intent-specific fallback (`james` for `what_uses`, `james` for `what_building`, `None` for `what_decided` and `list_kind`)

Vocabulary capsules (`lex/`, `typo/`, `alias/`, `corpus/`) are skipped during entity extraction — they're lexical, not entities.

### Walkers

Each walker is a function in `ask.py`'s `WALKERS` dict. A walker takes `(substrate, entity_id, text)` and returns `{ok, summary, detail}`.

Walkers compose existing queries: `_walk_why_trusted` calls `why.why_trusted`, `_walk_verified` calls `queries.verified`, `_walk_what_supports` calls `queries.what_supports`, `_walk_what_is` calls `explain.explain`. A new walker that answers a new question is one function + one intent capsule + one test.

### Talk layer dispatch

`scps talk` is a REPL that classifies input into protocol layers before dispatching:

- **Layer 0 (unknown)**: brief error, no word dump, logs `unparsed-input`
- **Layer 2–6 (ack)**: greeting, wellbeing, farewell, thanks, apology, request, smalltalk, question-mark, wh-question, ack — respond with a matched ack template
- **Layer 7 (application)**: parse, generate, or (for questions) route to `ask`

Questions (anything ending `?` or starting with wh-word) are tried against the substrate first via `ask.answer_question`. If the question matches an intent, the walker result is the response. Otherwise the layer-7 branch falls back to grammar parse + generate.

Layer-2 through layer-6 classifiers are capsules (`classifier/*`), not code. Adding a new greeting or farewell is a capsule edit, not a code change. Classifier match modes: `exact`, `contains` (word-boundary), `endswith`, `startswith`, `parses`.

### What it can and cannot answer

**Can** — anything expressible as a walk over existing graph structure: why is X trusted, is X signed, what did I decide about Y, what files in repo Z, where is function W, list all decisions/principles/repos, what happened in session Q.

**Cannot** — open-ended semantic queries ("what does this code do?"), cross-file content search (grep on disk is better), multi-hop reasoning beyond one or two link types per walker. Those remain future work: a new walker is a new capability, and each is bounded.


---

## 15. Gate pattern - the anti-drift mechanism

The substrate stores facts. It does not enforce what an LLM may say about them. That's a different problem, and it has a substrate-level pattern: **the gate**.

An `sc` capsule defines a contract that a gated function must honour. A gate checks proposed answers against that contract and refuses any answer that violates it. The gate does not judge reasoning - only references.

### The `sc` capsule

```

sc/<name>
foundation: knowledge
state:
kind: sc
name: <name>
purpose: <description>
must:        [{rule, description}, ...]
must_not:    [{rule, description}, ...]
test_cases:  [{input, expect_pass, reason}, ...]
boundary:    <description of what the gate checks and doesn't>
version:     <semver>

```

An `sc` capsule is data. It contains no executable logic. It describes what a gated function may produce. Adding a rule means adding a `must` or `must_not` entry and a matching checker in the gate implementation.

The first seeded contract is `sc/symlm-answerer`. `must` and `must_not` entries are both enforced:
- `no_invented_ids` - every slashed ID or path mentioned must be a capsule or appear in stored content
- `no_hallucinated_trust` - every numeric trust score must match `trust_now(id).score`, `fused_trust(id).posterior` or the capsule's stored `score`, within 0.02
- `no_hallucinated_entities` - every hyphenated slug and multi-word name must be a capsule or appear in stored content
- `no_llm_prior` - an affirmative answer must carry the real `input-intent` that produced it. Explicit refusals (`ok: false`) pass

"Stored content" means whole terms found in capsule state, link types and kind names. Logged chat (`conversation-turn`, `unparsed-input`) does not count: typing a name does not make it real.

Two limits are deliberate. A bare single word ("bigfoot") cannot be told apart from English, so it is out of reach. `no_llm_prior` checks provenance, not whether the words follow from the walk.

### The gate check

The gate is a function `check(substrate, {input, result}, sc) -> {ok, violations[]}`. Where `result` is the output of `ask.answer_question` (or of any LLM, later).

For each `must` and `must_not` entry in the `sc` capsule, a checker function runs. If any checker produces violations, `ok = false` and the answer is refused. If no checker exists for a rule name, the gate fails closed - an unknown rule is a violation, never a pass.

### The pattern, generalised

The gate is not Keystone-Gate-specific. Any application that produces language from substrate facts can adopt the same shape:

- Define an `sc` capsule naming the contract
- Write checkers for each `must` rule
- Route all output through the gate before rendering

What the pattern does and does not do:

1. Answers that fail a check are refused, but only on paths that use the gate. `kg ask` does. `scps ask` does not.
2. Contracts are data, and a new rule also needs a checker function.
3. A rejected answer is withheld, not shown with a warning.
4. Gates live in applications, not in `substrate.py`.

### Gating a real LLM

`sc/claude-answerer` is the contract for `kg ask --claude`, whichever model answers. The walker finds the facts and the model only rewords them. Each claim must carry a verbatim quote from the walker's evidence, so two rules join the four above:

- `claims_quote_evidence` - every claim's quote must appear in the evidence
- `no_unsourced_terms` - numbers and capitalised words must come from the evidence or the question

A paraphrase that misstates its quote, or a new lowercase word, still passes: the gate proves anchoring, not meaning. Any failure or refusal shows the walker's own gated answer, so the LLM path cannot be worse than the walker.

### Implementation reference

Keystone Gate is the first implementation of this pattern:

- `seeds/claims/seed_sc.py` - seeds `sc/symlm-answerer`
- `keystone-gate/kg_gate.py` - `check()` and one `_check_*` function per rule
- `keystone-gate/kg_hal.py` - `ask_gated()` - asks substrate, gates answer, returns pass or reject
- `keystone-gate/kg_llm.py` - `ask_llm()` - walker, then Claude, Gemini and Ollama in turn, each through the gate, with fallback
- `keystone-gate/kg gate test` - runs the sc capsule's own test cases against the live substrate

The substrate does not depend on the gate. The gate depends on capsule lookups, stored content and trust values.

---

## 16. Cubes

Cubes belong to Keystone Gate and use no new tables. `keystone-gate/README.md` describes how to use them.

### Capsules

| ID | Foundation | Kind | Holds |
|---|---|---|---|
| `cube/<slug>` | `foundation:cube` | `cube` | `content`, `source`, `tags`, `contradicts` |
| `<cube>/face/<LENS>` | `foundation:cube-face` | `cube-face` | `lens`, `content`, `filled_by`, `confidence` |
| `<cube>/face/human-validation` | `foundation:cube-face` | `cube-face` | `validator`, `note`, optional `stale` |
| `<cube>/proposal/<n>` | `foundation:knowledge` | `cube-proposal` | `proposal_type`, `status`, `proposed_by`, and the change |
| `<cube>/attestation` | `foundation:observation` | `attestation` | `score`, `source`, `note`, optional `retracted_because` |
| `source/<name>` | `foundation:knowledge` | `source-document` | Where a set of cubes came from |

Links: `has-face`, `about`, `classified-by`, `neighbour`, `contradicts`, `observes` (attestation to cube), `derived-from` (cube to source).

### Completeness

`score = lenses_filled * per_lens + human_validation`, with both weights read from `default-cube`: 0.16 and 0.20. A cube is complete at 1.0. A stale validation counts as none. Validation needs `rules.minimum_lenses` filled lenses.

### Attestation

Needs a complete cube. It writes the attestation observation, which `fused_trust` counts as evidence. Changing a face's content sets its score to 0 and records why.

### Browser access

`kg cube serve` runs an HTTP server bound to 127.0.0.1. `POST /api/do` applies one action and returns the updated cubes and clusters. Each POST needs the `X-Cube-Token` header, issued when the server starts and embedded in the page. `POST /api/unlock` checks the editing password against the scrypt hash in `~/.config/scp/cube-edit.json` and returns a key. `/api/do` also needs that key in `X-Cube-Key`, otherwise it returns 401. The key is held in memory, lapses after 30 idle minutes, and `POST /api/lock` ends it. `POST /api/status` reports the pending drafts and sends the cubes when that count has moved. The `new` action queues the cube for `kg_fill.py`, and the `draft` action queues every cube with a blank, one at a time on a background thread. Drafts are proposals with `proposed_by` set to `model-draft:<model>`. Requests with another `Host` or `Origin` are refused.

## 17. Entities, subjects and claims

The model the store is built on since 3 November 2026. A claim is a cube (section 16), and entities and subjects give it a place. [VOCABULARY.md](VOCABULARY.md) gives the reasons and the status of each part. Like cubes, they use no new tables.

### Capsules

| ID | Foundation | Holds |
|---|---|---|
| `entity/<slug>` | `foundation:entity` | `name`, `kind`, `created_by`, `created_at`, and optional fields such as `definition`, `aliases` and `parts` |
| `project/<slug>` | `foundation:project` | The same, for a project |
| `james` | `foundation:person` | The same, for a person. The store's owner stays `james` |
| `subject/<slug>` | `foundation:subject` | `name`, `kind` |
| `proposal/sort/<id>` | `foundation:knowledge` | A proposed entity kind for an existing capsule, waiting for `kg entity accept` or `reject` |

### Links

| From | Link | To |
|---|---|---|
| entity | `uses`, `can` | subject |
| entity | `part-of`, `owns`, `building`, `works-at`, `at` | entity |
| claim | `about-subject` | subject |
| claim | `about-entity` | entity |
| claim | `derived-from` | evidence |

`kg entity link` refuses any entity link not in this table. A claim's state may also hold `wires`, a list of pin-to-pin pairs, which `kg_wiring.py` joins into nets.

### Building them

One at a time: `kg entity add` makes an entity and `kg entity link` links it. `kg subject accept` makes a subject from a proposal, and `kg subject add` says a claim is about an existing subject. `kg import <outline>` makes an entity, its subjects and its claims from one file, checking every id first so that it writes all or nothing (`docs/OUTLINE.md`).
