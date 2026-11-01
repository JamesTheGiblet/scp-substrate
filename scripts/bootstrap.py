#!/usr/bin/env python3
"""Project sc.json into sc.db; import legacy capsules. Drift-tolerant."""
import hashlib, json, sqlite3, sys
from pathlib import Path

ROOT       = Path(__file__).resolve().parent.parent
SC_JSON    = ROOT / "sc.json"
SC_DB      = ROOT / "sc.db"
SCHEMA_SQL = ROOT / "schema.sql"
LEGACY_CAP = ROOT / "capsules"
DRIFT_FILE = ROOT / "drift-report.txt"

def init_db(conn):
    # Only create the schema if the DB is empty. Schema changes go through
    # numbered migrations, not silent recreation. This makes bootstrap
    # re-runnable against an existing sc.db.
    exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='capsules'"
    ).fetchone()
    if exists:
        return
    conn.executescript(SCHEMA_SQL.read_text())

def project_foundations(conn, version, foundations):
    with conn:
        for f in foundations:
            conn.execute("""
                INSERT INTO capsules (id, foundation, state_json, is_meta)
                VALUES (?, 'foundation:foundation', ?, 1)
                ON CONFLICT(id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = datetime('now')
            """, (f["id"], json.dumps(f["state"])))

        kept = [f["id"] for f in foundations]
        ph = ",".join("?" * len(kept))
        conn.execute(f"""
            UPDATE capsules
            SET state_json = json_set(state_json, '$.deprecated', json('true'))
            WHERE is_meta = 1 AND id NOT IN ({ph})
        """, kept)

        conn.execute("""
            DELETE FROM links
            WHERE source IN (SELECT id FROM capsules WHERE is_meta = 1)
        """)
        for f in foundations:
            for l in f.get("links", []):
                if isinstance(l, str):
                    l = {"type": "related-to", "target": l}
                conn.execute("""
                    INSERT OR IGNORE INTO links (source, type, target, metadata)
                    VALUES (?, ?, ?, ?)
                """, (f["id"], l["type"], l["target"], json.dumps(l.get("metadata", {}))))

        h = hashlib.sha256(SC_JSON.read_bytes()).hexdigest()
        conn.execute("""
            INSERT INTO events (event_type, payload) VALUES ('foundation.reloaded', ?)
        """, (json.dumps({"version": version, "hash": h, "count": len(foundations)}),))

def import_legacy_capsules(conn, foundation_names):
    if not LEGACY_CAP.exists():
        return [], 0, 0, 0
    n_existing = conn.execute(
        "SELECT COUNT(*) FROM capsules WHERE is_meta = 0"
    ).fetchone()[0]
    if n_existing:
        print(f"  skipped: {n_existing} instance capsules already in sc.db")
        return [], 0, 0, 0

    issues = []
    n_caps = 0

    # Pass 1: insert instance capsules
    with conn:
        for p in sorted(LEGACY_CAP.glob("*.json")):
            c = json.loads(p.read_text())
            foundation = c["foundation"]
            if not foundation.startswith("foundation:"):
                foundation = f"foundation:{foundation}"
            state = c.get("state", {})
            if "kind" in c:
                state = {**state, "kind": c["kind"]}
            conn.execute("""
                INSERT INTO capsules (id, foundation, state_json, is_meta)
                VALUES (?, ?, ?, 0)
            """, (c["id"], foundation, json.dumps(state)))
            conn.execute("""
                INSERT INTO events (event_type, capsule_id, payload)
                VALUES ('capsule.imported', ?, ?)
            """, (c["id"], json.dumps({"source": str(p)})))
            n_caps += 1

    instance_ids = set(r[0] for r in conn.execute(
        "SELECT id FROM capsules WHERE is_meta = 0"
    ))

    # Pass 2: insert links with resolution
    n_links, n_skipped = 0, 0
    with conn:
        for p in sorted(LEGACY_CAP.glob("*.json")):
            c = json.loads(p.read_text())
            for raw in c.get("links", []):
                if isinstance(raw, str):
                    target_raw, type_raw, metadata = raw, "related-to", {}
                    issues.append(f"UNTYPED  {c['id']} → {raw} (as 'related-to')")
                elif isinstance(raw, dict):
                    target_raw = raw.get("target")
                    type_raw   = raw.get("type", "related-to")
                    metadata   = raw.get("metadata", {})
                else:
                    issues.append(f"MALFORMED  {c['id']}: {raw!r}")
                    n_skipped += 1
                    continue

                if target_raw is None:
                    issues.append(f"MALFORMED  {c['id']}: {raw!r}")
                    n_skipped += 1
                    continue

                if target_raw in instance_ids:
                    target = target_raw
                elif target_raw.startswith("foundation:"):
                    target = target_raw
                elif target_raw in foundation_names:
                    target = f"foundation:{target_raw}"
                else:
                    issues.append(f"DANGLING  {c['id']} → {target_raw}")
                    n_skipped += 1
                    continue

                conn.execute("""
                    INSERT OR IGNORE INTO links (source, type, target, metadata)
                    VALUES (?, ?, ?, ?)
                """, (c["id"], type_raw, target, json.dumps(metadata)))
                n_links += 1

    return issues, n_caps, n_links, n_skipped

def drift_report(conn, issues):
    lines = []
    lines.append("=== DRIFT REPORT ===\n")

    missing_f = conn.execute("""
        SELECT DISTINCT foundation FROM capsules
        WHERE is_meta = 0
          AND foundation NOT IN (SELECT id FROM capsules WHERE is_meta = 1)
    """).fetchall()
    if missing_f:
        lines.append("Capsules referencing missing foundations:")
        for r in missing_f:
            ids = [x[0] for x in conn.execute(
                "SELECT id FROM capsules WHERE foundation = ?", (r[0],)
            )]
            lines.append(f"  {r[0]}")
            for cid in ids:
                lines.append(f"    - {cid}")
        lines.append("")

    if issues:
        lines.append("Link import issues:")
        for i in issues:
            lines.append(f"  {i}")
        lines.append("")

    report = "\n".join(lines)
    DRIFT_FILE.write_text(report)
    print(report)

def main():
    if not SC_JSON.exists():
        sys.exit(f"missing {SC_JSON} — write the constitution first")
    data = json.loads(SC_JSON.read_text())
    version, foundations = data["version"], data["foundations"]
    print(f"sc.json v{version}: {len(foundations)} foundations")

    foundation_names = set(
        f["id"].replace("foundation:", "", 1) for f in foundations
    )

    conn = sqlite3.connect(SC_DB)
    try:
        init_db(conn)
        project_foundations(conn, version, foundations)
        print(f"  projected {len(foundations)} foundations")
        issues, n_caps, n_links, n_skipped = import_legacy_capsules(conn, foundation_names)
        print(f"  imported {n_caps} capsules, {n_links} links, skipped {n_skipped}")
        drift_report(conn, issues)
    finally:
        conn.close()
    print(f"\nbootstrap complete → {SC_DB}")

if __name__ == "__main__":
    main()
