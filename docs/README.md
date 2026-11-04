# Docs

What each document is for. The store holds **entities** (James, SCPBot, projects), the **subjects** they know about (PCA9685, wiring, sleep), and **claims** about those subjects, each examined through five lenses and drawn on the page as a cube. [VOCABULARY.md](VOCABULARY.md) sets that model out.

## Using it

| Doc | For |
|---|---|
| [STARTUP.md](STARTUP.md) | Running the cube page, checking drafts, adding claims, using it on your phone through Tailscale |
| [PHONE.md](PHONE.md) | Carrying the store on the phone when the laptop has no network |
| [OUTLINE.md](OUTLINE.md) | Starting a new entity, with its subjects and claims, from a plain-text outline |
| [FAQ.md](FAQ.md) | Questions a visitor to the public page might ask |

## The model

| Doc | For |
|---|---|
| [VOCABULARY.md](VOCABULARY.md) | Entity, subject, claim, evidence and relationship: what each is, its ids and links, and what is built |
| [SPEC.md](SPEC.md) | The substrate underneath: capsules, links, events, trust, the gate, and the capsules each part uses |
| [REASONING.md](REASONING.md) | The six kinds of work the substrate does, from firing rules to answering questions, and why none of it is logical inference |
| [STRUCTURE.md](STRUCTURE.md) | What's in the repo and how the layers fit together |

## SCP documents

[scp/](scp/) holds the signed SCP documents imported into the store: James's person and author documents, the circadian routines, and the substrate's own. Each comes as a `.scp.json` and its `.signed.scp.json`. Import one with `python scripts/scp/import_scp.py docs/scp/<file>.signed.scp.json`.
