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

There is no fifth primitive. Every stored fact is one of these four.

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

The 11 foundations loaded at v0.1.0:

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

Append-only. Never updated, never deleted. Every write through Substrate.write(), link(), supersede() and every engine fire logs an event.

Event types in use:

event_type capsule_id payload
capsule.written the capsule {"foundation": "..."}
capsule.imported the capsule {"source": "<path>"}
capsule.superseded the old capsule {"new_id": "<id>"}
capsule.renamed the capsule {"from": "<old id>"}
capsule.deleted the capsule {"reason": "..."}
capsule.filled the capsule {"from": "placeholder"}
link.added the source {"type": "...", "target": "..."}
link.retyped the source {"target": "...", "new_type": "..."}
rule.fired the rule {"source": "...", "type": "...", "target": "..."}
trust.computed the instance {"model": "...", "score": 0.87, "prev": null}
foundation.reloaded NULL {"version": "0.1.0", "hash": "...", "count": 11}

Events are the ledger. Nothing in the system reconstructs state from events; the events are for audit, not for replay. This is a deliberate choice — replay is a v2 concern.

---

6. Two-layer invariant

The substrate has two artifacts that must stay in sync:

· sc.json — the constitution. Human-authored, versioned, single source of truth for foundations.
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

schema.sql has not changed since the initial JSON → SQLite migration. Seven layers of engines and features have been added on top without altering it:

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

1. schema.sql unchanged since initial migration
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
| Lexicon | 441 | `lex/*` capsules |
| Feature-tagged nouns | ~90 | `lex/*` capsules with `features.animacy` |
| Input classifiers | 11 | `classifier/*` capsules |
| Query intents | 10 | `intent/*` capsules |
| Corpus sentences | 24 | `corpus/*` capsules |

The system is enumerable. Every rule, every word, every classifier, every intent can be listed with `scps list -f knowledge`. Nothing is hidden in a blob.

### Properties

- **Symbolic** — representation is symbols (capsules), not dense vectors.
- **Bounded** — grammar and lexicon are fixed at any given time and listed in the substrate.
- **Local** — no network, no external model, one file.
- **Traceable** — every parse is a tree of `has-child` links; every query is a walk.
- **Grounded** — every answer comes from the substrate, never from statistical prior.
- **Deliberate** — behaviour changes only when a human adds, edits, or removes a capsule.

### Distinguished from a large language model

A large language model produces plausible text from a distribution over tokens, with no way to trace a given output to its cause. A SymLM produces text from rules the substrate can list, and any output can be traced to the rules and capsules that produced it. A SymLM will never hallucinate; it will fail obviously when it cannot parse or generate. An LLM will produce something plausible; a SymLM will produce something *correct or nothing*.

The two systems are not on the same axis. SymLM is not "smaller" — it is a different mechanism. The correct comparison is not "which is better" but "what do you need?" If you need provenance and explanation, you need a symbolic model. If you need fluency and breadth, you need a statistical one. A substrate like SCP can contain both; at v0.1 it contains one.
