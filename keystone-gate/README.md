# Keystone Gate

Tools built on the SCP substrate for examining claims and checking answers. It shares `sc.db` with the substrate. Sibling to Replicant, using the same Forge tools.

It has four parts:

- **Cubes:** one claim examined through five lenses, then validated and attested by a person.
- **Gate:** checks an answer against a contract, and withholds it if it fails.
- **Model layer:** optional. Claude, Gemini or a local Ollama model rewords answers the substrate has already found.
- **Page:** a 3D view of the cubes, with editing when run through the local server.

The rule behind the gate and the model layer is that an LLM handles wording, not facts.

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
2. A person writes OPINION, or accepts or rewrites a suggested draft. Drafts from `seed_opinions.py` are Claude's suggestions.
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

## Foundational cubes

Foundational cubes are tagged `foundational`, and come in three kinds, each with its own colour:

| Tag | Kind | Colour | Examples |
|---|---|---|---|
| `safety` | Safety | Orange | Li-ion charging and fire, emergency stops, mains work |
| `security` | Security | Pink | Keys and secrets, the page password, private text |
| `preference` | Preferences | Blue | British English, Python, plain words in docs, files under 400 lines |

A cube goes to the first kind its tags name, in that order. Each kind gathers in its own group around you at the centre, with strands in its colour that brighten once validated. `seed_cubes_preferences.py` marks your attested principle cubes as preferences, adds two drafts, and suggests links from each kind to what it governs.

Their rules are enforced in `kg_cube.py` and `kg_fill.py`:

- A face cannot be bulk accepted.
- All five faces must be accepted before validating, where other cubes need two.
- The validation note must be your own, and a suggested note is refused word for word.
- Models cannot draft faces or suggest notes for them.

Each group grows its own form like the other clusters, and its cubes drift and spin while the three groups turn around you together. Cubes tagged `defining`, such as the ones about you, form a green ring outside them, turning the other way. A group stops turning while you have it open.

These rules check the process, not the truth, and they work through the code only. Someone with direct access to `sc.db` can bypass them.

## Models

`kg ask --claude "<question>"` is opt-in, because it sends the question and the walker's answer to outside services. The flag keeps its name, but the model that answers can be any of three.

1. The walker answers, and the answer must pass the gate. With no facts, no model is called.
2. A model rewords it. Each claim must quote the exact evidence it rests on.
3. `sc/claude-answerer` checks the result: quotes must be verbatim, and numbers and capitalised words must come from the evidence or the question.
4. If the model fails, or the gate refuses its answer, the next model is tried. If they all fail, the walker's answer is shown with the reasons.

| Order | Model | Runs on | Needs |
|---|---|---|---|
| 1 | Claude Opus 5.5, low effort | Anthropic | `claude_API_KEY` and the SDK |
| 2 | `gemini-3.5-flash` | Google | `gemini_API_KEY` |
| 3 | `llama3.2:latest` | This machine, through Ollama | Ollama running with that model |

Setup:

```sh
pip install -r keystone-gate/requirements.txt
```

Put the keys in `.env` at the repo root, as `claude_API_KEY=<key>` and `gemini_API_KEY=<key>`. Git ignores that file. `ANTHROPIC_API_KEY` and `GEMINI_API_KEY` override it if set. The SDK is needed for Claude only. Gemini and Ollama use the standard library.

Each paid call costs a small amount. Check Google's terms for how your plan treats what you send. Model names are constants at the top of `kg_llm.py`, and a retired model fails over to the next one.

Gemini and Ollama have answered live, but only a few times. Claude has reached the API and returned a credit error, so a real Claude answer is untested. The gate shows that a claim is anchored to a quote, not that the sentence means the same as the quote, and a new lowercase word can still pass. Ollama's small model can be slow, and it takes longest on the first call after loading.

## Repos

```sh
python keystone-gate/kg repo add JamesTheGiblet/Replicant
```

This reads the repo's README through `gh` and has a model write 3 to 6 claims. Each claim must quote a line of the README, and a claim whose quote is not found there is dropped. The quote becomes a draft FACT, worded as what the README says, so accepting it records what the README claims, not that the claim is true. The other lenses stay blank until you press **Fill blanks**. Under **Cluster by**, **Repos** shows one box per repo. A repo that already has cubes is skipped.

Private repos go to Ollama only. Their cubes are tagged `private`, so later drafts stay local, and so does `kg ask --claude` when its evidence contains the text of a private cube's claim or filled face. That check matches text, so it can miss an answer that rewords the cube. These cubes are still stored in `sc.db`, so they travel wherever that file is pushed. A published page also includes them.

## Overlaps

```sh
python keystone-gate/kg overlaps            # λ 0.60 and above
python keystone-gate/kg overlaps --min 0.3  # a wider look
```

An overlap is two cubes from different sources whose accepted faces share unusual words on the same lens. Each one has a Leighton weight, λ, from 0 to 2:

