"""Tests for polynomial arithmetic over F_p."""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings, strategies as st

from stark_fibonacci.domain import blowup_domain, multiplicative_subgroup
from stark_fibonacci.field import FIELD_PRIME, FieldElement
from stark_fibonacci.polynomial import Polynomial
from stark_fibonacci.trace import fibonacci_trace


def test_zero_and_one() -> None:
    z = Polynomial.zero()
    o = Polynomial.one()
    assert z.is_zero()
    assert o.evaluate(FieldElement(7)) == 1


def test_zero_is_zero() -> None:
    p = Polynomial([1, 2, 3]) - Polynomial([1, 2, 3])
    assert p.is_zero()
    assert (Polynomial([0]) + Polynomial([0, 0, 0])).is_zero()


def test_constant_evaluation() -> None:
    p = Polynomial.constant(5)
    assert p.degree() == 0
    assert p.evaluate(FieldElement(0)) == 5
    assert p.evaluate(FieldElement(123)) == 5
    assert p.evaluate(999) == 5


def test_linear_evaluation() -> None:
    p = Polynomial([3, 2])
    assert p.degree() == 1
    assert p.evaluate(0) == 3
    assert p.evaluate(1) == 5
    assert p.evaluate(10) == 23


def test_degree_strips_leading_zeros() -> None:
    assert Polynomial([1, 2, 3]).degree() == 2
    assert Polynomial([0, 0, 5]).degree() == 2
    assert Polynomial([0]).degree() == 0
    assert Polynomial([0, 0, 0]).degree() == 0


def test_evaluation_horner() -> None:
    p = Polynomial([1, 2, 3, 4])
    assert p.evaluate(0) == 1
    assert p.evaluate(1) == 10
    assert p.evaluate(2) == 49


def test_addition() -> None:
    a = Polynomial([1, 2, 3])
    b = Polynomial([4, 5])
    assert a + b == Polynomial([5, 7, 3])


def test_subtraction() -> None:
    a = Polynomial([1, 2, 3])
    b = Polynomial([4, 5])
    assert a - b == Polynomial([-3, -3, 3])


def test_negation() -> None:
    a = Polynomial([1, 2, 3])
    assert -a + a == Polynomial.zero()


def test_multiplication() -> None:
    a = Polynomial([1, 2])
    b = Polynomial([3, 4])
    assert a * b == Polynomial([3, 10, 8])
    assert (a * b).evaluate(5) == 253
    assert (a * b * Polynomial([1, 1])).evaluate(2) == (a * b).evaluate(2) * 3


def test_scale() -> None:
    a = Polynomial([1, 2, 3])
    s = FieldElement(7)
    b = a.scale(s)
    assert b.evaluate(2) == a.evaluate(2) * s


def test_lagrange_constant() -> None:
    points = [(FieldElement(0), FieldElement(5)), (FieldElement(1), FieldElement(5))]
    p = Polynomial.lagrange_interpolate(points)
    assert p.degree() == 0
    assert p.evaluate(0) == 5
    assert p.evaluate(7) == 5


def test_lagrange_recovers_known_polynomial() -> None:
    p = Polynomial([1, 2, 3])
    points = [(FieldElement(i), p.evaluate(i)) for i in range(3)]
    q = Polynomial.lagrange_interpolate(points)
    assert q == p


def test_lagrange_passes_through_more_points() -> None:
    p = Polynomial([2, 5, 7])
    points = [(FieldElement(i), p.evaluate(i)) for i in [0, 3, 7, 11, 19]]
    q = Polynomial.lagrange_interpolate(points)
    assert q == p
    for x, y in points:
        assert q.evaluate(x) == y


def test_evaluation_matches_interpolation() -> None:
    points = [
        (FieldElement(0), FieldElement(1)),
        (FieldElement(1), FieldElement(3)),
        (FieldElement(2), FieldElement(7)),
        (FieldElement(3), FieldElement(13)),
    ]
    p = Polynomial.lagrange_interpolate(points)
    for x, y in points:
        assert p.evaluate(x) == y


def test_division_exact() -> None:
    # (X^2 - 1) / (X - 1) = X + 1
    a = Polynomial([FIELD_PRIME - 1, 0, 1])
    b = Polynomial([FIELD_PRIME - 1, 1])
    q, r = a.divide_by(b)
    assert r.is_zero()
    assert q == Polynomial([1, 1])
    assert q * b + r == a


def test_division_with_remainder() -> None:
    # (X^2 + 1) / (X - 1): quotient X + 1, remainder 2
    a = Polynomial([1, 0, 1])
    b = Polynomial([FIELD_PRIME - 1, 1])
    q, r = a.divide_by(b)
    assert q == Polynomial([1, 1])
    assert r == Polynomial.constant(2)
    assert q * b + r == a


