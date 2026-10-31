"""Pure-Python Ed25519 (RFC 8032). Self-contained: only hashlib from stdlib.

This is a reference implementation. NOT constant-time: Python's big-int
arithmetic leaks timing. Safe for signing your own documents on your own
device; NOT safe for keys on shared or adversarial machines.

Design choices (clarity over speed):
  - Affine coordinates (Edwards addition formula)
  - Double-and-add scalar multiplication
  - SHA-512 from hashlib
  - Little-endian encoding throughout
  - Malleability hardened: reject S >= l in verification

Validated against RFC 8032 §7.1 test vectors.
"""
import hashlib


# --- curve parameters ---------------------------------------------------
b = 256
q = 2**255 - 19                                                    # field prime
l = 2**252 + 27742317777372353535851937790883648493                # group order


# --- arithmetic helpers -------------------------------------------------
def _sha512(data):
    return hashlib.sha512(data).digest()


def _expmod(base, exp, mod):
    """(base**exp) mod mod, exp >= 0."""
    if exp == 0:
        return 1
    t = _expmod(base, exp // 2, mod) ** 2 % mod
    if exp & 1:
        t = (t * base) % mod
    return t


def _inv(x):
    """Modular inverse; q is prime, so Fermat's little theorem applies."""
    return _expmod(x, q - 2, q)


# --- curve constants ----------------------------------------------------
_d = -121665 * _inv(121666) % q
_I = _expmod(2, (q - 1) // 4, q)                                   # sqrt(-1) mod q


# --- base point ---------------------------------------------------------
def _xrecover(y):
    """Given y, return the even x with -x^2 + y^2 = 1 + d*x^2*y^2."""
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = _expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * _I) % q
    if x % 2 != 0:
        x = q - x
    return x


_By = 4 * _inv(5) % q
_Bx = _xrecover(_By)
B = [_Bx % q, _By % q]


# --- point arithmetic (affine) ------------------------------------------
def _edwards(P, Q):
    """Twisted Edwards addition (a = -1)."""
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + _d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - _d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]


def _scalarmult(P, e):
    """Scalar multiplication, double-and-add."""
    if e == 0:
        return [0, 1]
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


# --- encoding / decoding ------------------------------------------------
def _bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def _encodeint(y):
    """Integer -> 32 little-endian bytes."""
    return bytes((y >> (8 * i)) & 0xFF for i in range(32))


def _encodepoint(P):
    """Point -> 32 bytes: y little-endian (255 bits) + sign bit of x."""
    x, y = P
    out = bytearray(_encodeint(y))
    out[31] |= (x & 1) << 7
    return bytes(out)


def _decodeint(s):
    """32 little-endian bytes -> integer."""
    n = 0
    for i in reversed(range(32)):
        n = (n << 8) | s[i]
    return n


def _decodepoint(s):
    """32 bytes -> point; raises ValueError if not on curve."""
    if len(s) != 32:
        raise ValueError("encoded point must be 32 bytes")
    y = _decodeint(s) & ((1 << 255) - 1)
    x = _xrecover(y)
    if (x & 1) != (s[31] >> 7):
        x = q - x
    P = [x, y]
    if (-x * x + y * y - 1 - _d * x * x * y * y) % q != 0:
        raise ValueError("point not on curve")
    return P


# --- hashing to integers ------------------------------------------------
def _H(m):
    return _sha512(m)


def _Hint(m):
    """SHA-512(m) as a little-endian integer (not reduced)."""
    h = _H(m)
    n = 0
    for i in reversed(range(64)):
        n = (n << 8) | h[i]
    return n


# --- public API ---------------------------------------------------------
def publickey(seed):
    """32-byte seed -> 32-byte public key."""
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _H(seed)
    a = 2 ** (b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, b - 2))
    return _encodepoint(_scalarmult(B, a))


def sign(message, seed, pk):
    """Sign message with 32-byte seed -> 64-byte signature."""
    if len(seed) != 32 or len(pk) != 32:
        raise ValueError("seed and pk must be 32 bytes")
    h = _H(seed)
    a = 2 ** (b - 2) + sum(2 ** i * _bit(h, i) for i in range(3, b - 2))
    r = _Hint(h[32:64] + message) % l
    R = _scalarmult(B, r)
    k = _Hint(_encodepoint(R) + pk + message) % l
    S = (r + k * a) % l
    return _encodepoint(R) + _encodeint(S)


class SignatureMismatch(Exception):
    """Raised when a signature fails verification."""


def checkvalid(sig, message, pk):
    """Raise SignatureMismatch if sig is not valid for message under pk."""
    if len(sig) != 64 or len(pk) != 32:
        raise SignatureMismatch("bad lengths")
    R = _decodepoint(sig[:32])
    A = _decodepoint(pk)
    S = _decodeint(sig[32:])
    if S >= l:
        raise SignatureMismatch("S >= l (malleable signature rejected)")
    k = _Hint(_encodepoint(R) + pk + message) % l
    if _scalarmult(B, S) != _edwards(R, _scalarmult(A, k)):
        raise SignatureMismatch("verification failed")
