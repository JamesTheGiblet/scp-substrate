"""DB-native trust computation. Reads leighton-weight capsules, materialises scores."""
import json
import math
from datetime import datetime, timezone

from substrate import Substrate


FOUNDATION = "foundation:leighton-weight"
DEFAULT_MODEL = "default-trust-model"


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _load_weight_capsules(s):
    """Return (models, instances) split by numeric vs descriptive n0/k."""
    models, instances = [], []
    for r in s.conn.execute(
        "SELECT id, state_json, created_at FROM capsules WHERE foundation = ?",
        (FOUNDATION,)
    ):
        # Word and rule tallies share the foundation but are counts, not trust
        if r["id"].startswith("trust/freq/"):
            continue
        state = json.loads(r["state_json"])
        if _is_number(state.get("n0")) and _is_number(state.get("k")):
            instances.append({"id": r["id"], "state": state, "created_at": r["created_at"]})
        elif "formula" in state or not _is_number(state.get("n0")):
            models.append({"id": r["id"], "state": state})
    return models, instances


def _pick_model(s, instance_id, models):
    """Explicit link wins; else DEFAULT_MODEL; else first model."""
    if not models:
        return None
    link = s.conn.execute("""
        SELECT target FROM links
        WHERE source = ? AND type IN ('uses-model', 'uses')
    """, (instance_id,)).fetchone()
    if link:
        return link["target"]
    for m in models:
        if m["id"] == DEFAULT_MODEL:
            return DEFAULT_MODEL
    return models[0]["id"]


def _age_days(state, created_at):
    """Explicit age_days wins; else compute from created_at."""
    if _is_number(state.get("age_days")):
        return float(state["age_days"])
    try:
        created = datetime.fromisoformat(created_at.replace(" ", "T"))
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return max(0.0, (now - created).total_seconds() / 86400.0)
    except Exception:
        return 0.0


def decay_weight(n0, k, t_days):
    """N(t) = N0 * e^(-k*t), t in days."""
    return n0 * math.exp(-k * t_days)


def compute_all(s: Substrate):
    """Compute every trust instance. Idempotent. Logs 'trust.computed' on change."""
    models, instances = _load_weight_capsules(s)
    if not models:
        return {"computed": 0, "skipped": 0, "warnings": ["no trust model found"]}
    if not instances:
        return {"computed": 0, "skipped": 0, "warnings": ["no trust instances found"]}

    computed, skipped = 0, 0
    warnings = []

    for inst in instances:
        model_id = _pick_model(s, inst["id"], models)
        if not model_id:
            warnings.append(f"{inst['id']}: no model available")
            skipped += 1
            continue

        n0 = float(inst["state"]["n0"])
        k = float(inst["state"]["k"])
        t = _age_days(inst["state"], inst["created_at"])
        score = decay_weight(n0, k, t)

        with s.conn:
            prev = s.conn.execute(
                "SELECT score FROM trust_scores WHERE capsule_id = ? AND model_id = ?",
                (inst["id"], model_id)
            ).fetchone()
            prev_score = prev["score"] if prev else None

            s.conn.execute("""
                INSERT INTO trust_scores (capsule_id, model_id, score, computed_at)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(capsule_id, model_id) DO UPDATE SET
                    score = excluded.score,
                    computed_at = excluded.computed_at
            """, (inst["id"], model_id, score))

            if prev_score is None or abs(prev_score - score) > 1e-9:
                s.conn.execute("""
                    INSERT INTO events (event_type, capsule_id, payload)
                    VALUES ('trust.computed', ?, ?)
                """, (inst["id"], json.dumps({
                    "model": model_id,
                    "n0": n0, "k": k, "t_days": t,
                    "score": score, "prev": prev_score,
                })))
                computed += 1
            else:
                skipped += 1

    return {"computed": computed, "skipped": skipped,
            "warnings": warnings, "instances": len(instances)}


# ---------------------------------------------------------------------------
# Evidence-based trust
#
# The current compute_all reads n0, k, t from a trust instance's own state.
# That is trust the instance *asserts about itself*.
#
# trust_from_evidence walks the substrate instead: find observations that
# target the claim, sum their scores, decay each by the model's k. That is
# trust the substrate can *show*, not trust the instance can *claim*.
# ---------------------------------------------------------------------------


