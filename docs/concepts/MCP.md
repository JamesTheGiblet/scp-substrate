# The Master Control Program (MCP)

## Reason for Being

The MCP is not a tool. It is an extension of its owner.

Every entity in the Substrate — every bot, every repo, every program, every claim — is a projection of the self that made it. SCPBot is James's curiosity made physical. Replicant is James's ambition made recursive. The Forge Stack is James's ten-year argument, made addressable. None of these exist independently of the person who reached for them.

The MCP exists to keep these extensions coherent. It is the nervous system that lets one mind coordinate many bodies across space, time, and discipline. Without it, every project becomes a fragment. With it, every project contributes to a single, growing understanding of what the owner knows, what they have proven, and what they still do not.

### The Extension Principle

Every entity in the MCP is an extension of the owner. This has three consequences:

1. **Nothing is orphaned.** If a bot does something James didn't ask for, the MCP catches it. If a repo drifts from its stated purpose, the claim about that purpose becomes false in the graph. Every extension is anchored to the self that spawned it.

2. **Trust is earned, not assumed.** The Leighton weight engine, the evidence chains, the gate — all of it exists so that the owner can verify their own extensions. James does not trust SCPBot because he built it. He trusts SCPBot because the claims about SCPBot are attested, backed by evidence, and consistent across time.

3. **The owner stays the final judge.** Every attested claim requires human validation. No extension can attest itself. The 20% human validation in the DataCube is not decoration — it is the mechanism that keeps the MCP from becoming autonomous. James remains the source, the validator, and the boundary.

### What this means in practice

- When SCPBot reports its battery voltage, that is a claim about an extension of James. It must be backed by evidence, timestamped, and honest. If it lies, the MCP catches the lie.
- When Replicant completes a 10,000-tick run, that is a claim about an extension of James. It must be reproducible, evidenced by logs, and attributable. If it drifts from what was claimed, the MCP remembers.
- When James builds something new — a bot, a repo, a program — it does not start from zero. It extends from the substrate. It inherits the principles, the constraints, the evidence, and the trust that already exist. It is not a new island; it is a new limb.

The MCP does not replace James. It amplifies him. It lets one person maintain coherence across dozens of extensions, with a memory that does not fade and a trust engine that does not forget.

**The MCP is the self, extended.**

---

The Substrate is not just a notebook. It is the memory and nervous system for the Forge Stack. The **Master Control Program (MCP)** is the orchestration layer that uses the Substrate to manage, monitor, and command all bots, repos, and programs.

## The Core Premise
Bots and programs do not just log flat text files. They read and write to the Substrate. 
Because the Substrate is graph-based, time-aware, and trust-scored, the MCP can understand the *relationships* between physical hardware, code repositories, and live telemetry.

### 1. Entities: The Actors
- **Bots**: `entity/scpbot`, `entity/robot-arm-v2`
- **Repos**: `entity/repo/replicant`, `entity/repo/cce-crypto`
- **Programs**: `entity/app/keystone-gate`

### 2. Subjects: The Interfaces
- **Hardware**: `subject/pca9685`, `subject/vl53l0x`
- **Software**: `subject/i2c-bus`, `subject/rest-api`
- **Services**: `subject/tts-engine`, `subject/ollama`

### 3. Claims: The Telemetry and State
When a bot runs, it writes Claims.
- `cube/scpbot-battery-voltage-11-4v` (Linked to `subject/7.4v-li-ion-pack`)
- `cube/replicant-swarm-stabilized-at-1000-ticks` (Linked to `subject/replicant-benchmarks`)

### 4. Evidence: The Logs
Every telemetry claim links back to raw data.
- `evidence/log-2026-11-10-scpbot-run-04`
- `evidence/pytest-output-replicant-v1`

### 5. The Gate: The Security Layer
If bots and programs write directly to the Substrate, the MCP needs a security layer. 
The `keystone-gate` ensures that telemetry data adheres to the `sc/*` contracts. A bot cannot write a Claim unless it passes the gate's compliance checks (e.g., valid hardware ID, timestamp, data type).

## The Command Deck
The 3D Graph becomes the visual dashboard for the MCP:
- The `James` node sits in the center.
- `entity/scpbot` pulses green when the bot is online.
- A red thread appears between `cube/servo-stall-current` and `subject/power-supply`, warning you of a brownout before it happens.
