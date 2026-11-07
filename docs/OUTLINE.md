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

## Reviewing drafts on a sheet

Model drafts wait for you, five per claim. To clear them in a spreadsheet instead of one at a time:

```
python keystone-gate/kg cube sheet                  # writes drafts-to-review.csv, about 50 drafts, whole claims only
python keystone-gate/kg import drafts-to-review.csv           # check what it will do
python keystone-gate/kg import drafts-to-review.csv --write   # do it
```

Or upload the filled sheet with **Import CSV** on the page. In each row, fill in:

| Column | Means |
|---|---|
| `decision` | `accept` takes the draft, `reject` drops it, `edit` uses your text instead. Blank skips the row, so it comes back on the next sheet |
| `your_text` | with `edit`, the words to use |
| `words` | your words for linking the claim, on any of its rows |

Every row is checked before anything is written. Run `kg cube sheet` again for the next 50. If Excel asks, save as **CSV UTF-8**, so λ and quotes survive.

## Writing missing lenses on a sheet

```
python keystone-gate/kg cube gaps                         # list claims with lenses still to write
python keystone-gate/kg cube gaps --out sheets/gaps.csv   # the same claims as a sheet
```

One row per claim: `claim_id, entity, subject, claim, missing, tags`, then a column per lens. Write the lenses, add tags if you want, and import the file with `kg import` or **Import CSV**. Each lens goes in as a draft to confirm, replacing the model's draft for that lens; filled faces are left alone. New tags are added to the claim.

## Specing a new project

`kg spec "Desk Arm" --uses "servos, m5stick, camera" --brief "..."` matches each
word to subjects and entities, and lists the claims on them: validated, then
not yet validated, each saying which project it came from. Anything with no
claims behind it is listed as a question. Claims that protect or limit one in
the spec come too, under Safety, so the fuse shows up though nobody named it.
No model is asked. `--out
sheets/desk-arm.csv` writes the questions to a sheet; write a claim on the rows
you can and `kg import` it. Rows left blank are skipped.

The page's **Build** button does the same in the browser. Type what you're
building and what it uses; each word shows what it matched. Green means one
match, amber means more than one so you pick, grey means nothing, saved as a
new part or added as another name for one that exists. The spec fills in
below, and each "not known" question has a box for your answer. Save needs
the page unlocked, and writes only the project, its parts and counts, and the
claims you typed, each tagged needs-check.
