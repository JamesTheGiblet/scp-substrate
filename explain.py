"""explain(capsule_id) — narrative biography via graph traversal."""
import json
from substrate import Substrate


def _summarise_state(state, foundation):
    kind = state.get("kind")
    if kind == "style":
        if "voice" in state:
            v = state["voice"]
            return f"{v.get('register', '?')}, signs off \"{v.get('sign_off', '?')}\""
        if "build_rules" in state:
            n = len(state["build_rules"])
            first = state["build_rules"][0] if n else "?"
            return f"{n} build rules, first: \"{first}\""
        if "identity" in state:
            i = state["identity"]
            return f"{i.get('forge_name', '?')}: \"{i.get('motto', '?')}\" ({i.get('licence', '?')})"
    if foundation == "foundation:rule":
        c = state.get("condition", {})
        e = state.get("effect", {})
        if c.get("type") == "trust_above":
            return f"if trust > {c.get('threshold')} then derive '{e.get('relationship')}' from '{e.get('derive_from')}'"
        return f"if {c.get('source')} -> {c.get('target')} then derive '{e.get('relationship')}'"
    if foundation == "foundation:observation":
        return f"observation by {state.get('source', '?')} on {state.get('target', '?')}, score {state.get('score', '?')}"
    if foundation == "foundation:knowledge":
        claim = state.get("claim")
        if claim:
            return f"claim: \"{claim}\""
        decl_name = state.get("declaration", {}).get("entity", {}).get("name")
        if decl_name:
            return f"declaration by {decl_name}"
    if foundation == "foundation:leighton-weight":
        if all(isinstance(state.get(k), (int, float)) for k in ("n0", "k")):
            return f"trust instance: n0={state['n0']}, k={state['k']}"
        return f"trust model: {state.get('formula', '?')}"
    if foundation == "foundation:person":
        return state.get("role") or state.get("name") or "person"
    if foundation == "foundation:project":
        return f"project ({state.get('status', '?')})"
    if kind == "tool":
        return f"{state.get('name', '?')} — {state.get('use', '?')}"
    if kind == "skill":
        return state.get("name", "skill")
    if kind == "decision":
        return f"decision: {state.get('decision', '?')}"
    if kind == "question":
        return f"{state.get('status', '?')}: {state.get('question', '?')}"
    if kind == "principle":
        return f"\"{state.get('statement', '?')}\""
    if kind == "session":
        o = state.get('outcome', '')
        if len(o) > 60:
            o = o[:57] + "..."
        return f"session {state.get('date', '?')}: {o}"
    if kind in ("place", "organisation"):
        return f"{kind}: {state.get('name', '?')}"
    if kind == "concept":
        n = state.get("name", "?")
        m = state.get("members") or []
        return f"{n} ({len(m)} members)" if m else n
    return foundation.replace("foundation:", "")


def explain(s: Substrate, capsule_id: str) -> str:
    c = s.get(capsule_id)
    if not c:
        return f"capsule '{capsule_id}' not found"

    state = c["state"]
    out = []

    summary = _summarise_state(state, c["foundation"])
    out.append(f"{c['id']}")
    out.append(f"  is a {c['foundation'].replace('foundation:', '')} — {summary}")
    out.append("")

    # Author / subject (via 'declares' link)
    author = None
    for l in s.links_from(c["id"]):
        if l["type"] == "declares":
            author = s.get(l["target"])
            break
    if author:
        decl_entity = state.get("declaration", {}).get("entity", {})
        if decl_entity.get("name"):
            handle = decl_entity.get("handle")
            out.append(f"Declares: {decl_entity['name']}"
                       + (f" ({handle})" if handle else ""))
        else:
            a_state = author["state"]
            out.append(f"Declares: {a_state.get('name') or a_state.get('role') or author['id']}")
        out.append("")

    # Inheritance chain
    inherits = [l for l in s.links_from(c["id"]) if l["type"] == "inherits"]
    if inherits:
        out.append(f"Inherits from {len(inherits)}:")
        for l in inherits:
            target = s.get(l["target"])
            if target:
                tsum = _summarise_state(target["state"], target["foundation"])
                out.append(f"  → {l['target']}")
                out.append(f"      {tsum}")
        out.append("")

    # Classification (SCP-specific)
    lens = state.get("declaration", {}).get("lens_note")
    if lens:
        out.append("Classification:")
        out.append(f"  {lens}")
        out.append("")

    # Signature (SCP-specific)
    sig = state.get("source_format", {}).get("signature")
    if sig:
        signed = bool(sig.get("value"))
        out.append(f"Signature: {'signed' if signed else 'unsigned'}")
        out.append(f"  Algorithm: {sig.get('algorithm', '?')}")
        out.append(f"  Key: {sig.get('key_id', '?')} (declared)")
        out.append("")

    # Verification records (from substrate, not from state)
    verifications = s.conn.execute("""
        SELECT c.id, c.state_json FROM capsules c
        JOIN links l ON l.source = c.id
        WHERE l.type = 'verifies' AND l.target = ?
        ORDER BY c.created_at DESC
    """, (c["id"],)).fetchall()
    if verifications:
        out.append(f"Verifications: {len(verifications)}")
        for v in verifications:
            vstate = json.loads(v["state_json"])
            status = "valid" if vstate.get("valid") else f"invalid ({vstate.get('reason')})"
            key = vstate.get("key_id", "?")
            out.append(f"  {status} by {key[:48]}...")
        out.append("")

    # Format metadata (SCP-specific)
    fmt = state.get("source_format", {})
    if fmt.get("format"):
        out.append(f"Format: {fmt.get('format')} v{fmt.get('version')}, "
                   f"canonicalisation {fmt.get('canonicalisation')}")
        out.append("")

    # Remaining outbound relationships
    skip = {"inherits", "declares"}
    others = [l for l in s.links_from(c["id"]) if l["type"] not in skip]
    if others:
        out.append("Relationships:")
        for l in others:
            out.append(f"  → {l['type']:15} → {l['target']}")
        out.append("")

    return "\n".join(out).rstrip()
