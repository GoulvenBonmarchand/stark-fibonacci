"""Finite field arithmetic over a STARK-friendly prime.

The default prime is p = 3 * 2^30 + 1 = 3221225473. Its multiplicative group
F_p^* is cyclic of order 3 * 2^30, so it contains a subgroup of order 2^k for
every 0 <= k <= 30. That makes binary FRI folding straightforward: each round
squares the generator of the current subgroup.
"""

from __future__ import annotations

from typing import Optional

DEFAULT_PRIME: int = 3 * (1 << 30) + 1


class FieldElement:
    """An element of a prime field F_p.

    Values are stored reduced mod p as a Python int. The class is intentionally
    minimal: arithmetic operators, hashing, equality, and a couple of static
    constructors.
    """

    __slots__ = ("value", "prime")

    def __init__(self, value: int, prime: int = DEFAULT_PRIME) -> None:
        if not isinstance(value, int):
            raise TypeError(f"FieldElement value must be int, got {type(value).__name__}")
        if prime <= 2:
            raise ValueError(f"prime must be > 2, got {prime}")
        self.prime = prime
        self.value = value % prime

    # -- constructors ---------------------------------------------------------

    @classmethod
    def from_int(cls, value: int, prime: int = DEFAULT_PRIME) -> "FieldElement":
        return cls(value, prime)

    @classmethod
    def zero(cls, prime: int = DEFAULT_PRIME) -> "FieldElement":
        return cls(0, prime)

    @classmethod
    def one(cls, prime: int = DEFAULT_PRIME) -> "FieldElement":
        return cls(1, prime)

    # -- predicates -----------------------------------------------------------

    def is_zero(self) -> bool:
        return self.value == 0

    def is_one(self) -> bool:
        return self.value == 1

    # -- core arithmetic ------------------------------------------------------

    def __add__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(self.value + other.value, self.prime)

    def __radd__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(other.value + self.value, self.prime)

    def __sub__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(self.value - other.value, self.prime)

    def __rsub__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(other.value - self.value, self.prime)

    def __neg__(self) -> "FieldElement":
        return FieldElement(-self.value, self.prime)

    def __mul__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(self.value * other.value, self.prime)

    def __rmul__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        return FieldElement(other.value * self.value, self.prime)

    def __pow__(self, exponent: int) -> "FieldElement":
        if not isinstance(exponent, int):
            raise TypeError("exponent must be int")
        if exponent < 0:
            return self.inverse() ** (-exponent)
        return FieldElement(pow(self.value, exponent, self.prime), self.prime)

    def __truediv__(self, other) -> "FieldElement":
        other = self._coerce(other)
        self._check_prime(other)
        if other.value == 0:
            raise ZeroDivisionError("division by zero in field")
        # a / b = a * b^(p-2)  by Fermat's little theorem
        inv = pow(other.value, self.prime - 2, self.prime)
        return FieldElement(self.value * inv, self.prime)

    def inverse(self) -> "FieldElement":
        if self.value == 0:
            raise ZeroDivisionError("zero has no inverse")
        return FieldElement(pow(self.value, self.prime - 2, self.prime), self.prime)

    # -- comparison & hashing -------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FieldElement):
            return NotImplemented
        return self.prime == other.prime and self.value == other.value

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    def __hash__(self) -> int:
        return hash((self.value, self.prime))

    def __repr__(self) -> str:
        return f"FieldElement({self.value})"

    def __int__(self) -> int:
        return self.value

    # -- helpers --------------------------------------------------------------

    def _check_prime(self, other: "FieldElement") -> None:
        if self.prime != other.prime:
            raise ValueError(
                f"field mismatch: {self.prime} vs {other.prime}"
            )

    def _coerce(self, other):
        """Convert an int to a FieldElement of the same prime, or pass through."""
        if isinstance(other, FieldElement):
            return other
        if isinstance(other, int):
            return FieldElement(other, self.prime)
        return NotImplemented


# ---------------------------------------------------------------------------
# Domain generation
# ---------------------------------------------------------------------------

# Order of the 2-Sylow subgroup of F_p^*  (= 2^30 for the default prime).
MAX_TWO_ADIC_ORDER: int = 30


def primitive_root(prime: int = DEFAULT_PRIME) -> int:
    """Return a generator of F_p^*, computed by trial.

    A small candidate is iterated until `g^((p-1)/q) != 1` for every prime
    factor q of (p-1). For our default prime p-1 = 3 * 2^30 so only q in {2, 3}.
    """
    p = prime
    factors = _prime_factors(p - 1)
    g = 2
    while g < p:
        ok = True
        for q in factors:
            if pow(g, (p - 1) // q, p) == 1:
                ok = False
                break
        if ok:
            return g
        g += 1
    raise RuntimeError("no primitive root found (should not happen for primes)")


def two_adic_generator(prime: int = DEFAULT_PRIME, order: int = MAX_TWO_ADIC_ORDER) -> int:
    """Return g such that <g> is the 2-Sylow subgroup of F_p^*.

    Result has multiplicative order exactly 2^order. Validated.
    """
    if order < 0 or order > MAX_TWO_ADIC_ORDER:
        raise ValueError(f"order must be in [0, {MAX_TWO_ADIC_ORDER}], got {order}")
    g = primitive_root(prime)
    # raise to power (p-1)/2^order so that the result has order 2^order
    h = pow(g, (prime - 1) >> order, prime)
    assert pow(h, 1 << order, prime) == 1
    assert pow(h, 1 << (order - 1), prime) != 1 or order == 0
    return h


def subgroup_of_order(prime: int = DEFAULT_PRIME, order: int = 1) -> list[int]:
    """Return the unique subgroup of F_p^* of multiplicative order `order`.

    The order must be a power of 2 (and <= MAX_TWO_ADIC_ORDER).
    Returned as a Python list of ints, sorted ascending.
    """
    if order <= 0 or (order & (order - 1)) != 0:
        raise ValueError(f"order must be a positive power of 2, got {order}")
    if order > (1 << MAX_TWO_ADIC_ORDER):
        raise ValueError(f"order exceeds 2^{MAX_TWO_ADIC_ORDER}")
    g = two_adic_generator(prime, MAX_TWO_ADIC_ORDER)
    base = pow(g, 1 << (MAX_TWO_ADIC_ORDER - order.bit_length() + 1), prime)
    elements = [1]
    cur = 1
    for _ in range(order - 1):
        cur = (cur * base) % prime
        elements.append(cur)
    elements.sort()
    return elements


def coset_of_subgroup(subgroup: list[int], shift: int, prime: int = DEFAULT_PRIME) -> list[int]:
    """Return the coset {shift * g : g in subgroup} mod prime, sorted ascending."""
    out = sorted((shift * g) % prime for g in subgroup)
    return out


def sample_in_field(seed: bytes, prime: int = DEFAULT_PRIME) -> int:
    """Deterministically sample an int in [0, prime) from a byte seed."""
    import hashlib
    if not seed:
        raise ValueError("seed must be non-empty")
    out = int.from_bytes(hashlib.sha256(seed).digest(), "big")
    return out % prime


def _prime_factors(n: int) -> list[int]:
    """Return sorted list of distinct prime factors of n."""
    factors: list[int] = []
    d = 2
    while d * d <= n:
        if n % d == 0:
            factors.append(d)
            while n % d == 0:
                n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors