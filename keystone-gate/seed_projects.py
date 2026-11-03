#!/usr/bin/env python3
"""The SCP substrate, LLLM, Canon and JIG as projects, with checked claims.

James asked on 2026-11-03 for the store to hold more than a knowledge graph:
the substrate describes itself against the Forge Stack's five layers, gaps
included, and the projects it will draw on come out of "parked". Each claim
was checked on 2026-11-03 against the code or the README it names. The old
capsules are sorted by accepting their pending sort proposals; their status
comes from each repo's last commit. Faces are left blank.
Create-only: anything whose id exists is skipped.
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_agent import create_cube
from kg_cube import _update_state
from kg_entities import accept_sort, link_claim, relate
from kg_subjects import accept_subject, propose_subject

SOURCE = "Checked against {} on 2026-11-03: {}"

# old capsule -> (project id, status, last commit, where its code lives)
PROJECTS = {
    "scp": ("project/scp-substrate", "active", None, "this repo"),
    "parked/lllm": ("project/lllm", "active", "2026-10-30", "Documents/lllm"),
    "parked/canon": ("project/canon", "active", "2026-10-15", "Documents/Canon"),
    "parked/jig": ("project/jig", "active", "2026-10-27", "Documents/JIG"),
}
NAMES = {"project/scp-substrate": "SCP substrate", "project/lllm": "LLLM", "project/canon": "Canon",
         "project/jig": "JIG"}
# Shared subjects these projects are built round: slug -> (name, kind)
SUBJECTS = {"determinism": ("Determinism", "concept"), "provenance": ("Provenance", "concept"),
            "replay": ("Replay", "concept"), "sqlite": ("SQLite", "tool")}
USES = {"project/scp-substrate": ["scp", "datacube", "leighton-weight", "chronoscribe", "hal", "python", "sqlite"],
        "project/lllm": ["python", "sqlite", "determinism", "provenance"],
        "project/canon": ["python", "determinism", "replay"],
        "project/jig": ["python", "determinism", "replay"]}

SUB, LLLM, CANON, JIG = "project/scp-substrate", "project/lllm", "project/canon", "project/jig"
CODE, LLLM_DOC, CANON_DOC, JIG_DOC = "the scp-substrate code", "LLLM's README", "Canon's README", "JIG's README"
# (slug, claim, project, subjects, where checked, what in it)
CLAIMS = [
    ("scp-substrate-is-a-personal-store", "The SCP substrate is a personal knowledge store in SQLite, with "
     "Keystone Gate as its command line and its page.", SUB, ["sqlite"], CODE, "schema.sql and keystone-gate/kg"),
    ("scp-substrate-verifies-signed-imports", "The SCP substrate checks the Ed25519 signature on a signed person "
     "or circadian capsule when it imports one, with its own Ed25519 module and did:key encoding.", SUB, ["scp"],
     CODE, "src/signing.py and scripts/import_person.py"),
    ("scp-substrate-does-not-sign-its-own", "The SCP substrate doesn't sign the capsules or cubes it creates "
     "itself.", SUB, ["scp"], CODE, "keystone-gate/kg_cube.py, create_cube"),
    ("scp-substrate-has-five-lenses", "The SCP substrate's cubes have five lenses, FACT, COUNTER, OPINION, FICTION "
     "and CONTEXT, plus human validation, not the six lenses with UNKNOWN that the Forge Stack glossary defines.",
     SUB, ["datacube"], CODE, "keystone-gate/kg_cube.py, LENSES"),
    ("scp-substrate-completeness-weights", "In the SCP substrate each lens is worth 16% of a cube's completeness "
     "and human validation 20%, and only a complete cube can be attested.", SUB, ["datacube", "hal"], CODE,
     "keystone-gate/kg_cube.py"),
    ("scp-substrate-has-no-integrity-grades", "The SCP substrate doesn't grade cubes as CRYSTALLINE, COHERENT, "
     "FORMING or SPARSE yet.", SUB, ["datacube"], CODE, "a search of the code"),
    ("scp-substrate-standing-is-0-to-1", "The SCP substrate's standing runs from 0 to 1, fusing a parameter prior "
     "with decayed evidence, while the Forge Stack's λ runs from 0.00 to 2.00.", SUB, ["leighton-weight"], CODE,
     "src/trust.py, fused_trust"),
    ("scp-substrate-decays-with-forge-theory", "The SCP substrate decays evidence with Forge Theory's formula, "
     "N(t) = N₀·e^(−kt).", SUB, ["leighton-weight"], CODE, "src/trust.py, decay_weight"),
    ("scp-substrate-events-are-append-only", "The SCP substrate logs every write to an append-only events table, "
     "with archiving as the one exception.", SUB, ["chronoscribe"], CODE, "schema.sql and docs/SPEC.md"),
    ("scp-substrate-events-are-not-a-ledger", "The SCP substrate's events aren't hash-chained or signed, so they "
     "aren't a ChronoSCRIBE ledger yet.", SUB, ["chronoscribe"], CODE, "schema.sql, the events table"),
    ("scp-substrate-has-no-hal-tiers", "The SCP substrate has human validation and attestation, but no HAL tiers "
     "or seals yet.", SUB, ["hal"], CODE, "a search of the code"),
    ("scp-substrate-house-rules", "The SCP substrate keeps every file under 400 lines and allows no silent "
     "exception handlers, and tests enforce both.", SUB, [], CODE, "tests/test_house_rules.py"),
    ("lllm-is-statistical", "LLLM is a statistical next-word model, not a neural network: it learns "
     "context-to-next-word pairs and stores them in SQLite.", LLLM, ["sqlite"], LLLM_DOC, "What it is"),
    ("lllm-mixed-order-backoff", "LLLM uses mixed-order backoff over contexts of 1 to 4 words, so long contexts "
     "reproduce the source and short ones let it choose.", LLLM, [], LLLM_DOC, "What it is"),
    ("lllm-is-fully-local", "LLLM trains and runs fully locally, on a phone in Termux or a PC, with no cloud, "
     "downloaded weights or GPU, on Python's standard library alone.", LLLM, ["python"], LLLM_DOC, "What it is"),
    ("lllm-every-word-is-traceable", "Every word LLLM produces comes from a context that appears in its training "
     "docs.", LLLM, ["provenance"], LLLM_DOC, "Why it exists"),
    ("lllm-refuses-rather-than-invents", "LLLM refuses rather than invents: its join guard stops generation when "
     "continuing would stitch unrelated text together.", LLLM, ["provenance"], LLLM_DOC, "Why it exists"),
    ("lllm-is-deterministic", "The same corpus always gives LLLM a byte-identical model and manifest.", LLLM,
     ["determinism"], LLLM_DOC, "Why it exists"),
    ("lllm-checks-its-training-docs", "LLLM checks every training doc against its content hash before using it, "
     "and names every skipped doc with a reason.", LLLM, ["provenance"], LLLM_DOC, "Why it exists"),
    ("lllm-never-trains-on-itself", "LLLM won't train on the canon or lllm repos, because they describe the model "
     "and would mean training on its own output.", LLLM, ["provenance"], LLLM_DOC, "What gets skipped"),
    ("lllm-was-built-for-canon", "LLLM was built for Canon, where a language model is an unreliable witness that "
     "may speak only on the record.", LLLM, [], LLLM_DOC, "the opening"),
    ("canon-is-a-reasoning-engine", "Canon is a reasoning engine: it decides from declared rules, refuses what it "
     "can't justify, and keeps a signed record of every decision that can be replayed.", CANON, ["replay"],
     CANON_DOC, "the opening"),
    ("canon-llm-is-a-surface", "In Canon the LLM is only a surface: nothing authorises itself, and audit is "
     "replay.", CANON, ["replay"], CANON_DOC, "the opening"),
    ("canon-runs-without-cloud-or-model", "Canon is built and tested on a phone in Termux, with no cloud, no "
     "vendor and no model in the loop.", CANON, ["determinism"], CANON_DOC, "the opening"),
    ("canon-phases-0-to-40-built", "Canon's phases 0 to 40 are largely built.", CANON, [], CANON_DOC, "Status"),
    ("jig-is-a-deterministic-rule-engine", "JIG is a deterministic rule engine: facts, rules, constraints and "
     "goals are declared as small signed JSON capsules.", JIG, ["determinism"], JIG_DOC, "the opening"),
    ("jig-journal-is-hash-chained", "JIG records every decision in a hash-chained journal that can be replayed "
     "and verified.", JIG, ["replay"], JIG_DOC, "the opening"),
    ("jig-cycle-is-a-pure-function", "A JIG cycle is a pure function of the current state, the active rules and "
     "the observation, so the same inputs give the same journal entry byte for byte.", JIG,
     ["determinism", "replay"], JIG_DOC, "How it works"),
    ("jig-has-cli-and-web-app", "JIG has a command line and a web app.", JIG, [], JIG_DOC, "Status"),
]


def main():
    s = Substrate()
    for old, (pid, status, last, where) in PROJECTS.items():
        proposal = s.get(f"proposal/sort/{old}")
        if proposal and proposal["state"]["status"] == "pending":
            print(f"  sorted {old}: {accept_sort(s, f'proposal/sort/{old}', 'james', name=NAMES[pid])}")
        if s.get(pid):
            extra = {"last_commit": last} if last else {}
            _update_state(s, pid, {**s.get(pid)["state"], "name": NAMES[pid], "status": status,
                                   "code": where, **extra})
    for slug, (name, kind) in SUBJECTS.items():
        if s.get(f"subject/{slug}") is None:
            pid = propose_subject(s, name, [], "james", kind=kind,
                                  rationale="Shared by James's projects; added on 2026-11-03")["proposal_id"]
            accept_subject(s, pid, "james")
    for project, subjects in USES.items():
        for slug in subjects:
            relate(s, project, "uses", f"subject/{slug}")
    relate(s, CANON, "uses", LLLM)
    made = 0
    for slug, claim, project, subjects, checked, where in CLAIMS:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        create_cube(s, claim, source=SOURCE.format(checked, where), tags=[project.split("/")[1]], cube_id=cid)
        link_claim(s, cid, subjects=[f"subject/{x}" for x in subjects], entities=[project])
        made += 1
    print(f"{made} claims made")
    s.close()


if __name__ == "__main__":
    main()
