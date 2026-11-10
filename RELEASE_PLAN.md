# Forge Stack v1.2 Release Plan

**Target Release:** v1.2.0 (The Legacy Foundation)
**Status:** In Progress
**Objective:** Harmonize versioning, schema, and contracts across the entire Forge Stack: Substrate Core, SC-OS, Keystone Gate, UI, and SCP Documents.

Currently, the Forge Stack suffers from version drift:
- `scp-substrate` (Core) is at `0.1.0`.
- `SC-OS` is functionally robust but labeled `0.1` in its README.
- `keystone-gate` and the 3D View are unversioned.
- SCP Documents are at `1.2`.

This document outlines the phases required to bring every component into strict alignment at `v1.2.0`.

---

## Phase 1: The Substrate Core (`scp-substrate`)
**Goal:** Lock the new schema (Subject, Evidence) into the immutable constitution and bump the core version.

- [ ] **1.1 Patch `sc.json`:** Add `foundation:subject` and `foundation:evidence` to the constitution.
- [ ] **1.2 Bump Core Version:** Change `"version": "0.1.0"` to `"version": "1.2.0"` in `sc.json`.
- [ ] **1.3 Project the Core:** Run `python scripts/bootstrap.py` to project the new foundations into `sc.db`.
- [ ] **1.4 Temporal Schema:** Ensure the `events` table formally documents `valid_from` and `valid_to` in `docs/architecture/SPEC.md`.
- [ ] **1.5 Verify Invariants:** Run `python tests/run.py` to ensure no foundation collisions or broken links.

## Phase 2: SC-OS (The Nervous System)
**Goal:** Align the transport protocol and agent OS to v1.2.0.

- [ ] **2.1 Update SC-OS README:** Change the status line to `v1.2.0 (The Legacy Foundation)`.
- [ ] **2.2 Namespace Alignment:** Ensure SC-OS `self.*` capsules and Substrate `entity/*` namespaces align (e.g., `entity/sc-os`).
- [ ] **2.3 Edge Gateway Integration:** Verify `run_gateway.py` correctly maps incoming edge readings to Substrate `foundation:observation` capsules.

## Phase 3: Keystone Gate (The Enforcer)
**Goal:** Explicitly version the Gate to match the core, and formalize the Hierarchy Engine.

- [ ] **3.1 Create KG VERSION File:** Add `VERSION` inside `keystone-gate/` with `Keystone Gate: 1.2.0` and `Requires: Substrate Core >= 1.2.0`.
- [ ] **3.2 Version the SC Contracts:** Update `sc/symlm-answerer` (and others) to include `"version": "1.2"`.
- [ ] **3.3 Document the Hierarchy Engine:** Update `keystone-gate/README.md` to officially document the `cluster_to_subject` and `neighbour_by_tag` rules.
- [ ] **3.4 Gate Compliance Check:** Run `./keystone-gate/kg gate test` to ensure compliance.

## Phase 4: The Command Deck (`keystone-gate/view/`)
**Goal:** Brand the 3D UI as the v1.2 Command Deck.

- [ ] **4.1 UI Badge:** Add a subtle `v1.2` version badge to the top-left of `view_template.html`.
- [ ] **4.2 Subject & Evidence Rendering:** Ensure the 3D graph renders `foundation:subject` and `foundation:evidence` distinctly.
- [ ] **4.3 Time Slider Polish:** Ensure the temporal slider (`faceMap`) degrades gracefully if a cube has no `history` array.
- [ ] **4.4 Rebuild Snapshot:** Run the `kg_view` builder to generate the final `build/cubes.html`.

## Phase 5: The Official Release (Root)
**Goal:** Tie it all together, write the history, and push the tag.

- [ ] **5.1 Create Root VERSION File:** Add `Substrate Core: 1.2.0`, `SC-OS: 1.2.0`, `Knowledge Model: 2026-11`.
- [ ] **5.2 Update CHANGELOG.md:** Detail the journey from the "Cube Era" to the "Legacy Foundation".
- [ ] **5.3 Update Root README.md:** Add the version badge.
- [ ] **5.4 Git Tag:** Push the final `v1.2.0` tag.

---

## Version Matrix (Target State)

| Component | Current State | Target State | Artifact |
|---|---|---|---|
| **Substrate Core** | `0.1.0` | **`1.2.0`** | `sc.json` |
| **SC-OS** | `0.1` | **`1.2.0`** | `README.md` (SC-OS) |
| **Knowledge Model** | `2026-11` | **`2026-11`** | `docs/concepts/MODEL.md` |
| **Keystone Gate** | Unversioned | **`1.2.0`** | `keystone-gate/VERSION` |
| **SC Contracts** | Unversioned | **`1.2`** | `sc/symlm-answerer` |
| **SCP Documents** | `1.2` | **`1.2`** | `docs/scp/*.scp.json` |
| **Release Tag** | None | **`v1.2.0`** | Git Tag |
