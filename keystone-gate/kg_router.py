"""Neighbourhood-router.

Neighbours know only IDs and query the ledger for detail. The route list
shows which cubes have neighbour links and who they neighbour.
"""
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent))


def route_list():
    """Return [{cube, neighbours:[...]}] for all cubes with neighbour links.

    Empty list if no cube is linked to any other. Ordered by cube ID.
    """
    from substrate import Substrate
    s = Substrate()
    try:
        rows = s.conn.execute(
            "SELECT DISTINCT source FROM links WHERE type='neighbour' ORDER BY source"
        ).fetchall()
        out = []
        for r in rows:
            neighbours = [
                x["target"] for x in s.conn.execute(
                    "SELECT target FROM links WHERE source=? AND type='neighbour' ORDER BY target",
                    (r["source"],),
                )
            ]
            out.append({"cube": r["source"], "neighbours": neighbours})
        return out
    finally:
        s.close()
