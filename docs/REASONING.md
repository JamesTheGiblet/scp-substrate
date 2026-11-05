Reasoning

The substrate handles six kinds of work, described below. All of them walk the graph, sum numbers, compare words or apply stored rules. None uses logical inference.

---

1. Rule firing — deriving new facts

Question it answers: "Given what's in the substrate, what can be derived?"

How: iterate every capsule with foundation:rule. For each, evaluate its condition against the current graph. If it matches, insert a derived link and log a rule.fired event.

Four condition types:

pair (default) — condition is {source, target}. Fires if both capsules exist, derives a link from source to target with effect.relationship as the type.

```
condition: {"source": "james", "target": "scp"}
effect:    {"relationship": "contributor"}
→ james --contributor--> scp
```

trust_above — condition is {type: "trust_above", threshold}. Iterates every materialized trust score, computes its live-decayed value, and for those exceeding threshold, follows a specific outbound link on the trust instance to derive a new link to the same target.

```
condition: {"type": "trust_above", "threshold": 0.5}
effect:    {"relationship": "trusted", "derive_from": "about"}
→ scp-claim --trusted--> everything-is-capsules
```

kind_and_age — condition is {type: "kind_and_age", kind, min_age_days, age_field?, via_link?}. Fires when a capsule with a given kind is older than min_age_days, optionally only if reached via a specific inbound link type.

```
condition: {"type": "kind_and_age", "kind": "question",
            "min_age_days": 7, "age_field": "raised",
            "via_link": "open-question"}
effect:    {"relationship": "stale-question", "derive_from": "open-question"}
→ scp --stale-question--> granular-event-types
```

sequence — condition is {type: "sequence", match, ...}. Matches a run of adjacent parse nodes and reduces them to a new phrase, linked to its parts with has-child. This is how the grammar rules in SymLM fire.

Running it. scps rules writes to sc.db: it adds any derived links and logs them.

Idempotence. Every derivation uses INSERT OR IGNORE on (source, type, target). Re-running the engine produces zero new fires. Events only logged on successful insert.

What it doesn't do. No backward chaining. No negation. No universal quantifiers. No temporal reasoning beyond "age > N". A rule either matches or doesn't, based on the current state of the graph.

---

2. Trust computation — combining signals

Question it answers: "How much should this be trusted?"

Three modes:

