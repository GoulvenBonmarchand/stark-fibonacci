"""Field elements in F_p where p = 3 * 2**30 + 1 = 3221225473.

All arithmetic is performed modulo p using native Python ints, so no
overflow is possible. The multiplicative inverse of a non-zero element a
is computed as a**(p-2) via Fermat's little theorem.
"""

from __future__ import annotations

from dataclasses import dataclass


FIELD_PRIME: int = 3 * 2**30 + 1


@dataclass(frozen=True, slots=True)
class FieldElement:
    """Immutable element of F_p."""

    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or isinstance(self.value, bool):
            raise TypeError("FieldElement value must be a Python int")
        object.__setattr__(self, "value", self.value % FIELD_PRIME)

    @classmethod
    def from_int(cls, n: int) -> "FieldElement":
        """Build a FieldElement from any Python int (reduced modulo p)."""
        return cls(n)

    @classmethod
    def zero(cls) -> "FieldElement":
        """The additive identity."""
        return cls(0)

    @classmethod
    def one(cls) -> "FieldElement":
        """The multiplicative identity."""
        return cls(1)

    def __add__(self, other: "FieldElement | int") -> "FieldElement":
        if isinstance(other, FieldElement):
            return FieldElement(self.value + other.value)
        if isinstance(other, int) and not isinstance(other, bool):
            return FieldElement(self.value + other)
        return NotImplemented

    def __radd__(self, other: int) -> "FieldElement":
        return self.__add__(other)

    def __sub__(self, other: "FieldElement | int") -> "FieldElement":
        if isinstance(other, FieldElement):
            return FieldElement(self.value - other.value)
        if isinstance(other, int) and not isinstance(other, bool):
            return FieldElement(self.value - other)
        return NotImplemented

    def __rsub__(self, other: int) -> "FieldElement":
        return FieldElement(int(other) - self.value)

    def __neg__(self) -> "FieldElement":
        return FieldElement(-self.value)

    def __mul__(self, other: "FieldElement | int") -> "FieldElement":
        if isinstance(other, FieldElement):
            return FieldElement(self.value * other.value)
        if isinstance(other, int) and not isinstance(other, bool):
            return FieldElement(self.value * other)
        return NotImplemented

    def __rmul__(self, other: int) -> "FieldElement":
        return self.__mul__(other)

    def __truediv__(self, other: "FieldElement | int") -> "FieldElement":
        if isinstance(other, FieldElement):
            return self * other.inverse()
        if isinstance(other, int) and not isinstance(other, bool):
            return self * FieldElement(other).inverse()
        return NotImplemented

    def __rtruediv__(self, other: int) -> "FieldElement":
        return FieldElement(int(other)) * self.inverse()

    def __pow__(self, exponent: int) -> "FieldElement":
        if not isinstance(exponent, int) or isinstance(exponent, bool):
            raise TypeError("exponent must be an integer")
        return FieldElement(pow(self.value, exponent, FIELD_PRIME))

    def inverse(self) -> "FieldElement":
        """Multiplicative inverse via Fermat's little theorem."""
        if self.value == 0:
            raise ZeroDivisionError("cannot invert 0 in F_p")
        return FieldElement(pow(self.value, FIELD_PRIME - 2, FIELD_PRIME))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FieldElement):
            return self.value == other.value
        if isinstance(other, int) and not isinstance(other, bool):
            return self.value == other % FIELD_PRIME
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return f"FieldElement({self.value})"
