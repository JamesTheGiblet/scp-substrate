"""Walkers: one function per kind of question, each a walk over the graph."""
import json
import re


def extract_kind(s, text):
    """For 'list all decisions' → 'decision'."""
    tokens = [t for t in re.findall(r"[a-z]+", text.lower()) if len(t) >= 3]
    rows = s.conn.execute("""
        SELECT DISTINCT json_extract(state_json, '$.kind') AS kind
        FROM capsules WHERE is_meta = 0
          AND json_extract(state_json, '$.kind') IS NOT NULL
    """).fetchall()
    known_kinds = {r["kind"] for r in rows if r["kind"]}
    for t in tokens:
        # Singular/plural
        for candidate in (t, t.rstrip("s")):
            if candidate in known_kinds:
                return candidate
            if candidate + "s" in known_kinds:
                return candidate + "s"
    return None


# --- walkers ------------------------------------------------------------
def _walk_why_trusted(s, entity_id, text):
    from why import why_trusted
    chain = why_trusted(s, entity_id)
    if not chain.get("derived_link"):
        return {"ok": False,
                "summary": f"{entity_id} is not currently trusted.",
                "detail": None}
    score = chain.get("score") or {}
    link = chain["derived_link"]
    rule = chain.get("rule") or {}
    model = chain.get("model") or {}
    lines = [
        f"  score: {score.get('score', 0):.6f} "
        f"(materialized {score.get('materialized_score', 0):.6f})",
        f"  derived by: {rule.get('id', '?')} at {link.get('created_at', '?')}",
        f"  model: {model.get('id', '?')}",
    ]
    return {
        "ok": True,
        "summary": (f"{entity_id} is trusted (score {score.get('score', 0):.4f}) "
                    f"via a 'trusted' link to '{link['target']}', "
                    f"fired by {rule.get('id', '?')}."),
        "detail": chr(10).join(lines),
    }


def _walk_verified(s, entity_id, text):
    from queries import verified as qverified
    records = qverified(s, entity_id)
    if not records:
        return {"ok": True,
                "summary": f"{entity_id} has no verification records.",
                "detail": None}
    lines = [f"  {r['valid'] and 'valid' or 'invalid'} by {r['key_id'][:32]}... "
             f"at {r['at']}" for r in records]
    return {"ok": True,
            "summary": f"{entity_id} has {len(records)} verification(s).",
            "detail": "\n".join(lines)}


def _walk_what_decided(s, entity_id, text):
    # If entity given, find decisions about it; else list all decisions
    if entity_id:
        rows = s.conn.execute("""
            SELECT c.id, c.state_json FROM capsules c
            JOIN links l ON l.source = c.id
            WHERE l.type = 'about' AND l.target = ?
              AND json_extract(c.state_json, '$.kind') = 'decision'
        """, (entity_id,)).fetchall()
    else:
        # Search by topic word
        tokens = [t for t in re.findall(r"[a-z]+", text.lower()) if len(t) >= 3]
        rows = []
        for r in s.conn.execute("""
            SELECT id, state_json FROM capsules
            WHERE json_extract(state_json, '$.kind') = 'decision'
        """):
            state = json.loads(r["state_json"])
            blob = json.dumps(state).lower()
            if any(t in blob for t in tokens):
                rows.append(r)
        if not rows:
            # Fall back to all decisions
            rows = s.conn.execute("""
                SELECT id, state_json FROM capsules
                WHERE json_extract(state_json, '$.kind') = 'decision'
            """).fetchall()

    if not rows:
        return {"ok": True,
                "summary": "No decisions found matching that.",
                "detail": None}

    summaries = []
    for r in rows:
        state = json.loads(r["state_json"]) if isinstance(r["state_json"], str) else r["state_json"]
        summary = (f"  {r['id']}: {state.get('decision', '?')} "
                   f"(by {state.get('decided_by', '?')}, {state.get('date', '?')})")
        summaries.append(summary)
    return {"ok": True,
            "summary": f"Found {len(rows)} decision(s):",
            "detail": "\n".join(summaries)}


