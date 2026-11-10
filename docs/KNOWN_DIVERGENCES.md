# Substrate Alignment Map

The Substrate is not the root of the Forge Stack; it is a **consumer** of it. 

The canonical implementations of the stack's spine live in `the-full-stack` and `canon-verify`. The Substrate acts as a local, time-aware memory cache for the **author-tier consumer** (James). This document maps the Substrate's implementation to the canonical Forge Stack spec.

## 1. ChronoSCRIBE (Audit)
- **Canonical:** `canon-verify` / `record.py`. Hash-chained, Ed25519-signed `.jsonl` ledgers with full JCS / RFC 8785 support.
- **Substrate implementation:** The `events` table in `sc.db` is a local append-only cache. It is *not* hash-chained and *not* the canonical ledger.
- **Alignment:** The Substrate now includes `canon_export.py`. This script exports the local `events` table into a Canon-format `.jsonl` ledger that can be independently verified by `canon-verify`. The substrate is the cache; Canon is the immutable record.

## 2. Leighton Weight (Trust-score)
- **Canonical:** `leighton_weight.py` in `the-full-stack`. Uses the neutral-attractor formula: `λ(t) = 1.00 + (λ₀ − 1.00) × e^(−kt)`. Computed on the fly from observations.
- **Substrate implementation:** `trust.py` currently stores cached trust scores in the `trust_scores` table using a decaying-to-zero formula.
- **Alignment:** The Substrate's `trust_scores` table is explicitly defined as a **cache**. The canonical λ must be computed from the observation stream using the `the-full-stack` formula. A future patch will align the formula, but the Substrate's job is simply to render the cache provided by the canonical engine.

## 3. DataCube (Classify)
- **Canonical:** Six lenses/faces (`FACT`, `COUNTER`, `OPINION`, `FICTION`, `CONTEXT`, `UNKNOWN`). Lenses are *bins*, not scores.
- **Substrate implementation:** The `completeness` score was incorrectly treated as a knowledge metric. It has now been renamed `inspection_status` (see Step 3 below) to correctly reflect that it measures *process* (how many bins have been checked) not *truth*.
- **Alignment:** The `UNKNOWN` face is restored. The Substrate renders the cube, but the actual trust-score comes from Leighton.

## 4. HAL (Act)
- **Canonical:** 5-tier λ ladder (quarantine below 0.60), Fact Validator / Consequence Authoriser roles.
- **Substrate implementation:** `keystone-gate` enforces structural compliance (no invented IDs), but does not enforce λ tier thresholds.
- **Alignment:** The Gate ensures structural integrity. The λ-tier gating will be enforced by the HAL module calling into the Substrate's cache.
