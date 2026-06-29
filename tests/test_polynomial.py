"""Tests for polynomial operations over a finite field."""

import pytest

from stark_fibonacci.field import FieldElement, subgroup_of_order
from stark_fibonacci.polynomial import (
    add_polys,
    degree,
    eval_poly_at,
    evaluate_on_domain,
    interpolate_lagrange,
    low_degree_extension,
    mul_polys,
    poly_div,
    scalar_mul,
    strip,
    sub_polys,
    vanishing_eval_at,
    vanishing_poly_coeffs,
    zero_poly,
)


@pytest.fixture
def fe():
    """Shorthand constructor bound to the default prime."""
    return lambda x: FieldElement(x)


def test_zero_poly_and_degree():
    z = zero_poly()
    assert degree(z) == 0
    assert z[0].is_zero()


def test_strip_removes_trailing_zeros(fe):
    p = [fe(1), fe(2), fe(0), fe(0)]
    assert strip(p) == [fe(1), fe(2)]


def test_strip_keeps_middle_zeros(fe):
    p = [fe(1), fe(0), fe(2)]
    assert strip(p) == [fe(1), fe(0), fe(2)]


def test_horner_evaluation(fe):
    # p(x) = 1 + 2x + 3x^2
    p = [fe(1), fe(2), fe(3)]
    assert int(eval_poly_at(p, fe(5))) == 1 + 2 * 5 + 3 * 25
    assert eval_poly_at(p, fe(0)) == fe(1)


def test_add_sub_mul_polys(fe):
    a = [fe(1), fe(2), fe(3)]   # 1 + 2x + 3x^2
    b = [fe(10), fe(20)]        # 10 + 20x
    s = add_polys(a, b)
    assert s == [fe(11), fe(22), fe(3)]
    d = sub_polys(a, b)
    assert d == [fe(-9 % FieldElement(0).prime), fe(-18 % FieldElement(0).prime), fe(3)]
    m = mul_polys(a, b)
    # (1 + 2x + 3x^2)(10 + 20x) = 10 + 40x + 70x^2 + 60x^3
    assert m == [fe(10), fe(40), fe(70), fe(60)]


def test_scalar_mul(fe):
    a = [fe(1), fe(2), fe(3)]
    s = scalar_mul(a, fe(5))
    assert s == [fe(5), fe(10), fe(15)]


def test_poly_div_exact(fe):
    # (x^3 + x^2 + x + 1) / (x + 1) = x^2 + 1 (in F_p, x^3+1 = (x+1)(x^2-x+1)
    # Actually let's just check (x^4 - 1) / (x - 1) = x^3 + x^2 + x + 1
    num = [fe(-1), fe(0), fe(0), fe(0), fe(1)]
    den = [fe(-1), fe(1)]
    q, r = poly_div(num, den)
    assert r == [fe(0)]
    expected_q = [fe(1), fe(1), fe(1), fe(1)]
    assert q == expected_q


def test_poly_div_with_remainder(fe):
    # (x^2 + 1) / x = x (quotient), 1 (remainder)
    num = [fe(1), fe(0), fe(1)]
    den = [fe(0), fe(1)]
    q, r = poly_div(num, den)
    assert q == [fe(0), fe(1)]
    assert r == [fe(1)]


def test_lagrange_interpolation_round_trip(fe):
    H = [fe(x) for x in subgroup_of_order(order=64)]
    vals = [fe(i * i + 7) for i in range(64)]
    p = interpolate_lagrange(H, vals)
    for x, v in zip(H, vals):
        assert eval_poly_at(p, x) == v


def test_vanishing_poly(fe):
    H = [fe(x) for x in subgroup_of_order(order=32)]
    Z = vanishing_poly_coeffs(H)
    for x in H:
        assert eval_poly_at(Z, x).is_zero()


def test_vanishing_eval_at():
    H = [FieldElement(x) for x in subgroup_of_order(order=16)]
    x = FieldElement(123)
    Z_coeffs = vanishing_poly_coeffs(H)
    assert eval_poly_at(Z_coeffs, x) == vanishing_eval_at(H, x)


def test_evaluate_on_domain(fe):
    H = [fe(x) for x in subgroup_of_order(order=8)]
    p = [fe(1), fe(2), fe(3), fe(4)]
    vals = evaluate_on_domain(p, H)
    for x, v in zip(H, vals):
        assert v == eval_poly_at(p, x)


def test_low_degree_extension(fe):
    H_small = [fe(x) for x in subgroup_of_order(order=8)]
    vals_small = [fe(i * i + 3) for i in range(8)]
    H_big = [fe(x) for x in subgroup_of_order(order=16)]
    extended = low_degree_extension(H_small, vals_small, H_big)
    p = interpolate_lagrange(H_small, vals_small)
    for x, v in zip(H_big, extended):
        assert v == eval_poly_at(p, x)


def test_low_degree_extension_consistency_with_interp(fe):
    H_small = [fe(x) for x in subgroup_of_order(order=8)]
    vals_small = [fe(i * 3 + 1) for i in range(8)]
    H_big = [fe(x) for x in subgroup_of_order(order=16)]
    p = interpolate_lagrange(H_small, vals_small)
    extended = low_degree_extension(H_small, vals_small, H_big)
    for x, v in zip(H_big, extended):
        assert v == eval_poly_at(p, x)


def test_degree(fe):
    assert degree([fe(0)]) == 0
    assert degree([fe(0), fe(0)]) == 0
    assert degree([fe(1)]) == 0
    assert degree([fe(0), fe(1)]) == 1  # polynomial is x
    assert degree([fe(1), fe(2), fe(3)]) == 2
    assert degree([fe(1), fe(2), fe(0)]) == 1  # trailing zero stripped


def test_poly_div_by_zero_raises():
    with pytest.raises(ZeroDivisionError):
        poly_div([FieldElement(1)], [FieldElement(0)])


def test_interpolate_requires_same_length():
    with pytest.raises(ValueError):
        interpolate_lagrange([FieldElement(1), FieldElement(2)], [FieldElement(0)])


def test_mul_polys_by_zero():
    zero = [FieldElement(0)]
    a = [FieldElement(1), FieldElement(2)]
    assert mul_polys(a, zero) == zero_poly() or mul_polys(a, zero) == [FieldElement(0)]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])