# Docs

- [FORGE_STACK_ARCHITECTURE.md](../FORGE_STACK_ARCHITECTURE.md): The 6-layer vertical architecture and v1.2.0 version matrix.

The Substrate stores knowledge as **Entities** (James, SCPBot), the **Subjects** they know about (PCA9685, wiring, sleep), and the **Claims** about those subjects, each backed by evidence. 

The most important principle in the system is this: **A subject exists once and is reused.** When you build a new robot, it does not need new notes on the PCA9685; it just links to `subject/pca9685` and inherits all the accumulated knowledge and trust.

The model is defined in [concepts/MODEL.md](concepts/MODEL.md). A claim is rendered visually as a cube in the 3D explorer.

## Concepts: What it is
| Doc | For |
|---|---|
| [concepts/MODEL.md](concepts/MODEL.md) | Entity, subject, claim, evidence, and relationship: the schema of the system |
| [concepts/MCP.md](concepts/MCP.md) | The Master Control Program: using Substrate to orchestrate bots, repos, and live telemetry. |
| [concepts/REASONING.md](concepts/REASONING.md) | The six kinds of work the substrate does, from firing rules to answering questions |
| [concepts/FAQ.md](concepts/FAQ.md) | Questions a visitor to the public page might ask |

## Guides: How to use it
| Doc | For |
|---|---|
| [guides/STARTUP.md](guides/STARTUP.md) | Running the visual explorer, checking drafts, adding claims, using it via Tailscale |
| [guides/PHONE.md](guides/PHONE.md) | Carrying the store on the phone when the laptop has no network |
| [guides/OUTLINE.md](guides/OUTLINE.md) | Starting a new entity, with its subjects and claims, from a plain-text outline |

## Architecture: How it works
| Doc | For |
|---|---|
| [architecture/SPEC.md](architecture/SPEC.md) | The substrate underneath: capsules, links, events, trust, the gate |
| [architecture/TOPOLOGY.md](architecture/TOPOLOGY.md) | The physical hardware: the air-gapped Ryzen Vault and the Pi Gatekeeper |
| [architecture/STRUCTURE.md](architecture/STRUCTURE.md) | What's in the repo and how the layers fit together |

## SCP documents
[scp/](scp/) holds the signed SCP documents imported into the store: James's person and author documents, the circadian routines, and the substrate's own. Each comes as a `.scp.json` and its `.signed.scp.json`. Import one with `python scripts/scp/import_scp.py docs/scp/<file>.signed.scp.json`.
