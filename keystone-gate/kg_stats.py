"""Statistics about Keystone Gate content in the substrate.

Pure substrate-side querying — proves the boundary works before any logic is built.
"""
from substrate import Substrate


def count_by_foundation(s, foundation_id):
    return s.conn.execute(
        "SELECT COUNT(*) FROM capsules WHERE foundation = ? AND is_meta = 0",
        (foundation_id,),
    ).fetchone()[0]


def stats():
    s = Substrate()
    try:
        return {
            "cubes":      count_by_foundation(s, "foundation:cube"),
            "lenses":     count_by_foundation(s, "foundation:lens"),
            "cube_faces": count_by_foundation(s, "foundation:cube-face"),
            "neighbours": count_by_foundation(s, "foundation:neighbour"),
        }
    finally:
        s.close()
