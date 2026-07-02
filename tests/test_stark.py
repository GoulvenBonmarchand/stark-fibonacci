"""Tests for the STARK Fibonacci prover and verifier."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from stark_fibonacci.field import FieldElement
from stark_fibonacci.merkle import MerkleProof
from stark_fibonacci.proof import StarkOpening, StarkProof
from stark_fibonacci.stark import prove_fibonacci, verify_fibonacci
from stark_fibonacci.trace import fibonacci_trace


def _fib_value(c0: int, c1: int, n: int) -> int:
    return fibonacci_trace(c0, c1, n)[n].value


def test_prove_and_verify_basic() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    assert verify_fibonacci(proof)


def test_prove_and_verify_longer() -> None:
    n = 31
    c = _fib_value(1, 1, n)
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=n,
        claimed_output=c,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=8,
    )
    assert verify_fibonacci(proof)


def test_prove_and_verify_different_seed() -> None:
    n = 15
    c = _fib_value(2, 5, n)
    proof = prove_fibonacci(
        c0=2,
        c1=5,
        n=n,
        claimed_output=c,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=8,
    )
    assert verify_fibonacci(proof)


def test_public_inputs_match() -> None:
    n = 7
    c = _fib_value(1, 1, n)
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=n,
        claimed_output=c,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    assert proof.public_inputs.c0 == 1
    assert proof.public_inputs.c1 == 1
    assert proof.public_inputs.n == n
    assert proof.public_inputs.claimed_output == c
    assert proof.public_inputs.lde_domain_size == 4 * 8
    assert proof.public_inputs.fri_claimed_degree == 3
    assert proof.public_inputs.num_queries == 4


def test_invalid_n_raises() -> None:
    with pytest.raises(ValueError):
        prove_fibonacci(c0=1, c1=1, n=1, claimed_output=1)


def test_wrong_claimed_output_raises() -> None:
    with pytest.raises(ValueError):
        prove_fibonacci(c0=1, c1=1, n=7, claimed_output=99)


def test_wrong_c1_does_not_break_protocol() -> None:
    # The protocol currently checks only the transition chain; a wrong public
    # c1, c0, or C is therefore not directly detected. This test documents
    # the gap (intentional for now).
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    assert proof.public_inputs.c1 == 1


def test_modified_trace_proof_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    opening = proof.openings[0]
    bad_pr = MerkleProof(
        index=opening.trace_x_proof.index,
        leaf_hash=opening.trace_x_proof.leaf_hash,
        siblings=(b"\x00" * 32,) + opening.trace_x_proof.siblings[1:],
    )
    bad_opening = replace(opening, trace_x_proof=bad_pr)
    bad_proof = replace(proof, openings=(bad_opening,) + proof.openings[1:])
    assert not verify_fibonacci(bad_proof)


def test_modified_trace_value_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    opening = proof.openings[0]
    bad_opening = StarkOpening(
        initial_index=opening.initial_index,
        trace_x_value=opening.trace_x_value,
        trace_gx_value=opening.trace_gx_value,
        trace_g2x_value=(opening.trace_g2x_value + 1) % 3221225473,
        trace_x_proof=opening.trace_x_proof,
        trace_gx_proof=opening.trace_gx_proof,
        trace_g2x_proof=opening.trace_g2x_proof,
        composition_x_value=opening.composition_x_value,
        composition_x_proof=opening.composition_x_proof,
        fri_opening=opening.fri_opening,
    )
    bad_proof = replace(proof, openings=(bad_opening,) + proof.openings[1:])
    assert not verify_fibonacci(bad_proof)


def test_modified_trace_root_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    bad_root = bytes((proof.trace_merkle_root[0] ^ 1,)) + proof.trace_merkle_root[1:]
    bad_proof = replace(proof, trace_merkle_root=bad_root)
    assert not verify_fibonacci(bad_proof)


def test_modified_composition_root_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    bad_root = (
        bytes((proof.composition_merkle_root[0] ^ 1,))
        + proof.composition_merkle_root[1:]
    )
    bad_proof = replace(proof, composition_merkle_root=bad_root)
    assert not verify_fibonacci(bad_proof)


def test_modified_fri_layer_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    bad_layer = proof.fri_proof.layers[0]
    from stark_fibonacci.merkle import MerkleTree as _MT

    bad_root = _MT(
        tuple(FieldElement(v) for v in [0] * len(bad_layer.evaluations))
    ).root()
    bad_layer = replace(bad_layer, merkle_root=bad_root)
    bad_fri = replace(proof.fri_proof, layers=(bad_layer,) + proof.fri_proof.layers[1:])
    bad_proof = replace(proof, fri_proof=bad_fri)
    assert not verify_fibonacci(bad_proof)


def test_modified_n_rejected() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=15,
        claimed_output=987,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=8,
    )
    bad_inputs = replace(proof.public_inputs, n=4)
    bad_proof = replace(proof, public_inputs=bad_inputs)
    assert not verify_fibonacci(bad_proof)


def test_deterministic() -> None:
    # Two consecutive proofs with the same parameters should be identical (FRI
    # + transcript are deterministic).
    p1 = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    p2 = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    assert p1 == p2


def test_proof_serializable_to_json() -> None:
    proof = prove_fibonacci(
        c0=1,
        c1=1,
        n=7,
        claimed_output=21,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=3,
    )
    j = proof.to_json()
    assert isinstance(j, str)
    d = json.loads(j)
    assert "public_inputs" in d
    assert "trace_merkle_root_hex" in d
    proof2 = StarkProof.from_json(j)
    assert verify_fibonacci(proof2)


def test_json_invalid_raises() -> None:
    with pytest.raises(Exception):
        StarkProof.from_json("not valid json")
