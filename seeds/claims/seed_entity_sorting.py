#!/usr/bin/env python3
"""Suggested sorting of what `james` links to, into entities and subjects, by Claude.

Each is a proposal and changes nothing until accepted with `kg entity accept`.
Accept the subjects before the merges that fold duplicates into them.
Re-running updates pending proposals and leaves rejected ones alone.
"""
import sys
from pathlib import Path

# keystone-gate, beside seeds/ in the repo
_here = Path(__file__).resolve().parents[2] / "keystone-gate"
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from store.substrate import Substrate
from kg_entities import propose_sort

# (target, action, options, rationale)
SORTING = [
    ("person/james-gilbert", "describe", {"into": "james"},
     "Your signed person document. It stays as it is, so its signature still checks, and describes you."),
    ("person", "drop", {}, "A stray copy of the person foundation from an early seed, with no links."),

    ("project/robot-arm", "entity", {"kind": "project"}, "You are building it."),
    ("project/3d-printer-build", "entity", {"kind": "project"}, "You are building it."),
    ("project/if-game", "entity", {"kind": "project"}, "You are building it."),
    ("project/sim-emergence", "entity", {"kind": "project"}, "You are building it, as part of the Forge Stack."),
    ("scp", "entity", {"kind": "project", "new_id": "project/scp-substrate", "name": "SCP Substrate"},
     "This project. Its repo is repo/scp-substrate."),
    ("forge-stack", "entity", {"kind": "project", "new_id": "project/forge-stack"},
     "The umbrella the SCP substrate, Canon, JIG and LLLM sit under."),
    ("parked/canon", "entity", {"kind": "project", "new_id": "project/canon", "name": "Canon"},
     "A project, parked. Its status stays parked."),
    ("parked/jig", "entity", {"kind": "project", "new_id": "project/jig", "name": "JIG"},
     "A project, parked. Its status stays parked."),
    ("parked/lllm", "entity", {"kind": "project", "new_id": "project/lllm", "name": "LLLM"},
     "A project, parked. Its status stays parked."),

    ("forge", "entity", {"kind": "organisation", "new_id": "entity/giblets-forge", "name": "Giblets Forge"},
     "Your sole-trader business."),
    ("qinetiq", "entity", {"kind": "organisation", "new_id": "entity/qinetiq"}, "Where you work."),
    ("malvern", "entity", {"kind": "place", "new_id": "entity/malvern"}, "Where you are."),
] + [
    (repo, "entity", {"kind": "repo"}, "A repo you own. Its id stays, so re-indexing still finds it.")
    for repo in ("repo/scp-substrate", "repo/jamesthegiblet/blockforge-platform",
                 "repo/jamesthegiblet/lightweight-env-validator", "repo/jamesthegiblet/m-i-l-o-chatbot",
                 "repo/jamesthegiblet/project-aegis-cli-mvp-ready", "repo/jamesthegiblet/project-forgemind",
                 "repo/jamesthegiblet/vibecode-ai-assisted")
] + [
    ("tool/esp32", "subject", {"kind": "component"}, "A microcontroller you use, and the robot arm uses."),
    ("esp32", "merge", {"into": "subject/esp32"}, "A duplicate of tool/esp32."),
    ("tool/claude", "subject", {"kind": "tool"}, "A model you use."),
    ("claude", "merge", {"into": "subject/claude"}, "A duplicate of tool/claude."),
    ("tool/chisels", "subject", {"kind": "tool"}, "Tools in general, not one particular set."),
    ("tool/router", "subject", {"kind": "tool"}, "Tools in general, not one particular router."),
    ("tool/jig", "subject", {"kind": "tool", "new_id": "subject/workholding-jig"},
     "Workholding jigs, not the JIG project."),
    ("tool/printer", "subject", {"kind": "tool"}, "3D printing in general. Your own printer could be an entity."),
    ("carpentry", "subject", {"kind": "skill"}, "Your first trade."),
]


def main():
    s = Substrate()
    for target, action, opts, why in SORTING:
        r = propose_sort(s, target, action, "claude", rationale=why, kind=opts.get("kind"),
                         new_id=opts.get("new_id"), name=opts.get("name"), into=opts.get("into"))
        print(f"  {target}: {r.get('status') or r.get('reason') or r.get('error')}")
    s.close()


if __name__ == "__main__":
    main()