def _walk_what_uses(s, entity_id, text):
    if not entity_id:
        entity_id = "james"
    links = [l for l in s.links_from(entity_id) if l["type"] == "uses"]
    if not links:
        return {"ok": True,
                "summary": f"{entity_id} has no recorded 'uses' links.",
                "detail": None}
    lines = []
    for l in links:
        c = s.get(l["target"])
        name = c["state"].get("name") if c else l["target"]
        cat = c["state"].get("category") if c else "?"
        lines.append(f"  {l['target']} ({cat})")
    return {"ok": True,
            "summary": f"{entity_id} uses {len(links)} tool(s):",
            "detail": "\n".join(lines)}


def _walk_what_building(s, entity_id, text):
    if not entity_id:
        entity_id = "james"
    links = [l for l in s.links_from(entity_id) if l["type"] == "building"]
    if not links:
        return {"ok": True,
                "summary": f"{entity_id} has no recorded 'building' links.",
                "detail": None}
    lines = []
    for l in links:
        c = s.get(l["target"])
        status = c["state"].get("status", "?") if c else "?"
        lines.append(f"  {l['target']} ({status})")
    return {"ok": True,
            "summary": f"{entity_id} is building {len(links)} project(s):",
            "detail": "\n".join(lines)}


def _walk_what_supports(s, entity_id, text):
    from queries import what_supports
    if not entity_id:
        return {"ok": False, "summary": "No claim specified.", "detail": None}
    rows = what_supports(s, entity_id)
    if not rows:
        return {"ok": True,
                "summary": f"No direct supporting links for {entity_id}.",
                "detail": None}
    lines = [f"  {r['id']} ({r['foundation'].replace('foundation:', '')})"
             for r in rows]
    return {"ok": True,
            "summary": f"{len(rows)} supporting item(s) for {entity_id}:",
            "detail": "\n".join(lines)}


def _walk_list_kind(s, entity_id, text):
    kind = extract_kind(s, text)
    if not kind:
        # List all distinct kinds present
        rows = s.conn.execute("""
            SELECT json_extract(state_json, '$.kind') AS kind, COUNT(*) AS n
            FROM capsules WHERE is_meta = 0
              AND json_extract(state_json, '$.kind') IS NOT NULL
            GROUP BY kind ORDER BY n DESC
        """).fetchall()
        lines = [f"  {r['kind']:25} {r['n']}" for r in rows]
        return {"ok": True,
                "summary": "Available kinds:",
                "detail": "\n".join(lines)}

    rows = s.conn.execute("""
        SELECT id FROM capsules WHERE is_meta = 0
          AND json_extract(state_json, '$.kind') = ?
        ORDER BY id
    """, (kind,)).fetchall()
    if not rows:
        return {"ok": True,
                "summary": f"No capsules with kind '{kind}'.",
                "detail": None}
    lines = [f"  {r['id']}" for r in rows]
    return {"ok": True,
            "summary": f"{len(rows)} capsule(s) of kind '{kind}':",
            "detail": "\n".join(lines)}


def _walk_what_happened(s, entity_id, text):
    # Try to find a session or date capsule mentioned
    if entity_id:
        c = s.get(entity_id)
        if c and c["state"].get("kind") == "session":
            return _render_session(s, entity_id, c["state"])
    # Fall back: most recent sessions
    rows = s.conn.execute("""
        SELECT id, state_json FROM capsules
        WHERE json_extract(state_json, '$.kind') = 'session'
        ORDER BY id DESC LIMIT 3
    """).fetchall()
    if not rows:
        return {"ok": True,
                "summary": "No sessions recorded.",
                "detail": None}
    lines = []
    for r in rows:
        st = json.loads(r["state_json"])
        lines.append(f"  {r['id']}: {st.get('outcome', '?')[:80]}")
    return {"ok": True,
            "summary": f"{len(rows)} most recent session(s):",
            "detail": "\n".join(lines)}


def _render_session(s, session_id, state):
    touched = [l["target"] for l in s.links_from(session_id) if l["type"] == "touched"]
    lines = [f"  Date: {state.get('date', '?')}",
             f"  Outcome: {state.get('outcome', '?')}"]
    if touched:
        lines.append(f"  Touched: {', '.join(touched)}")
    return {"ok": True,
            "summary": f"Session {session_id}:",
            "detail": "\n".join(lines)}


