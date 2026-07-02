"""Tests for the Fibonacci trace generator."""

from __future__ import annotations

import pytest

from stark_fibonacci.field import FIELD_PRIME, FieldElement
from stark_fibonacci.trace import fibonacci_trace


def test_length() -> None:
    assert len(fibonacci_trace(1, 1, 4)) == 5
    assert len(fibonacci_trace(1, 1, 0)) == 1
    assert len(fibonacci_trace(1, 1, 1)) == 2
    assert len(fibonacci_trace(1, 1, 31)) == 32


def test_initial_values() -> None:
    trace = fibonacci_trace(2, 3, 5)
    assert trace[0] == 2
    assert trace[1] == 3


def test_recurrence_respected() -> None:
    trace = fibonacci_trace(1, 1, 7)
    for i in range(len(trace) - 2):
        assert trace[i + 2] == trace[i + 1] + trace[i]


def test_known_small_example() -> None:
    # Standard Fibonacci sequence
    trace = fibonacci_trace(1, 1, 7)
    expected = [1, 1, 2, 3, 5, 8, 13, 21]
    assert trace == [FieldElement(x) for x in expected]


def test_known_other_seeds() -> None:
    trace = fibonacci_trace(0, 1, 6)
    assert trace == [FieldElement(x) for x in [0, 1, 1, 2, 3, 5, 8]]


def test_zero_initial_seed() -> None:
    trace = fibonacci_trace(0, 0, 5)
    assert all(t == 0 for t in trace)


def test_modulo_p_wrapping() -> None:
    big = FIELD_PRIME - 1
    trace = fibonacci_trace(big, big, 4)
    for v in trace:
        assert 0 <= v.value < FIELD_PRIME
    for i in range(len(trace) - 2):
        assert trace[i + 2] == trace[i + 1] + trace[i]


def test_accepts_field_or_int() -> None:
    a = FieldElement(3)
    b = FieldElement(5)
    assert fibonacci_trace(a, b, 4) == fibonacci_trace(3, 5, 4)


def test_invalid_n() -> None:
    with pytest.raises(ValueError):
        fibonacci_trace(1, 1, -1)


def test_last_value_known() -> None:
    trace = fibonacci_trace(1, 1, 31)
    assert trace[-1] == 2178309
