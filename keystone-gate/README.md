# Keystone Gate

Tools built on the SCP substrate for examining claims and checking answers. It shares `sc.db` with the substrate. Sibling to Replicant, using the same Forge tools.

It has four parts:

- **Cubes:** one claim examined through five lenses, then validated and attested by a person.
- **Gate:** checks an answer against a contract, and withholds it if it fails.
- **Claude layer:** optional. Claude rewords answers the substrate has already found.
- **Page:** a 3D view of the cubes, with editing when run through the local server.

The rule behind the gate and the Claude layer is that an LLM handles wording, not facts.

## Boundary with the substrate

Keystone Gate adds no code to `src/substrate.py`, `src/rules.py`, `src/queries.py` or `schema.sql`, and its capsules are written through `Substrate.write()` and `Substrate.link()`.

The substrate side knows about cubes in three places: four foundations in `sc.json` (`cube`, `lens`, `cube-face`, `neighbour`), a `default-cube` capsule holding the weights, and read-only cube support in `src/walk_cubes.py` and `src/explain.py`.

Removing Keystone Gate would mean deleting this folder, those foundations, `walk_cubes.py` with its walker and intent, and the cube capsules.

## Cubes

A cube holds a claim. Each of its five lenses is a face, worth 16%, and human validation is worth 20%. The weights come from `default-cube`.

| Lens | Holds |
|---|---|
| FACT | What is recorded or known |
| COUNTER | The case against, or where it fails |
| OPINION | Your own view |
| FICTION | A what-if |
| CONTEXT | Where it came from and why it matters |

The usual path:

1. Lenses arrive as proposals, from rules (`kg cube tick`) or seed files. A proposal changes nothing until a person accepts it. A rejected proposal stays rejected unless its content or rationale changes.
2. A person writes OPINION.
3. A person validates the cube. `default-cube` sets a minimum of 2 lenses for this.
4. At 100%, a person can attest it. This writes an observation of the cube, so `fused_trust` counts it as evidence, moving the score from 0.50 to about 0.73.

Changing a face marks the validation stale and retracts the attestation, until a person validates and attests again.

Bulk accepted faces are recorded as `james (bulk accept, not read line by line)`, and the page shows them dimmed.

## The gate

An `sc` capsule is a contract: a list of rule names, stored as data. `kg_gate.py` holds a checker function for each name. A rule with no checker counts as a violation, so an unknown rule refuses the answer.

`sc/symlm-answerer` checks walker answers:

| Rule | Check |
|---|---|
| `no_invented_ids` | Slashed IDs and paths must be capsules or appear in stored content |
| `no_hallucinated_trust` | Trust numbers must match the capsule's real value, within 0.02 |
| `no_hallucinated_entities` | Hyphenated slugs and multi-word names must be capsules or appear in stored content |
| `no_llm_prior` | An affirmative answer must carry the real intent that produced it |

"Stored content" excludes logged chat, so typing a name does not make it pass.

`kg ask` shows an answer only if it passes; otherwise it prints the violations. `scps ask` does not use the gate, and neither does anything else that calls `ask.answer_question` directly.

The gate checks references, not reasoning. A passing answer can still be wrong. It cannot catch a single invented word such as "bigfoot", and `no_llm_prior` shows where an answer came from, not that its words follow from the walk.

To add a rule, add an entry to the `sc` capsule and a checker to `_RULES` in `kg_gate.py`.

## Claude

`kg ask --claude "<question>"` is opt-in, because it sends the question and the walker's answer to the Anthropic API.

1. The walker answers, and the answer must pass the gate. With no facts, Claude is not called.
2. Claude rewords it. Each claim must quote the exact evidence it rests on.
3. `sc/claude-answerer` checks the result: quotes must be verbatim, and numbers and capitalised words must come from the evidence or the question.
4. Any failure or refusal shows the walker's answer and says why.

Setup:

```sh
pip install -r keystone-gate/requirements.txt
```

Then set `ANTHROPIC_API_KEY`. It uses Claude Opus 5.5 at low effort, with server-side refusal fallback on, and each call costs a small amount.

This has been tested with a fake client and a mock server, not against the live API. The gate shows that a claim is anchored to a quote, not that the sentence means the same as the quote, and a new lowercase word can still pass.

## The page

```sh
python keystone-gate/kg cube serve --by james      # edit and add cubes
python keystone-gate/kg cube view                  # read-only file, build/cubes.html
```

Cubes appear as 3D nodes grouped in clusters inside a large cube. Click a cluster to enter it, and a cube to open it. Drag to orbit, scroll to zoom, and press Esc to go back. A grid view lists the same cubes.

