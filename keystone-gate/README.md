# Keystone Gate

A knowledge system built on top of the SCP substrate. Sibling app to Replicant, sharing the same Forge tools.

## Boundary

This program and the substrate share **one database** (`../sc.db`). It does **not** add code to `substrate.py`, `rules.py`, `trust.py`, or `schema.sql`. It calls `from substrate import Substrate` and writes via `Substrate.write()` and `Substrate.link()`.

The substrate provides:
- Four foundations: `foundation:cube`, `foundation:lens`, `foundation:cube-face`, `foundation:neighbour`
- `default-cube` capsule with the 5-lens shape and 16%/20% weighting
- Everything else it already had (capsules, links, events, trust, crypto)

Keystone Gate provides:
- Cube-as-agent behaviour (fills its own faces, keeps confidence up, finds related cubes)
- Neighbourhood-router (broadcast + ledger query)
- The gate (LLM compliance against an `sc` capsule that defines its function)
- HAL (LLM interface — language only, never truth)
- Keystone Gate specific rule types
- Weighted completeness scoring (5 lenses × 16% + human validation × 20% = 100%)
- Attestation gating: completeness gates trust; the two do not run in parallel

## Status

Boundary proven. Logic to be built.

## Files

- `kg` — CLI (executable)
- `kg_stats.py` — substrate-side statistics for cubes
- `kg_router.py` — neighbourhood-router (stub)
- `kg_agent.py` — cube agent (stub)
- `kg_gate.py` — the gate (stub)
- `kg_hal.py` — LLM interface (stub)
- `test_kg.py` — tests
