# The Master Control Program (MCP)

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
