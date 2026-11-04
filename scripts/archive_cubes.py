#!/usr/bin/env python3
"""Move every cube except James's own and the foundational ones into an archive db.

Kept: cubes tagged james, defining, principle or foundational, or none with
--keep-none. Everything else
under an archived cube's id (faces, proposals, validation drafts, attestation),
links touching it, overlap decisions, subject proposals and subjects naming it,
sources only archived cubes drew on,
trust scores and events go to archive/sc-archive-<date>.db, then leave sc.db.
The repo index and SymLM's language data are not touched.

Stop `kg cube serve` first, since its drafter writes to sc.db.

    python scripts/archive_cubes.py            # dry run, prints what would move
    python scripts/archive_cubes.py --write    # copy to the archive, then remove
    python scripts/archive_cubes.py --keep-none --write   # archive every cube
"""
import argparse, json, sqlite3, sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
SC_DB      = ROOT / "sc.db"
SCHEMA_SQL = ROOT / "schema.sql"
KEEP_TAGS  = {"james", "defining", "principle", "foundational"}


def _cubes(conn):
    rows = conn.execute("SELECT id, state_json FROM capsules WHERE foundation = 'foundation:cube'")
    return {cid: json.loads(st) for cid, st in rows}


def _under(cid, ids):
    return cid in ids or any(cid.startswith(a + "/") for a in ids)


def plan(conn, keep_tags=KEEP_TAGS):
    """Return (kept cube ids, archived cube ids, every capsule id to move)."""
    cubes = _cubes(conn)
    kept = {c for c, st in cubes.items() if keep_tags & set(st.get("tags") or [])}
    gone = set(cubes) - kept
    moving = set()
    for cid, st in conn.execute("SELECT id, state_json FROM capsules"):
        st = json.loads(st)
        if _under(cid, gone):
            moving.add(cid)
        # A link proposal stored under a kept cube that points at an archived one
        elif st.get("kind") == "cube-proposal" and st.get("other_cube_id") in gone:
            moving.add(cid)
        elif st.get("kind") == "overlap-decision" and {st.get("a"), st.get("b")} & gone:
            moving.add(cid)
        elif st.get("kind") == "subject-proposal" and set(st.get("members") or []) & gone:
            moving.add(cid)
    # A subject goes only when every claim about it goes
    for (subj,) in conn.execute("SELECT id FROM capsules WHERE foundation = 'foundation:subject'"):
        claims = {r[0] for r in conn.execute(
            "SELECT source FROM links WHERE target = ? AND type = 'about-subject'", (subj,))}
        if claims <= gone:
            moving.add(subj)
    # A source goes only when every cube drawing on it goes
    for (src,) in conn.execute("SELECT id FROM capsules WHERE id LIKE 'source/%'"):
        users = {r[0] for r in conn.execute(
            "SELECT source FROM links WHERE target = ? AND type = 'derived-from'", (src,))}
        if users and users <= gone:
            moving.add(src)
    return kept, gone, moving


def _rows(conn, table, where, ids):
    ph = ",".join("?" * len(ids))
    return conn.execute(f"SELECT * FROM {table} WHERE {where.format(ph=ph)}", list(ids) * where.count("{ph}")).fetchall()


def gather(conn, moving):
    ids = sorted(moving)
    return {
        "capsules":     _rows(conn, "capsules", "id IN ({ph})", ids),
        "links":        _rows(conn, "links", "source IN ({ph}) OR target IN ({ph})", ids),
        "events":       _rows(conn, "events", "capsule_id IN ({ph})", ids),
        "trust_scores": _rows(conn, "trust_scores", "capsule_id IN ({ph})", ids),
    }


def _archive_path():
    """archive/sc-archive-<date>.db, or -2, -3 and so on if that day has one."""
    base, n = f"sc-archive-{date.today().isoformat()}", 1
    path = ROOT / "archive" / f"{base}.db"
    while path.exists():
        n += 1
        path = ROOT / "archive" / f"{base}-{n}.db"
    return path


def write_archive(path, rows):
    if path.exists():
        sys.exit(f"error: {path} already exists, refusing to overwrite it")
    path.parent.mkdir(exist_ok=True)
    arc = sqlite3.connect(path)
    arc.executescript(SCHEMA_SQL.read_text())
    # Archived links still point at kept capsules such as default-cube, which
    # stay in sc.db, so foreign keys are off for the copy
    arc.execute("PRAGMA foreign_keys = OFF")
    with arc:
        for table, data in rows.items():
            if data:
                ph = ",".join("?" * len(data[0]))
                arc.executemany(f"INSERT INTO {table} VALUES ({ph})", data)
    for table, data in rows.items():
        n = arc.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        if n != len(data):
            arc.close()
            sys.exit(f"error: archive has {n} {table} rows, expected {len(data)}; sc.db not changed")
    arc.close()


def remove(conn, moving, rows, path, keep_tags):
    ids = sorted(moving)
    ph = ",".join("?" * len(ids))
    counts = {t: len(d) for t, d in rows.items()}
    with conn:
        conn.execute(f"DELETE FROM events WHERE capsule_id IN ({ph})", ids)
        conn.execute(f"DELETE FROM links WHERE source IN ({ph}) OR target IN ({ph})", ids * 2)
        conn.execute(f"DELETE FROM trust_scores WHERE capsule_id IN ({ph})", ids)
        conn.execute(f"DELETE FROM capsules WHERE id IN ({ph})", ids)
        conn.execute("INSERT INTO events (event_type, capsule_id, payload, occurred_at) VALUES (?, NULL, ?, ?)",
                     ("archive.moved", json.dumps({"archive": path.relative_to(ROOT).as_posix(),"kept_tags": sorted(keep_tags),
                                                   "counts": counts}),
                      datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="copy to the archive and remove from sc.db")
    ap.add_argument("--list", action="store_true", help="print every kept and archived cube id")
    ap.add_argument("--keep-none", action="store_true", help="archive every cube, whatever its tags")
    args = ap.parse_args()
    keep_tags = set() if args.keep_none else KEEP_TAGS

    conn = sqlite3.connect(SC_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    kept, gone, moving = plan(conn, keep_tags)
    rows = gather(conn, moving)

    print(f"cubes kept: {len(kept)}, archived: {len(gone)}")
    for table, data in rows.items():
        print(f"  {table:13} {len(data)}")
    if args.list:
        print("\nkept:");     [print("  " + c) for c in sorted(kept)]
        print("\narchived:"); [print("  " + c) for c in sorted(gone)]
    if not args.write:
        print("\ndry run, nothing changed. Add --write to archive.")
        return

    path = _archive_path()
    write_archive(path, rows)
    remove(conn, moving, rows, path, keep_tags)
    left = conn.execute("SELECT COUNT(*) FROM capsules WHERE foundation = 'foundation:cube'").fetchone()[0]
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    print(f"\narchived to {path.relative_to(ROOT)}; {left} cubes left in sc.db")


if __name__ == "__main__":
    main()
