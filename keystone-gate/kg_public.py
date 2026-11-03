"""A read-only copy of the page that is safe to put on the open web.

The snapshot leaves out every cube tagged private, every cube from a private
repo, and every cube that names a private repo anywhere in its text. Model
drafts you have not confirmed are left out too, so only your own or accepted
words go public. The page carries no token and no edit tools, and nothing here
reads or copies sc.db: the output is one HTML file.

Run: python keystone-gate/kg cube snapshot
"""
import json
import re
import subprocess
from pathlib import Path

from kg_overlaps import attach_overlaps, load_decisions
from kg_view import collect, render, user_name


OUTPUT = Path(__file__).resolve().parent.parent / "build" / "public" / "index.html"
# The snapshot's own repo is private, but its name is an ordinary word in the cubes
SNAPSHOT_REPO = "cubes"


def private_repos(s, owner="JamesTheGiblet"):
    """Names of private repos, from GitHub and from the repos already in the store."""
    done = subprocess.run(["gh", "repo", "list", owner, "--limit", "500", "--json", "name,visibility"],
                          capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        # Better no snapshot than one that might name a private repo
        raise RuntimeError(f"could not list repos from GitHub: {done.stderr.strip()[:200]}")
    names = {r["name"] for r in json.loads(done.stdout) if r["visibility"] != "PUBLIC"}
    rows = s.conn.execute("SELECT json_extract(state_json, '$.name') AS name FROM capsules "
                          "WHERE id LIKE 'repo/%' AND json_extract(state_json, '$.private')").fetchall()
    return sorted((names | {r["name"] for r in rows if r["name"]}) - {SNAPSHOT_REPO})


def _texts(cube):
    found = [cube["content"], cube["source"] or "", cube["group"] or "", cube["repo"] or "", cube["note_draft"] or ""]
    found += [f["content"] for f in cube["faces"].values() if f and f.get("content")]
    found += [(cube[k] or {}).get("note") or "" for k in ("validation", "attestation")]
    return "\n".join(found)


def _names(private):
    return [re.compile(rf"(?<![\w-]){re.escape(name)}(?![\w-])", re.I) for name in private]


def is_public(cube, private):
    """False if the cube is private, from a private repo, or names one, drafts included."""
    if "private" in cube["tags"] or cube["repo"] in private:
        return False
    text = _texts(cube)
    return not any(p.search(text) for p in _names(private))


def _scrub(cube, kept):
    faces = {lens: None if f and f.get("pending") else f for lens, f in cube["faces"].items()}
    return {**cube, "faces": faces, "note_draft": None, "link_drafts": [],
            "neighbours": [n for n in cube["neighbours"] if n in kept],
            "link_reasons": {k: v for k, v in cube.get("link_reasons", {}).items() if k in kept},
            "link_words": {k: v for k, v in cube.get("link_words", {}).items() if k in kept},
            "contradicts": cube["contradicts"] if cube["contradicts"] in kept else None}


def public_cubes(cubes, private, decisions=None):
    kept = {c["id"] for c in cubes if is_public(c, private)}
    return attach_overlaps([_scrub(c, kept) for c in cubes if c["id"] in kept], decisions)


def write_snapshot(s, path=OUTPUT, private=None):
    private = private_repos(s) if private is None else private
    everything = collect(s)
    cubes = public_cubes(everything, private, load_decisions(s))
    page = render(cubes, user=user_name(s))
    # Check the finished page, not just the steps that made it
    data = json.dumps(cubes, ensure_ascii=False)
    leaked = [p.pattern for p in _names(private) if p.search(data)]
    kept = {c["id"] for c in cubes}
    leaked += [c["id"] for c in everything if c["id"] not in kept and (c["id"] in page or c["content"] in page)]
    if leaked or '"token"' in page:
        raise RuntimeError(f"snapshot refused, it would carry private text: {leaked[:5]}")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(page, encoding="utf-8")
    return {"path": path, "cubes": len(cubes), "left_out": len(everything) - len(cubes)}
