# Changelog

All notable changes to the Substrate project. This document tracks the evolution from early prototypes to the Master Control Program foundation.

## [1.0.0] - 2026-11-10
**The MCP Foundation Release**

The substrate is no longer a personal notebook. It is the orchestration layer for the Forge Stack.

### Added
- **Master Control Program (MCP):** `docs/concepts/MCP.md` defines how bots, repos, and programs use the substrate as a live telemetry and command layer.
- **Hierarchy (Subjects):** The `cluster_to_subject` rule automatically discovers dense tag clusters and promotes them to first-class `subject/<slug>` capsules (e.g., `subject/pca9685`).
- **Temporal Versioning:** `kg_view` now parses the event ledger to reconstruct historical states. The 3D graph time slider filters faces based on `filled_at` timestamps.
- **First-Class Evidence:** `kg_evidence.py` allows the creation of `evidence/` capsules (datasheets, logs) which claims link to via `derived-from`.

### Changed
- **The Knowledge Model:** Officially finalized the transition from "cubes" to "Claims". The UI renders cubes, but the data model is Entity -> Subject -> Claim -> Evidence.
- **Documentation Restructure:** Moved to `concepts/`, `guides/`, and `architecture/`. Added `MODEL.md` as the definitive constitution.
- **Graph Rendering:** Replaced the `neighbour_by_tag` explosion with a top-3 overlap cap to prevent O(N^2) link generation.

---

## [0.9.0] - 2026-11-03
**The Great Archive & Model Reset**

### Changed
- **The Archive:** 206 messy, word-matched cubes (e.g., tags on "never", "answer") were moved to `sc-archive-2026-11-03.db`. The substrate was pared down to 44 foundational claims.
- **Schema Shift:** Formalized the `Entity -> Subject -> Claim` hierarchy.
- **The Split:** Separated the UI terminology ("Cube") from the data terminology ("Claim"). 

---

## [0.8.0] - 2026-10-31
**The Time and Scale Era**

### Added
- **SCP Document Ingestion:** Built `import_scp.py` to ingest signed Giblets Forge SCP documents (`james-gilbert-v1.scp.json`).
- **Cryptographic Provenance:** Implemented our own pure-Python Ed25519 signing. Added `keygen.py` and `sign_doc.py`.
- **The 3D Field:** Built the Three.js/Canvas force-directed graph to visualize the claims as a 3D universe.
- **The Keystone Gate:** Created `kg_gate.py` and `kg_hal.py` to enforce `sc/*` contracts, ensuring LLMs cannot hallucinate references or trust scores.

---

## [0.5.0] - 2026-10-25
**The Cube Era**

### Added
- **The 5 Lenses:** Introduced the DataCube model. Every claim is examined through FACT, COUNTER, OPINION, FICTION, and CONTEXT.
- **Completeness Scoring:** Claims are scored 16% per lens + 20% human validation.
- **Attestation:** Added the "gold glow" status for fully validated claims.

---

## [0.1.0] - 2026-10-20
**The SQLite Migration**

### Added
- **`sc.db`:** Migrated from flat JSON files (`capsules/` and `foundations/`) to a single SQLite database.
- **The Invariant:** The schema (`schema.sql`) was locked. Everything else had to fit in `state_json` or typed `links`.
- **Foundations:** Defined the original 11 foundational capsules (knowledge, observation, rule, trust, etc.).

---

## [0.0.1] - 2016 to 2026
**The Forge Stack (Conceptual Era)**

### The Decade of Design
- The Master Control Program (MCP), the Keystone Gate, and the concept of "capsules" existed as separate designs, notes, and failed prototypes across various repos (Axiom, Canon, JIG, LLLM, Replicant).
- The Substrate is the first successful unification of these ideas into a single, working, local-first epistemic engine.
