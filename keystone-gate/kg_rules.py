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


def _cube_tags(cube_state):
    return set(t.lower() for t in (cube_state.get("tags") or []))


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


# --- Rule 5: neighbour_by_tag -------------------------------------------
def _rule_neighbour_by_tag(s, cube_state):
    cube_tags = _cube_tags(cube_state)
    if not cube_tags:
        return []
    # Find other cubes that share at least one tag
    cube_id = cube_state.get("_cube_id")  # injected by run_rules
    if not cube_id:
        return []
    rows = s.conn.execute(
        "SELECT id, state_json FROM capsules WHERE foundation = 'foundation:cube' AND is_meta = 0"
    ).fetchall()
    proposals = []
    for r in rows:
        if r["id"] == cube_id:
            continue
        other_state = json.loads(r["state_json"])
        other_tags = _cube_tags(other_state)
        shared = cube_tags & other_tags
        if shared:
            proposals.append({
                "type": "neighbour",
                "other_cube_id": r["id"],
                "proposed_by": "neighbour_by_tag",
                "rationale": f"shared tags: {sorted(shared)}",
            })
    return proposals



def _rule_cluster_to_subject(s, cube_state):
    """If multiple cubes share a tag, propose creating a Subject and linking them."""
    cube_tags = _cube_tags(cube_state)
    if not cube_tags:
        return []
    
    cube_id = cube_state.get("_cube_id")
    if not cube_id:
        return []

    best_tag = None
    best_count = 0
    best_rows = []

    # Find the single most common tag for this cube
    for tag in cube_tags:
        if tag in ("general", "misc", "temp"):
            continue
            
        rows = s.conn.execute("""
            SELECT id FROM capsules 
            WHERE foundation = 'foundation:cube' 
              AND json_extract(state_json, '$.tags') LIKE ?
        """, (f'%"{tag}"%',)).fetchall()
        
        count = len(rows)
        if count > best_count and count >= 3:
            best_count = count
            best_tag = tag

    proposals = []
    if best_tag:
        subject_id = f"subject/{best_tag}"
        subject_exists = s.get(subject_id) is not None
        
        # 1. Propose the subject if it doesn't exist
        if not subject_exists:
            proposals.append({
                "type": "new_subject",
                "subject_id": subject_id,
                "name": best_tag,
                "proposed_by": "cluster_to_subject",
                "rationale": f"{best_count} claims share this tag",
            })
        
        # 2. Propose linking this cube to the subject
        existing_link = s.conn.execute(
            "SELECT 1 FROM links WHERE source=? AND type='about-subject' AND target=?",
            (cube_id, subject_id)
        ).fetchone()
        
        if not existing_link:
            proposals.append({
                "type": "link_subject",
                "cube_id": cube_id,
                "subject_id": subject_id,
                "proposed_by": "cluster_to_subject",
                "rationale": f"cube is tagged #{best_tag}",
            })
            
    return proposals

RULES = [
    {"id": "fact_from_decision",         "propose": _rule_fact_from_decision},
    {"id": "counter_from_alternatives",  "propose": _rule_counter_from_alternatives},
    {"id": "context_from_source",        "propose": _rule_context_from_source},
    {"id": "counter_from_contradicts",   "propose": _rule_counter_from_contradicts},
    {"id": "neighbour_by_tag",           "propose": _rule_neighbour_by_tag},
    {"id": "cluster_to_subject",         "propose": _rule_cluster_to_subject},
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
            elif p.get("type") == "new_subject":
                if not s.get(p["subject_id"]):
                    s.write({
                        "id": p["subject_id"],
                        "foundation": "foundation:subject",
                        "state": {"kind": "subject", "name": p["name"]}
                    })
                    r = {"status": "created", "subject": p["subject_id"]}
                else:
                    r = {"status": "skipped", "reason": "subject already exists"}
            elif p.get("type") == "link_subject":
                existing = s.conn.execute(
                    "SELECT 1 FROM links WHERE source=? AND type='about-subject' AND target=?",
                    (p["cube_id"], p["subject_id"])
                ).fetchone()
                if not existing:
                    s.link(p["cube_id"], "about-subject", p["subject_id"])
                    r = {"status": "created", "link": f"{p['cube_id']} -> {p['subject_id']}"}
                else:
                    r = {"status": "skipped", "reason": "link already exists"}
            else:
                continue
            r["rule"] = rule["id"]
            results.append(r)
    return results
