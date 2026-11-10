# SCP Substrate

SCP is a reusable knowledge substrate. It stores knowledge as:

**Entity**
 └─ **Subject**
     └─ **Claim**
         └─ **Evidence**

Relationships connect all four. The core principle is that **a subject exists once and is reused.** Every project you build contributes to a shared, compounding understanding of the hardware, principles, and systems you use. 

## The Extension Principle

Every entity in the substrate — every bot, repo, program, and claim — is an extension of the owner that made it. The substrate exists so that these extensions remain coherent, verifiable, and connected to the self.

When SCPBot reports its battery voltage, that is a claim about an extension of James. It must be backed by evidence, timestamped, and honest. The MCP (see [docs/concepts/MCP.md](docs/concepts/MCP.md)) is the nervous system that keeps all extensions coordinated.

## Quick Start
- **New here?** Read [docs/concepts/MODEL.md](docs/concepts/MODEL.md) to understand the data model.
- **Want to see it in action?** Check out [docs/EXAMPLE.md](docs/EXAMPLE.md) (if you haven't created it yet).
- **Want to run it?** See [docs/guides/STARTUP.md](docs/guides/STARTUP.md).
- **Want the technical spec?** See [docs/architecture/SPEC.md](docs/architecture/SPEC.md).

## The Visual Explorer
The store includes a 3D visual explorer (`keystone-gate/view`) where claims are rendered as cubes. The five lenses of the cube represent the ways a claim is examined, and the gold glow indicates human attestation.
