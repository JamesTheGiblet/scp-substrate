# Starting a project from an outline or a CSV

Write a plain-text outline with three kinds of heading, then import it:

```
python keystone-gate/kg import my-project.md           # shows what it would make
python keystone-gate/kg import my-project.md --write   # makes it
```

Without `--write` nothing is written. The import checks every id the outline points at before it writes anything, so an outline goes in whole or not at all. Running it again skips claims that already exist, so you can add to the outline and import again.

## The headings

| Heading | Makes | Lines under it |
|---|---|---|
| `# entity <name>` | the thing being modelled | `kind:` (project, robot, person, ...), `id:` to choose the id, and any relation: `part-of:`, `uses:`, `owns:`, `at:`, `works-at:`, `can:`. `building: james` links the other way: James is building it. |
| `## subject <name>` | a part, concept or topic of the entity | `kind:`, and `uses: yes` when the entity uses it (it then circles the entity's dot on the page) |
| `### claim <sentence>` | a claim, about the subject above it, or about the entity as a whole if it comes before any subject | `source:`, `from:` (evidence ids), `also:` (more subject ids it is about), `tags:`, `words:` (your words for linking), `id:`, lens lines, and links to other claims: `supports:`, `goes-against:`, `protects:`, `limits:`, `depends-on:`, `causes:`, `is-part-of:`, `is-an-example-of:` |

A link line names claim ids, in the outline or already in the store, and reads as a sentence from the claim it is under: `supports: cube/x` means this claim supports `cube/x`.

A subject that already exists is reused, never copied, so `## subject PCA9685` in a new robot's outline joins the PCA9685 that SCPBot already uses.

## Lenses

A lens line under a claim (`FACT:`, `COUNTER:`, `OPINION:`, `FICTION:`, `CONTEXT:`) is offered as a draft, never filled. You confirm it in the grid or with `kg cube review`, like any model's draft.

For the lenses you leave out, `kg cube draft` asks the models in turn:

1. **LLLM** drafts FACT from your own writing. Every word comes from a line in its corpus, and it says nothing rather than make something up. It runs on this machine, so private cubes can use it. Set `LLLM_DB` to the model's path.
2. **Claude**, then **Gemini**, then **Ollama** draft whatever is still blank. A private cube goes to Ollama only.

## Example

```
# entity Rover
kind: robot
building: james
part-of: project/forge-stack

### claim Rover is a four-wheeled test robot for the Forge Stack.

## subject PCA9685
uses: yes

### claim Rover drives its steering servos from one PCA9685.
source: Stated by James
FACT: Two steering servos use channels 0 and 1.

### claim Rover's steering servos run from their own 5 V supply.
id: cube/rover-servo-supply

### claim The PCA9685 can't power servos from its logic supply.
supports: cube/rover-servo-supply

## subject Wheel motor
kind: component
uses: yes

### claim A wheel motor needs a driver board, not a GPIO pin.
tags: needs-check
```

## From a CSV

A spreadsheet works too: one row per claim. Save it as CSV and import it the same way, or use **Import CSV** in the grid once the page is unlocked. Both show what would be made first, and write nothing if any row has a problem.

```
python keystone-gate/kg import claims.csv           # shows what it would make
python keystone-gate/kg import claims.csv --write   # makes it
```

`docs/claims-template.csv` has every column and three example rows. Only `entity` and `claim` are needed:

| Column | Means |
|---|---|
| `entity` | what the claim is about, by name (SCPBot) or id (`entity/scpbot`). A name nothing has yet makes a new entity |
| `entity_kind` | the kind of a new entity: robot, project, person and so on |
| `subject` | the part or topic it is about, by name or id. A new name makes a new subject |
| `subject_kind`, `uses` | the kind of a new subject, and `yes` when the entity uses it |
| `claim` | the claim, one sentence |
| `id`, `source`, `tags`, `from`, `also` | as in an outline |
| `words` | your words for linking; claims sharing one get a suggested link |
| `FACT`, `COUNTER`, `OPINION`, `FICTION`, `CONTEXT` | drafts you confirm later |
| `supports`, `goes-against`, `depends-on` and the other connecting words | claim ids this one links to |

Names are matched against existing entities, subjects and their aliases, ignoring case. A cell can hold several values separated by commas or semicolons; a cell containing a comma needs quotes, which Excel adds when it saves.