**Cluster by** regroups the cubes by tag or by lens. Lens clustering compares each lens only with the same lens on other cubes, and links two cubes that share at least two uncommon words. Thread colour shows which lens. This measures shared vocabulary, so some links are coincidences. Group names are taken from the highest-scoring words and vary in quality, and a single edit can move other cubes between groups.

Under `serve` you can add cubes, write and edit faces, accept or reject drafts, validate and attest. These run the same functions as the CLI. Pending drafts appear hollow and count for nothing, but their text is used for clustering.

The server listens on 127.0.0.1 only. Writes need a token issued when the server starts, and requests naming another host or origin are refused. Do not expose it on a network.

`build/` is ignored by git because the page contains your opinions. The page is a snapshot under `view`, so run the command again to refresh it. The Screenshot button saves the 3D view only, not the text panel.

## Commands

```
kg stats                            count cubes, lenses, faces, neighbour pairs
kg route list                       list all neighbours
kg ask "<question>"                 gated answer
kg ask --claude "<question>"        reworded by Claude; uses the Anthropic API
kg gate check "<question>"          show the rules and the result
kg gate test                        run the contract's test cases

kg cube new "<content>"             create a cube (--source, --tag)
kg cube fill <id> <lens> "<text>"   fill one face
kg cube validate <id> --by <name>   record validation (--note)
kg cube attest <id> --by <name>     vouch for a complete cube
kg cube review --by <name>          work through cubes at the terminal (--tag)
kg cube show <id>                   faces, validation, completeness
kg cube list                        all cubes with scores
kg cube view                        write and open the read-only page
kg cube serve --by <name>           run the editable page (--port, --no-open)
kg cube contradicts <id> <other>    flag a contradiction
kg cube tick [id]                   run rules, creating proposals
kg cube proposals [id]              list proposals (--status)
kg cube accept <proposal> --by <n>  apply a proposal
kg cube reject <proposal> --by <n>  reject a proposal (--reason)

kg neighbour link <a> <b>           link two cubes both ways
kg neighbour list <id>              list a cube's neighbours
```

Run these as `python keystone-gate/kg ...`.

## Files

| File | Purpose |
|---|---|
| `kg` | CLI entry point |
| `kg_cube_cli.py` | `kg cube` and `kg neighbour` commands |
| `kg_agent.py` | Imports `kg_cube.py` and `kg_proposals.py` as one module |
| `kg_cube.py` | Cubes, faces, validation, attestation, neighbours |
| `kg_proposals.py` | Proposals |
| `kg_rules.py` | Rules that create proposals |
| `kg_review.py` | Terminal review |
| `kg_gate.py` | Gate rules and checkers |
| `kg_hal.py` | Asks the substrate and gates the answer |
| `kg_llm.py` | Claude layer |
| `kg_lens_links.py` | Lens links and clusters |
| `kg_view.py` | Builds the page |
| `kg_serve.py` | Local server |
| `view_template.html`, `view_field.js`, `view_edit.js` | The page |
| `kg_stats.py`, `kg_router.py` | Counts and neighbour listing |
| `seed_sc.py` | Creates and updates `sc` capsules |
| `seed_cubes.py` | Project claims as draft cubes |
| `seed_cubes_pca9685.py` | Cubes from Adafruit's PCA9685 guide |
| `seed_cubes_related.py` | General-knowledge cubes drafted by Claude, not from a stored document. Check figures against a datasheet or spec |
| `requirements.txt` | Anthropic SDK, needed only for `--claude` |
| `support_kg.py`, `test_*.py` | Tests |

## Tests

```sh
python tests/run.py
```

Gate and boundary tests read a temporary copy of `sc.db`, so they cannot write to the live one. The Claude tests use a fake client.

Browser behaviour is not covered by the test suite. It has been checked by hand and with scripted runs in Edge.

## Known issues

- `kg_router.py` only lists neighbours.
- `view_field.js` is over the project's 400-line rule.
- `default-cube` rules `unknown_required` and `forward_only_lens_changes` are not enforced.
- Attestation adds the same trust whatever the reasoning, so "correct" counts the same as a full argument.

## Design decisions

- **One database, separate program.** The gate can check answers against the substrate directly. The cost is that cube data and substrate data are mixed, and a bad write affects both.
- **Contract as data, checks as code.** A contract edit alone adds nothing, because a new rule also needs a checker.
- **Structure-only gate.** Judging reasoning automatically is a harder problem, and would itself need checking. That is left to the person validating.
