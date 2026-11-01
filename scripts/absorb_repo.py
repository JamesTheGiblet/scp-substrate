"""Absorb a repository into the substrate as repo + file capsules.

Phase 1: metadata only. No content, no symbols, no imports.

Usage:
  python scripts/absorb_repo.py <path> --dry-run     # show what would happen
  python scripts/absorb_repo.py <path> --write       # actually write
  python scripts/absorb_repo.py <path>               # dry-run is default
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
import argparse
import re
import ast
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone

from substrate import Substrate

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", "venv", ".venv", "env", ".env",
    "target", "build", "dist", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".next", ".nuxt", ".cache", "legacy", ".DS_Store",
}

SKIP_FILE_EXTS = {
    # binaries
    ".pyc", ".pyo", ".so", ".dylib", ".dll", ".exe", ".o", ".a",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".ico", ".bmp",
    ".mp3", ".mp4", ".wav", ".mov", ".avi",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".woff", ".woff2", ".ttf", ".otf", ".eot",
    ".sqlite", ".db", ".db-wal", ".db-shm",
    # generated
    ".min.js", ".min.css", ".map", ".bak", ".bak.py",
}

LANG_BY_EXT = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".rb": "ruby",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".md": "markdown",
    ".txt": "text",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".svg": "svg",
}

MAX_FILE_BYTES = 500_000  # 500 KB
MAX_FILES_HARD = 10_000   # safety cap per repo


def _git_meta(repo_path):
    """Return {branch, head} if repo_path is a git repo, else {}."""
    try:
        branch = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        return {"git_branch": branch or None, "git_head": head or None}
    except Exception:
        return {}


def _should_skip_file(path, size):
    if size > MAX_FILE_BYTES:
        return True
    suffix = path.suffix.lower()
    if suffix in SKIP_FILE_EXTS:
        return True
    # .min.js etc
    if ".min." in path.name:
        return True
    return False


def _sha256(path, chunk=65536):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk_b := f.read(chunk):
            h.update(chunk_b)
    return h.hexdigest()


def _count_lines(path):
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return None


def _extract_python_symbols(path):
    """Top-level functions, classes, and class methods via ast."""
    try:
        tree = ast.parse(Path(path).read_text(errors="replace"))
    except (SyntaxError, OSError):
        return [], []

    symbols = []
    imports = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            symbols.append({
                "name": node.name,
                "kind": "function",
                "line": node.lineno,
                "docstring": (ast.get_docstring(node) or "")[:200],
            })
        elif isinstance(node, ast.ClassDef):
            symbols.append({
                "name": node.name,
                "kind": "class",
                "line": node.lineno,
                "docstring": (ast.get_docstring(node) or "")[:200],
            })
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({
                        "name": f"{node.name}.{sub.name}",
                        "kind": "method",
                        "line": sub.lineno,
                        "docstring": (ast.get_docstring(sub) or "")[:200],
                    })
    return symbols, imports


_JS_FUNC_RE = re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)", re.MULTILINE)
_JS_CLASS_RE = re.compile(r"^\s*(?:export\s+)?class\s+(\w+)", re.MULTILINE)
_JS_CONST_FN_RE = re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", re.MULTILINE)
_JS_IMPORT_RE = re.compile(r"^\s*import\s+(?:.*?)\s+from\s+['\"]([^'\"]+)['\"]", re.MULTILINE)


def _extract_js_symbols(path):
    """Regex-based function/class/const-fn extraction for JavaScript."""
    try:
        text = Path(path).read_text(errors="replace")
    except OSError:
        return [], []
    symbols = []
    for m in _JS_FUNC_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "function", "line": line, "docstring": ""})
    for m in _JS_CLASS_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "class", "line": line, "docstring": ""})
    for m in _JS_CONST_FN_RE.finditer(text):
        line = text[:m.start()].count("\n") + 1
        symbols.append({"name": m.group(1), "kind": "function", "line": line, "docstring": ""})
    imports = [m.group(1) for m in _JS_IMPORT_RE.finditer(text)]
    return symbols, imports


def _symbol_slug_from_path(rel_path):
    return rel_path.replace("/", "_").rsplit(".", 1)[0].replace(".", "-")


def _extract_symbols_for(lang, abs_path):
    if lang == "python":
        return _extract_python_symbols(abs_path)
    if lang in ("javascript", "typescript"):
        return _extract_js_symbols(abs_path)
    return [], []


def walk_repo(root):
    """Yield (rel_path, abs_path, size, language) for files we want to absorb."""
    root = root.resolve()
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skip dirs in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]

        for fn in filenames:
            abs_p = Path(dirpath) / fn
            try:
                size = abs_p.stat().st_size
            except OSError:
                continue
            if _should_skip_file(abs_p, size):
                continue
            rel = abs_p.relative_to(root)
            lang = LANG_BY_EXT.get(abs_p.suffix.lower(), "unknown")
            yield (str(rel), abs_p, size, lang)
            count += 1
            if count >= MAX_FILES_HARD:
                print(f"  warning: hit MAX_FILES_HARD={MAX_FILES_HARD}; stopping")
                return


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def absorb(s, root, write=False):
    root = root.resolve()
    if not root.exists():
        return {"error": f"not found: {root}"}
    if not root.is_dir():
        return {"error": f"not a directory: {root}"}

    repo_name = root.name
    repo_id = f"repo/{_slug(repo_name)}"

    # Collect files
    print(f"Scanning {root}")
    files = list(walk_repo(root))
    if not files:
        return {"error": "no files to absorb"}

    total_size = sum(f[2] for f in files)
    languages = sorted({f[3] for f in files if f[3] != "unknown"})
    primary = None
    if languages:
        # count by language
        from collections import Counter
        lang_counts = Counter(f[3] for f in files if f[3] != "unknown")
        primary = lang_counts.most_common(1)[0][0] if lang_counts else None

    print(f"  {len(files)} files, {total_size:,} bytes")
    print(f"  languages: {', '.join(languages)}")
    print(f"  primary: {primary}")

    git_meta = _git_meta(root)
    if git_meta.get("git_branch"):
        print(f"  git: {git_meta['git_branch']} @ {git_meta['git_head'][:8]}")

    if not write:
        print()
        print("(dry-run — no capsules written)")
        print("  would create repo capsule:", repo_id)
        print(f"  would create/update {len(files)} file capsules")
        print(f"  would link {repo_id} --contains--> each file")
        print()
        print("Re-run with --write to actually absorb.")
        return {
            "repo_id": repo_id,
            "files": len(files),
            "languages": languages,
            "primary": primary,
            "dry_run": True,
        }

    # Write
    s_conn = s.conn

    # --- Repo capsule ---
    repo_state = {
        "kind": "repo",
        "name": repo_name,
        "path": str(root),
        "languages": languages,
        "primary_language": primary,
        "file_count": len(files),
        "size_bytes": total_size,
        "last_modified": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if git_meta.get("git_branch"):
        repo_state["git_branch"] = git_meta["git_branch"]
    if git_meta.get("git_head"):
        repo_state["git_head"] = git_meta["git_head"]

    existing = s.get(repo_id)
    if existing:
        with s_conn:
            s_conn.execute(
                "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                (json.dumps(repo_state), repo_id),
            )
    else:
        s.write({"id": repo_id, "foundation": "foundation:knowledge", "state": repo_state})
        # james owns this repo
        try:
            s.link("james", "owns", repo_id)
        except Exception:
            pass

    # --- File capsules ---
    created = updated = skipped = 0
    for rel, abs_p, size, lang in files:
        fid = f"file/{_slug(repo_name)}/{rel}"
        try:
            sha = _sha256(abs_p)
        except OSError:
            continue
        file_state = {
            "kind": "source-file",
            "repo": repo_name,
            "repo_id": repo_id,
            "path": rel,
            "abs_path": str(abs_p),
            "language": lang,
            "size_bytes": size,
            "sha256": sha,
            "lines": _count_lines(abs_p),
            "last_modified": datetime.fromtimestamp(
                abs_p.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        ex = s.get(fid)
        if ex:
            # Only update if hash changed
            if ex["state"].get("sha256") == sha:
                skipped += 1
                continue
            with s_conn:
                s_conn.execute(
                    "UPDATE capsules SET state_json=?, updated_at=datetime('now') WHERE id=?",
                    (json.dumps(file_state), fid),
                )
            updated += 1
        else:
            s.write({"id": fid, "foundation": "foundation:knowledge", "state": file_state})
            s.link(repo_id, "contains", fid)
            created += 1

    # --- Symbol capsules ---
    sym_created = sym_skipped = 0
    for rel, abs_p, size, lang in files:
        symbols, imports = _extract_symbols_for(lang, abs_p)
        if not symbols and not imports:
            continue
        fid = f"file/{_slug(repo_name)}/{rel}"
        path_slug = _symbol_slug_from_path(rel)

        # Store imports on the file capsule
        if imports:
            cur = s.get(fid)
            if cur:
                cur_state = dict(cur["state"])
                if cur_state.get("imports") != imports:
                    cur_state["imports"] = imports
                    with s_conn:
                        s_conn.execute(
                            "UPDATE capsules SET state_json=? WHERE id=?",
                            (json.dumps(cur_state), fid),
                        )

        for sym in symbols:
            sid = f"symbol/{_slug(repo_name)}/{path_slug}/{sym['name']}"
            existing_sym = s.get(sid)
            if existing_sym:
                sym_skipped += 1
                continue
            s.write({
                "id": sid,
                "foundation": "foundation:knowledge",
                "state": {
                    "kind": "symbol",
                    "name": sym["name"],
                    "symbol_kind": sym["kind"],
                    "line": sym["line"],
                    "docstring": sym["docstring"],
                    "repo": repo_name,
                    "file": rel,
                    "file_id": fid,
                    "language": lang,
                },
            })
            s.link(fid, "defines", sid)
            sym_created += 1

    print()
    print(f"Repo: {repo_id}")
    print(f"  files: {created} new, {updated} updated, {skipped} unchanged")
    print(f"  symbols: {sym_created} new, {sym_skipped} already present")
    return {
        "repo_id": repo_id,
        "files": len(files),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "symbols_created": sym_created,
        "dry_run": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="path to repo")
    ap.add_argument("--write", action="store_true",
                    help="actually write (default is dry-run)")
    ap.add_argument("--dry-run", action="store_true",
                    help="dry-run (default)")
    args = ap.parse_args()

    root = Path(args.path)
    s = Substrate()
    result = absorb(s, root, write=args.write and not args.dry_run)
    s.close()

    if "error" in result:
        print(f"error: {result['error']}")
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
