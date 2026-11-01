# SCP Substrate

A local store of capsules and typed links, with a few small engines on top, and a bounded symbolic language model (SymLM) that queries it in natural language.

## The idea

Everything is a capsule. The substrate only understands capsules and the links between them. The kinds of capsules that can exist are defined by foundations. What a capsule *means* is defined by the foundation it belongs to and the links it carries.

## The two-layer rule

Foundations live in `sc.json`. The substrate loads them at startup. They define what kinds of capsules can exist — `person`, `project`, `rule`, `observation`, `knowledge`, `leighton-weight`, `token`, `phrase`, `sentence`, and so on. Adding one is a versioned edit to a single file.

Instances live in `sc.db`. They are the actual things — `james`, `scp`, `obs-001`, SCP documents, verification records, repos, source files, symbols, conversation turns. They change constantly.

`bootstrap.py` copies `sc.json` into `sc.db` at startup. The DB is a projection of the file plus the instances that have accumulated on top.

`schema.sql` describes the shape of both layers. **One schema change since migration**: the never-populated `rules` table was dropped, logged as a `schema.migration` event. Everything else has been additive in `state_json`.

## What's in this directory

Root holds the world (`sc.json`, `sc.db`, `schema.sql`) and the `scps` CLI. Code lives in `src/` (engines, SymLM, crypto), `scripts/` (ingestion and tools), `seeds/`, `tests/` and `keystone-gate/`.

### Substrate
| File | Purpose |
|---|---|
| `schema.sql` | DDL for `capsules`, `links`, `events`, `trust_scores`, `schema_version` |
| `sc.json` | 18 foundations. Versioned, reviewed, single source of truth |
| `sc.db` | The world: instances, links, events, trust scores |
| `bootstrap.py` | Projects `sc.json` into `sc.db` |
| `substrate.py` | `Substrate` class — SQLite access, `decay_weight()` UDF, `write`, `link`, `supersede` |

### Engines
| File | Purpose |
|---|---|
| `rules.py` | Rule engine — 4 condition types: `pair`, `trust_above`, `kind_and_age`, `sequence` |
| `trust.py` | Trust — parameter (`n0 * e^(-k*t)`), evidence (observations + verifications), Bayesian fusion (`sigmoid`, `fuse`, `fused_trust`) |
| `queries.py` | Read-only queries: `trust_now`, `verified`, `latest`, `observations`, `what_supports`, `support_tree` |
| `why.py` | `why_trusted(id)` — walks backward through reasoning |
| `explain.py` | `explain(id)` — walks outward through structure and narrates |

### SymLM (language layer)
| File | Purpose |
|---|---|
| `parse.py` | Tokenise, reduce via grammar rules; alias/typo fallback |
| `generate.py` | Top-down expansion with feature filtering, retries, tense bias |
| `corpus.py` | Load corpus sentences from `corpus/*` capsules |
| `analysis.py` | Gap analysis — unreduced spans + composition gaps |
| `protocol.py` | Input classifier (layer 0–7); ack + error responses |
| `feedback.py` | `confirm`/`reject` → trust updates on words and rules |
| `talk.py` | REPL with layer dispatch, discourse state, pronoun resolution |
| `ask.py` | Natural language queries via intent classification + walkers |

### Keystone Gate (sibling application)
| Path | Purpose |
|---|---|
| `keystone-gate/kg` | CLI - stats, route, ask, gate, cube, neighbour |
| `keystone-gate/kg_gate.py` | The gate - rules, checks, refusal |
| `keystone-gate/kg_hal.py` | HAL - asks substrate, gates answer |
| `keystone-gate/kg_agent.py` | Cubes - faces, validation, completeness, neighbours, proposals |
| `keystone-gate/kg_rules.py` | Rules that propose face fills and neighbour links |
| `keystone-gate/seed_sc.py` | Seeds `sc/*` capsules |
| `keystone-gate/test_kg.py` | 57 boundary, gate, cube and proposal tests |

Keystone Gate shares `sc.db` with the substrate and writes its own capsules through `Substrate`; it does not change substrate code. See `keystone-gate/README.md` for the gate pattern and `docs/SPEC.md §15` for the general specification.

### Crypto
| File | Purpose |
|---|---|
| `ed25519.py` | Pure-Python Ed25519 (RFC 8032). Tested against RFC §7.1 vectors |
| `signing.py` | `sign`, `verify`, `canonicalise`, `did:key` encoding |
| `keygen.py` | Generate a keypair under `~/.config/scp/keys/` |
| `sign_doc.py` | Sign an SCP document |

### Ingestion
| File | Purpose |
|---|---|
| `import_scp.py` | Import a `giblets-scp` v1.x document |
| `import_person.py` | Import a person model document |
| `import_circadian.py` | Import a daily routine document |
| `absorb_repo.py` | Index a local repo — files + Python/JS symbols |
| `absorb_github.py` | Index a GitHub repo — metadata + tree (no content) |
| `fill_styles.py` | Promote `inherits` placeholders to real content |

### Seeds (create-only, capsules are authoritative after first run)
`seed_lexicon.py`, `seed_grammar.py`, `seed_corpus.py`, `seed_capsules.py`, `seed_protocol.py`, `seed_expansion.py`, `seed_features.py`, `seed_intents.py`, `learn_frequencies.py`, `extract_vocab.py`, `reconcile_seeds.py`