Parameter trust (trust.compute_all)
Reads every capsule with foundation:leighton-weight that has numeric n0 and k, except trust/freq/* capsules, which are word counts rather than trust. Computes n0 * e^(-k * t_days). Writes to trust_scores. Logs trust.computed on change.

```
trust instance state: {n0: 1.0, k: 0.01, age_days: 0}
→ score = 1.0 * e^(-0.01 * 0) = 1.0
```

Evidence trust (trust.trust_from_evidence)
Walks the graph for incoming observes and verifies links to a target. Observations contribute score * e^(-k * age). Verifications contribute ±1.0 * e^(-k * age) (sign depends on validity). For a claim it also adds the evidence the claim is derived from, weighted by kind (a measurement 1.0, a datasheet, code file or doc 0.75, James's person document 0.5, a listing or one review 0.25), and 0.5 for each claim that supports it, minus 0.5 for each that goes against it, halved when nobody has validated that other claim. Claim links count one step only. Summed.

James's word on its own and a model's general knowledge are not evidence, so a claim resting only on them stays at 0.5 until it is validated or backed.

```
obs-001 --observes--> everything-is-capsules  (score 1.8)
→ evidence = 1.8 * e^(-k * age) ≈ 1.79
```

If the queried capsule has an about link (i.e. it's a trust instance), evidence is gathered at the about target and decayed by the instance's k. If not (i.e. it's a knowledge capsule like an SCP document), evidence is gathered at the capsule itself with k=0 — undecayed.

Fusion (trust.fuse, trust.fused_trust)
Combines a prior probability with evidence likelihood:

```
prior      = parameter trust (or 0.5 if none)
likelihood = sigmoid(evidence_score)
posterior  = Bayesian update(prior, likelihood)
```

Both prior and likelihood clamped to [1e-3, 1-1e-3] so extreme values don't freeze the posterior.

What it doesn't do. No learning. The sigmoid is fixed; there is no calibration loop adjusting it against ground truth. If observation scores are miscalibrated, the fusion inherits the miscalibration. The result is a modelling choice, not a measured probability.

---

3. Why — backward reasoning

Question it answers: "Why is X trusted?"

How: why.why_trusted(s, id) walks backward through the reasoning chain:

1. Look for a trusted link with source = id. That's the derived fact.
2. Read the link's metadata.derived_by to know which rule fired.
3. Read the rule's condition.threshold.
4. Read the materialized trust score and its live-decayed value.
5. Read the trust model that computed the score.
6. Read the model's formula.
7. Read the about link to know what the trust instance is about.

Output (print_chain) renders this as a narrative:

```
Why is scp-claim trusted?
  → Because it has a 'trusted' link to 'everything-is-capsules'
    (derived at 2026-10-31 10:03:22 by trusted-rule)

  → Which was fired because its trust score exceeded 0.5
    (current score = 0.999871, materialized 1.000000 at ..., elapsed 1110.5s)

  → Which was computed by trust model 'default-trust-model'
    (formula = N(t)=N0*e^(-k*t))

  → About: everything-is-capsules
```

Each line comes from a query, though the rule it reads is fixed in code as trusted-rule. Change that rule's threshold and re-run it, and the output changes.

What it doesn't do. It walks one specific chain (trust → rule → score → model). A generic "explain this arbitrary fact" would need a graph-walker over all typed links, which is what explain does — but explain produces a different kind of answer (see below).

---

4. Explain — forward reasoning

Question it answers: "What is X, in context?"

How: explain.explain(s, id) walks forward through the structure:

1. Print the capsule's summary, derived from its foundation and state.kind.
2. Follow outbound declares to note what it declares.
3. Follow outbound inherits to list what it inherits from, and summarise each target.
4. Surface SCP-specific fields: classification, signature, verification records, format.
5. List remaining outbound links with their types.

Output — a narrative, not a claim:

```
giblets-forge/author/james-gilbert-v1
  is a knowledge — declaration by James Gilbert

Declares: James Gilbert (JamesTheGiblet)

Inherits from 3:
  → giblets-forge/style/james-voice
      direct and informal, signs off "Giblet out"
  → giblets-forge/style/james-style
      9 build rules, first: "Phase 0 is always documentation"
  → giblets-forge/style/visual-identity
      Giblets Forge: "I wanted it. So I forged it. Now forge yours." (MSL-1.0)

Classification:
  Self-declaration. Cube under OPINION/CONTEXT, not FACT. ...

Signature: signed
  Algorithm: Ed25519
  Key: did:key:z6Mkkv72... (declared)

Verifications: 2
  valid by did:key:z6Mkkv72...
  valid by did:key:z6Mksk9...

Format: giblets-scp v1.2, canonicalisation forge-c14n-1
```

The summary block dispatches on state.kind — tool, skill, decision, question, principle, session, place, organisation, concept, style, signature-verification, plus a fallback to the foundation name. Adding a new kind requires adding a summariser branch.

What it doesn't do. No inference. Everything it says is either in the capsule's own state_json or reachable by one hop along an outbound link.

---

5. Attestation — a person's judgement as evidence

Question it answers: "Does a person stand behind this cube?"

How: attest() refuses a cube that is not complete. Otherwise it writes an observation with score 1.0 and an observes link to the cube. trust_from_evidence counts that like any other observation, so fused_trust moves from 0.50 to about 0.73.

Changing a face sets the observation's score to 0 and marks it retracted, and marks the validation stale.

What it doesn't do. It records that a person agreed, not how good their reasoning was. Every attested cube gets the same score.

---

6. Lens links — comparing what cubes say

Question it answers: "Which cubes say related things on the same lens?"

How: kg_lens_links.py compares each lens only with the same lens on other cubes, using TF-IDF and cosine similarity. Cubes that share a subject or entity need at least two shared terms and a similarity of at least 0.10; cubes with nothing in common need three terms and 0.20. Being about the store's owner doesn't count as sharing anything. Pronouns, the owner's name, the store's own words and any term on more than a quarter of a lens's faces are left out. Each cube keeps its strongest three links. Clusters come from label propagation over the links. Pending drafts are included.

What it doesn't do. It compares vocabulary, not meaning. Two cubes can share words by coincidence, and two cubes making the same point in different words will not link.

---

Composition — how the modes cooperate

The interesting behaviour is when modes chain. A real example from the substrate:

```
1. compute_all() writes a parameter trust score for scp-claim
        ↓
2. evaluate_rules() runs trusted-rule
   condition type = trust_above, threshold = 0.5
        ↓
3. rule fires → derives link: scp-claim --trusted--> everything-is-capsules
   metadata: {"derived_by": "trusted-rule", "trust": 0.999985}
        ↓
4. why_trusted(scp-claim) walks back:
   trusted link → rule → threshold → score → model → about
        ↓
5. explain(scp-claim) walks forward:
   summary → trusted link → about link
```

Five stages, four subsystems. Each stage reads the substrate; the only writes are in stages 1 and 3. Everything else is traversal and rendering.

Reasoning here means composing walks over the graph, not inference over propositions.

---

What it isn't

· Not a theorem prover. No unification, no resolution, no proof search.
· Not a Bayesian network. Fusion is one formula at one node, not a network of conditionally-dependent variables.
· Not a Datalog engine. Rules don't query each other's results compositionally. A rule's output is a link, not a fact that another rule's condition can test (yet).
· Not learning. No gradient, no fitting, no feedback loop from outcomes to parameters.

If any of those become necessary, they're additions, not replacements. The substrate underneath doesn't change.
