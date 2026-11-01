"""Neighbourhood-router. Stub.

Neighbours know only IDs and query the ledger for detail.
Implementation deferred until boundary is proven stable.
"""

def route_list():
    """Return all neighbour capsule IDs."""
    from substrate import Substrate
    s = Substrate()
    try:
        rows = s.conn.execute(
            "SELECT id FROM capsules WHERE foundation = 'foundation:neighbour' AND is_meta = 0 ORDER BY id"
        ).fetchall()
        return [r["id"] for r in rows]
    finally:
        s.close()
