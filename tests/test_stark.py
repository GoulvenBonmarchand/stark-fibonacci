"""End-to-end tests for the Fibonacci STARK."""

import pytest
from dataclasses import replace

from stark_fibonacci.field import FieldElement
from stark_fibonacci.stark import (
    StarkParams,
    generate_trace,
    prove_stark,
    verify_stark,
    recompute_composition,
    trace_domain_size,
)


def test_trace_generation_small():
    trace = generate_trace(1, 2, 7)
    assert [int(t) for t in trace] == [1, 2, 3, 5, 8, 13, 21, 34]


def test_trace_domain_size():
    assert trace_domain_size(2) == 4   # need 3 points, next pow2 = 4
    assert trace_domain_size(3) == 4
    assert trace_domain_size(7) == 8
    assert trace_domain_size(8) == 16  # need 9 points, next pow2 = 16
    assert trace_domain_size(31) == 32


def test_stark_small_n():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    assert verify_stark(proof)


def test_stark_medium_n():
    trace = generate_trace(1, 2, 31)
    params = StarkParams(c0=1, c1=2, N=31, C=int(trace[-1]),
                         blowup_factor=4, num_queries=8,
                         max_degree_plus_one=16, shift=3)
    proof = prove_stark(params)
    assert verify_stark(proof)


def test_stark_different_c0_c1():
    trace = generate_trace(3, 7, 15)
    params = StarkParams(c0=3, c1=7, N=15, C=int(trace[-1]),
                         blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    assert verify_stark(proof)


def test_stark_rejects_wrong_C():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    tampered = replace(proof, params=replace(proof.params, C=35))
    assert not verify_stark(tampered)


def test_stark_rejects_wrong_c0():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    tampered = replace(proof, params=replace(proof.params, c0=2))
    assert not verify_stark(tampered)


def test_stark_rejects_wrong_c1():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    tampered = replace(proof, params=replace(proof.params, c1=3))
    assert not verify_stark(tampered)


def test_stark_rejects_tampered_trace_value():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    bad_q = proof.queries[0]
    bad_q = replace(bad_q, trace_x_value=bad_q.trace_x_value + FieldElement(1, params.prime))
    bad_queries = list(proof.queries)
    bad_queries[0] = bad_q
    tampered = replace(proof, queries=bad_queries)
    assert not verify_stark(tampered)


def test_stark_rejects_tampered_composition_value():
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    bad_q = proof.queries[0]
    bad_q = replace(bad_q, comp_value=bad_q.comp_value + FieldElement(1, params.prime))
    bad_queries = list(proof.queries)
    bad_queries[0] = bad_q
    tampered = replace(proof, queries=bad_queries)
    assert not verify_stark(tampered)


def test_recompute_composition_consistency():
    """recompute_composition at the query's x must match the committed
    composition value (which the verifier checks in verify_stark)."""
    from stark_fibonacci.stark import build_trace_domain, two_adic_generator
    params = StarkParams(c0=1, c1=2, N=7, C=34, blowup_factor=4, num_queries=4,
                         max_degree_plus_one=8, shift=3)
    proof = prove_stark(params)
    prime = params.prime
    M = trace_domain_size(params.N)
    lde_size = params.blowup_factor * M
    lde_order = lde_size.bit_length() - 1
    g_lde = two_adic_generator(prime, lde_order)
    q = proof.queries[0]
    x = FieldElement((proof.fri_proof.initial_domain_shift * pow(g_lde, q.initial_index, prime)) % prime, prime)
    recomputed = recompute_composition(
        trace_x=q.trace_x_value,
        trace_gx=q.trace_gx_value,
        trace_g2x=q.trace_g2x_value,
        x=x,
        params=params,
    )
    assert recomputed == q.comp_value


def test_stark_params_validation():
    with pytest.raises(ValueError):
        StarkParams(c0=1, c1=1, N=0, C=0)
    with pytest.raises(ValueError):
        StarkParams(c0=1, c1=1, N=5, C=5, blowup_factor=3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])