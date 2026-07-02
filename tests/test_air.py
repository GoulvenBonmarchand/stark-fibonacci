"""Tests for the Fibonacci AIR."""

from __future__ import annotations

import pytest

from stark_fibonacci.air import FibonacciAIR
from stark_fibonacci.domain import (
    multiplicative_subgroup,
    primitive_root_of_unity,
)
from stark_fibonacci.field import FieldElement
from stark_fibonacci.polynomial import Polynomial
from stark_fibonacci.trace import fibonacci_trace


def _make_air(
    c0: int = 1, c1: int = 1, n: int = 8, c: int | None = None
) -> FibonacciAIR:
    trace = fibonacci_trace(c0, c1, n)
    return FibonacciAIR(
        c0=FieldElement(c0),
        c1=FieldElement(c1),
        claimed_output=FieldElement(c if c is not None else trace[-1].value),
        trace_length=n,
    )


def test_creation_and_attributes() -> None:
    air = _make_air()
    assert air.c0 == 1
    assert air.c1 == 1
    assert air.trace_length == 8


def test_invalid_trace_length() -> None:
    with pytest.raises(ValueError):
        FibonacciAIR(FieldElement(1), FieldElement(1), FieldElement(2), 1)
    with pytest.raises(ValueError):
        FibonacciAIR(FieldElement(1), FieldElement(1), FieldElement(2), 0)


def test_boundary_constraints_contents() -> None:
    air = _make_air(n=10, c=55)
    bcs = air.boundary_constraints()
    assert (0, FieldElement(1)) in bcs
    assert (1, FieldElement(1)) in bcs
    assert (10, FieldElement(55)) in bcs


def test_valid_trace_satisfies_boundary() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    assert air.verify_boundary(trace)


def test_modified_initial_fails_boundary() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    bad = list(trace)
    bad[0] = FieldElement(99)
    assert not air.verify_boundary(bad)


def test_modified_c1_fails_boundary() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    bad = list(trace)
    bad[1] = FieldElement(99)
    assert not air.verify_boundary(bad)


def test_final_constraint_verified() -> None:
    air = _make_air(n=10, c=89)
    trace = fibonacci_trace(1, 1, 10)
    assert trace[air.trace_length] == FieldElement(89)


def test_wrong_claimed_output_fails_boundary() -> None:
    air = _make_air(n=10, c=999)  # wrong
    trace = fibonacci_trace(1, 1, 10)
    assert not air.verify_boundary(trace)


def test_valid_trace_satisfies_transition() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    assert air.transition_constraint()(trace)


def test_modified_trace_fails_transition() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    bad = list(trace)
    bad[5] = FieldElement(0)  # break the recurrence at index 5
    assert not air.transition_constraint()(bad)


def test_transition_evaluation_at_each_index() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    for i in range(air.trace_length - 1):
        assert air.transition_evaluation(trace, i) == 0


def test_transition_polynomial_zero_on_valid_trace() -> None:
    n = 10
    air = _make_air(n=n)
    trace = fibonacci_trace(1, 1, n)
    domain_size = 16
    domain = multiplicative_subgroup(domain_size)
    g = primitive_root_of_unity(domain_size)
    points = [(domain[i], trace[i]) for i in range(n + 1)]
    T = Polynomial.lagrange_interpolate(points)
    poly = air.transition_polynomial(T, g)
    for i in range(n - 1):
        assert poly.evaluate(domain[i]) == 0


def test_transition_polynomial_non_zero_off_valid_anchors() -> None:
    n = 10
    air = _make_air(n=n)
    trace = fibonacci_trace(1, 1, n)
    domain_size = 16
    domain = multiplicative_subgroup(domain_size)
    g = primitive_root_of_unity(domain_size)
    points = [(domain[i], trace[i]) for i in range(n + 1)]
    T = Polynomial.lagrange_interpolate(points)
    poly = air.transition_polynomial(T, g)
    assert poly.evaluate(domain[n - 1]) != 0
    assert poly.evaluate(domain[n]) != 0


def test_verify_combines_boundary_and_transition() -> None:
    air = _make_air(n=10)
    trace = fibonacci_trace(1, 1, 10)
    assert air.verify(trace)
    bad = list(trace)
    bad[3] = FieldElement(0)
    assert not air.verify(bad)
