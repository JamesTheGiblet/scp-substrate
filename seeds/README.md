# Seeds

Scripts that create starting capsules. Run one from the repo folder, as `python seeds/<folder>/<file>`.

| Folder | Holds | Uses |
|---|---|---|
| `substrate/` | The substrate's own capsules: the SymLM lexicon, grammar, corpus, intents and features, the social protocol, and 11 core capsules | `src/` only |
| `claims/` | Claims, entities and subjects: James, SCPBot, Replicant, the Forge Stack and the projects, the gate's `sc` capsule, and the sorting of what `james` links to | `src/` and `keystone-gate/` |
| `claims/before-pivot/` | The cube seeds from before 3 November 2026, when every cube was archived. **Don't run them on the live store.** Tests use their cubes as test data | `src/` and `keystone-gate/` |

The substrate seeds are mostly create-only, so after the first run the capsules are authoritative, not the seed. `substrate/reconcile_seeds.py` rewrites those seeds to match the capsules. [keystone-gate/README.md](../keystone-gate/README.md) describes each claims seed.

A new entity is easier to start from an outline than a seed: see [docs/OUTLINE.md](../docs/OUTLINE.md).