- N₀ is the sum of the lens similarities, capped at 2.
- λ = N₀ × e^(−kt), where t is the days since either cube last changed.
- Only λ of 0.60 or more is shown. That is the stack's boundary for λ.
- **Confirm** adds 0.20 and restarts the clock. **Not related** hides the pair for good.

In the page, **Overlaps** under **Cluster by** joins overlapping cubes into boxes, and a cube opened in the grid lists its overlaps. Pending drafts do not count.

This measures shared vocabulary, not shared meaning, so some overlaps are coincidences. The half-life is set to 60 days as a starting choice, not calibrated against outcomes.

## The page

```sh
python keystone-gate/kg cube serve --by james      # browse, and edit in the grid
python keystone-gate/kg cube view                  # read-only file, build/cubes.html
```

Cubes appear as 3D nodes grouped in clusters. Each cluster grows its own form: its cubes are joined by their shortest links with a soft skin around them, so the shape comes from where the cubes are and changes as they move. Click a cluster to enter it, and a cube to open it. Drag to orbit, scroll to zoom, and press Esc to go back. A grid view lists the same cubes.

Click a thread between two cubes to pull it. The two cubes come together, their clusters stay lit and the rest fades, and a panel says why they are linked: the word they share, with it marked in both sentences, or the reason given for a link you accepted or a model suggested. Press Esc or click empty space to let go. The threads that only shape a cluster cannot be pulled.

You are the green glow at the centre. A green strand runs to each cube you have validated, so a cube with no strand has not been vouched for, and the strands grow as you move along the time bar.

To keep a growing set readable, cubes shrink as their number rises, down to half size, and return to full size as you zoom in. From far away each cluster shows its three strongest cubes and dims the rest, and searching or filtering shows them all. Clusters circle slowly and cubes drift around their cluster, which stops for an open cluster and when the system is set to reduce motion.

**Cluster by** regroups the cubes by tag, repo or lens. Lens clustering compares each lens only with the same lens on other cubes, and links two cubes that share at least two uncommon words. Thread colour shows which lens. This measures shared vocabulary, so some links are coincidences. Group names are taken from the highest-scoring words and vary in quality, and a single edit can move other cubes between groups.

The bar at the bottom of the 3D view goes back through time, and **Play** runs it forward. Each step is a moment when something changed, so its spacing is not even in clock time. It uses the dates stored on cubes, faces, validations and attestations. Those dates hold only the latest change, so a face you edited appears at its last edit, with today's wording, and a past validation that later went stale still shows as stale. Retractions are not undone. The grid always shows the present, and editing is not affected by the bar.

Editing happens in the grid view only, under `serve`, after you unlock it. Set the password once:

```sh
python keystone-gate/kg cube password
```

Then press **Unlock to edit** in the grid. You can add cubes, write and edit faces, accept or reject drafts, write or edit the validation note, and attest. These run the same functions as the CLI. Validating needs all five faces accepted or written. Pending drafts appear hollow and count for nothing, but their text is used for clustering. Editing a validation note leaves an attestation in place.

Models can draft blank faces. A new cube is drafted automatically, and **Fill blanks** drafts the rest, including faces where you rejected a draft. This uses the same order as `kg ask --claude`, so the cube's text goes to Anthropic, then Google if Claude fails, then Ollama. Each draft stays pending until you accept it, so it adds nothing to the score. The page checks every 8 seconds and shows a message, a count in the tab title and a button that lists the drafts. Nothing checks a draft against your data, so reading it is the check. A rejected draft is only offered again if a model writes something different. The drafter runs only while `serve` is running. `kg cube draft` does the same at the terminal.

`kg cube notes` stores a suggested validation note for each cube that has none. The note appears in the **Validate** box and counts for nothing until you save it, and the wording is then yours. Suggestions are told not to claim you tested anything, but read them for that anyway.

Editing locks again when you press Lock, reload the page, stop the server, or leave it idle for 30 minutes. Only a scrypt hash is stored, at `~/.config/scp/cube-edit.json`, outside the repo. If you forget the password, delete that file and set a new one.

The password protects the page only. Anyone who can use your account on this machine can still change `sc.db` directly or through the `kg` commands.

The server listens on 127.0.0.1 only. Every request needs a token issued when the server starts, writes also need the unlock key, and requests naming another host or origin are refused. `--host` adds one name to that list, for use with a private network such as Tailscale. Do not expose it on a public network.

`build/cubes.html` is tracked in git. It holds nothing `sc.db` does not, and `sc.db` is tracked too. The page is a snapshot under `view`, so run the command again to refresh it. The Screenshot button saves the 3D view only, not the text panel.

### Public snapshot

`kg cube snapshot` writes a read-only copy for the open web to `build/public/index.html`. It leaves out cubes tagged private, cubes from a private repo, and any cube whose text names a private repo, matching the name as a whole word. Pending model drafts and suggested notes are left out too, and links to hidden cubes are cut. The list of private repos comes from `gh`, and if GitHub cannot be reached no snapshot is written. The finished page is checked again before it is saved.

`build/public` is a separate git repo, published at <https://jamesthegiblet.github.io/cubes/>. To refresh it:

