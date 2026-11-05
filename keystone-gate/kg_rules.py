"""Cube rules. Each rule reads the substrate and proposes face fills or
neighbour links for a cube. Rules are pure: given substrate state, they
return a list of proposals. Nothing fires without a human accept.

Rule shape:
    {
        "id": str,
        "description": str,
        "applies": callable(s, cube) -> bool,
        "propose": callable(s, cube) -> list of {type, ...kwargs}
    }

The propose callable returns dicts ready to pass to propose_face or
propose_neighbour. Rules must be idempotent — running twice must produce
the same proposal IDs (the propose_* functions handle that).
"""
import json
import re
import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here.parent / "src"))
sys.path.insert(0, str(_here))

from kg_agent import LENSES, propose_face, propose_neighbour


# Words too generic to prove a text match on their own
_STOP = {
    "have", "with", "this", "that", "from", "they", "there", "these",
    "those", "their", "which", "when", "where", "what", "were", "been",
    "being", "will", "would", "could", "should", "also", "just", "only",
    "even", "still", "more", "most", "less", "least", "then", "than",
    "into", "onto", "upon", "your", "some", "many", "much", "very",
    "over", "under", "through", "about", "above", "below",
    "chose", "choose", "chosen", "decide", "decided", "decision",
}


def _tokens(text):
    """Return the set of significant words (4+ chars) in a text."""
    return set(re.findall(r"[a-z]{4,}", text.lower())) - _STOP


def _find_substrate_capsule_by_text(s, text, kind=None):
    """Find a capsule whose field value matches the text.

    Match rules, in order:
      1. Whole field is a substring of the text (exact phrase)
      2. Token overlap: a significant word from the capsule's ID appears in
         the text, or at least two from the field do. One shared field word
         ("file", "mode") is ordinary English and proves nothing.

    Exact phrases win; otherwise the capsule with the most overlap.
    """
    query = "SELECT id, state_json FROM capsules WHERE foundation = 'foundation:knowledge'"
    params = []
    if kind:
        query += " AND json_extract(state_json, '$.kind') = ?"
        params.append(kind)
    rows = s.conn.execute(query, params).fetchall()
    text_l = text.lower()
    text_words = _tokens(text_l)
    best, best_overlap = None, 0

    for r in rows:
        st = json.loads(r["state_json"])
        id_overlap = _tokens(r["id"]) & text_words
        for field in ("text", "name", "claim", "statement", "decision", "question"):
            v = st.get(field)
            if not isinstance(v, str):
                continue
            v_l = v.lower()
            # Rule 1: whole field appears in text
            if v_l in text_l:
                return {"id": r["id"], "state": st}
            # Rule 2: token overlap
            overlap = _tokens(v_l) & text_words
            if (id_overlap or len(overlap) >= 2) and len(overlap | id_overlap) > best_overlap:
                best = {"id": r["id"], "state": st}
                best_overlap = len(overlap | id_overlap)
    return best


def _find_decision_for(s, text):
    return _find_substrate_capsule_by_text(s, text, kind="decision")


# --- Rule 1: fact_from_decision -----------------------------------------
def _rule_fact_from_decision(s, cube_state):
    decision = _find_decision_for(s, cube_state.get("content", ""))
    if not decision:
        return []
    st = decision["state"]
    parts = []
    if st.get("decision"):
        parts.append(st["decision"])
    if st.get("rationale"):
        parts.append(st["rationale"])
    if not parts:
        return []
    return [{
        "type": "face",
        "lens": "FACT",
        "content": " ".join(parts),
        "proposed_by": "fact_from_decision",
        "rationale": f"from capsule {decision['id']} (kind=decision)",
        "confidence": 0.85,
    }]


# --- Rule 2: counter_from_alternatives ----------------------------------
def _rule_counter_from_alternatives(s, cube_state):
    decision = _find_decision_for(s, cube_state.get("content", ""))
    if not decision:
        return []
    alts = decision["state"].get("alternatives_considered") or []
    if not alts:
        return []
    return [{
        "type": "face",
        "lens": "COUNTER",
        "content": "Considered but not chosen: " + "; ".join(alts),
        "proposed_by": "counter_from_alternatives",
        "rationale": f"from {decision['id']}.alternatives_considered",
        "confidence": 0.80,
    }]


# --- Rule 3: context_from_source ----------------------------------------
def _rule_context_from_source(s, cube_state):
    source = cube_state.get("source")
    if not source:
        return []
    # Search for a capsule whose state or id mentions the source
    source_l = source.lower()
    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE foundation = 'foundation:knowledge'"
    ).fetchall()
    for r in rows:
        st = json.loads(r["state_json"])
        for field in ("name", "text", "statement", "claim"):
            v = st.get(field)
            if isinstance(v, str) and v.lower() in source_l:
                return [{
                    "type": "face",
                    "lens": "CONTEXT",
                    "content": f"Source: {r['id']} — " + (st.get("description") or st.get("statement") or st.get("decision") or st.get(field, ""))[:200],
                    "proposed_by": "context_from_source",
                    "rationale": f"cube references source {source!r}",
                    "confidence": 0.70,
                }]
    return []


