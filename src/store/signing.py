"""Ed25519 signing + did:key encoding, on our own ed25519 module.

Canonicalisation: sorted keys, no whitespace, signature.value blanked
before hashing. Matches RFC 8032 signing flow.

did:key encoding: multicodec 0xed01 + Ed25519 public key, base58btc.
"""
import base64
import json
import os

from store import ed25519 as _ed

DID_KEY_PREFIX = "did:key:z"
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ED25519_MULTICODEC = bytes([0xed, 0x01])


def b58encode(b: bytes) -> str:
    n = int.from_bytes(b, "big")
    out = ""
    while n > 0:
        n, r = divmod(n, 58)
        out = B58[r] + out
    pad = len(b) - len(b.lstrip(b"\x00"))
    return "1" * pad + out


def b58decode(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + B58.index(ch)
    pad = len(s) - len(s.lstrip("1"))
    body = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    return b"\x00" * pad + body


def did_key_from_public(public_bytes: bytes) -> str:
    return DID_KEY_PREFIX + b58encode(ED25519_MULTICODEC + public_bytes)


def public_from_did_key(did_key: str) -> bytes:
    if not did_key.startswith(DID_KEY_PREFIX):
        raise ValueError(f"not a did:key identifier: {did_key[:20]}...")
    raw = b58decode(did_key[len(DID_KEY_PREFIX):])
    if raw[:2] != ED25519_MULTICODEC:
        raise ValueError("wrong multicodec prefix (not Ed25519)")
    return raw[2:]


def normalise_signature(doc):
    """Coerce `signature` into {key_id, algorithm, value} form.

    Some documents use a bare string placeholder ("PLACEHOLDER - sign locally").
    This converts it to the standard object form so canonicalise/sign work.
    """
    sig = doc.get("signature")
    if isinstance(sig, dict):
        return doc
    return {**doc, "signature": {
        "key_id": None,
        "algorithm": "Ed25519",
        "value": sig if isinstance(sig, str) and sig and sig != "PLACEHOLDER - sign locally" else None,
    }}


def canonicalise(doc: dict) -> bytes:
    d = json.loads(json.dumps(doc))
    if isinstance(d.get("signature"), dict):
        d["signature"]["value"] = None
    return json.dumps(d, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def generate_keypair() -> dict:
    seed = os.urandom(32)
    pk = _ed.publickey(seed)
    return {
        "private_b64": base64.b64encode(seed).decode(),
        "public_b64":  base64.b64encode(pk).decode(),
        "did_key":     did_key_from_public(pk),
    }


def sign(doc: dict, private_b64: str) -> dict:
    seed = base64.b64decode(private_b64)
    pk   = _ed.publickey(seed)
    did  = did_key_from_public(pk)

    out = json.loads(json.dumps(doc))
    out.setdefault("signature", {})
    out["signature"]["key_id"]    = did
    out["signature"]["algorithm"] = "Ed25519"
    out["signature"]["value"]     = None

    payload = canonicalise(out)
    sig = _ed.sign(payload, seed, pk)
    out["signature"]["value"] = base64.b64encode(sig).decode()
    return out


def verify(doc: dict) -> dict:
    sig = doc.get("signature") or {}
    did = sig.get("key_id")
    val = sig.get("value")
    if not val:
        return {"signed": False, "valid": False, "key_id": did,
                "reason": "no signature value"}
    try:
        pk = public_from_did_key(did)
        _ed.checkvalid(base64.b64decode(val), canonicalise(doc), pk)
        return {"signed": True, "valid": True, "key_id": did, "reason": None}
    except _ed.SignatureMismatch as e:
        return {"signed": True, "valid": False, "key_id": did, "reason": str(e)}
    except Exception as e:
        return {"signed": True, "valid": False, "key_id": did, "reason": str(e)}