```sh
python keystone-gate/kg cube snapshot
cd build/public && git commit -am "Refresh the snapshot" && git push
```

The name match is by word, so a cube that describes a private project without naming it would still go out. Read what a new cube says before refreshing. Your own notes can carry your full name, and those do go out.

## Commands

```
kg stats                            count cubes, lenses, faces, neighbour pairs
kg route list                       list all neighbours
kg ask "<question>"                 gated answer
kg ask --claude "<question>"        reworded by Claude, Gemini or Ollama
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
kg cube snapshot                    write the public copy, without private cubes or drafts
kg cube password                    set the password that unlocks editing
kg cube serve --by <name>           run the editable page (--port, --no-open)
kg cube contradicts <id> <other>    flag a contradiction
kg cube tick [id]                   run rules, creating proposals
kg cube draft [id]                  have a model draft blank faces
kg cube notes [id]                  have a model suggest validation notes
kg cube proposals [id]              list proposals (--status)
kg cube accept <proposal> --by <n>  apply a proposal
kg cube reject <proposal> --by <n>  reject a proposal (--reason)

kg repo add <owner/name> ...        write claim cubes from each repo's README
kg overlaps                         list overlapping work (--min)

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
| `kg_llm.py` | Model layer: Claude, Gemini, Ollama |
| `kg_lens_links.py` | Lens links and clusters |
| `kg_view.py` | Builds the page |
| `kg_serve.py` | Local server |
| `kg_public.py` | The public snapshot, without private cubes or drafts |
| `kg_lock.py` | Editing password |
| `kg_repos.py` | Claim cubes from a repo's README |
| `kg_overlaps.py` | Overlaps valued by Leighton weight |
| `kg_fill.py` | Models draft blank faces, in the background under `serve` |
| `view_template.html` | The page's HTML. `kg_view.py` joins the parts below into it |
| `view_style.css`, `view_grid.js`, `view_bar.js`, `view_edit.js` | Styling, grid view, top bar, editing |
| `view_field_world.js`, `view_field_draw.js`, `view_field_form.js`, `view_field_time.js`, `view_field_move.js` | The 3D view: layout, drawing, cluster forms, the time bar, moving around |
| `kg_stats.py`, `kg_router.py` | Counts and neighbour listing |
| `seed_sc.py` | Creates and updates `sc` capsules |
| `seed_cubes.py` | Project claims as draft cubes |
| `seed_opinions.py` | Suggested OPINION drafts by Claude, as proposals. They are not your views until accepted |
| `seed_cubes_james.py` | Cubes about James, as drafts in Claude's words, tagged private |
| `seed_cubes_m5stick.py` | M5StickC Plus2 cubes, cross-referenced across sources, as drafts |
| `seed_cubes_servos.py` | SG90, MG90S and MG996R cubes, cross-referenced, as drafts |
| `seed_cubes_batteries.py` | 7.4V 3000mAh Li-ion pack cubes, cross-referenced, as drafts |
| `seed_cubes_sensors.py` | Distance sensors, buzzers, LEDs and switches, cross-referenced, as drafts |
| `seed_cubes_wiring.py`, `seed_cubes_boards.py` | Wiring and dev board cubes, cross-referenced, as drafts |
| `seed_cubes_safety.py` | Hardware safety cubes linked to the rest, as drafts. Reference notes, not official guidance |
| `seed_cubes_robots.py` | Robot shapes and configurations, as drafts |
| `seed_cubes_security.py` | Foundational security cubes, and marks safety cubes foundational |
| `seed_links_foundations.py` | Suggested links from foundational cubes to related cubes, as proposals |
| `seed_cubes_preferences.py` | Marks your principle cubes as foundational preferences, adds two drafts, and suggests links |
| `seed_cubes_pca9685.py` | Cubes from Adafruit's PCA9685 guide |
| `seed_cubes_related.py` | General-knowledge cubes drafted by Claude, not from a stored document. Check figures against a datasheet or spec |
| `requirements.txt` | Anthropic SDK, needed only for Claude under `--claude` |
| `support_kg.py`, `test_*.py` | Tests |

## Tests

```sh
python tests/run.py
```

Gate and boundary tests read a temporary copy of `sc.db`, so they cannot write to the live one. The model tests use fake replies, so they make no network calls.

Browser behaviour is not covered by the test suite. It has been checked by hand and with scripted runs in Edge.

## Known issues

- `kg_router.py` only lists neighbours.
- `default-cube` rules `unknown_required` and `forward_only_lens_changes` are not enforced.
- Attestation adds the same trust whatever the reasoning, so "correct" counts the same as a full argument.

## Design decisions

- **One database, separate program.** The gate can check answers against the substrate directly. The cost is that cube data and substrate data are mixed, and a bad write affects both.
- **Contract as data, checks as code.** A contract edit alone adds nothing, because a new rule also needs a checker.
- **Structure-only gate.** Judging reasoning automatically is a harder problem, and would itself need checking. That is left to the person validating.
