"""Cubes about James, as drafts for him to confirm.

The words are Claude's, written from conversation, so every face is a proposal
and the validation is only a suggestion. They are tagged private, so later
drafting and answers about them stay on this machine.
Run: python seeds/claims/before-pivot/seed_cubes_james.py
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[3] / "keystone-gate"
sys.path[:0] = [str(_here.parent / "src"), str(_here)]

from substrate import Substrate

from kg_agent import create_cube, propose_face


PERSON = "person/james-gilbert"
BY = "model-draft:claude"
WHY = "written by Claude from conversation, in Claude's words"
NOTE = "Confirmed by James, about himself, 2026-11-02."

CUBES = [
    ("james-builds-for-choice-not-money", "James builds because he chooses to, not for money.", {
        "FACT": "James says money is something humanity decided mattered, and that he builds because he chooses to live.",
        "COUNTER": "Giblets Forge is a trading name, so money is in the picture somewhere, even if it isn't the point.",
        "OPINION": "It explains the shape of the work: sovereign, open, and built to be owned rather than sold.",
        "FICTION": "Suppose a buyer offers to fund the Forge Stack on the condition that it closes. The answer shows whether this cube holds.",
        "CONTEXT": 'It fits the motto: "Now forge yours."',
    }),
    ("james-carpenter-by-trade", "James is a carpenter by trade.", {
        "FACT": "He trained on chisels and hammers, and was self-employed with routers and jigs three years later.",
        "COUNTER": "Jigs speed up cuts, but they also constrain them. A tool that makes things fast can make the wrong thing fast.",
        "OPINION": "The router-and-jig analogy is the clearest way he explains what AI does for him: it amplifies skill without replacing judgement.",
        "FICTION": "Suppose he'd stayed with chisels only. The ideas would exist, but most would still be parked.",
        "CONTEXT": "The habit of building fixtures carried over: capsules, gates and guards are jigs for code.",
    }),
    ("llms-unlocked-execution", "LLMs made his work buildable.", {
        "FACT": "James says it wasn't until LLMs arrived that he could build his work and dreams.",
        "COUNTER": "The ideas predate LLMs, because he documents ideas fully and parks them for years. LLMs unlocked execution, not vision.",
        "OPINION": "That distinction matters, because it's why his stack never lets the LLM decide what's true.",
        "FICTION": "Suppose LLM access vanished tomorrow. The specs would survive, and the build rate wouldn't.",
        "CONTEXT": "He uses models for specs and drafting, and builds deliberately around their unreliability.",
    }),
    ("james-not-one-title", "James won't be boxed in by a title.", {
        "FACT": "He codes, 3D-models, draws, paints, and builds robots, 3D printers and systems.",
        "COUNTER": "Breadth has a cost, and many projects sit at idea stage. Range and finishing pull against each other.",
        "OPINION": "The Forge Stack is what makes the breadth coherent, since one substrate sits under many projects.",
        "FICTION": "Suppose he picked one title for a year. Whether that would help or hurt is an open question.",
        "CONTEXT": "He's self-taught, and his brand is Giblets Forge.",
    }),
    ("life-in-capsules", "James has always defined his life in capsules.", {
        "FACT": "He says only now, with the Forge Stack and SCP, do the capsules fit him.",
        "COUNTER": "A capsule is a boundary, and describing a life in boundaries can flatten what doesn't fit them.",
        "OPINION": "The fact that the tool matches how he already thinks is probably why he finally finishes things in it.",
        "FICTION": "Suppose the capsules hadn't fit. SCP would have been another parked idea.",
        "CONTEXT": "His daily routine is modelled as circadian capsules too.",
    }),
    ("james-parks-ideas", "James parks ideas until they fit.", {
        "FACT": "He documents ideas fully, then shelves them, sometimes for years.",
        "COUNTER": "Parked specs go stale, because the tools and assumptions they relied on move on.",
        "OPINION": "Parking only works if each parked spec says what it's waiting for.",
        "FICTION": "Suppose an old spec is revived and built exactly as written, against a world that has moved on.",
        "CONTEXT": "Canon's FACT and COUNTER faces suit reviving an old idea: check what's still true.",
    }),
    ("james-qinetiq-malvern", "James moved from facilities at OPG to QinetiQ Malvern.", {
        "FACT": "He started at QinetiQ in September 2026, in a role that includes cutting keys, which he likes. He's relocating to the Malvern area.",
        "COUNTER": "One profile line still says he works at Oxford PharmaGenesis. Only the latest one is true.",
        "OPINION": "The key-cutting work has already produced a project idea, the key blank cross-reference tool.",
        "CONTEXT": "He previously wrote a tribal-knowledge handover for OPG facilities before leaving.",
    }),
]


def seed(s, cubes=CUBES):
    made = []
    for slug, claim, faces in cubes:
        cube_id = f"cube/{slug}"
        if s.get(cube_id):
            continue
        create_cube(s, claim, source="Written by Claude from conversation with James",
                    tags=["james", "private", "defining"], cube_id=cube_id)
        if s.get(PERSON):
            s.link(cube_id, "derived-from", PERSON)
        for lens, text in faces.items():
            propose_face(s, cube_id, lens, text, BY, rationale=WHY)
        s.write({"id": f"{cube_id}/validation-draft", "foundation": "foundation:knowledge", "state": {
            "kind": "validation-draft", "cube_id": cube_id, "content": NOTE, "proposed_by": BY}})
        made.append(cube_id)
    return made


if __name__ == "__main__":
    s = Substrate()
    print(f"Added {len(seed(s))} cubes about James, as drafts.")
    s.close()
