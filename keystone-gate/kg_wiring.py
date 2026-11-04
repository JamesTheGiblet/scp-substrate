"""Wiring: which pins of an entity's parts end up joined. Imported by kg.

A wiring claim is about an entity and subject/wiring, and its state lists the
wires it describes as [[part, pin], [part, pin]] pairs, where a part is a
subject. Nets are traced from those wires, so a common ground shows up from
the wiring itself rather than being stated. See docs/VOCABULARY.md.
"""
from store.substrate import Substrate

WIRING = "subject/wiring"


def wiring_claims(s, entity_id):
    """The wiring claims about an entity that list their wires."""
    about = {l["source"] for l in s.links_to(entity_id, "about-entity")}
    wiring = {l["source"] for l in s.links_to(WIRING, "about-subject")}
    out = []
    for cid in sorted(about & wiring):
        wires = s.get(cid)["state"].get("wires")
        if wires:
            out.append({"id": cid, "wires": wires})
    return out


def nets(s, entity_id):
    """Every group of pins joined by wires, largest first, each with the claims
    that join it. A pin is "part:pin"."""
    parent, claims = {}, {}

    def root(p):
        parent.setdefault(p, p)
        while parent[p] != p:
            parent[p] = parent[parent[p]]
            p = parent[p]
        return p

    wired = wiring_claims(s, entity_id)
    for c in wired:
        for a, b in c["wires"]:
            a, b = ":".join(a), ":".join(b)
            parent[root(a)] = root(b)
    groups = {}
    for p in list(parent):
        groups.setdefault(root(p), set()).add(p)
    for c in wired:
        for a, _ in c["wires"]:
            claims.setdefault(root(":".join(a)), set()).add(c["id"])
    out = [{"pins": sorted(g), "parts": sorted({p.rsplit(":", 1)[0] for p in g}),
            "claims": sorted(claims.get(r, ()))} for r, g in groups.items()]
    return sorted(out, key=lambda n: (-len(n["parts"]), n["pins"]))


def cmd_wiring(args):
    s = Substrate()
    found = nets(s, args.entity)
    s.close()
    if not found:
        print(f"No wiring claims about {args.entity}.")
    for n in found:
        print(f"\n{len(n['parts'])} parts joined: {', '.join(n['pins'])}")
        for cid in n["claims"]:
            print(f"    from {cid}")


def add_wiring_parser(sub):
    p = sub.add_parser("wiring", help="trace which pins an entity's wiring claims join")
    p.add_argument("entity")
    p.set_defaults(func=cmd_wiring)
