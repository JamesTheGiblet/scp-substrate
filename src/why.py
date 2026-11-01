"""Explain a fact by walking back through the substrate."""
import json
from substrate import Substrate
from queries import trust_now


def why_trusted(s: Substrate, claim_id: str):
    chain = {"claim": claim_id}

    link = s.conn.execute("""
        SELECT source, target, metadata, created_at
        FROM links WHERE source=? AND type='trusted'
    """, (claim_id,)).fetchone()
    if not link:
        return {"claim": claim_id, "trusted": False}
    chain["derived_link"] = dict(link)

    live = trust_now(s, claim_id)
    if live:
        chain["score"] = {
            "model_id":           s.conn.execute(
                "SELECT model_id FROM trust_scores WHERE capsule_id=?",
                (claim_id,)
            ).fetchone()["model_id"],
            "score":              live["score"],
            "materialized_score": live["materialized_score"],
            "computed_at":        live["computed_at"],
            "elapsed_days":       live["elapsed_days"],
        }
        model = s.conn.execute(
            "SELECT id, state_json FROM capsules WHERE id=?",
            (chain["score"]["model_id"],)
        ).fetchone()
        chain["model"] = {
            "id":    model["id"],
            "state": json.loads(model["state_json"]),
        }
    else:
        chain["score"] = None
        chain["model"] = None

    about = s.conn.execute(
        "SELECT target FROM links WHERE source=? AND type='about'",
        (claim_id,)
    ).fetchone()
    chain["about"] = about["target"] if about else None

    rule = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE id='trusted-rule'"
    ).fetchone()
    chain["rule"] = {"id": rule["id"], "state": json.loads(rule["state_json"])}

    return chain


def print_chain(chain):
    if not chain.get("derived_link"):
        print(f"{chain['claim']} is NOT trusted.")
        return

    link  = chain["derived_link"]
    score = chain["score"] or {}
    model = chain.get("model") or {}
    rule  = chain.get("rule") or {}

    print(f"Why is {chain['claim']} trusted?")
    print(f"  → Because it has a 'trusted' link to '{link['target']}'")
    print(f"    (derived at {link['created_at']} by {rule.get('id', '?')})")
    print()
    threshold = rule.get("state", {}).get("condition", {}).get("threshold", "?")
    print(f"  → Which was fired because its trust score exceeded {threshold}")
    if score:
        print(f"    (current score = {score['score']:.6f}, "
              f"materialized {score['materialized_score']:.6f} "
              f"at {score['computed_at']}, "
              f"elapsed {score['elapsed_days']*86400:.1f}s)")
    print()
    if model:
        print(f"  → Which was computed by trust model '{model['id']}'")
        print(f"    (formula = {model['state'].get('formula', '?')})")
        print()
    print(f"  → About: {chain.get('about')}")