def trust_from_evidence(s: Substrate, capsule_id: str):
    """Aggregate evidence (observations + verifications) about a capsule.

    Two shapes supported:
      1. Trust instance (has `about → claim` and numeric `k` in state):
         score evidence pointing at `claim`, decayed by `k`.
      2. Knowledge capsule (no `about` link, no numeric `k`):
         score evidence pointing at the capsule itself, no decay (k=0).
    """
    instance = s.get(capsule_id)
    if not instance:
        return {"error": f"{capsule_id} not found"}

    about = [l for l in instance["links"] if l["type"] == "about"]
    if about:
        claim_id = about[0]["target"]
        k = instance["state"].get("k")
        if not isinstance(k, (int, float)):
            return {"error": f"{capsule_id} has 'about' but no numeric k"}
        k_source = capsule_id
    else:
        claim_id = capsule_id
        k = 0.0
        k_source = None

    evidence, total = [], 0.0

    # Observations
    for r in s.conn.execute("""
        SELECT c.id, c.state_json, c.created_at
        FROM capsules c JOIN links l ON l.source = c.id
        WHERE l.type = 'observes' AND l.target = ?
    """, (claim_id,)).fetchall():
        state = json.loads(r["state_json"])
        raw   = float(state.get("score", 0.0))
        age   = _age_days({}, r["created_at"])
        w     = raw * math.exp(-k * age) if k else raw
        total += w
        evidence.append({"id": r["id"], "kind": "observation",
                        "raw_score": raw, "age_days": age, "weighted": w,
                        "source": state.get("source")})

    # Verifications
    for r in s.conn.execute("""
        SELECT c.id, c.state_json, c.created_at
        FROM capsules c JOIN links l ON l.source = c.id
        WHERE l.type = 'verifies' AND l.target = ?
    """, (claim_id,)).fetchall():
        state = json.loads(r["state_json"])
        valid = bool(state.get("valid"))
        raw   = 1.0 if valid else -1.0
        age   = _age_days({}, r["created_at"])
        w     = raw * math.exp(-k * age) if k else raw
        total += w
        evidence.append({"id": r["id"], "kind": "verification",
                        "raw_score": raw, "age_days": age, "weighted": w,
                        "source": state.get("key_id")})

    return {
        "trust_instance": capsule_id,
        "claim":          claim_id,
        "k":              k,
        "k_source":       k_source,
        "evidence":       evidence,
        "score":          total,
    }


# ---------------------------------------------------------------------------
# Bayesian fusion
#
# Posterior = P(true | evidence) ∝ P(evidence | true) × P(true)
#   prior      = parameter trust (n0 * e^(-kt))
#   L          = sigmoid(evidence_score)
#   posterior  = prior*L / (prior*L + (1-prior)*(1-L))
#
# Both prior and L clamped to [eps, 1-eps] to avoid degenerate 0/1 cases.
# ---------------------------------------------------------------------------


def sigmoid(x):
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    z = math.exp(x)
    return z / (1.0 + z)


def fuse(prior, evidence_score, eps=1e-3):
    """Bayesian fusion of a prior probability with evidence."""
    p = max(eps, min(1 - eps, prior))
    L = max(eps, min(1 - eps, sigmoid(evidence_score)))
    return p * L / (p * L + (1 - p) * (1 - L))


def fused_trust(s: Substrate, capsule_id: str):
    """Combine parameter trust (prior) and evidence trust (likelihood)."""
    from queries import trust_now

    p = trust_now(s, capsule_id)
    e = trust_from_evidence(s, capsule_id)

    prior = p["score"] if p else None
    ev_score = e["score"] if (e and not e.get("error")) else None

    if prior is None and ev_score is None:
        return {"capsule_id": capsule_id, "error": "no trust data"}

    if prior is None:
        prior_used = 0.5
        source = "evidence-only (prior=0.5)"
    else:
        prior_used = prior
        source = "both" if ev_score is not None else "prior-only"

    if ev_score is None:
        L = 0.5
        posterior = prior_used
        source = "prior-only (no evidence)"
    else:
        L = sigmoid(ev_score)
        posterior = fuse(prior_used, ev_score)

    return {
        "capsule_id":      capsule_id,
        "prior":           prior_used,
        "evidence_score":  ev_score,
        "likelihood":      L,
        "posterior":       posterior,
        "source":          source,
    }
