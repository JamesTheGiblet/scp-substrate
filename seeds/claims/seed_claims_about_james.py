#!/usr/bin/env python3
"""Claims about James, from his signed person document, confirmed by him on 2026-11-03.

Each claim is tagged private, is about-entity james, and is derived-from
person/james-gilbert. Entries the document marks as inferred were put to James
and confirmed, and their source says so. Topics become subjects, accepted on
his confirmation. Faces are left blank for him to fill. Create-only: a claim
whose id exists is skipped.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[2] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from substrate import Substrate
from kg_agent import create_cube
from kg_entities import accept_sort, link_claim
from kg_subjects import accept_subject, add_claim, propose_subject

DOC = "person/james-gilbert"
STATED = "Stated in James's signed person document"
CONFIRMED = "Inferred in James's signed person document; confirmed by James on 2026-11-03"

# (slug, claim, topic or None, source)
CLAIMS = [
    ("to-build-is-to-be-free", "To build is to be free, is to be me.", None, STATED),
    ("tammi-comes-first", "Time with Tammi comes first and overrides all solo time, building included.", None, STATED),
    ("the-plumberz-comes-second", "The Plumberz, his rescue dog, comes second.", None, STATED),
    ("james-goes-by-james", 'James goes by James, his handle is JamesTheGiblet, and he signs off "Giblet out".', None, STATED),
    ("james-runs-giblets-forge", 'James runs Giblets Forge as a sole trader: "I wanted it. So I forged it. Now forge yours."',
     None, STATED),
    ("james-is-a-polymath-builder", "James is a polymath builder who won't be boxed in by a title.", None, STATED),
    ("james-is-a-carpenter-by-trade", "James is a carpenter by trade, and the move from chisels to routers and jigs "
     "is how he explains what AI did for building.", "carpentry", STATED),
    ("james-is-self-taught", "James is self-taught: he went from an Eaglemoss V-Summit kit to designing a custom "
     "1.5 m², four-bed printer.", "3d-printing", STATED),
    ("james-builds-for-love-not-money", "James builds for the love of it, not for money.", None, STATED),
    ("james-defines-life-in-capsules", "James has always defined his life in capsules, and SCP is where they finally fit.",
     None, STATED),
    ("james-self-acceptance-at-36", "James reached self-acceptance at around 36, after decades of navigating "
     "neurotypical social patterns.", None, STATED),
    ("james-is-dyslexic", "James is dyslexic: he writes fast and wants spelling errors flagged and corrected.",
     "dyslexia", STATED),
    ("james-has-adhd", "James has ADHD and no built-in scheduler, so external structure tells him what's next.",
     "adhd", STATED),
    ("james-has-misophonia", "James has misophonia, triggered by eating sounds: chewing, chomping and gulping.", "misophonia", STATED),
    ("james-finishes-what-he-is-pointed-at", "Pointed at a task, James finishes it. Left alone, he wanders.",
     "working-style", STATED),
    ("adversity-fuels-james", 'Adversity fuels James: being told "it can\'t be done" is what makes him do it.',
     "working-style", STATED),
    ("james-scraps-and-restarts", "James scraps and restarts rather than patching, once he finds a better way.",
     "working-style", STATED),
    ("james-wakes-with-the-solution", "James often wakes up with the solution to whatever he's stuck on.",
     "working-style", STATED),
    ("james-documents-then-parks-ideas", "James documents ideas fully, then parks them until they fit.",
     "working-style", STATED),
    ("james-uses-claude-for-specs", "James uses Claude for rigorous specs and writes the code elsewhere.",
     "working-style", STATED),
    ("james-learns-by-doing", "James learns by doing, not by instruction.", "working-style", STATED),
    ("how-to-talk-to-james", "James wants a direct, informal tone, honest pushback over flattery, bullets over "
     "blocks of text, and spelling flagged.", "communication", STATED),
    ("comfort-cartoons-soothe-james", "Familiar comfort cartoons soothe James.", None, STATED),
    ("smoking-marks-james-transitions", "Smoking is part of James's routine at transitions.", None, STATED),
    ("strict-rules-backfire-for-james", "Strict rules backfire for James, and soft targets work.", None, STATED),
    ("james-mode-switches-are-costly", "Switching between modes is costly for James, so his routine has decompress "
     "buffers around each switch.", None, CONFIRMED),
    ("cartoons-mark-james-mode-switches", "The comfort cartoons mark James's mode switches: morning, after work, "
     "and before bed.", None, CONFIRMED),
    ("james-needs-chosen-structure", "James needs structure that feels chosen, not imposed.", "working-style",
     CONFIRMED),
    ("james-real-build-time-is-the-weekend", "James's real build time is Friday night to Saturday night, with about "
     "15 minutes on weekday mornings plus solo evenings.", None, CONFIRMED),
    ("building-is-james-third-priority", "Building is James's third priority, after Tammi and the Plumberz.", None,
     CONFIRMED),
]

# Topics that are new subjects: (slug, name, kind)
NEW_SUBJECTS = {"dyslexia": ("Dyslexia", "condition"), "adhd": ("ADHD", "condition"),
                "misophonia": ("Misophonia", "condition"), "working-style": ("Working style", "topic"),
                "communication": ("Communication", "topic")}
# Topics that come from sorting an old capsule: slug -> (proposal, name)
SORTED_SUBJECTS = {"carpentry": ("proposal/sort/carpentry", None),
                   "3d-printing": ("proposal/sort/tool/printer", "3D printing")}


def main():
    s = Substrate()
    made = {}
    for slug, claim, topic, source in CLAIMS:
        cid = f"cube/{slug}"
        if s.get(cid):
            print(f"  skipped, exists: {cid}")
            continue
        create_cube(s, claim, source=source, tags=["private", "james"], cube_id=cid)
        link_claim(s, cid, entities=["james"], evidence=[DOC])
        made.setdefault(topic, []).append(cid)
    for topic, (pid, name) in SORTED_SUBJECTS.items():
        if s.get(f"subject/{topic}") is None:
            print(f"  sorted {pid}: {accept_sort(s, pid, 'james', name=name)}")
        for cid in made.get(topic, []):
            add_claim(s, cid, f"subject/{topic}")
    for topic, (name, kind) in NEW_SUBJECTS.items():
        if topic in made:
            pid = propose_subject(s, name, made[topic], "james", kind=kind,
                                  rationale="Confirmed by James on 2026-11-03")["proposal_id"]
            print(f"  subject {name}: {accept_subject(s, pid, 'james')}")
    print(f"{sum(len(v) for v in made.values())} claims made")
    s.close()


if __name__ == "__main__":
    main()
