"""Cross-module helpers: hashing of field elements, challenge sampling, bytes
serialisation."""

from __future__ import annotations

import hashlib
import struct
from typing import Sequence

from .field import DEFAULT_PRIME, FieldElement


# ---------------------------------------------------------------------------
# Byte serialisation of field elements
# ---------------------------------------------------------------------------

def field_element_to_bytes(fe: FieldElement) -> bytes:
    """Canonical 32-byte big-endian encoding of a field element's value."""
    return fe.value.to_bytes(32, "big")


def field_elements_to_bytes(*fes: FieldElement) -> bytes:
    out = bytearray()
    for fe in fes:
        out += field_element_to_bytes(fe)
    return bytes(out)


def list_to_bytes(xs: Sequence[FieldElement]) -> bytes:
    return field_elements_to_bytes(*xs)


def bytes_to_field_element(b: bytes, prime: int = DEFAULT_PRIME) -> FieldElement:
    """Inverse of field_element_to_bytes (value taken mod prime)."""
    return FieldElement(int.from_bytes(b, "big"), prime)


# ---------------------------------------------------------------------------
# Hashing for commitments and Fiat-Shamir
# ---------------------------------------------------------------------------

def hash_many(*parts: bytes) -> bytes:
    """SHA-256 of the concatenation of all parts (each already byte-encoded)."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p)
    return h.digest()


def hash_field_elements(*fes: FieldElement) -> bytes:
    return hash_many(*(field_element_to_bytes(fe) for fe in fes))


# ---------------------------------------------------------------------------
# Fiat-Shamir challenge derivation
# ---------------------------------------------------------------------------

def sample_field_element(seed: bytes, prime: int = DEFAULT_PRIME) -> FieldElement:
    """Derive a field element by hashing `seed` and reducing mod prime.

    Uses a single SHA-256 + mod prime, which is unbiased up to a tiny bias of
    size at most 2^256 mod prime. For the primes used here that's negligible.
    """
    if not seed:
        raise ValueError("seed must be non-empty")
    out = int.from_bytes(hashlib.sha256(seed).digest(), "big")
    return FieldElement(out % prime, prime)


def sample_int_in_range(seed: bytes, lo: int, hi_inclusive: int) -> int:
    """Derive a uniformly distributed int in [lo, hi_inclusive] from `seed`."""
    if hi_inclusive < lo:
        raise ValueError("invalid range")
    span = hi_inclusive - lo + 1
    h = int.from_bytes(hashlib.sha256(seed).digest(), "big")
    return lo + (h % span)


def sample_distinct_ints(
    seed: bytes, lo: int, hi_inclusive: int, count: int
) -> list[int]:
    """Sample `count` distinct ints in [lo, hi_inclusive] using rejection sampling.

    Uses a chain of SHA-256 hashes to derive additional candidates. Returns a
    list of integers in arbitrary order.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if count == 0:
        return []
    span = hi_inclusive - lo + 1
    if count > span:
        raise ValueError(f"cannot sample {count} distinct values from range of size {span}")
    seen: set[int] = set()
    out: list[int] = []
    cur = seed
    while len(out) < count:
        h = int.from_bytes(hashlib.sha256(cur).digest(), "big")
        cand = lo + (h % span)
        if cand not in seen:
            seen.add(cand)
            out.append(cand)
        cur = hashlib.sha256(cur).digest()
    return out