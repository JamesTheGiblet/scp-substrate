"""Absorb a GitHub repository into the substrate. Phase 1: metadata only.

Two API calls per repo:
  1. GET /repos/{owner}/{repo}                    → metadata + default_branch
  2. GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1  → full file tree

No content download. File identity is the git blob SHA from the tree response.

Usage:
  python scripts/repos/absorb_github.py owner/repo --dry-run
  python scripts/repos/absorb_github.py owner/repo --write

Auth: GITHUB_TOKEN or GH_TOKEN if set, else the GitHub CLI's login (gh auth token),
so a private repo works in any terminal once `gh auth login` has been run.
  Without token: 60 req/hour (30 repos).
  With token:    5,000 req/hour (2,500 repos).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request
from datetime import datetime, timezone

from absorb_repo import (
    SKIP_DIRS, SKIP_FILE_EXTS, LANG_BY_EXT,
    MAX_FILE_BYTES, MAX_FILES_HARD, _slug,
)
from store.substrate import Substrate

API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"


def _headers():
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": API_VERSION,
        "User-Agent": "scp-substrate/1.0",
    }
    token = _token()
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _token():
    """GITHUB_TOKEN or GH_TOKEN, else the GitHub CLI's login, else None."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def _get(path):
    url = f"{API_BASE}{path}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[:400]
        if e.code == 403:
            raise SystemExit(
                f"GitHub API 403 (rate limit or private repo).\n"
                f"  Set GITHUB_TOKEN to raise the limit from 60/hr to 5,000/hr.\n"
                f"  {body}"
            )
        if e.code == 404:
            raise SystemExit(f"Repo not found: {url}\n  {body}")
        raise SystemExit(f"GitHub API error {e.code}: {url}\n  {body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"Network error reaching GitHub: {e}")


def _should_skip(path_str, size):
    if size is not None and size > MAX_FILE_BYTES:
        return True
    if any(part in SKIP_DIRS for part in Path(path_str).parts):
        return True
    suffix = Path(path_str).suffix.lower()
    if suffix in SKIP_FILE_EXTS:
        return True
    if ".min." in Path(path_str).name:
        return True
    return False


def absorb_github(s, owner, repo, write=False):
    full_name = f"{owner}/{repo}"

    print(f"Fetching {full_name} from GitHub")
    meta = _get(f"/repos/{full_name}")
    default_branch = meta.get("default_branch", "main")
    print(f"  default_branch: {default_branch}")

    tree_resp = _get(
        f"/repos/{full_name}/git/trees/{default_branch}?recursive=1"
    )
    tree_sha = tree_resp.get("sha")
    truncated = tree_resp.get("truncated", False)
    entries = tree_resp.get("tree", [])

    if truncated:
        print("  WARNING: tree response truncated — file list may be incomplete")

    # Filter to blobs we want
    files = []
    for e in entries:
        if e.get("type") != "blob":
            continue
        path = e["path"]
        size = e.get("size", 0)
        if _should_skip(path, size):
            continue
        files.append({
            "path": path,
            "sha": e["sha"],
            "size": size,
            "language": LANG_BY_EXT.get(
                Path(path).suffix.lower(), "unknown"
            ),
        })
        if len(files) >= MAX_FILES_HARD:
            print(f"  warning: hit MAX_FILES_HARD={MAX_FILES_HARD}")
            break

    if not files:
        return {"error": "no files to absorb"}

    total_size = sum(f["size"] for f in files)
    from collections import Counter
    lang_counts = Counter(
        f["language"] for f in files if f["language"] != "unknown"
    )
    primary = lang_counts.most_common(1)[0][0] if lang_counts else None
    languages = sorted(lang_counts)

    repo_id = f"repo/{_slug(owner)}/{_slug(repo)}"

    print(f"  {len(files)} files, {total_size:,} bytes")
    print(f"  languages: {', '.join(languages) or '(none)'}")
    print(f"  primary: {primary}")
    print(f"  tree_sha: {tree_sha[:12]}...")

    if not write:
        print()
        print("(dry-run — no capsules written)")
        print(f"  would create: {repo_id}")
        print(f"  would create/update {len(files)} file capsules")
        print(f"  would link {repo_id} --contains--> each file")
        print()
        print("Re-run with --write to absorb.")
        return {
            "repo_id": repo_id,
            "files": len(files),
            "languages": languages,
            "primary": primary,
            "dry_run": True,
        }

    # --- Repo capsule ---
    license_info = meta.get("license") or {}
    repo_state = {
        "kind": "repo",
        "source": "github",
        "full_name": meta.get("full_name", full_name),
        "owner": meta.get("owner", {}).get("login", owner),
        "name": meta.get("name", repo),
        "description": meta.get("description"),
        "default_branch": default_branch,
        "tree_sha": tree_sha,
        "language": meta.get("language") or primary,
        "languages": languages,
        "stars": meta.get("stargazers_count", 0),
        "forks": meta.get("forks_count", 0),
        "open_issues": meta.get("open_issues_count", 0),
        "size_kb": meta.get("size", 0),
        "license": license_info.get("spdx_id"),
        "topics": meta.get("topics", []),
        "html_url": meta.get("html_url"),
        "clone_url": meta.get("clone_url"),
        "created_at": meta.get("created_at"),
        "updated_at": meta.get("updated_at"),
        "pushed_at": meta.get("pushed_at"),
        "file_count": len(files),
        "total_size_bytes": total_size,
        "last_absorbed": datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
    }

    existing = s.get(repo_id)
    if existing:
        s.write({"id": repo_id, "foundation": "foundation:knowledge", "state": repo_state})
    else:
        s.write({
            "id": repo_id,
            "foundation": "foundation:knowledge",
            "state": repo_state,
        })
        # Link to james if james exists
        if s.get("james"):
            s.link("james", "owns", repo_id)

    # --- File capsules ---
    created = updated = skipped = 0
    for f in files:
        fid = f"file/{_slug(owner)}/{_slug(repo)}/{f['path']}"
        file_state = {
            "kind": "source-file",
            "source": "github",
            "repo": f"{owner}/{repo}",
            "repo_id": repo_id,
            "path": f["path"],
            "language": f["language"],
            "size_bytes": f["size"],
            "sha": f["sha"],
            "last_absorbed": repo_state["last_absorbed"],
        }

        ex = s.get(fid)
        if ex:
            if ex["state"].get("sha") == f["sha"]:
                skipped += 1
                continue
            s.write({"id": fid, "foundation": "foundation:knowledge", "state": file_state})
            updated += 1
        else:
            s.write({
                "id": fid,
                "foundation": "foundation:knowledge",
                "state": file_state,
            })
            s.link(repo_id, "contains", fid)
            created += 1

    print()
    print(f"Repo: {repo_id}")
    print(f"  files: {created} new, {updated} updated, {skipped} unchanged")
    return {
        "repo_id": repo_id,
        "files": len(files),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "dry_run": False,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Absorb a GitHub repo as capsules (metadata only)."
    )
    ap.add_argument("repo", help="GitHub repo as owner/name")
    ap.add_argument("--write", action="store_true",
                    help="write capsules (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="dry-run (default; explicit no-op for symmetry with absorb_repo.py)")
    args = ap.parse_args()

    if "/" not in args.repo:
        raise SystemExit("repo must be owner/name, e.g. octocat/Hello-World")
    owner, name = args.repo.split("/", 1)

    if not _token():
        print("WARNING: no GITHUB_TOKEN and no gh login: 60 req/hour, and no private repos.")
        print("  Run `gh auth login` once, or set GITHUB_TOKEN.")
        print()

    s = Substrate()
    result = absorb_github(s, owner, name, write=args.write and not args.dry_run)
    s.close()

    if "error" in result:
        print(f"error: {result['error']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
