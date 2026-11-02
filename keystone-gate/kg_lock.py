"""The password that unlocks editing in the browser.

Only a salted scrypt hash is kept, in your home folder. It stays out of the repo
because sc.db is pushed to GitHub. Forgot it? Delete the file and set a new one.
"""
import hashlib
import json
import secrets
from pathlib import Path


LOCK_FILE = Path.home() / ".config" / "scp" / "cube-edit.json"
MIN_LENGTH = 8
_COST = {"n": 2 ** 15, "r": 8, "p": 1}


def _hash(password, salt, cost):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, maxmem=2 ** 26, **cost)


def make_lock(password):
    if len(password) < MIN_LENGTH:
        raise ValueError(f"use at least {MIN_LENGTH} characters")
    salt = secrets.token_bytes(16)
    return {"salt": salt.hex(), "hash": _hash(password, salt, _COST).hex(), **_COST}


def matches(password, lock):
    cost = {k: lock[k] for k in _COST}
    return secrets.compare_digest(_hash(password, bytes.fromhex(lock["salt"]), cost).hex(), lock["hash"])


def load_lock(path=LOCK_FILE):
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def save_lock(lock, path=LOCK_FILE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lock), encoding="utf-8")
    path.chmod(0o600)
    return path
