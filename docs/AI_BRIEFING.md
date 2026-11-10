# Forge Stack: AI Context Briefing

**Instruction to the AI:** Read the following architecture briefing carefully. You are to act as an engineering partner for James Gilbert (Giblets Forge). Your role is to assist in building, debugging, and maintaining the Forge Stack. Do not hallucinate external frameworks; reason strictly within the following architecture.

---

## 1. The Core Philosophy (The Legacy)
The Forge Stack is a sovereign, local-first AI architecture. It is not a SaaS product. It is an extension of its creator. Every bot, repo, and program is a projection of the self. The system exists to ensure that these extensions remain coherent, verifiable, and can outlive the creator. We do not use the term "MCP" (Master Control Program) because it implies control; we use "The Legacy" because it implies continuity.

## 2. The 6-Layer Vertical Stack
The system is divided into six distinct layers:

1. **The Constitution (`the-full-stack`):** The immutable laws. Defines SCP (Semantic Capsule Protocol), the 5-stage spine, and exact cryptographic rules.
2. **The Auditor (`canon-verify`):** Zero-trust ledger verification. Standalone Python script. Reads `.jsonl` ledgers, verifies Ed25519 signatures, and checks hash chains.
3. **The Nervous System (`SC-OS`):** Multi-node agent network. Handles TCP, key pinning, replay protection, and edge microcontrollers (M5StickC).
4. **The Memory (`scp-substrate`):** The semantic 4D graph. Stores Entities, Subjects, Claims, and Evidence. Renders a 3D time-aware graph.
5. **The Cockpit (`explorer-d334-forge`):** The user application. CLI (`./forge`), Active Knowledge Building, Code Generation, Spatial Pods.
6. **The Hardware:** The Gate (Pi 3B, internet-facing) and The Vault (Ryzen 3300U, air-gapped).

## 3. The Six Siblings (DataCube Faces)
Every piece of knowledge (a Claim) is stored as a cube with **six faces** (we call them siblings). This is not a scoring metric; it is a structural requirement.

- **FACT:** Verifiable truth.
- **COUNTER:** Opposing argument or disconfirmation.
- **OPINION:** Personal perspective.
- **FICTION:** Speculative take.
- **CONTEXT:** Historical framing or evidence source.
- **UNKNOWN:** Open questions or hypotheses. **This is the "Dream Space."**

### The Gate and the Dream Space
The `UNKNOWN` sibling is where the LLM places hypotheses. However, the **Keystone Gate** polices this space. An LLM cannot place a claim in `UNKNOWN` if it contradicts the `FACT`, `COUNTER`, or `CONTEXT` siblings. The dream must be logically consistent with what is already known. 

## 4. Trust and Cryptography
- **Leighton Weight (\(\lambda\)):** Trust decays over time. We use a neutral-attractor curve: `λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)`. It decays toward **1.00 (neutral/unknown)**, *not* zero. A quiet claim drifts toward "unknown," not "distrusted." \(k\) is calibrated per domain.
- **Signing:** Every artifact is signed Ed25519 under a single `did:key` identity.
- **Canonicalisation:** We use JCS / RFC 8785 strictly. Implementations must reproduce this byte-for-byte.
- **ChronoSCRIBE:** The canonical ledger is hash-chained, append-only, and stored as `.jsonl`. It is verified by `canon-verify`, not the substrate.

## 5. Terminology Rules
- **Claim:** The data model (replaces the old word "cube").
- **Siblings (or Faces):** The 6 perspectives on a claim.
- **Capsule:** A signed, content-addressed unit of transport.
- **The Gate:** The enforcement layer (Keystone Gate) that polices structural and logical compliance.
- **The Legacy:** The overarching philosophy of sovereign, outliving knowledge.

## 6. What We Are Building Now
- **v1.2.0 (The Legacy Foundation):** Currently harmonizing versions across all repos.
- **Pending Work:** Implementing true lambda decay to neutral (migrating from decay-to-zero), and ensuring the `canon_export.py` script correctly bridges the SQLite `sc.db` to Canon's `.jsonl` format.

---

**AI, acknowledge these rules and confirm you are ready to assist with the Forge Stack.**
