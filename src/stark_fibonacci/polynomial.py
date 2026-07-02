"""Polynomials over F_p represented by their coefficients (lowest degree first).

Form: P(x) = coeffs[0] + coeffs[1] x + ... + coeffs[d] x^d.
"""

from __future__ import annotations

from typing import Sequence


from stark_fibonacci.field import FieldElement


class Polynomial:
    """Polynomial over F_p."""

    def __init__(self, coeffs: Sequence[FieldElement | int]) -> None:
        if not coeffs:
            raise ValueError("polynomial must have at least one coefficient")
        normalized: list[FieldElement] = []
        for c in coeffs:
            if isinstance(c, FieldElement):
                normalized.append(c)
            elif isinstance(c, int) and not isinstance(c, bool):
                normalized.append(FieldElement(c))
            else:
                raise TypeError("coefficient must be a FieldElement or int")
        while len(normalized) > 1 and normalized[-1].value == 0:
            normalized.pop()
        self._coeffs: list[FieldElement] = normalized

    @classmethod
    def zero(cls) -> "Polynomial":
        return cls([0])

    @classmethod
    def one(cls) -> "Polynomial":
        return cls([1])

    @classmethod
    def constant(cls, c: FieldElement | int) -> "Polynomial":
        return cls([c])

    @property
    def coeffs(self) -> list[FieldElement]:
        return list(self._coeffs)

    def degree(self) -> int:
        return len(self._coeffs) - 1

    def is_zero(self) -> bool:
        return len(self._coeffs) == 1 and self._coeffs[0].value == 0

    def evaluate(self, x: FieldElement | int) -> FieldElement:
        if isinstance(x, int) and not isinstance(x, bool):
            x = FieldElement(x)
        if not isinstance(x, FieldElement):
            raise TypeError("x must be a FieldElement or int")
        result = FieldElement.zero()
        for c in reversed(self._coeffs):
            result = result * x + c
        return result

    def __add__(self, other: "Polynomial") -> "Polynomial":
        if not isinstance(other, Polynomial):
            return NotImplemented
        n = max(len(self._coeffs), len(other._coeffs))
        a = self._coeffs + [FieldElement.zero()] * (n - len(self._coeffs))
        b = other._coeffs + [FieldElement.zero()] * (n - len(other._coeffs))
        return Polynomial([a[i] + b[i] for i in range(n)])

    def __sub__(self, other: "Polynomial") -> "Polynomial":
        if not isinstance(other, Polynomial):
            return NotImplemented
        n = max(len(self._coeffs), len(other._coeffs))
        a = self._coeffs + [FieldElement.zero()] * (n - len(self._coeffs))
        b = other._coeffs + [FieldElement.zero()] * (n - len(other._coeffs))
        return Polynomial([a[i] - b[i] for i in range(n)])

    def __neg__(self) -> "Polynomial":
        return Polynomial([-c for c in self._coeffs])

    def __mul__(self, other: "Polynomial | FieldElement | int") -> "Polynomial":
        if isinstance(other, FieldElement):
            return Polynomial([c * other for c in self._coeffs])
        if isinstance(other, int) and not isinstance(other, bool):
            return Polynomial([c * FieldElement(other) for c in self._coeffs])
        if not isinstance(other, Polynomial):
            return NotImplemented
        n = len(self._coeffs) + len(other._coeffs) - 1
        result: list[FieldElement] = [FieldElement.zero()] * n
        for i, a in enumerate(self._coeffs):
            if a.value == 0:
                continue
            for j, b in enumerate(other._coeffs):
                if b.value == 0:
                    continue
                result[i + j] = result[i + j] + a * b
        return Polynomial(result)

    def __rmul__(self, other: "Polynomial | FieldElement | int") -> "Polynomial":
        return self.__mul__(other)

    def scale(self, s: FieldElement | int) -> "Polynomial":
        return self.__mul__(s)

    def divide_by(self, other: "Polynomial") -> tuple["Polynomial", "Polynomial"]:
        """Polynomial long division returning (quotient, remainder).

        Requires a non-zero divisor; in F_p every non-zero leading
        coefficient is a unit, so the algorithm always terminates.
        """
        if not isinstance(other, Polynomial):
            return NotImplemented
        if other.is_zero():
            raise ZeroDivisionError("division by zero polynomial")
        if other.degree() > self.degree():
            return Polynomial.zero(), Polynomial(self._coeffs)
        rem = list(self._coeffs)
        d = other._coeffs
        m = len(d)
        n = len(rem)
        lead_inv = d[-1].inverse()
        q_size = n - m + 1
        quot: list[FieldElement] = [FieldElement.zero()] * q_size
        for i in range(q_size - 1, -1, -1):
            coef = rem[i + m - 1] * lead_inv
            quot[i] = coef
            for j in range(m):
                rem[i + j] = rem[i + j] - coef * d[j]
        if m == 1:
            return Polynomial(quot), Polynomial.zero()
        remainder = rem[: m - 1]
        return Polynomial(quot), Polynomial(remainder)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Polynomial):
            return NotImplemented
        if self.is_zero() and other.is_zero():
            return True
        return self._coeffs == other._coeffs

    def __hash__(self) -> int:
        return hash(tuple(c.value for c in self._coeffs))

    def __repr__(self) -> str:
        if self.is_zero():
            return "Polynomial(0)"
        parts: list[str] = []
        for i, c in enumerate(self._coeffs):
            if c.value == 0:
                continue
            if i == 0:
                parts.append(f"{c.value}")
            elif i == 1:
                parts.append(f"{c.value}·X" if c.value != 1 else "X")
            else:
                parts.append(f"{c.value}·X^{i}" if c.value != 1 else f"X^{i}")
        return "Polynomial(" + " + ".join(parts) + ")"

    @staticmethod
    def lagrange_interpolate(
        points: Sequence[tuple[FieldElement, FieldElement]],
    ) -> "Polynomial":
        """Build the unique polynomial of degree < n interpolating n points.

        P(X) = sum_i y_i * L_i(X), where
        L_i(X) = prod_{j != i} (X - x_j) / (x_i - x_j).
        """
        coeffs = [FieldElement.zero()] * len(points)
        for i, (xi, yi) in enumerate(points):
            num: list[FieldElement] = [FieldElement.one()]
            denom = FieldElement.one()
            for j, (xj, _) in enumerate(points):
                if j == i:
                    continue
                num = Polynomial._multiply_by_linear(num, xj)
                denom = denom * (xi - xj)
            scale = yi * denom.inverse()
            for k, c in enumerate(num):
                coeffs[k] = coeffs[k] + c * scale
        return Polynomial(coeffs)

    @staticmethod
    def zerofier(domain: Sequence[FieldElement]) -> "Polynomial":
        """The unique monic polynomial vanishing exactly on the given domain."""
        result: list[FieldElement] = [FieldElement.one()]
        for d in domain:
            result = Polynomial._multiply_by_linear(result, d)
        return Polynomial(result)

    @staticmethod
    def interpolate_trace(
        trace: Sequence[FieldElement],
        domain: Sequence[FieldElement],
    ) -> "Polynomial":
        """Interpolate the trace on the first `len(trace)` points of the domain.

        Returns the unique polynomial of degree < len(trace) matching
        trace[i] at x = domain[i] for i in [0, len(trace)).
        """
        if len(domain) < len(trace):
            raise ValueError("domain must have at least len(trace) points")
        points = [(domain[i], trace[i]) for i in range(len(trace))]
        return Polynomial.lagrange_interpolate(points)

    @staticmethod
    def low_degree_extend(
        poly: "Polynomial",
        extended_domain: Sequence[FieldElement],
    ) -> list[FieldElement]:
        """Evaluate `poly` at each point of `extended_domain`."""
        return [poly.evaluate(x) for x in extended_domain]  # type: ignore[misc]  # x is FieldElement

    @staticmethod
    def _multiply_by_linear(
        poly: list[FieldElement], root: FieldElement
    ) -> list[FieldElement]:
        """Multiply a polynomial (coefficient form) by (X - root)."""
        new_len = len(poly) + 1
        out: list[FieldElement] = [FieldElement.zero()] * new_len
        out[0] = -root * poly[0]
        for k in range(1, len(poly)):
            out[k] = poly[k - 1] - root * poly[k]
        out[-1] = poly[-1]
        return out