def _walk_where_is(s, entity_id, text):
    """Find symbols or files matching the name in the query."""
    import re as _re
    skip = {"where", "is", "find", "function", "class", "locate",
            "the", "a", "an", "show", "me"}
    tokens = [t for t in _re.findall(r"[a-zA-Z0-9_]+", text.lower())
              if len(t) >= 2 and t not in skip]
    if not tokens:
        return {"ok": False, "summary": "No name given to search for.",
                "detail": None}

    results = []
    for token in tokens:
        rows = s.conn.execute("""
            SELECT id, state_json FROM capsules
            WHERE json_extract(state_json, '$.kind') = 'symbol'
              AND lower(json_extract(state_json, '$.name')) LIKE ?
            LIMIT 20
        """, (f"%{token}%",)).fetchall()
        for r in rows:
            st = json.loads(r["state_json"])
            results.append((st.get("file", "?"),
                            st.get("line", "?"),
                            st.get("name", "?"),
                            st.get("symbol_kind", "?")))

    seen = set()
    unique = []
    for r in results:
        if r not in seen:
            seen.add(r)
            unique.append(r)

    if not unique:
        # Fall back to file path search
        rows = s.conn.execute("""
            SELECT json_extract(state_json, '$.path') AS path,
                   json_extract(state_json, '$.language') AS lang
            FROM capsules
            WHERE json_extract(state_json, '$.kind') = 'source-file'
        """).fetchall()
        for r in rows:
            if r["path"] and any(t in r["path"].lower() for t in tokens):
                unique.append((r["path"], None, None, r["lang"]))
        if not unique:
            return {"ok": True,
                    "summary": f"Nothing matching {tokens} in symbols or files.",
                    "detail": None}
        lines = [f"  {f[0]}  ({f[3]})" for f in unique[:20]]
        return {"ok": True,
                "summary": f"{len(unique)} file(s) match:",
                "detail": chr(10).join(lines)}

    lines = []
    for path, line, name, kind in unique[:20]:
        loc = f"{path}:{line}" if line is not None else path
        n = f" [{kind}] {name}" if name else ""
        lines.append(f"  {loc}{n}")
    return {"ok": True,
            "summary": f"{len(unique)} match(es):",
            "detail": chr(10).join(lines)}


def _walk_what_files(s, entity_id, text):
    """List files contained in a repo."""
    if not entity_id:
        return {"ok": False, "summary": "No repo specified.", "detail": None}
    c = s.get(entity_id)
    if not c or c["state"].get("kind") != "repo":
        return {"ok": True,
                "summary": f"{entity_id} is not a repo.",
                "detail": None}
    links = [l for l in s.links_from(entity_id) if l["type"] == "contains"]
    if not links:
        return {"ok": True,
                "summary": f"{entity_id} contains no recorded files.",
                "detail": None}
    lines = [f"  {l['target']}" for l in links[:25]]
    if len(links) > 25:
        lines.append(f"  ... and {len(links) - 25} more")
    return {"ok": True,
            "summary": f"{len(links)} file(s) in {entity_id}:",
            "detail": chr(10).join(lines)}


def _walk_who_is(s, entity_id, text):
    return _walk_what_is(s, entity_id, text)


def _walk_what_is(s, entity_id, text):
    from explain import explain
    if not entity_id:
        return {"ok": False, "summary": "Nothing identified to describe.", "detail": None}
    c = s.get(entity_id)
    if not c:
        return {"ok": True,
                "summary": f"Nothing called '{entity_id}' in the substrate.",
                "detail": None}
    # Short summary from explain; full detail available via `scps explain`
    lines = explain(s, entity_id).split("\n")[:6]
    return {"ok": True,
            "summary": f"{entity_id}:",
            "detail": "\n".join(lines)}


WALKERS = {
    "why_trusted": _walk_why_trusted,
    "verified": _walk_verified,
    "what_decided": _walk_what_decided,
    "what_uses": _walk_what_uses,
    "what_building": _walk_what_building,
    "what_supports": _walk_what_supports,
    "list_kind": _walk_list_kind,
    "what_happened": _walk_what_happened,
    "who_is": _walk_who_is,
    "where_is": _walk_where_is,
    "what_files": _walk_what_files,
    "what_is": _walk_what_is,
}