def test_division_by_constant() -> None:
    a = Polynomial([2, 4, 6])
    b = Polynomial.constant(2)
    q, r = a.divide_by(b)
    assert r.is_zero()
    assert q == Polynomial([1, 2, 3])
    assert q * b == a


def test_division_divisor_higher_degree() -> None:
    a = Polynomial([1, 1])
    b = Polynomial([1, 1, 1])
    q, r = a.divide_by(b)
    assert q.is_zero()
    assert r == a


def test_division_by_zero_raises() -> None:
    a = Polynomial([1, 2])
    with pytest.raises(ZeroDivisionError):
        a.divide_by(Polynomial.zero())


def test_zerofier_vanishes_on_domain() -> None:
    domain = [FieldElement(1), FieldElement(2), FieldElement(3), FieldElement(5)]
    z = Polynomial.zerofier(domain)
    assert z.degree() == len(domain)
    for d in domain:
        assert z.evaluate(d) == 0
    assert z.evaluate(FieldElement(4)) != 0


def test_zerofier_empty_domain_is_one() -> None:
    assert Polynomial.zerofier([]) == Polynomial.one()


def test_zerofier_single_element() -> None:
    z = Polynomial.zerofier([FieldElement(5)])
    assert z == Polynomial([-5, 1])
    assert z.evaluate(5) == 0


def test_rejects_non_int_or_field() -> None:
    with pytest.raises(TypeError):
        Polynomial([1, "x"])  # type: ignore[list-item]
    with pytest.raises(ValueError):
        Polynomial([])


def test_equality_normalizes() -> None:
    assert Polynomial([1, 2, 0]) == Polynomial([1, 2])
    assert Polynomial.zero() == Polynomial([0, 0, 0])


small_ints = st.integers(min_value=0, max_value=FIELD_PRIME - 1)


@given(coeffs=st.lists(small_ints, min_size=1, max_size=6))
def test_evaluation_uses_horner(coeffs: list[int]) -> None:
    p = Polynomial(coeffs)
    x = FieldElement(7)
    expected = FieldElement.zero()
    power = FieldElement.one()
    for c in coeffs:
        expected = expected + FieldElement(c) * power
        power = power * x
    assert p.evaluate(x) == expected


@given(
    points=st.lists(
        st.tuples(small_ints, small_ints),
        min_size=1,
        max_size=8,
    ).map(
        lambda lst: [
            (FieldElement(x) + FieldElement(i), FieldElement(y) + FieldElement(i))
            for i, (x, y) in enumerate(lst)
        ]
    )
)
@settings(max_examples=20)
def test_lagrange_passes_through_distinct_points(points) -> None:
    xs = [x for x, _ in points]
    assume(len(set(xs)) == len(xs))
    p = Polynomial.lagrange_interpolate(points)
    for x, y in points:
        assert p.evaluate(x) == y


def test_interpolate_trace_recovers_values_on_initial_domain() -> None:
    n = 8
    trace = fibonacci_trace(1, 1, n)
    domain_size = 16
    domain = multiplicative_subgroup(domain_size)
    T = Polynomial.interpolate_trace(trace, domain)
    assert T.degree() < len(trace)
    for i in range(len(trace)):
        assert T.evaluate(domain[i]) == trace[i]


def test_interpolate_trace_truncates_at_len_trace() -> None:
    n = 5
    trace = fibonacci_trace(1, 1, n)
    domain = multiplicative_subgroup(8)
    T = Polynomial.interpolate_trace(trace, domain)
    for i in range(len(trace)):
        assert T.evaluate(domain[i]) == trace[i]


def test_interpolate_trace_rejects_short_domain() -> None:
    trace = fibonacci_trace(1, 1, 4)
    domain = multiplicative_subgroup(4)
    with pytest.raises(ValueError):
        Polynomial.interpolate_trace(trace, domain)


def test_low_degree_extend_size() -> None:
    p = Polynomial([1, 2, 3])
    domain = [FieldElement(i + 1) for i in range(8)]
    lde = Polynomial.low_degree_extend(p, domain)
    assert len(lde) == 8


def test_low_degree_extend_matches_polynomial() -> None:
    p = Polynomial([1, 2, 3])
    domain = [FieldElement(i) for i in range(16)]
    lde = Polynomial.low_degree_extend(p, domain)
    for i, x in enumerate(domain):
        assert lde[i] == p.evaluate(x)


def test_low_degree_extend_to_blowup() -> None:
    n = 7
    trace = fibonacci_trace(1, 1, n)
    domain_size = 8
    base = multiplicative_subgroup(domain_size)
    extended = blowup_domain(domain_size, 4)
    T = Polynomial.interpolate_trace(trace, base)
    lde = Polynomial.low_degree_extend(T, extended)
    assert len(lde) == domain_size * 4
    for i, x in enumerate(extended):
        assert lde[i] == T.evaluate(x)
