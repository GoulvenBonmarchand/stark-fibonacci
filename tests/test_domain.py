"""Tests for multiplicative subgroups and LDE domains."""

from __future__ import annotations

import pytest

from stark_fibonacci.domain import (
    _find_primitive_root,
    blowup_domain,
    multiplicative_subgroup,
    primitive_root_of_unity,
)
from stark_fibonacci.field import FIELD_PRIME


def test_primitive_root_is_primitive() -> None:
    r = _find_primitive_root()
    assert r ** (FIELD_PRIME - 1) == 1
    assert r ** ((FIELD_PRIME - 1) // 2) != 1
    assert r ** ((FIELD_PRIME - 1) // 3) != 1


def test_primitive_root_cached() -> None:
    r1 = _find_primitive_root()
    r2 = _find_primitive_root()
    assert r1 is r2


def test_primitive_root_of_unity_exact_order() -> None:
    for size in [1, 2, 4, 8, 16, 32, 64]:
        g = primitive_root_of_unity(size)
        assert g**size == 1
        if size > 1:
            assert g ** (size // 2) != 1


def test_primitive_root_of_unity_powers() -> None:
    g = primitive_root_of_unity(8)
    assert g**0 == 1
    assert g**4 == -1


def test_primitive_root_of_unity_invalid_order() -> None:
    with pytest.raises(ValueError):
        primitive_root_of_unity(5)
    with pytest.raises(ValueError):
        primitive_root_of_unity(FIELD_PRIME)
    with pytest.raises(ValueError):
        primitive_root_of_unity(0)
    with pytest.raises(ValueError):
        primitive_root_of_unity(-2)


def test_multiplicative_subgroup_size() -> None:
    for size in [1, 2, 4, 8, 16]:
        sub = multiplicative_subgroup(size)
        assert len(sub) == size


def test_multiplicative_subgroup_no_duplicates() -> None:
    for size in [2, 4, 8, 16, 32]:
        sub = multiplicative_subgroup(size)
        assert len({x.value for x in sub}) == size


def test_multiplicative_subgroup_first_is_one() -> None:
    sub = multiplicative_subgroup(16)
    assert sub[0] == 1


def test_multiplicative_subgroup_each_element_has_correct_order() -> None:
    for size in [1, 2, 4, 8, 16, 32]:
        sub = multiplicative_subgroup(size)
        for x in sub:
            assert x**size == 1


def test_multiplicative_subgroup_invalid_size() -> None:
    with pytest.raises(ValueError):
        multiplicative_subgroup(5)
    with pytest.raises(ValueError):
        multiplicative_subgroup(0)
    with pytest.raises(ValueError):
        multiplicative_subgroup(-1)


def test_blowup_domain_size() -> None:
    for base in [4, 8, 16]:
        for factor in [2, 4, 8]:
            d = blowup_domain(base, factor)
            assert len(d) == base * factor
            assert len({x.value for x in d}) == base * factor


def test_blowup_domain_negative_pairing() -> None:
    n = 16
    d = blowup_domain(n, 1)
    for i in range(n // 2):
        assert d[i] == -d[i + n // 2]


def test_blowup_domain_disjoint_from_subgroup() -> None:
    base = 8
    sub_set = {x.value for x in multiplicative_subgroup(base)}
    bd_set = {x.value for x in blowup_domain(base, 4)}
    assert sub_set.isdisjoint(bd_set)


def test_blowup_domain_invalid_size() -> None:
    with pytest.raises(ValueError):
        blowup_domain(5, 2)
    with pytest.raises(ValueError):
        blowup_domain(0, 2)
    with pytest.raises(ValueError):
        blowup_domain(4, 0)