# --- Rule 4: counter_from_contradicts -----------------------------------
def _rule_counter_from_contradicts(s, cube_state):
    contra = cube_state.get("contradicts")
    if not contra:
        return []
    other_id = contra.get("other")
    other = s.get(other_id)
    if not other:
        return []
    # Look for a FACT face on the other cube
    other_fact = s.get(f"{other_id}/face/FACT")
    if other_fact:
        content = other_fact["state"].get("content", "")
    else:
        content = other["state"].get("content", "")
    if not content:
        return []
    return [{
        "type": "face",
        "lens": "COUNTER",
        "content": f"Contradicts {other_id}: {content[:200]}",
        "proposed_by": "counter_from_contradicts",
        "rationale": f"cube has contradicts field pointing at {other_id}",
        "confidence": 0.75,
    }]


# --- Rule 5: neighbour_on_subject ---------------------------------------
# Tags now say where a claim came from (needs-check, seller), so sharing one
# says nothing about meaning. Two claims on the same subject that say the
# same words probably bear on each other; James picks the word that says how.
NEIGHBOURS_PER_CUBE = 3


def _rule_neighbour_on_subject(s, cube_state):
    from kg_lens_links import _terms, _word
    from store.claim_links import relations
    cube_id = cube_state.get("_cube_id")  # injected by run_rules
    if not cube_id:
        return []
    linked = {other for _, other, _ in relations(s, cube_id)}
    # Saying the subject's or entity's own name is being about it, not
    # saying the same thing, so names don't count as shared words
    named = lambda cid: set().union(*[_terms(" ".join([n["state"].get("name", ""), *(
        a if isinstance(a := n["state"].get("aliases") or [], list) else a.split(","))]))
        for l in s.links_from(cid) if l["type"] in ("about-subject", "about-entity") if (n := s.get(l["target"]))])
    mine = set(_terms(cube_state.get("content"))) - named(cube_id)
    found = {}
    for subj in sorted(l["target"] for l in s.links_from(cube_id) if l["type"] == "about-subject"):
        for l in s.links_to(subj, "about-subject"):
            other = l["source"]
            if other == cube_id or other in linked or other in found:
                continue
            words = set(_terms((s.get(other) or {"state": {}})["state"].get("content"))) - named(other)
            shared = mine & words
            if len(shared) >= 2:
                found[other] = (subj, shared)
    best = sorted(found.items(), key=lambda f: (-len(f[1][1]), f[0]))[:NEIGHBOURS_PER_CUBE]
    return [{
        "type": "neighbour",
        "other_cube_id": other,
        "proposed_by": "neighbour_on_subject",
        "rationale": f"both about {(s.get(subj) or {'state': {}})['state'].get('name', subj)}, "
                     f"and both say {', '.join(sorted(_word(w) for w in shared))}",
    } for other, (subj, shared) in best]


RULES = [
    {"id": "fact_from_decision",         "propose": _rule_fact_from_decision},
    {"id": "counter_from_alternatives",  "propose": _rule_counter_from_alternatives},
    {"id": "context_from_source",        "propose": _rule_context_from_source},
    {"id": "counter_from_contradicts",   "propose": _rule_counter_from_contradicts},
    {"id": "neighbour_on_subject",       "propose": _rule_neighbour_on_subject},
]


def run_rules(s, cube_id, only_rules=None):
    """Run all rules against a cube. Return list of proposal results.

    Idempotent: existing pending proposals are updated in place, not
    duplicated. Filled lenses are skipped. Existing neighbour links skipped.
    """
    cube = s.get(cube_id)
    if not cube:
        return [{"error": f"cube {cube_id} not found"}]

    cube_state = dict(cube["state"])
    cube_state["_cube_id"] = cube_id

    results = []
    for rule in RULES:
        if only_rules and rule["id"] not in only_rules:
            continue
        try:
            proposals = rule["propose"](s, cube_state) or []
        except Exception as e:
            results.append({"rule": rule["id"], "error": str(e)})
            continue
        for p in proposals:
            if p.get("type") == "face":
                r = propose_face(
                    s, cube_id, p["lens"], p["content"],
                    proposed_by=p["proposed_by"],
                    rationale=p.get("rationale"),
                    confidence=p.get("confidence"),
                )
            elif p.get("type") == "neighbour":
                r = propose_neighbour(
                    s, cube_id, p["other_cube_id"],
                    proposed_by=p["proposed_by"],
                    rationale=p.get("rationale"),
                )
            else:
                continue
            r["rule"] = rule["id"]
            results.append(r)
    return results
