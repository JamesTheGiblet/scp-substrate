import json, math, sqlite3
from pathlib import Path

class Substrate:
    def __init__(self, db_path=None):
        self.db_path = db_path or str(Path(__file__).parent / "sc.db")
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        # Leighton decay: N(t) = N0 * e^(-k*t), t in days
        self.conn.create_function(
            "decay_weight", 3,
            lambda n0, k, t: n0 * math.exp(-k * t) if (n0 is not None and k is not None and t is not None) else None
        )

    def get(self, capsule_id):
        row = self.conn.execute(
            "SELECT id, foundation, state_json, is_meta FROM capsules WHERE id = ?",
            (capsule_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "id":         row["id"],
            "foundation": row["foundation"],
            "state":      json.loads(row["state_json"]),
            "is_meta":    bool(row["is_meta"]),
            "links":      self.links_from(row["id"]),
        }

    def links_from(self, capsule_id):
        return [dict(r) for r in self.conn.execute(
            "SELECT type, target, metadata FROM links WHERE source = ?",
            (capsule_id,)
        )]

    def links_to(self, capsule_id, type_=None):
        q = "SELECT source, type, metadata FROM links WHERE target = ?"
        args = [capsule_id]
        if type_:
            q += " AND type = ?"
            args.append(type_)
        return [dict(r) for r in self.conn.execute(q, args)]

    def by_foundation(self, foundation_id):
        return [self.get(r["id"]) for r in self.conn.execute(
            "SELECT id FROM capsules WHERE foundation = ? AND is_meta = 0",
            (foundation_id,)
        )]

    def write(self, capsule):
        if capsule["id"].startswith("foundation:") or capsule.get("is_meta"):
            raise ValueError("foundations are written via sc.json; run bootstrap.py")
        with self.conn:
            self.conn.execute("""
                INSERT INTO capsules (id, foundation, state_json)
                VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    state_json = excluded.state_json,
                    updated_at = datetime('now')
            """, (capsule["id"], capsule["foundation"], json.dumps(capsule.get("state", {}))))
            self.conn.execute("""
                INSERT INTO events (event_type, capsule_id, payload)
                VALUES ('capsule.written', ?, ?)
            """, (capsule["id"], json.dumps({"foundation": capsule["foundation"]})))

    def link(self, source, type_, target):
        with self.conn:
            self.conn.execute("""
                INSERT OR IGNORE INTO links (source, type, target)
                VALUES (?, ?, ?)
            """, (source, type_, target))
            self.conn.execute("""
                INSERT INTO events (event_type, capsule_id, payload)
                VALUES ('link.added', ?, ?)
            """, (source, json.dumps({"type": type_, "target": target})))

    def supersede(self, old_id, new_id, new_state):
        """Create new_id as a version of old_id."""
        old = self.conn.execute(
            "SELECT foundation FROM capsules WHERE id=?", (old_id,)
        ).fetchone()
        if not old:
            raise ValueError(f"{old_id} not found")
        with self.conn:
            self.conn.execute("""
                INSERT INTO capsules (id, foundation, state_json, is_meta)
                VALUES (?, ?, ?, 0)
            """, (new_id, old["foundation"], json.dumps(new_state)))
            self.conn.execute("""
                INSERT OR IGNORE INTO links (source, type, target)
                VALUES (?, 'supersedes', ?)
            """, (new_id, old_id))
            self.conn.execute("""
                UPDATE capsules
                SET state_json = json_set(state_json, '$.superseded_by', ?),
                    updated_at = datetime('now')
                WHERE id = ?
            """, (new_id, old_id))
            self.conn.execute("""
                INSERT INTO events (event_type, capsule_id, payload)
                VALUES ('capsule.superseded', ?, ?)
            """, (old_id, json.dumps({"new_id": new_id})))

    def close(self):
        self.conn.close()
