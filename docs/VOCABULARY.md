# Vocabulary

The words this project uses for what it knows, and how they fit together. Agreed on 3 November 2026, when every cube was archived to start again on this structure.

`SPEC.md` describes what is built. This file describes the agreed model, and marks each part as **built**, **partly built** or **not built**. When a part is built, `SPEC.md` gains the detail and this file keeps the meaning.

---

## The idea

Five kinds of thing, joined by named links:

| Term | Is | Example |
|---|---|---|
| **Entity** | A thing that exists | James, SCPBot, a robot arm, a house, a project |
| **Subject** | Something an entity knows about | PCA9685, ESP32, Li-ion packs, sleep |
| **Claim** | A statement about a subject, examined through five lenses | "The PCA9685 drives 16 PWM channels" |
| **Evidence** | Why a claim exists | A datasheet, a test log, an observation |
| **Relationship** | A named link between two of the above | servo current *depends on* battery capacity |

A claim is what the page draws as a **cube**. The two words mean the same thing: *claim* in the model, *cube* on the page and in the code.

The same rules apply at every scale. James, SCPBot, a company and a world are all entities, and nothing changes in the model as more are added.

---

## Entity

A thing that exists, with identity. People, robots, projects, places, organisations, vehicles.

- **ID:** `entity/<slug>`, stored under `foundation:entity`. Projects are `project/<slug>` under `foundation:project`, and people `foundation:person`. All three count as entities. James stays `james`, since the walkers look for that id, and repos keep `repo/...`, so re-indexing still finds them.
- **Kind:** a field saying what sort of entity it is, such as `person`, `robot`, `project` or `place`.
- **Links:** an entity *uses* or *knows about* subjects, and *is part of* or *owns* other entities.

**Status: partly built.** `kg entity add`, `link`, `list` and `show` exist, in `keystone-gate/kg_entities.py`. The entities so far are James, SCPBot, the ACEBOTT spider chassis (part of SCPBot), and the projects the Forge Stack, the SCP substrate, Replicant, LLLM, Canon and JIG; the rest of what James links to is still waiting to be sorted (below). The SCP substrate describes itself against the Forge Stack's five layers, gaps included, as claims about project/scp-substrate. On the page, an entity that uses subjects is a smaller green dot with its parts circling it, and each claim gathers round the first of its parts. In the grid, every entity and subject has a card; opening one shows what it is, its parts or who uses it, and only its claims.

### Sorting what was already there

Before this model, the capsules around James were stored as plain knowledge. A **sort proposal** says what one should become, and changes nothing until James accepts it, with `kg entity accept`. He can correct it while accepting, with `--as`, `--kind`, `--id`, `--name` and `--into`.

| Action | What it does |
|---|---|
| entity | Gives it an entity foundation and a kind, and a new id if one is named |
| subject | Moves it to `subject/<slug>`, and turns `<subject> used-in <entity>` into `<entity> uses <subject>` |
| merge | Folds a duplicate into another capsule, moving its links. Its state is kept in the `capsule.merged` event |
| drop | Deletes it, keeping its state in the `capsule.deleted` event |
| describe | Marks a document as describing an entity: `same-as` becomes `<entity> described-by <document>` |

A rename moves every link with the capsule and logs `capsule.renamed`. Older events keep the old id.

`seed_entity_sorting.py` proposes a sorting of everything `james` links to: projects, organisations, a place and repos as entities, tools, ESP32, Claude and carpentry as subjects, two duplicates merged, a stray capsule dropped, and `person/james-gilbert` as the signed document that describes James. Its content is not folded into `james`, because that would break its signature.

## Subject

Something one or more entities know about. A component, a topic, a measure.

- **ID:** `subject/<slug>`, such as `subject/pca9685`.
- **Exists once.** If James, SCPBot and the robot arm all use a PCA9685, there is one `subject/pca9685` and three links to it. Knowledge about it is written once and reused.
- **Links:** a claim links to its subject with `about-subject`. Plain `about` is taken: `trust.py` reads it as marking a trust record. Subjects can be *part of* other subjects, and *depend on* them.

**Status: partly built.** `foundation:subject`, subject proposals and `about-subject` links exist, through `kg subject` and `keystone-gate/kg_subjects.py`. Links between subjects are not built. Each subject has its own place in the grid. Tags stay as labels for filtering.

