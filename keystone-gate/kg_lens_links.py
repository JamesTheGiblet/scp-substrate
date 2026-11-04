"""Cluster cubes by what they say on the same lens.

Two cubes link when one lens on each shares unusual words: two will do for
cubes on the same subject or entity, but cubes with nothing else in common need
three and a closer match. Lenses are compared only with themselves, so a shared
COUNTER means two cubes share a weakness, not merely a topic. Pronouns, the
store's own words and any word on more than a quarter of a lens's faces don't
count, since seeded faces repeat stock phrases. This measures shared
vocabulary, not agreement in meaning.
"""
import math
import re
from collections import Counter, defaultdict


LENSES = ("FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT")
THRESHOLD = 0.10
# Cubes that share no subject or entity need more before a word links them
APART_THRESHOLD, APART_TERMS = 0.20, 3
# A word on more than this share of a lens's faces is boilerplate, once a lens has enough faces
MAX_SHARE, MIN_FACES = 0.25, 8
LINKS_PER_CUBE = 3

_STOP = set("""about above after again against also because been before being
below between both but can cannot could does doing down each even every from
further have having here into just like made make many more most much must
near need needs not now off once one only other out over own same should since
some still such than that the their them then there these they this those
through too two under until very was were what when where which while who why
will with would you your its are for and has had may might use used using
without would first second another already often rather page pages cube cubes
fully new not back matter matters kit build built chosen principle recorded
guide says say said itself add adds run runs seem seems work works part parts
far full long short high low way ways thing things get gets keep keeps
check checks moment case point every whole
he him his himself she her hers herself they them their theirs we our us
james james's
attached attach entity entities link links linked document documents person
suppose supposing stated states written confirmed inferred claim claims
subject subjects lens lenses face faces draft drafts""".split())


def _stem(word):
    for ending in ("ing", "ed", "es", "s"):
        if word.endswith(ending) and len(word) - len(ending) >= 3:
            return word[:-len(ending)]
    return word


_seen_as = defaultdict(Counter)


def _word(stem):
    """The word people actually wrote for a stem, for labels."""
    forms = _seen_as.get(stem)
    return min(forms, key=lambda w: (-forms[w], w)) if forms else stem


_STOP_STEMS = {_stem(w) for w in _STOP}


def _terms(text):
    words = re.findall(r"[a-z][a-z0-9]{2,}", (text or "").lower())
    terms = Counter()
    for w in words:
        if w not in _STOP and _stem(w) not in _STOP_STEMS:
            terms[_stem(w)] += 1
            _seen_as[_stem(w)][w] += 1
    return terms


def _vectors(cubes, lens):
    """TF-IDF per cube for one lens. Common words count for little."""
    bags = {}
    for c in cubes:
        face = c["faces"].get(lens)
        if face and face.get("content"):
            bags[c["id"]] = _terms(face["content"])
    seen = Counter(term for bag in bags.values() for term in bag)
    total = max(len(bags), 1)
    common = {t for t, n in seen.items() if total >= MIN_FACES and n / total > MAX_SHARE}
    return {cid: {t: n * math.log((1 + total) / seen[t]) for t, n in bag.items() if t not in common}
            for cid, bag in bags.items()}


def _similar(a, b, terms=2):
    """Cosine similarity, and the term that contributes most."""
    shared = set(a) & set(b)
    # One shared word is a coincidence; two are the start of a subject
    if len(shared) < terms:
        return 0.0, None
    size = math.sqrt(sum(v * v for v in a.values()) * sum(v * v for v in b.values()))
    if not size:
        return 0.0, None
    return sum(a[t] * b[t] for t in shared) / size, max(sorted(shared), key=lambda t: a[t] * b[t])


def _ties(cubes):
    """What each cube is about. The store's owner, whom every cube about you is
    about, and any tie on more than a third of the cubes are too broad to count
    as having something in common."""
    ties = {c["id"]: set(c.get("subjects") or []) | set(c.get("entities") or []) for c in cubes}
    seen = Counter(t for tie in ties.values() for t in tie)
    broad = {t for t, n in seen.items() if len(cubes) >= MIN_FACES and n > len(cubes) / 3}
    yours = [ties[c["id"]] for c in cubes if c.get("about_you")]
    broad |= set.intersection(*yours) if yours else set()
    return {cid: tie - broad for cid, tie in ties.items()}


