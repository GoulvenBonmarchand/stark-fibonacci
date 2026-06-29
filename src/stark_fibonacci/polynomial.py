"""Polynomial operations over a finite field.

Polynomials are stored as lists of coefficients in ascending degree:
    coeffs[i] is the coefficient of x^i.

For the trace sizes used in this project (up to a few hundred elements),
plain O(n^2) Lagrange interpolation is fast enough; no FFT is used.
"""

from __future__ import annotations

from typing import Iterable, Sequence

from .field import FieldElement


# ---------------------------------------------------------------------------
# Core polynomial helpers
# ---------------------------------------------------------------------------

def zero_poly() -> list[FieldElement]:
    return [FieldElement.zero()]


def is_zero(coeffs: Sequence[FieldElement]) -> bool:
    return all(c.is_zero() for c in coeffs)


def strip(coeffs: Sequence[FieldElement]) -> list[FieldElement]:
    """Remove trailing zero high-degree coefficients."""
    end = len(coeffs)
    while end > 1 and coeffs[end - 1].is_zero():
        end -= 1
    return list(coeffs[:end])


def degree(coeffs: Sequence[FieldElement]) -> int:
    s = strip(coeffs)
    return len(s) - 1 if s else -1


def eval_poly_at(coeffs: Sequence[FieldElement], x: FieldElement) -> FieldElement:
    """Horner evaluation of polynomial at point x."""
    if not coeffs:
        return FieldElement.zero()
    acc = coeffs[-1]
    for c in reversed(coeffs[:-1]):
        acc = acc * x + c
    return acc


def add_polys(a: Sequence[FieldElement], b: Sequence[FieldElement]) -> list[FieldElement]:
    n = max(len(a), len(b))
    out = [FieldElement.zero() for _ in range(n)]
    for i, c in enumerate(a):
        out[i] = out[i] + c
    for i, c in enumerate(b):
        out[i] = out[i] + c
    return strip(out)


def sub_polys(a: Sequence[FieldElement], b: Sequence[FieldElement]) -> list[FieldElement]:
    n = max(len(a), len(b))
    out = [FieldElement.zero() for _ in range(n)]
    for i, c in enumerate(a):
        out[i] = out[i] + c
    for i, c in enumerate(b):
        out[i] = out[i] - c
    return strip(out)


def scalar_mul(coeffs: Sequence[FieldElement], s: FieldElement) -> list[FieldElement]:
    return strip([c * s for c in coeffs])


def mul_polys(a: Sequence[FieldElement], b: Sequence[FieldElement]) -> list[FieldElement]:
    """Schoolbook polynomial multiplication."""
    if not a or not b:
        return zero_poly()
    n = len(a) + len(b) - 1
    out = [FieldElement.zero() for _ in range(n)]
    for i, ca in enumerate(a):
        if ca.is_zero():
            continue
        for j, cb in enumerate(b):
            if cb.is_zero():
                continue
            out[i + j] = out[i + j] + ca * cb
    return strip(out)


def scale_and_add(coeffs: Sequence[FieldElement], s: FieldElement) -> list[FieldElement]:
    """Return strip(coeffs * s + constant?), actually: add s as constant term shift.

    Kept for compatibility with future APIs; currently unused.
    """
    return scalar_mul(coeffs, s)


# ---------------------------------------------------------------------------
# Polynomial division
# ---------------------------------------------------------------------------

