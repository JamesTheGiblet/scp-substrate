# Starting a project from an outline

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
| `### claim <sentence>` | a claim, about the subject above it, or about the entity as a whole if it comes before any subject | `source:`, `from:` (evidence ids), `tags:`, `id:`, and lens lines |

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

## subject Wheel motor
kind: component
uses: yes

### claim A wheel motor needs a driver board, not a GPIO pin.
tags: needs-check
```