def _links(cubes, lenses):
    """Strongest lens per pair, keeping each cube's best few."""
    pairs = {}
    ties = _ties(cubes)
    for lens in lenses:
        vectors = _vectors(cubes, lens)
        ids = sorted(vectors)
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                near = bool(ties[a] & ties[b])
                weight, term = _similar(vectors[a], vectors[b], 2 if near else APART_TERMS)
                if weight < (THRESHOLD if near else APART_THRESHOLD):
                    continue
                if weight > pairs.get((a, b), {"weight": 0})["weight"]:
                    pairs[(a, b)] = {"a": a, "b": b, "lens": lens, "term": term, "word": _word(term),
                                     "weight": round(weight, 3)}
    per_cube = defaultdict(list)
    for link in pairs.values():
        per_cube[link["a"]].append(link)
        per_cube[link["b"]].append(link)
    kept = {}
    for links in per_cube.values():
        for link in sorted(links, key=lambda l: (-l["weight"], l["a"], l["b"]))[:LINKS_PER_CUBE]:
            kept[(link["a"], link["b"])] = link
    return sorted(kept.values(), key=lambda l: (l["a"], l["b"]))


def _plain(links):
    """Labels for the page: the written word, not the stem."""
    return [{"a": l["a"], "b": l["b"], "lens": l["lens"], "term": l["word"], "weight": l["weight"]}
            for l in links]


def _communities(ids, links):
    """Label propagation: each cube takes the label its links weigh most."""
    label = {cid: cid for cid in ids}
    around = defaultdict(list)
    for l in links:
        around[l["a"]].append((l["b"], l["weight"]))
        around[l["b"]].append((l["a"], l["weight"]))
    for _ in range(12):
        changed = False
        for cid in ids:
            votes = Counter()
            for other, weight in around[cid]:
                votes[label[other]] += weight
            if votes:
                best = min(votes, key=lambda k: (-votes[k], k))
                if votes[best] > votes.get(label[cid], 0) and best != label[cid]:
                    label[cid] = best
                    changed = True
        if not changed:
            break
    groups = defaultdict(list)
    for cid in ids:
        groups[label[cid]].append(cid)
    return list(groups.values())


def _name(members, links):
    inside = set(members)
    terms = Counter()
    for l in links:
        if l["a"] in inside and l["b"] in inside:
            terms[l["term"]] += l["weight"]
    top = sorted(terms, key=lambda t: (-terms[t], t))[:2]
    return " + ".join(_word(t) for t in top) if top else "unlinked"


def cluster(cubes, lenses):
    ids = sorted(c["id"] for c in cubes)
    links = _links(cubes, lenses)
    named, loners = [], []
    for members in _communities(ids, links):
        (named if len(members) > 1 else loners).append(members)
    groups = [{"name": _name(m, links), "members": m} for m in named]
    if loners:
        groups.append({"name": "no shared lens", "members": [m[0] for m in loners]})
    return {"clusters": sorted(groups, key=lambda g: g["name"]), "links": _plain(links)}


def by_repo(cubes):
    """One box per repo, and one for every cube that belongs to none."""
    boxes = defaultdict(list)
    for c in sorted(cubes, key=lambda c: c["id"]):
        boxes[c.get("repo") or "not from a repo"].append(c["id"])
    return {"clusters": [{"name": name, "members": members} for name, members in sorted(boxes.items())],
            "links": []}


def by_place(cubes):
    """One box per entity and subject, as each cube's place names it."""
    boxes = defaultdict(list)
    for c in sorted(cubes, key=lambda c: c["id"]):
        boxes[c["place"]].append(c["id"])
    return {"clusters": [{"name": name, "members": members} for name, members in sorted(boxes.items())],
            "links": []}


def all_modes(cubes):
    """One clustering for all lenses together, one per lens that has links, and one per repo."""
    modes = {"ALL": cluster(cubes, LENSES)}
    if any(c.get("place") for c in cubes):
        modes["PLACES"] = by_place(cubes)
    if any(c.get("repo") for c in cubes):
        modes["REPOS"] = by_repo(cubes)
    if any(c.get("overlaps") for c in cubes):
        from kg_overlaps import by_overlap
        modes["OVERLAPS"] = by_overlap(cubes)
    for lens in LENSES:
        result = cluster(cubes, (lens,))
        if result["links"]:
            modes[lens] = result
    return modes
