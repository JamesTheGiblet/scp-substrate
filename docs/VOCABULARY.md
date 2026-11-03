# Vocabulary

The words this project uses for what it knows, and how they fit together. Agreed on 3 November 2026, when the store was archived down to 44 cubes to start again on this structure.

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

- **ID:** `entity/<slug>`. People keep `person/<slug>` and projects `project/<slug>`, since those foundations already exist. Both count as entities.
- **Kind:** a field saying what sort of entity it is, such as `person`, `robot`, `project` or `place`.
- **Links:** an entity *uses* or *knows about* subjects, and *is part of* or *owns* other entities.

**Status: partly built.** `foundation:entity`, `foundation:person` and `foundation:project` exist, and `person/james-gilbert` is in the store. No entity is linked to subjects yet.

## Subject

Something one or more entities know about. A component, a topic, a measure.

- **ID:** `subject/<slug>`, such as `subject/pca9685`.
- **Exists once.** If James, SCPBot and the robot arm all use a PCA9685, there is one `subject/pca9685` and three links to it. Knowledge about it is written once and reused.
- **Links:** a claim links to its subject with `about-subject`. Plain `about` is taken: `trust.py` reads it as marking a trust record. Subjects can be *part of* other subjects, and *depend on* them.

**Status: partly built.** `foundation:subject`, subject proposals and `about-subject` links exist, through `kg subject` and `keystone-gate/kg_subjects.py`. Links between subjects, and showing subjects on the page, are not built. Tags stay as labels for filtering.

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

- **Subject:** a claim is *about* one or more subjects.

**Status: built**, apart from kinds and subjects.

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

**Status: partly built.** Four `source/<slug>` capsules do this job today, linked by `derived-from` from 29 cubes. The 7 cubes about James are `derived-from` `person/james-gilbert`, which is an entity, not evidence. They are to become `evidence/<slug>`.

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
| entity | `part-of` | entity |
| entity | `owns` | entity |
| subject | `part-of` | subject |
| claim | `about-subject` | subject |
| claim | `derived-from` | evidence |

A relationship records who made it and, if it came from a suggestion, the reason given. A link a model suggests stays a proposal until James accepts it and picks the word.

**Status: partly built.** Connecting words between claims are built (`kg cube accept --word`), but none has been used yet. The entity and subject links are not built.

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

The first archive, on 3 November 2026, kept the cubes tagged `james`, `defining`, `principle` or `foundational`, and moved the other 162 cubes, including 38 attested ones, with their faces, drafts and links. The repo index and SymLM's language data stayed. `scripts/archive_cubes.py` did it.

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
| person, project | entities, of kind person or project |

## Not yet decided

- Which existing tags become subjects, and which are dropped.
- Whether a claim can be about more than one subject, or must pick one.
- What the page shows for subjects and entities: clusters, boxes or something else.
- Whether a Rejected claim is hidden or shown dimmed.