def poly_div(
    num: Sequence[FieldElement], den: Sequence[FieldElement]
) -> tuple[list[FieldElement], list[FieldElement]]:
    """Divide `num` by `den` in F[x], returning (quotient, remainder)."""
    if is_zero(den):
        raise ZeroDivisionError("division by zero polynomial")
    a = strip(list(num))
    b = strip(list(den))
    if len(a) < len(b):
        return zero_poly(), a
    # Lead coefficient inversion
    lead_b_inv = b[-1].inverse()
    q: list[FieldElement | None] = [None] * (len(a) - len(b) + 1)
    r = list(a)
    while len(r) >= len(b) and not is_zero(r):
        coef = r[-1] * lead_b_inv
        idx = len(r) - len(b)
        q[idx] = coef
        for i, cb in enumerate(b):
            r[idx + i] = r[idx + i] - coef * cb
        r = strip(r)
    out_q = [c if c is not None else FieldElement.zero() for c in q]
    return strip(out_q), strip(r) if r else zero_poly()


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def vanishing_poly_coeffs(domain: Sequence[FieldElement]) -> list[FieldElement]:
    """Return coefficients of Z(x) = prod_{d in domain}(x - d)."""
    coeffs: list[FieldElement] = [FieldElement.one()]
    for d in domain:
        coeffs = mul_polys(coeffs, [-d, FieldElement.one()])
    return strip(coeffs)


def vanishing_eval_at(
    domain: Sequence[FieldElement], x: FieldElement
) -> FieldElement:
    """Evaluate Z(x) = prod_{d in domain}(x - d) at x without materializing coeffs."""
    acc = FieldElement.one()
    for d in domain:
        acc = acc * (x - d)
    return acc


def evaluate_on_domain(
    coeffs: Sequence[FieldElement], domain: Sequence[FieldElement]
) -> list[FieldElement]:
    """Evaluate a polynomial on every point of `domain`."""
    return [eval_poly_at(coeffs, x) for x in domain]


# ---------------------------------------------------------------------------
# Lagrange interpolation
# ---------------------------------------------------------------------------

def interpolate_lagrange(
    domain: Sequence[FieldElement], values: Sequence[FieldElement]
) -> list[FieldElement]:
    """Lagrange interpolation through (domain[i], values[i]).

    Returns coefficients in ascending degree. O(n^2) time, O(n) space.
    """
    n = len(domain)
    if n != len(values):
        raise ValueError("domain and values must have same length")
    if n == 0:
        return zero_poly()
    # denominators[i] = prod_{j != i} (domain[i] - domain[j])
    denom: list[FieldElement] = []
    for i in range(n):
        prod = FieldElement.one()
        di = domain[i]
        for j in range(n):
            if j == i:
                continue
            prod = prod * (di - domain[j])
        denom.append(prod)
    out: list[FieldElement] = [FieldElement.zero() for _ in range(n)]
    for i in range(n):
        wi = values[i] * denom[i].inverse()
        # add wi * prod_{j != i} (x - domain[j])
        basis = [FieldElement.one()]
        for j in range(n):
            if j == i:
                continue
            basis = mul_polys(basis, [-domain[j], FieldElement.one()])
        for k, c in enumerate(basis):
            out[k] = out[k] + wi * c
    return strip(out)


# ---------------------------------------------------------------------------
# Low-degree extension
# ---------------------------------------------------------------------------

def low_degree_extension(
    trace_domain: Sequence[FieldElement],
    trace_values: Sequence[FieldElement],
    lde_domain: Sequence[FieldElement],
) -> list[FieldElement]:
    """Given evaluations on `trace_domain`, return evaluations on the larger
    `lde_domain` (assumed to be a strict superset), by Lagrange interpolation.

    A naive O(|lde| * |trace|) algorithm; acceptable for the sizes used here.
    """
    if len(trace_domain) != len(trace_values):
        raise ValueError("trace domain/values length mismatch")
    # Pre-compute barycentric-style weights for stability when trace_domain is large.
    # For our sizes we just do direct Lagrange evaluation at each lde point.
    n = len(trace_domain)
    out: list[FieldElement] = []
    for x in lde_domain:
        # L(x) = sum_i values[i] * prod_{j != i} (x - trace_domain[j]) / (trace_domain[i] - trace_domain[j])
        num = FieldElement.zero()
        for i in range(n):
            wi = FieldElement.one()
            di = trace_domain[i]
            for j in range(n):
                if j == i:
                    continue
                wi = wi * (x - trace_domain[j]) * (di - trace_domain[j]).inverse()
            num = num + trace_values[i] * wi
        out.append(num)
    return out