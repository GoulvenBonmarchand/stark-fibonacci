"""Tests for the prime field F_p arithmetic."""

from __future__ import annotations

import pytest
from hypothesis import assume, given, strategies as st

from stark_fibonacci.field import FIELD_PRIME, FieldElement


def test_from_int_reduces_mod_p() -> None:
    assert FieldElement.from_int(FIELD_PRIME) == 0
    assert FieldElement.from_int(FIELD_PRIME + 1) == 1
    assert FieldElement.from_int(-1) == FIELD_PRIME - 1
    assert FieldElement.from_int(2**1000) == FieldElement(pow(2, 1000, FIELD_PRIME))


def test_rejects_bool() -> None:
    with pytest.raises(TypeError):
        FieldElement(True)
    with pytest.raises(TypeError):
        FieldElement(False)


def test_zero_and_one() -> None:
    z = FieldElement.zero()
    o = FieldElement.one()
    a = FieldElement(42)
    assert a + z == a
    assert a - z == a
    assert a * z == z
    assert a * o == a
    assert a / o == a


def test_add_mod_p() -> None:
    a = FieldElement(FIELD_PRIME - 1)
    b = FieldElement(2)
    assert (a + b) == 1
    assert (a + b) == FieldElement(1)


def test_sub_mod_p() -> None:
    z = FieldElement.zero()
    o = FieldElement.one()
    assert z - o == FieldElement(FIELD_PRIME - 1)


def test_neg() -> None:
    a = FieldElement(5)
    assert -a == FieldElement(FIELD_PRIME - 5)
    assert a + (-a) == 0
    assert -FieldElement.zero() == FieldElement.zero()


def test_mul_mod_p() -> None:
    a = FieldElement(FIELD_PRIME - 1)
    assert a * a == 1
    b = FieldElement(FIELD_PRIME // 2)
    assert b + (-b) == 0


def test_inverse_roundtrip() -> None:
    a = FieldElement(7)
    b = a.inverse()
    assert a * b == 1
    assert b * a == 1


def test_inverse_of_inverse() -> None:
    a = FieldElement(123_456_789 % FIELD_PRIME)
    assert a.inverse().inverse() == a


def test_division() -> None:
    a = FieldElement(20)
    b = FieldElement(5)
    assert a / b == 4
    assert a / b == FieldElement(4)


def test_pow() -> None:
    a = FieldElement(2)
    assert a**10 == FieldElement(1024)
    assert a**0 == 1


def test_fermat_little_theorem() -> None:
    a = FieldElement(17)
    assert a ** (FIELD_PRIME - 1) == 1
    b = FieldElement(FIELD_PRIME - 3)
    assert b ** (FIELD_PRIME - 1) == 1


def test_division_by_zero_forbidden() -> None:
    z = FieldElement.zero()
    a = FieldElement(5)
    with pytest.raises(ZeroDivisionError):
        z.inverse()
    with pytest.raises(ZeroDivisionError):
        a / z


def test_int_arithmetic() -> None:
    a = FieldElement(7)
    assert a + 3 == 10
    assert a - 3 == 4
    assert a * 3 == 21
    assert a**3 == FieldElement(343)
    assert 3 + a == 10
    assert 3 * a == 21


def test_hashable() -> None:
    s = {FieldElement(1), FieldElement(1), FieldElement(2)}
    assert len(s) == 2


small_ints = st.integers(min_value=0, max_value=FIELD_PRIME - 1)
field_elements = small_ints.map(FieldElement)


@given(a=field_elements, b=field_elements, c=field_elements)
def test_add_associativity(a: FieldElement, b: FieldElement, c: FieldElement) -> None:
    assert (a + b) + c == a + (b + c)


@given(a=field_elements, b=field_elements)
def test_add_commutativity(a: FieldElement, b: FieldElement) -> None:
    assert a + b == b + a


@given(a=field_elements, b=field_elements)
def test_mul_commutativity(a: FieldElement, b: FieldElement) -> None:
    assert a * b == b * a


@given(a=field_elements, b=field_elements, c=field_elements)
def test_distributivity(a: FieldElement, b: FieldElement, c: FieldElement) -> None:
    assert a * (b + c) == a * b + a * c


@given(a=field_elements)
def test_a_div_a_eq_one(a: FieldElement) -> None:
    assume(a.value != 0)
    assert a / a == 1
