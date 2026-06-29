"""Tests for finite field arithmetic and domain generation."""

import pytest

from stark_fibonacci.field import (
    DEFAULT_PRIME,
    FieldElement,
    MAX_TWO_ADIC_ORDER,
    coset_of_subgroup,
    primitive_root,
    sample_in_field,
    subgroup_of_order,
    two_adic_generator,
)


def test_default_prime_is_st_friendly():
    # p = 3 * 2^30 + 1
    assert DEFAULT_PRIME == 3 * (1 << 30) + 1
    # 2 is a primitive root mod p (order = p-1 = 3 * 2^30)
    g = primitive_root(DEFAULT_PRIME)
    assert pow(g, DEFAULT_PRIME - 1, DEFAULT_PRIME) == 1
    # Order of g divides p-1 and is a multiple of 3 * 2^30 / gcd
    for q in [2, 3]:
        assert pow(g, (DEFAULT_PRIME - 1) // q, DEFAULT_PRIME) != 1


def test_two_adic_generator_has_correct_order():
    g = two_adic_generator(DEFAULT_PRIME, MAX_TWO_ADIC_ORDER)
    assert pow(g, 1 << MAX_TWO_ADIC_ORDER, DEFAULT_PRIME) == 1
    # And no smaller power should give 1.
    for k in range(0, MAX_TWO_ADIC_ORDER):
        assert pow(g, 1 << k, DEFAULT_PRIME) != 1 or k == MAX_TWO_ADIC_ORDER


def test_subgroup_of_order():
    for k in range(0, 6):
        H = subgroup_of_order(DEFAULT_PRIME, 1 << k)
        assert len(H) == (1 << k)
        # Closure under multiplication (sample check).
        for i in range(min(8, len(H))):
            for j in range(min(8, len(H))):
                assert (H[i] * H[j]) % DEFAULT_PRIME in H


def test_fieldelement_basic_arithmetic():
    a = FieldElement(123)
    b = FieldElement(456)
    assert int(a + b) == 579
    assert int(a - b) == (123 - 456) % DEFAULT_PRIME
    assert int(a * b) == (123 * 456) % DEFAULT_PRIME
    assert int(-a) == (-123) % DEFAULT_PRIME


def test_fieldelement_inverse_and_division():
    a = FieldElement(789012)
    inv = a.inverse()
    assert a * inv == FieldElement.one()
    assert a / a == FieldElement.one()
    assert a / FieldElement(2) == FieldElement(789012) * FieldElement(2).inverse()


def test_fieldelement_pow_negative():
    a = FieldElement(5)
    assert a ** (-1) == a.inverse()
    assert a ** 0 == FieldElement.one()
    assert a ** 1 == a
    assert int(a ** 10) == pow(5, 10, DEFAULT_PRIME)


def test_fieldelement_equality_and_hash():
    a = FieldElement(42)
    b = FieldElement(42)
    c = FieldElement(43)
    assert a == b
    assert a != c
    assert hash(a) == hash(b)
    assert {a, b, c} == {a, c}


def test_fieldelement_modular_reduction():
    a = FieldElement(DEFAULT_PRIME + 5)
    assert int(a) == 5


def test_fieldelement_mixed_arithmetic():
    a = FieldElement(7)
    assert int(a + 5) == 12
    assert int(a * 3) == 21
    assert int(10 - a) == 3
    assert int(2 * a) == 14


def test_sample_in_field():
    for seed in [b"abc", b"", b"x" * 100]:
        if seed:
            v = sample_in_field(seed)
            assert 0 <= v < DEFAULT_PRIME


def test_coset_of_subgroup():
    H = subgroup_of_order(DEFAULT_PRIME, 8)
    coset = coset_of_subgroup(H, 5)
    assert len(coset) == 8
    assert set(coset) == {(5 * h) % DEFAULT_PRIME for h in H}


def test_fieldelement_zero_and_one():
    assert FieldElement.zero().is_zero()
    assert FieldElement.one().is_one()
    assert not FieldElement(1).is_zero()
    assert not FieldElement(0).is_one()


def test_fieldelement_invalid_construction():
    with pytest.raises(TypeError):
        FieldElement("not an int")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        FieldElement(1, prime=2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])