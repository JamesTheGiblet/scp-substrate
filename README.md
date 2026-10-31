# SCP Substrate

A local store of capsules and typed links, with a few small engines on top.

The language layer in this repo is a **SymLM** — a Symbolic Language Model. It parses, generates, classifies, and answers queries against the substrate using rules and capsules. No gradients. No weights. Every answer is a graph walk you can trace. See [SPEC.md §12](SPEC.md) for the definition and bounds.

## The idea

Everything is a capsule. The substrate only understands capsules and the
links between them. The kinds of capsules that can exist are defined by
foundations. What a capsule *means* is defined by the foundation it
belongs to and the links it carries.

## The two-layer rule

Foundations live in `sc.json`. The substrate loads them at startup. They
define what kinds of capsules can exist — `person`, `project`, `rule`,
`observation`, `knowledge`, `leighton-weight`, and so on. Adding one is
a versioned edit to a single file.

Instances live in `sc.db`. They are the actual things — `james`, `scp`,
`obs-001`, the SCP document, the verification record. They change
constantly.

`schema.sql` describes the shape of both layers. It has not changed
since the initial migration from JSON files to SQLite.

`bootstrap.py` copies `sc.json` into `sc.db` at startup. The DB is a
projection of the file plus the instances that have accumulated on top.

## What's in this directory

| File | Purpose |
|---|---|
| `schema.sql` | DDL for `capsules`, `links`, `events`, `rules`, `trust_scores`. Hasn't moved. |
| `sc.json` | 11 foundation definitions. Versioned, reviewed, single source of truth. |
| `sc.db` | The world: instance capsules, links, events, trust scores. |
| `bootstrap.py` | Projects `sc.json` into `sc.db`. Also imports any legacy `capsules/*.json`. |
| `substrate.py` | The `Substrate` class — SQLite access, `decay_weight()` UDF. |
| `rules.py` | Rule engine. Two condition types: `pair` (source → target), `trust_above` (score > threshold). |
| `trust.py` | Trust computation. Two formulas: parameter-based (`n0 * e^(-k*t)`) and evidence-based (sum of decayed observation scores). |
| `queries.py` | Read-only queries: `trust_now`, `verified`, `observations`, `what_supports`, `support_tree`. |
| `why.py` | `why_trusted(id)` — walks back through reasoning. |
| `explain.py` | `explain(id)` — walks out through structure and narrates. |
| `ed25519.py` | Pure-Python Ed25519 (RFC 8032). Tested against RFC §7.1 vectors. |
| `signing.py` | `sign`, `verify`, `canonicalise`, `did:key` encoding. |
| `keygen.py` | Generate an Ed25519 keypair under `~/.config/scp/keys/`. |
| `sign_doc.py` | Sign an SCP document. |
| `import_scp.py` | Import a `giblets-scp` v1.x document into `sc.db`. |
| `fill_styles.py` | Promote `inherits` placeholders to real content. |
| `scps` | The CLI. Nine subcommands. |

## Quick start

```sh
cd ~/scp-substrate
python bootstrap.py        # project sc.json into sc.db, import legacy capsules
./scps stats               # see what's in the substrate
```

Expected:

```
capsules (instances)      20
capsules (foundations)    11
links                     29
events                    65
trust scores              1
verifications             1
```

CLI

```
scps stats                                # substrate counts
scps list [-f foundation]                 # list instances, optionally by foundation
scps observations                         # list observation capsules
scps rules                                # run the rule engine, report fires and warnings
scps trust-compute                        # recompute materialised trust scores
scps trust <id>                           # parameter + evidence trust for a capsule
scps why <id>                             # why is it trusted (backward through reasoning)
scps explain <id>                         # narrate a capsule (outward through structure)
scps verified <id>                        # verification records for a capsule
```

Note: the binary is scps, not scp. scp is OpenSSH's secure copy.

Signing an SCP document

```sh
python keygen.py default
# → ~/.config/scp/keys/default.json (mode 0600)

python sign_doc.py my-doc.scp.json -o my-doc.signed.scp.json

python import_scp.py my-doc.signed.scp.json
```

import_scp.py verifies the signature and writes a verification:*
capsule with a verifies link back to the document. Signing does not
modify trust. Provenance and trust are separate.

What it does not do

· No network. No HTTP server, no API, no distributed store. A single SQLite file. One writer at a time.
· No AI, no ML. "Reasoning" here means graph traversal and SQL aggregates. The substrate counts and sums; it doesn't infer.
· Two rule condition types only. pair and trust_above. A third requires an _eval_X() function in rules.py and a branch in evaluate_rules().
· Parameter trust and evidence trust do not combine. They're two independent numbers, both true, neither overriding the other. Bayesian fusion is not implemented.
· Ed25519 is pure-Python. Not constant-time. Fine for signing your own documents on your own device. Not for adversarial contexts or signing on behalf of others.
· Canonicalisation is a local convention. Sorted keys, no whitespace, signature.value blanked. Matches no external standard (not JCS / RFC 8785). If you exchange signed documents with another system, both sides must canonicalise identically.
· import_scp.py handles giblets-scp v1.x only. Other SCP formats need a new importer.
· No instance versioning. If you overwrite a capsule, the previous state is in events, but there's no supersedes link convention. james-gilbert-v2 would be unrelated to james-gilbert-v1 unless you wire it.

Extension points

· Add a foundation — edit sc.json, run bootstrap.py. No DDL change.
· Add a rule condition type — add _eval_X() to rules.py, branch in evaluate_rules().
· Add a query — add a function to queries.py.
· Add a CLI subcommand — add cmd_X() and a subparser in scps.
· Read a new SCP field — json_extract(state_json, '$.path.to.field') in a query. No migration.

What has held up

Adding rules, trust, composition, SCP import, signing, verification, and the shell — none of that touched schema.sql after the initial migration. The substrate has been constant through seven layers of stuff on top of it.

That was the point.