**Wiring.** A claim about how an entity is wired links to `subject/wiring` and lists its wires as pin-to-pin pairs. `kg wiring <entity>` traces which pins end up joined, so a common ground or a shared bus forms from the wiring rather than being stated as a claim of its own. Built in `keystone-gate/kg_wiring.py`.

## Claim

One statement, examined through the five lenses. This is the cube.

- **ID:** `cube/<slug>`, kept as it is so existing cubes and their faces keep their IDs.
- **Statement:** the claim itself, in `content`.
- **Kind:** what sort of statement it is. Plain claims have no kind. The others are:

  | Kind | A claim that |
  |---|---|
  | `question` | asks something not yet known |
  | `assumption` | is taken as true without being checked |
  | `constraint` | limits what can be done |
  | `requirement` | must hold for something to work |
  | `experiment` | sets out a test to run |
  | `decision` | records a choice made |

  A kind does not change how the claim is scored. Every kind is still examined through all five lenses.

- **Subject:** a claim is *about* one or more subjects, and can also be about one or more entities as a whole.

**Status: built**, apart from kinds. A claim links to its subjects with `about-subject` and to its entities with `about-entity`.

## Lens and face

A lens is a way of looking at a claim. There are five, and every claim is looked at through all of them:

| Lens | Holds |
|---|---|
| FACT | What is recorded or known |
| COUNTER | The case against, or where it fails |
| OPINION | James's own view |
| FICTION | A what-if |
| CONTEXT | Where it came from and why it matters |

A **face** is one claim's filling of one lens. A claim has five lens faces plus a human validation face. Each lens face is worth 16% and validation 20%, set by `default-cube`.

A lens is not a tag and not a kind. "Tag" was once listed as a lens; it is a label instead.

**Status: built.**

## Evidence

What a claim rests on. Datasheets, guides, test logs, videos, papers, forum threads, James's own observations.

- **ID:** `evidence/<slug>`.
- **One piece, many claims.** A datasheet backs every claim drawn from it, so evidence is its own capsule, linked from each claim it supports.
- **Fields:** `kind` (datasheet, test-log, observation, paper and so on), `title`, and `url` or `path` where there is one.
- **Links:** a claim is *derived from* evidence. A face can name the evidence it quotes, mostly FACT.

**Status: not built.** Before the archive, `source/<slug>` capsules did this job, linked by `derived-from`. They went with the cubes that cited them. They are to become `evidence/<slug>`.

## Relationship

A link between two capsules, read as a sentence: *from* — *word* — *to*.

Between claims, the word comes from a fixed list, so each one means the same every time:

| Word | Reads as |
|---|---|
| supports | a test log result *supports* the datasheet's figure |
| goes against | a measured current *goes against* the advertised rating |
| protects | fuse near the pack *protects* the wiring |
| limits | the 3.3 V logic level *limits* which sensors fit |
| depends on | servo current *depends on* battery capacity |
| causes | a reversed battery *causes* a failed board |
| is part of | first power-on checks *is part of* safe bring-up |
| is an example of | a Li-ion fire *is an example of* an internal fault |

Between entities and subjects, the link types already used in the store carry the meaning:

| From | Link | To |
|---|---|---|
| entity | `uses` | subject |
| entity | `can` | subject, for a skill |
| entity | `building` | entity |
| entity | `part-of` | entity |
| entity | `owns` | entity |
| entity | `works-at` | entity |
| entity | `at` | entity, for a place |
| entity | `described-by` | a document about it |
| subject | `part-of` | subject |
| claim | `about-subject` | subject |
| claim | `about-entity` | entity |
| claim | `derived-from` | evidence |

A relationship records who made it and, if it came from a suggestion, the reason given. A link a model suggests stays a proposal until James accepts it and picks the word.

**Status: partly built.** Connecting words between claims are built (`kg cube accept --word`), but none has been used yet. `kg entity link` makes the entity links and allows only the ones in this table, apart from `described-by`, which sorting makes. Links between subjects are not built.

---

## The hierarchy is a graph

It is easy to draw as a tree:

```
James
├── SCPBot
│   ├── PCA9685
│   │   ├── claim: drives 16 PWM channels
│   │   │   └── evidence: Adafruit guide
│   │   └── claim: OE pin disables outputs
│   ├── ESP32
│   └── Servo
└── Health
    ├── Sleep
    └── Blood pressure
```

