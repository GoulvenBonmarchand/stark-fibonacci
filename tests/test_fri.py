"""Tests for the simplified FRI prover and verifier."""

from __future__ import annotations

import pytest
from dataclasses import replace

from stark_fibonacci.domain import multiplicative_subgroup, primitive_root_of_unity
from stark_fibonacci.field import FieldElement
from stark_fibonacci.fri import (
    fri_fold,
    fri_prove,
    fri_verify,
)
from stark_fibonacci.merkle import MerkleProof
from stark_fibonacci.polynomial import Polynomial
from stark_fibonacci.transcript import Transcript


def test_fold_halves_the_domain() -> None:
    domain = [FieldElement(i + 1) for i in range(8)]
    evals = [FieldElement((i + 1) * 2) for i in range(8)]
    new_dom, new_evs = fri_fold(domain, evals, FieldElement(0))
    assert len(new_dom) == 4
    assert len(new_evs) == 4


def test_fold_preserves_low_degree_structure() -> None:
    poly = Polynomial([1, 2, 3, 4])
    g = primitive_root_of_unity(16)
    domain = [g**i for i in range(16)]
    evals = [poly.evaluate(x) for x in domain]
    new_dom, new_evs = fri_fold(domain, evals, FieldElement(0))
    new_poly = Polynomial.lagrange_interpolate(
        [(new_dom[i], new_evs[i]) for i in range(len(new_dom))]
    )
    for i, x in enumerate(new_dom):
        assert new_poly.evaluate(x) == new_evs[i]


def test_fold_errors_on_size_mismatch() -> None:
    domain = [FieldElement(i) for i in range(8)]
    evals = [FieldElement(i) for i in range(7)]
    with pytest.raises(ValueError):
        fri_fold(domain, evals, FieldElement(0))


def test_fold_errors_on_non_power_of_two() -> None:
    domain = [FieldElement(i) for i in range(6)]
    evals = [FieldElement(i) for i in range(6)]
    with pytest.raises(ValueError):
        fri_fold(domain, evals, FieldElement(0))


def _poly_on_subgroup(
    coeffs: list[int], size: int
) -> tuple[list[FieldElement], list[FieldElement]]:
    poly = Polynomial(coeffs)
    g = primitive_root_of_unity(size)
    domain = [g**i for i in range(size)]
    evals = [poly.evaluate(x) for x in domain]
    return domain, evals


def test_valid_fri_proof_accepted() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    ts2 = Transcript(b"test-fri")
    assert fri_verify(proof, proof.layers[0].merkle_root, 16, claimed, ts2)


def test_evaluations_size_mismatch_rejected() -> None:
    domain = [FieldElement(i) for i in range(8)]
    evals = [FieldElement(i) for i in range(7)]
    ts = Transcript(b"test")
    with pytest.raises(ValueError):
        fri_prove(domain, evals, 3, ts)


def test_evaluations_not_power_of_two_rejected() -> None:
    domain = [FieldElement(i) for i in range(6)]
    evals = [FieldElement(i) for i in range(6)]
    ts = Transcript(b"test")
    with pytest.raises(ValueError):
        fri_prove(domain, evals, 3, ts)


def test_modified_merkle_root_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    bad_layer = proof.layers[0]
    bad_root = bytes((bad_layer.merkle_root[0] ^ 1,)) + bad_layer.merkle_root[1:]
    bad_proof = replace(
        proof,
        layers=(replace(bad_layer, merkle_root=bad_root),) + proof.layers[1:],
    )
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(bad_proof, proof.layers[0].merkle_root, 16, claimed, ts2)


def test_modified_layer_value_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    bad_layer = replace(
        proof.layers[0],
        evaluations=tuple(
            FieldElement(99) for _ in range(len(proof.layers[0].evaluations))
        ),
    )
    bad_proof = replace(proof, layers=(bad_layer,) + proof.layers[1:])
    ts2 = Transcript(b"test-fri")
    # A modified layer fails because the Merkle root no longer matches.
    assert not fri_verify(
        bad_proof,
        proof.layers[0].merkle_root,
        16,
        claimed,
        ts2,
    )


def test_modified_query_value_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    query = proof.queries[0]
    bad_opening = (FieldElement(99),) + query.layer_openings[0][1:]
    bad_query = replace(
        query,
        layer_openings=(bad_opening,) + query.layer_openings[1:],
    )
    bad_proof = replace(proof, queries=(bad_query,) + proof.queries[1:])
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(
        bad_proof,
        proof.layers[0].merkle_root,
        16,
        claimed,
        ts2,
    )


def test_modified_merkle_path_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    query = proof.queries[0]
    pos, neg, pr_pos, pr_neg = query.layer_openings[0]
    bad_pr = MerkleProof(
        index=pr_pos.index,
        leaf_hash=pr_pos.leaf_hash,
        siblings=(b"\x00" * 32,) + pr_pos.siblings[1:],
    )
    bad_opening = (pos, neg, bad_pr, pr_neg)
    bad_query = replace(
        query,
        layer_openings=(bad_opening,) + query.layer_openings[1:],
    )
    bad_proof = replace(proof, queries=(bad_query,) + proof.queries[1:])
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(
        bad_proof,
        proof.layers[0].merkle_root,
        16,
        claimed,
        ts2,
    )


def test_modified_alpha_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, claimed, ts, num_queries=3)
    new_alphas = (FieldElement(99),) + proof.alphas[1:]
    bad_proof = replace(proof, alphas=new_alphas)
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(
        bad_proof,
        proof.layers[0].merkle_root,
        16,
        claimed,
        ts2,
    )


def test_liar_who_breaks_fold_consistency_rejected() -> None:
    domain = multiplicative_subgroup(16)
    good_evals = [FieldElement(i + 1) for i in range(16)]
    claimed = 3
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, good_evals, claimed, ts, num_queries=4)
    tamper_layer = replace(
        proof.layers[1],
        evaluations=tuple(FieldElement(7) for _ in proof.layers[1].evaluations),
    )
    from stark_fibonacci.merkle import MerkleTree as _MT

    tamper_layer = replace(
        tamper_layer, merkle_root=_MT(tamper_layer.evaluations).root()
    )
    bad_layers = (proof.layers[0], tamper_layer) + proof.layers[2:]
    bad_proof = replace(proof, layers=bad_layers)
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(bad_proof, proof.layers[0].merkle_root, 16, claimed, ts2)


def test_proof_object_is_hashable() -> None:
    domain, evals = _poly_on_subgroup([1, 2, 3], 16)
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, 3, ts, num_queries=2)
    s = {proof}
    assert len(s) == 1


def test_domain_size_mismatch_rejected() -> None:
    domain, evals = _poly_on_subgroup([0, 1, 2, 3], 16)
    ts = Transcript(b"test-fri")
    proof = fri_prove(domain, evals, 3, ts, num_queries=3)
    ts2 = Transcript(b"test-fri")
    assert not fri_verify(proof, proof.layers[0].merkle_root, 32, 3, ts2)
