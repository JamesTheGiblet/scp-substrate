#!/usr/bin/env python3
"""Turn each claim's source line into evidence it is derived from.

A claim's `source` says in words what it rests on: "Checked against the
Replicant repo on 2026-11-03: CHANGELOG.md", "The listing copy", "Customer
review (Ry01)". This reads those lines, makes one evidence/<slug> per real
thing named (a README, a changelog, a code file, the listing, one review),
and links every claim that names it. Sources that are not evidence are left
alone: James stating something, Claude's general knowledge, an inference, or
"a search of the code", which names nothing to check again.

Paths are given as they are now, so src/trust.py is cited as src/store/trust.py.
The claims themselves are not changed.

    python scripts/evidence_from_sources.py           # dry run, prints the plan
    python scripts/evidence_from_sources.py --write   # make and link the evidence
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from store.evidence import add_evidence, cite
from store.substrate import Substrate

BY = "claude, from each claim's source line, 2026-11-05"
FILE = re.compile(r"[\w./-]+\.(?:py|md|json|sql)\b|rust/wasm/|keystone-gate/kg\b|the file tree")
# Files that moved since the claims were written
MOVED = {"src/trust.py": "src/store/trust.py", "src/signing.py": "src/store/signing.py",
         "scripts/import_person.py": "scripts/scp/import_person.py"}
REPOS = {"Replicant": ("replicant", "repo/jamesthegiblet/replicant"),
         "LLLM": ("lllm", None),
         "Canon": ("canon", "repo/jamesthegiblet/canon"),
         "JIG": ("jig", "repo/jamesthegiblet/jig"),
         "scp-substrate": ("scp-substrate", "repo/scp-substrate")}


def _slug(text):
    return "-".join(re.findall(r"[a-z0-9]+", text.lower()))


def _file(repo_name, repo_slug, repo_id, path):
    path = MOVED.get(path, path)
    kind = "doc" if path.endswith(".md") else "code"
    title = f"{repo_name}: {'its file tree' if path == 'the file tree' else path}"
    # README.md is cited as <repo>-readme, like a README named on its own
    return (f"evidence/{repo_slug}-{_slug(path.removesuffix('.md'))}", kind, title,
            {"path": None if path == "the file tree" else path, "repo": repo_id})


def pieces(source):
    """The evidence a source line names, as [(id, kind, title, extra)]."""
    src = source or ""
    if "person document" in src:
        return [("person/james-gilbert", None, None, None)]
    m = re.search(r"Forge Stack's frozen, signed docs, (\S+?/docs/([\w.-]+\.md))", src)
    if m:
        return [(f"evidence/forge-stack-docs-{_slug(m.group(2)[:-3])}", "doc",
                 f"Forge Stack docs: {m.group(2)}", {"path": m.group(1)})]
    m = re.search(r"(?:against|to match) (?:the )?(\S+?)(?:'s)? (README|repo|code) on [\d-]+: (.*)", src)
    if m and m.group(1) in REPOS:
        name, (slug, repo_id) = m.group(1), REPOS[m.group(1)]
        if m.group(2) == "README":
            return [(f"evidence/{slug}-readme", "doc", f"{name}: README.md", {"path": "README.md", "repo": repo_id})]
        return [_file(name, slug, repo_id, f) for f in dict.fromkeys(FILE.findall(m.group(3)))]
    if src.startswith("Inferred"):
        return []
    found = []
    if "listing" in src:
        found.append(("evidence/acebott-spider-listing", "listing",
                      "ACEBOTT Bionic Spider: the Amazon UK listing's copy and images", {}))
    for who in re.findall(r"customer review \((\w+)", src, re.I):
        found.append((f"evidence/acebott-review-{who.lower()}", "review",
                      f"ACEBOTT Bionic Spider: {who}'s customer review", {}))
    return found


def plan(s):
    """[(claim id, source, [pieces])] for every claim."""
    rows = s.conn.execute("SELECT id FROM capsules WHERE foundation = 'foundation:cube' AND is_meta = 0 ORDER BY id")
    return [(r[0], s.get(r[0])["state"].get("source"), pieces(s.get(r[0])["state"].get("source"))) for r in rows]


def _ensure_foundation(s):
    """Add foundation:evidence from sc.json, as bootstrap.py would, without
    running bootstrap's legacy import against the live store."""
    if not s.get("foundation:evidence"):
        f = next(f for f in json.loads((ROOT / "sc.json").read_text(encoding="utf-8"))["foundations"]
                 if f["id"] == "foundation:evidence")
        with s.conn:
            s.conn.execute("INSERT INTO capsules (id, foundation, state_json, is_meta) VALUES "
                           "('foundation:evidence', 'foundation:foundation', ?, 1)", (json.dumps(f["state"]),))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="make and link the evidence")
    args = ap.parse_args()
    s = Substrate()
    rows = plan(s)
    made = {p[0]: p for _, _, ps in rows for p in ps}
    backed = [r for r in rows if r[2]]
    print(f"{len(made)} pieces of evidence, backing {len(backed)} of {len(rows)} claims\n")
    for eid, kind, title, _ in sorted(made.values()):
        n = sum(1 for _, _, ps in rows if any(p[0] == eid for p in ps))
        print(f"  {eid:52} {kind or 'person':10} {n:3}  {title or ''}")
    print("\nnot evidence, left alone:")
    for cid, src, ps in rows:
        if not ps:
            print(f"  {cid}: {src}")
    if not args.write:
        print("\ndry run, nothing changed. Add --write to make and link them.")
        return
    _ensure_foundation(s)
    for eid, kind, title, extra in made.values():
        if kind:
            add_evidence(s, eid, kind, title, BY, **{k: v for k, v in extra.items() if v})
    links = 0
    for cid, _, ps in rows:
        for p in ps:
            r = cite(s, cid, p[0])
            if "error" in r:
                sys.exit(f"error: {r['error']}")
            links += 1
    s.close()
    print(f"\nlinked {links} claim-evidence pairs")


if __name__ == "__main__":
    main()
