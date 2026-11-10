# ⚒️ The Forge Stack Architecture

**Version:** 1.2.0 (The Legacy Foundation)
**Author:** James Gilbert (Giblets Forge)
**Philosophy:** Sovereign, local-first, cryptographically verifiable, and designed to outlive its creator.

The Forge Stack is a 6-layer vertical architecture for building sovereign AI systems. It is not a single application; it is an ecosystem of repositories, protocols, and hardware that function together as a single, coherent nervous system.

---

## The 6 Layers

### Layer 1: The Constitution (The Physics)
- **Repository:** `the-full-stack`
- **Target Version:** `v1.2.0`
- **Role:** Defines the immutable laws of the ecosystem. It houses the 5-stage spine (SCP, DataCube, Leighton Weight, ChronoSCRIBE, HAL), the canonicalisation rules (JCS / Canon form), and the governance lineage.
- **Artifact:** `sc/*.sc.json` (signed, immutable capsules).

### Layer 2: The Auditor (The Truth)
- **Repository:** `canon-verify`
- **Target Version:** `v1.2.0`
- **Role:** The zero-trust verification layer. It reads the `.jsonl` ledgers produced by the system, verifies the Ed25519 signatures, checks the hash chains, and validates the anchors. It uses none of the Forge Stack's code; it is a standalone truth-verifier.
- **Artifact:** `ledger.jsonl` + `.anchors` file.

### Layer 3: The Nervous System (The Transport)
- **Repository:** `SC-OS`
- **Target Version:** `v1.2.0`
- **Role:** The multi-node agent network. It handles TCP sessions, key pinning, replay protection, rule learning, and the edge gateway for microcontrollers (M5StickC).
- **Artifact:** Signed network capsules (`__readings__`, `__sensors__`, `task_result`).

### Layer 4: The Memory (The Mind)
- **Repository:** `scp-substrate` (This repo)
- **Target Version:** `v1.2.0`
- **Role:** The semantic, time-aware graph. It stores Entities, Subjects, Claims, and Evidence. It provides the 4D visualization (time slider) and the six sibling faces (FACT, COUNTER, OPINION, FICTION, CONTEXT, UNKNOWN).
- **Artifact:** `sc.db` (SQLite) + `canon_export.jsonl`.

### Layer 5: The Cockpit (The Interface)
- **Repository:** `explorer-d334-forge`
- **Target Version:** `v1.2.0`
- **Role:** The user-facing application. It provides the CLI (`./forge`), the web UI, the Active Knowledge Building scanner, Code Generation, and the P.DE.I Exocortex.
- **Artifact:** C Code, Web UI, 3D Spatial Pods.

### Layer 6: The Hardware (The Vault)
- **Repository:** Physical Infrastructure
- **Target Version:** `v1.2.0`
- **Role:** The physical embodiment.
  - **Node 1 (The Gate):** Raspberry Pi 3B. Internet-facing. Runs SC-OS and Keystone Gate. Filters incoming data.
  - **Node 2 (The Vault):** Ryzen 3300U. Air-gapped. Bare metal Linux. Holds the `sc.db`, the 3D graph, and the private Ed25519 keys.

---

## The Legacy Principle

The Forge Stack is not a tool. It is an extension of its owner.

Every bot, repo, program, and claim is a projection of the self that made it. The Stack exists to keep these extensions coherent, verifiable, and connected to the self. It is the architecture of a mind that refuses to be deleted.

**The Legacy is the self, extended.**

---

## The Flow of a Thought

1. **The Spark:** An LLM in `explorer-d334-forge` proposes a hypothesis (e.g., "The PCA9685 can drive 32 servos using a TCA9548A multiplexer").
2. **The Dream Space:** The proposal is placed into the `UNKNOWN` face of a Claim.
3. **The Gate:** `keystone-gate` enforces structural compliance. It checks the proposal against the `FACT`, `COUNTER`, and `CONTEXT` siblings. If it contradicts known facts, it is rejected.
4. **The Transport:** `SC-OS` wraps the validated capsule in Ed25519, signs it, and moves it across the network.
5. **The Memory:** `scp-substrate` ingests the capsule, updates the graph, and the 3D time slider reflects the change.
6. **The Audit:** `canon-verify` hashes the event and appends it to the immutable `.jsonl` ledger.
7. **The Validation:** James reviews the dream in the Cockpit and promotes it to `FACT`. HAL signs the seal.
8. **The Legacy:** The claim is now part of the permanent record, protected by the air-gapped Ryzen Vault.

---

## Version Harmonization Matrix (v1.2.0)

To ensure total system coherence, all components must be synchronized to `v1.2.0`.

| Layer | Repository | Component | Target |
|---|---|---|---|
| 1 | `the-full-stack` | Constitution & Spine | `v1.2.0` |
| 2 | `canon-verify` | Ledger Auditor | `v1.2.0` |
| 3 | `SC-OS` | Agent Network & Gateway | `v1.2.0` |
| 4 | `scp-substrate` | Memory & 3D Graph | `v1.2.0` |
| 5 | `explorer-d334-forge` | Cockpit & CLI | `v1.2.0` |
| 6 | Hardware | Ryzen Vault + Pi Gate | `v1.2.0` |