But it is stored as links, because one subject belongs to many entities and one piece of evidence backs many claims. The page can draw whichever tree suits the view, starting from any entity.

## How it grows

Claims form subjects, subjects form entities, and entities form worlds.

When a dense cluster of claims looks like a subject, or a group of subjects looks like an entity, it arrives as a **proposal**: a suggested name and the members it would gather. James accepts, renames or rejects it. Nothing becomes a subject or an entity on its own.

This matters because clusters come from shared words, not shared meaning. Before the archive, 413 threads were word matches on words such as "never" and "answer".

**Status: not built.**

---

## Status of a claim

Status is separate from lens. A FACT can be unattested, and an OPINION can be attested.

| Status | Means | Today |
|---|---|---|
| Draft | Not yet looked at as a whole | No validation, or validation gone stale |
| Observed | James has looked at it and recorded why it holds | Validated |
| Attested | James vouches for it. Needs 100% | Attested |
| Disputed | Something credible goes against it, and that is unresolved | `contradicts` set |
| Rejected | James has decided it does not hold. It stays, for the record | Not built |
| Deprecated | It held once, but no longer does or has been replaced | Not built |

Attested claims are the **gold** cubes. Gold comes from status, not from lens.

Moves between them:

- Draft → Observed when James validates it. Foundational claims need all five faces first, others need two.
- Observed → Attested when it reaches 100% and James vouches for it.
- Editing any face sends it back to Draft, retracting validation and attestation, as it does today.
- Any status → Disputed when a contradiction is flagged, and back when it is resolved.
- Any status → Rejected or Deprecated by James only. Deprecated sets `valid_to`.

**Status: partly built.** Draft, Observed and Attested exist under today's names. Disputed exists as the `contradicts` field. Rejected and Deprecated do not exist.

---

## Time

Every capsule is meant to carry when it holds: `valid_from`, and `valid_to` once it stops holding. Then the store can answer "what did James believe in March?" or "what was SCPBot made of two revisions ago?".

Today only the latest change date is stored, so an edit overwrites the old wording. The events log keeps every write, which is enough to rebuild history once something reads it. That means treating events as the record to replay, which `SPEC.md` section 5 calls a v2 concern.

**Status: not built.** This comes last.

---

## Archive

An archive is a separate database, `archive/sc-archive-<date>.db`, with the same schema as `sc.db`. Archiving moves capsules, their links, their trust scores and their events out of `sc.db`, and writes one `archive.moved` event to `sc.db` saying what went and where.

This is the one exception to events never being deleted. The ledger is `sc.db` and its archives together.

On 3 November 2026 every cube was archived, in two steps by `scripts/archive_cubes.py`:

- `sc-archive-2026-11-03.db`: 162 cubes, including 38 attested ones, with their faces, drafts and links. Cubes tagged `james`, `defining`, `principle` or `foundational` stayed.
- `sc-archive-2026-11-03-2.db`: those 44 cubes, with the 11 subject proposals made for them and the 4 sources they cited (`--keep-none`).

The repo index, SymLM's language data, the foundations and `person/james-gilbert` stayed in `sc.db`.

On 5 November 2026 SymLM's talk logs went too:

- `sc-archive-talk-logs-2026-11-05.db`: 127 observations from the 31 October `symlm` chat tests, 85 conversation turns and 42 unparsed lines, with their events. Nothing linked to them, and `kg_gate` never used them as evidence. `symlm/talk.py` still writes new ones.

---

## Old words and new

| Before | Now |
|---|---|
| cube | claim (still drawn and coded as a cube) |
| tag `pca9685`, `servo` and the like | subject, with the tag kept as a label |
| `source/<slug>` | evidence, `evidence/<slug>` |
| neighbour link | relationship between claims, with a connecting word |
| validated | Observed |
| `contradicts` | Disputed |
| person, project, and plain knowledge of kind project, organisation, place or repo | entities |
| plain knowledge of kind tool or skill | subjects |

## Not yet decided

- Which existing tags become subjects, and which are dropped.
- Whether a claim can be about more than one subject, or must pick one.
- What the page shows for subjects and entities: clusters, boxes or something else.
- Whether a Rejected claim is hidden or shown dimmed.
