"""LLLM, James's own model, drafts the FACT lens from his own writing. Imported by kg_fill.

LLLM is a statistical next-word model trained only on James's writing. Every
word it gives comes from a line in that corpus, and it says nothing rather
than join unrelated text. So it drafts FACT alone: what his own writing says
about the claim's subject. The other lenses fall through to the other models.
It runs on this machine, so private cubes may use it.

LLLM_REPO names its checkout (default ~/Documents/lllm). LLLM_DB names the
model, else $LLLM_HOME/lllm.db, else the checkout's var/lllm.db.
"""
import os
import re
import sys
from pathlib import Path

from kg_llm import LLMUnavailable

# A seed runs from the claim's start to its first verb, "the pca9685 is",
# which is the form LLLM continues best
VERBS = {"is", "are", "was", "were", "has", "have", "can", "needs", "uses", "keeps", "runs"}


def seed_of(claim):
    words = re.findall(r"[a-z0-9][a-z0-9.+'-]*", claim.lower())
    for i, w in enumerate(words[:8]):
        if w in VERBS:
            return " ".join(words[:i + 1])
    return " ".join(words[:3])


def _repo():
    return Path(os.environ.get("LLLM_REPO") or Path.home() / "Documents" / "lllm")


def _db():
    if os.environ.get("LLLM_DB"):
        return Path(os.environ["LLLM_DB"])
    if os.environ.get("LLLM_HOME"):
        return Path(os.environ["LLLM_HOME"]) / "lllm.db"
    return _repo() / "var" / "lllm.db"


def _generate(seed):
    repo, db = _repo(), _db()
    if not (repo / "lllm" / "generate.py").exists():
        raise LLMUnavailable(f"no LLLM checkout at {repo}")
    if not db.exists():
        raise LLMUnavailable(f"no LLLM model at {db}; set LLLM_DB")
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from lllm.generate import generate_trace
    try:
        return generate_trace(seed, db_path=str(db), max_sentences=2)
    except RuntimeError as e:
        # LLLM refuses a model it can't vouch for, such as an old format
        raise LLMUnavailable(f"LLLM refused its model: {e}") from e


def lllm(ask, known, **_how):
    """Draft FACT from James's own writing, or say why it can't."""
    if "FACT" not in ask:
        raise LLMUnavailable("LLLM drafts FACT only")
    claim = next((l[len("Claim: "):] for l in known.splitlines() if l.startswith("Claim: ")), "")
    seed = seed_of(claim)
    trace = _generate(seed)
    if not trace or not trace["text"]:
        stopped = trace["stopped"] if trace else "no model"
        raise LLMUnavailable(f"nothing on record for {seed!r} ({stopped})")
    return [{"lens": "FACT", "content": trace["text"]}]
