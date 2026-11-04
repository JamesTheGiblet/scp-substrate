"""Preferences become the third kind of foundation, beside safety and security.

Your attested principle cubes are marked foundational and tagged `preference`.
Their words and attestations stay as they are, and from now on they follow the
foundational rules. Two new preference cubes are drafts in Claude's words for
you to confirm. Suggested links tie each kind of foundation to what it governs.
Run: python seeds/claims/before-pivot/seed_cubes_preferences.py
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from store.substrate import Substrate

from kg_agent import create_cube, list_proposals, propose_face, propose_neighbour
from kg_cube import FOUNDATIONAL, _update_state


BY = "model-draft:claude"
WHY = "written by Claude from this repo's README, docs and code"
PREFERENCE = "preference"

# Attested principles of yours that are really preferences about how you work
EXISTING = ["british-english-everywhere", "split-files-over-400-lines", "compress-in-uncertain-channels",
            "log-everything-fail-loud", "phase-0-is-documentation", "keep-dependencies-to-one"]

CUBES = [
    ("python-for-these-tools", "These tools are written in Python, on its standard library.", ["code"], {
        "FACT": "Every tool in this repo is Python, and the README says it needs no third-party packages except the optional Anthropic SDK.",
        "COUNTER": "Replicant has a Rust implementation beside its Python one, so Python is the choice here, not everywhere.",
        "OPINION": "Python keeps the tools readable and quick to change, which matters more here than speed.",
        "FICTION": "Suppose the substrate were rewritten in Rust. It might run faster, and it would be slower to change.",
        "CONTEXT": "It goes with keeping dependencies to one, since the standard library covers SQLite, hashing and HTTP.",
    }),
    ("plain-words-in-docs", "Docs are written in plain words, without hype or buzzwords.", ["docs"], {
        "FACT": "The docs here say what each part does, list its limits, and say where something is untested.",
        "COUNTER": "Plain words can undersell work, and some technical terms have no plain substitute.",
        "OPINION": "A reader should be able to check every sentence against the code.",
        "FICTION": "Suppose the README called the substrate revolutionary. The first limit a reader met would cost it their trust.",
        "CONTEXT": "It goes with British English everywhere, and with Phase 0 being documentation.",
    }),
]

NEIGHBOURS = [
    # Preferences, out to how things are written and built
    ("british-english-everywhere", "plain-words-in-docs", "both are about how things are written"),
    ("phase-0-is-documentation", "plain-words-in-docs", "documentation comes first, so how it reads matters"),
    ("compress-in-uncertain-channels", "plain-words-in-docs", "short, plain wording survives a noisy channel"),
    ("python-for-these-tools", "keep-dependencies-to-one", "the standard library is what makes one dependency possible"),
    ("python-for-these-tools", "replicant-has-reached-version-1-0", "Replicant also has a Rust implementation"),
    ("python-for-these-tools", "symlm-has-no-weights", "SymLM is Python rules, with no model to load"),
    ("split-files-over-400-lines", "keep-dependencies-to-one", "both keep the code small enough to read"),
    ("log-everything-fail-loud", "every-write-goes-through-substrate", "every write leaves a logged event"),
    # Security, out to keys and signing
    ("never-commit-secrets", "own-ed25519-for-local-signing", "the private signing key is a secret too"),
    ("rotate-a-leaked-key-immediately", "signed-means-provenance-not-trust", "a leaked signing key lets anyone sign as you"),
    # Safety, out to the Li-ion packs
    ("li-ion-fire-get-out-and-call-999", "li-ion-2s-needs-a-bms", "a BMS guards against some causes of fire, not all"),
    ("li-ion-warning-signs", "li-ion-storage", "check stored packs for the warning signs"),
    ("do-not-charge-li-ion-unattended", "li-ion-2s-is-8v4-full", "charging should stop at 8.4V for a 2S pack"),
    ("protection-cannot-stop-internal-faults", "li-ion-3000mah-labels-need-checking", "a relabelled cell may not have the protection it claims"),
    ("fuse-the-battery-positive-near-the-pack", "xt60-is-30a-continuous", "the fuse and the connector should suit the same current"),
]

# The rigid cube's CONTEXT draft described the old fixed lattice
RIGID_CONTEXT = ("They sit in three groups around you at the centre of the field: orange for safety, "
                 "pink for security and blue for preferences.")


def mark_preference(s, slug):
    """Tag an existing cube as a foundational preference. Returns True if it changed."""
    capsule = s.get(f"cube/{slug}")
    if not capsule:
        return False
    state = capsule["state"]
    tags = [t for t in state["tags"] if t != "security"]
    for tag in (FOUNDATIONAL, PREFERENCE):
        if tag not in tags:
            tags.append(tag)
    if tags == state["tags"]:
        return False
    _update_state(s, capsule["id"], {**state, "tags": tags})
    return True


def fix_rigid_context(s):
    """Reword Claude's own pending draft, which no one has accepted yet."""
    for p in list_proposals(s, cube_id="cube/foundational-cubes-are-rigid", status="pending"):
        if p.get("lens") == "CONTEXT" and p.get("proposed_by") == BY and p.get("content") != RIGID_CONTEXT:
            state = {k: v for k, v in p.items() if k != "id"}
            _update_state(s, p["id"], {**state, "content": RIGID_CONTEXT})
            return True
    return False


def seed(s):
    marked = [slug for slug in EXISTING if mark_preference(s, slug)]
    made = []
    for slug, claim, tags, faces in CUBES:
        cube_id = f"cube/{slug}"
        if s.get(cube_id):
            continue
        create_cube(s, claim, source="Written by Claude from this repo's README, docs and code",
                    tags=[FOUNDATIONAL, PREFERENCE, *tags], cube_id=cube_id)
        for lens, text in faces.items():
            propose_face(s, cube_id, lens, text, BY, rationale=WHY)
        made.append(cube_id)
    linked = 0
    for a, b, why in NEIGHBOURS:
        if s.get(f"cube/{a}") and s.get(f"cube/{b}"):
            linked += propose_neighbour(s, f"cube/{a}", f"cube/{b}", BY, rationale=why).get("status") == "created"
        else:
            print(f"skipped {a} -> {b}: a cube is missing")
    return {"marked": marked, "made": made, "linked": linked, "rigid": fix_rigid_context(s)}


if __name__ == "__main__":
    s = Substrate()
    r = seed(s)
    print(f"Marked {len(r['marked'])} cubes as preferences, added {len(r['made'])} drafts, "
          f"suggested {r['linked']} links, rigid CONTEXT draft {'updated' if r['rigid'] else 'unchanged'}.")
    s.close()