### Interface & tests
| File | Purpose |
|---|---|
| `scps` | CLI — see `./scps --help` |
| `test_substrate.py` | 70 tests, in-memory fixtures, no `sc.db` dependency |

### Docs
`docs/SPEC.md` (substrate spec), `docs/STRUCTURE.md` (file map, schema, extension points), `docs/REASONING.md` (how rules/trust/why/explain work). `docs/` also holds SCP source documents. `legacy/` holds pre-SQLite JSON.

## Quick start

```sh
cd ~/scp-substrate
python scripts/bootstrap.py         # project sc.json into sc.db
python tests/test_substrate.py    # confirm 70 tests pass
./scps stats                # what's in the substrate
```

CLI

```
scps stats                     # substrate counts
scps list [-f foundation] [-k kind]   # list instances
scps observations              # list observation capsules
scps rules                     # run the rule engine, report fires and warnings
scps trust-compute             # recompute materialised trust scores
scps trust <id>                # parameter + evidence trust
scps fused <id>                # Bayesian-fused trust (prior × evidence)
scps why <id>                  # why is it trusted (backward)
scps explain <id>              # narrate a capsule (outward)
scps verified <id>             # verification records
scps version <id>              # version chain via supersedes

scps ask "<question>"          # natural language query
scps talk                      # interactive REPL

scps parse "<sentence>"        # grammar parse, print tree
scps generate [--seed N] [--start S|NP|VP|PP]   # generate from grammar
scps sweep-parse [--older-than-hours N]         # delete old parse sessions
scps forget-parse <session>                     # delete one parse session
scps analyse-corpus [--only parseable|gaps|all] # gap analysis

scps confirm <session>         # mark parse as correct → trust up
scps reject  <session>         # mark parse as wrong → trust down
```

The binary is scps, not scp. scp is OpenSSH's secure copy.

Ask examples

```sh
./scps ask "who is james"
./scps ask "what did I decide about sqlite"
./scps ask "what tools do I use"
./scps ask "why is scp-claim trusted"
./scps ask "is james-gilbert-v1 signed"
./scps ask "list all repos"
./scps ask "where is parse_sentence"
./scps ask "what files in repo/scp-substrate"
./scps ask "what is repo/jamesthegiblet/blockforge-platform"
```

Signing an SCP document

```sh
python scripts/keygen.py default                    # → ~/.config/scp/keys/default.json (mode 0600)
python scripts/sign_doc.py my-doc.scp.json -o my-doc.signed.scp.json
python scripts/import_scp.py my-doc.signed.scp.json
```

import_scp.py verifies the signature and writes a verification:* capsule with a verifies link. Signing does not modify trust. Provenance and trust are separate.

Absorbing repos

```sh
python scripts/absorb_repo.py  /path/to/repo --dry-run    # local
python scripts/absorb_repo.py  /path/to/repo --write

python scripts/absorb_github.py owner/repo --dry-run      # GitHub (no token needed for public)
python scripts/absorb_github.py owner/repo --write
```

Local absorption reads contents: file hashes, line counts, imports, function/class symbols (Python via ast, JS via regex). GitHub absorption reads metadata + tree only (no content, no symbols).

What it does not do

· No network, no server. One SQLite file, one writer. absorb_github.py is the only outbound call and only when invoked manually.
· No neural components. SymLM is symbolic: grammar rules, features, intents. It parses and classifies; it does not generate from weights.
· No content indexing. Repos store file metadata (sha, size, language) and symbol names, not file bytes. grep on disk remains better for content search.
· No cross-session conversation memory. Each scps talk starts fresh. Conversation turns are logged as capsules but not read back as context.
· ~380 untagged nouns. The lexicon has 478 words; only 97 have animacy features. Untagged nouns pass semantic checks by default, which occasionally produces grammatically valid but semantically odd sentences.
· Ed25519 is pure-Python. Not constant-time. Fine for signing your own documents on your own device. Not for adversarial contexts or signing on behalf of others.
· Canonicalisation is a local convention. Sorted keys, no whitespace, signature.value blanked. Matches no external standard (not JCS / RFC 8785). Interop requires agreement on both sides.
· import_scp.py handles giblets-scp v1.x only. Other formats need a new importer.
· SymLM has 4 rule condition types, not arbitrary rules. A new condition requires an _eval_X() function in rules.py and a branch in evaluate_rules().
· Crypto and trust are separate systems. A valid signature does not raise trust; it adds evidence. The two combine only through fused_trust.

Extension points

· Add a foundation — edit sc.json, run bootstrap.py. No DDL change.
· Add a rule condition type — _eval_X() in rules.py, branch in evaluate_rules(), one rule capsule.
· Add a query — a function in queries.py, a walker in ask.py's WALKERS dict, an intent capsule.
· Add a CLI subcommand — cmd_X() and a subparser in scps.
· Add an SCP field — json_extract(state_json, '$.path.to.field'). No migration.
· Add a lexical entry — Substrate.write() with kind: lexical-entry. Or run seed_lexicon.py after editing it (create-only).

What has held up

Bootstrap, rules, trust, fusion, crypto, signing, verification, SCP import, SymLM (parser, generator, classifier, intents, feedback, REPL, NL queries), repo absorption, symbol extraction, and the shell — all added without further schema changes after the rules table was dropped. The substrate has been constant through ~15 distinct capability layers.

That was the point.
