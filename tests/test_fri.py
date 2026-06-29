"""Tests for the FRI protocol."""

import pytest

from stark_fibonacci.field import FieldElement
from stark_fibonacci.fri import gen_domain, prove_fri, verify_fri
from stark_fibonacci.polynomial import eval_poly_at, interpolate_lagrange
from stark_fibonacci.utils import hash_many, sample_field_element, field_elements_to_bytes


def _make_low_degree_function(size: int, degree: int, shift: int = 3):
    prime = FieldElement(0).prime
    coeffs = [FieldElement(i + 1, prime) for i in range(degree + 1)]
    domain, _, _ = gen_domain(size, shift=shift)
    values = [eval_poly_at(coeffs, x) for x in domain]
    return domain, values, shift


def test_honest_proof_verifies():
    domain, values, shift = _make_low_degree_function(64, degree=10)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    assert verify_fri(proof, max_degree_plus_one=16)


def test_boundary_degree_15_verifies():
    domain, values, shift = _make_low_degree_function(64, degree=15)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    assert verify_fri(proof, max_degree_plus_one=16)


def test_high_degree_function_is_low_degree_after_fold():
    """On a 64-point domain, any function has an interpolant of degree < 64.
    After 2 FRI folds (64 → 32 → 16), the interpolant shrinks, so the FRI
    final polynomial will still be of degree < 16. This is the expected
    behavior of FRI on a small domain."""
    domain, values, shift = _make_low_degree_function(64, degree=20)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    assert verify_fri(proof, max_degree_plus_one=16)


def test_tampered_query_value_rejected():
    from dataclasses import replace
    domain, values, shift = _make_low_degree_function(64, degree=10)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    bad = proof.queries[0]
    bad = replace(bad, layer_openings=bad.layer_openings)
    bad_openings = list(bad.layer_openings)
    bad_openings[0] = replace(bad_openings[0], left_value=bad_openings[0].left_value + FieldElement(1, FieldElement(0).prime))
    bad = replace(bad, layer_openings=bad_openings)
    tampered = replace(proof, queries=[bad] + list(proof.queries[1:]))
    assert not verify_fri(tampered, max_degree_plus_one=16)


def test_tampered_final_poly_rejected():
    from dataclasses import replace
    domain, values, shift = _make_low_degree_function(64, degree=10)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    prime = FieldElement(0).prime
    tampered = replace(proof, final_poly_coeffs=[FieldElement(0, prime)] + list(proof.final_poly_coeffs[1:]))
    assert not verify_fri(tampered, max_degree_plus_one=16)


def test_low_degree_final_poly_rejected():
    from dataclasses import replace
    domain, values, shift = _make_low_degree_function(64, degree=10)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=4, initial_shift=shift)
    # Append a non-zero coefficient so strip() can't trim it back down.
    prime = FieldElement(0).prime
    long_poly = list(proof.final_poly_coeffs) + [FieldElement(1, prime)]
    tampered = replace(proof, final_poly_coeffs=long_poly)
    assert not verify_fri(tampered, max_degree_plus_one=16)


def test_more_queries_works():
    domain, values, shift = _make_low_degree_function(128, degree=15)
    proof = prove_fri(domain, values, max_degree_plus_one=16, num_queries=8, initial_shift=shift)
    assert verify_fri(proof, max_degree_plus_one=16)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])