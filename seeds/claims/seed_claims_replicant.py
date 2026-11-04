#!/usr/bin/env python3
"""Replicant, its subjects and claims, from Claude's draft of 2026-11-03.

The draft came from what James said in chat. Each claim was then checked
against github.com/JamesTheGiblet/Replicant (master) on 2026-11-03:
- checked: the repo backs it up, and the claim cites the repo
- fixed: the repo said otherwise, so the claim was corrected to match it
- unchecked: not in the repo, so it is tagged needs-check
Subjects are shared where they name a real thing (Rust, Leighton Weight), and
named for Replicant where they only group its claims. Faces are left blank.
Create-only: anything whose id exists is skipped.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[2] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from store.substrate import Substrate
from kg_agent import create_cube
from kg_entities import add_entity, link_claim, relate
from kg_subjects import accept_subject, propose_subject

REPO = "repo/jamesthegiblet/replicant"
CHECKED = "Checked against the Replicant repo on 2026-11-03: {}"
FIXED = "Corrected from Claude's draft to match the Replicant repo on 2026-11-03: {}"
UNCHECKED = "Stated by James in chat, drafted by Claude on 2026-11-03; not found in the Replicant repo"

# slug -> (name, kind, used by Replicant)
SUBJECTS = {
    "leighton-weight": ("Leighton Weight", "layer", True), "stigmergy": ("Stigmergy", "concept", True),
    "rust": ("Rust", "language", True), "python": ("Python", "language", True), "wasm": ("WASM", "platform", True),
    "swarm-intelligence": ("Swarm intelligence", "concept", False),
    "adversarial-agents": ("Adversarial agents", "concept", False), "msl-1-0": ("MSL-1.0", "licence", False),
    "replicant-benchmarks": ("Replicant benchmarks", "topic", False),
    "replicant-behaviour": ("Replicant behaviour", "topic", False),
    "replicant-applications": ("Replicant applications", "topic", False),
}

# (slug, claim, subjects, status, where in the repo)
CLAIMS = [
    ("replicant-is-a-hybrid-bio-inspired-swarm", "Replicant is a hybrid bio-inspired swarm framework built on the "
     "Forge Stack.", [], "checked", "README.md"),
    ("replicant-tagline", 'Replicant\'s tagline is "Born pregnant. Born ready. Born signed."', [], "fixed",
     "README.md; the draft left out \"Born signed\""),
    ("replicant-v1-layout", "Replicant v1.0 has a README.md, a python/ and a rust/ implementation, and a wasm/ "
     "browser build.", [], "checked", "the file tree"),
    ("replicant-seven-species", "Replicant borrows mechanisms from seven species: ant pheromone stigmergy, honey "
     "bee waggle dance, termite blueprint-less construction, social spider collective capture, paper wasp "
     "individual recognition (now replaced by the Leighton Weight Engine), naked mole-rat hypoxia tolerance and "
     "aphid parthenogenesis.", ["swarm-intelligence", "stigmergy"], "fixed",
     "README.md, Source mechanisms; the draft missed that the paper wasp mechanism was replaced"),
    ("replicant-four-layers", "Replicant's architecture has four layers: Sensing, Signalling, Action and "
     "Reproduction.", ["swarm-intelligence"], "unchecked", None),
    ("replicant-parallel-python-rust", "Replicant has parallel Python and Rust implementations of the core sim, "
     "and neither is authoritative.", ["python", "rust"], "checked", "README.md"),
    ("replicant-rust-to-wasm", "Replicant's Rust sim compiles to WASM and runs in the browser.", ["rust", "wasm"],
     "checked", "rust/wasm/ and CHANGELOG.md v1.1"),
    ("replicant-wasm-folders", "Replicant's WASM folders aren't duplicates: python/wasm/www is the browser UI for "
     "the Flask API, rust/wasm builds the Rust sim to WASM, and the root wasm/ holds the browser build, whose "
     "built files aren't committed.", ["wasm"], "fixed",
     "the file tree; the root wasm/ holds only its README"),
    ("replicant-lambda-from-event-ledger", "Each Replicant agent's λ is computed from an append-only ledger of "
     "decaying events on read, never stored.", ["leighton-weight"], "checked", "README.md and CHANGELOG.md v1.0"),
    ("replicant-quarantine-and-expel-thresholds", "Replicant quarantines agents below λ 0.60 and expels them "
     "below λ 0.15, both derived from the ledger.", ["leighton-weight"], "checked", "python/src/world.py and README.md"),
    ("replicant-misconduct-scars", "Replicant's λ events decay to a permanent residue, so merit fades and "
     "misconduct scars.", ["leighton-weight"], "unchecked", None),
    ("replicant-recidivism-escalates", "Repeat offences in Replicant escalate through a per-agent offences "
     "counter, each prior offence adding 100% to the penalty.", ["leighton-weight"], "checked",
     "python/src/leighton.py and README.md"),
    ("replicant-quarantined-agents-act-without-weight", "Quarantined Replicant agents still act, but their "
     "attestations carry no weight.", ["leighton-weight"], "unchecked", None),
    ("replicant-claims-decay-like-pheromones", "Replicant's claims decay every tick like pheromones, and OPINION "
     "claims are archived once their strength falls to 0.01 or below.", ["stigmergy"], "fixed",
     "python/src/world.py, _decay_claims; only OPINION claims are archived"),
    ("replicant-one-attestation-per-agent", "Each Replicant agent can attest to a claim only once.",
     ["stigmergy"], "checked", "python/src/world.py, attest_claim"),
    ("replicant-claims-close-when-adjudicated", "A Replicant claim closes once it is adjudicated.", ["stigmergy"],
     "unchecked", None),
    ("replicant-four-adversary-types", "Replicant has four adversary types: fiction_planter, hoarder, killer and "
     "poisoner.", ["adversarial-agents"], "checked", "python/src/adversary.py"),
    ("replicant-detection-verified", "Replicant's detection pipeline was verified end to end: fiction claims were "
     "adjudicated false, λ penalties logged, and quarantine and expulsion fired.", ["adversarial-agents", "leighton-weight"],
     "unchecked", None),
    ("replicant-rust-13x-faster", "Rust was faster than Python at every tested scale, averaging 13.1x (range 3.0x "
     "to 26.3x) over 16 points.", ["replicant-benchmarks", "rust", "python"], "checked",
     "CHANGELOG.md and benchmark_results.json"),
    ("replicant-python-wins-small-was-artefact", "Replicant's earlier \"Python wins small\" benchmark result was "
     "an artefact of timing cargo run's toolchain check.", ["replicant-benchmarks", "rust"], "checked",
     "CHANGELOG.md"),
    ("replicant-same-seed-different-trajectory", "The same seed gives different trajectories in Replicant's "
     "Python and Rust versions, because they use different PRNGs.", ["replicant-benchmarks", "python", "rust"],
     "checked", "CHANGELOG.md, an open question"),
    ("replicant-rust-nonlinear-at-100-agents", "Replicant's Rust sim showed a nonlinear timing jump at 100 "
     "agents, likely from its linear-scan spatial queries.", ["replicant-benchmarks", "rust"], "unchecked", None),
    ("replicant-10k-tick-run-stabilised", "A 100-agent, 10,000-tick Replicant run stabilised and self-optimised "
     "its resource allocation.", ["replicant-behaviour"], "unchecked", None),
    ("replicant-20-servo-biped", "Replicant is being applied to a 20-servo biped, where every servo, sensor and "
     "state is an agent, and validated emergent patterns become new agents.", ["replicant-applications"],
     "unchecked", None),
    ("replicant-game-single-agent-survival", "Replicant's game version makes the player a single agent who has "
     "to survive against the odds.", ["replicant-applications"], "unchecked", None),
    ("replicant-emergent-vocabulary-extension", "An emergent signal-vocabulary extension is planned for "
     "Replicant, where claim types evolve rather than being fixed.", ["replicant-applications"], "unchecked", None),
    ("replicant-is-a-stack-consumer", "Replicant is a Forge Stack consumer with its own capsule namespace and "
     "its own consumer ledger anchored to root, under MSL-1.0.", ["msl-1-0"], "checked", "README.md"),
    ("replicant-changelog-good-bad-ugly", "Replicant's root CHANGELOG.md is a summary. The full Good, Bad and Ugly "
     "entries, with Confidence, Risk and Severity ratings, are in python/CHANGELOG.md and rust/CHANGELOG.md.", [],
     "fixed", "CHANGELOG.md; the draft put them in the root file"),
]


def main():
    s = Substrate()
    bot = "project/replicant"
    if s.get(bot) is None:
        add_entity(s, "Replicant", "project", "james", definition="A hybrid bio-inspired swarm framework; "
                   "a Forge Stack consumer", repo="https://github.com/JamesTheGiblet/Replicant")
        relate(s, "james", "building", bot)
        relate(s, bot, "part-of", "project/forge-stack" if s.get("project/forge-stack") else "forge-stack")
    for slug, (name, kind, used) in SUBJECTS.items():
        if s.get(f"subject/{slug}") is None:
            pid = propose_subject(s, name, [], "james", kind=kind,
                                  rationale="From Claude's Replicant draft; agreed with James on 2026-11-03")
            accept_subject(s, pid["proposal_id"], "james")
        if used:
            relate(s, bot, "uses", f"subject/{slug}")
    made = 0
    for slug, claim, subjects, status, where in CLAIMS:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        source = {"checked": CHECKED, "fixed": FIXED}.get(status, UNCHECKED).format(where)
        tags = ["replicant"] + (["needs-check"] if status == "unchecked" else [])
        create_cube(s, claim, source=source, tags=tags, cube_id=cid)
        link_claim(s, cid, subjects=[f"subject/{x}" for x in subjects], entities=[bot],
                   evidence=[REPO] if status != "unchecked" else [])
        made += 1
    print(f"{made} claims made")
    s.close()


if __name__ == "__main__":
    main()
