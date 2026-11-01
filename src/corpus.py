"""Query corpus sentences from the substrate."""


def load_corpus(s):
    """Return list of {id, text} for every corpus-sentence capsule."""
    rows = s.conn.execute("""
        SELECT id, json_extract(state_json, '$.text') AS text
        FROM capsules
        WHERE foundation = 'foundation:knowledge'
          AND json_extract(state_json, '$.kind') = 'corpus-sentence'
        ORDER BY id
    """).fetchall()
    return [{"id": r["id"], "text": r["text"]} for r in rows]
