"""The field's Cluster by modes, and the word scoring kg_overlaps uses.

The field once clustered cubes by words their lenses shared. Those links
measured vocabulary, not meaning, and named clusters after words such as
"harder", so they are gone: the field groups by entity and subject, tag,
repo and overlap, and its threads are the links you made. The scoring below
is kept for kg_overlaps and kg_rules, which compare one lens with itself
and show their match for you to confirm.
"""
import math
import re
from collections import Counter, defaultdict


LENSES = ("FACT", "COUNTER", "OPINION", "FICTION", "CONTEXT")
# A word on more than this share of a lens's faces is boilerplate, once a lens has enough faces
MAX_SHARE, MIN_FACES = 0.25, 8

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
    """One box per entity and subject, and per repo and overlap where there are any."""
    modes = {}
    if any(c.get("place") for c in cubes):
        modes["PLACES"] = by_place(cubes)
    if any(c.get("repo") for c in cubes):
        modes["REPOS"] = by_repo(cubes)
    if any(c.get("overlaps") for c in cubes):
        from kg_overlaps import by_overlap
        modes["OVERLAPS"] = by_overlap(cubes)
    return modes
