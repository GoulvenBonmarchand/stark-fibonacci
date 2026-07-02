"""Simplified pedagogical FRI (Fast Reed-Solomon IOP of Proximity).

Given a function f evaluated on a domain D, FRI produces a proof that
f is close to a polynomial of degree below `claimed_degree`.

The proof is a sequence of Merkle-committed "layers", each halving in
size via the fold

    f_next(x^2) = (f(x) + f(-x))/2 + alpha * (f(x) - f(-x)) / (2x).

After enough folds the function fits in a small polynomial which is
shipped directly. A verifier picks random indices and checks that the
fold chain is consistent down to the polynomial.

The Fiat-Shamir transcript is shared between prover and verifier; both
absorb the same canonical bytes from the proof to recompute the
folding challenges and the query indices.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


from stark_fibonacci.field import FieldElement
from stark_fibonacci.merkle import MerkleProof, MerkleTree, hash_leaf
from stark_fibonacci.polynomial import Polynomial
from stark_fibonacci.transcript import Transcript


TWO_INV: FieldElement = FieldElement(2).inverse()


def fri_fold(
    domain: Sequence[FieldElement],
    evaluations: Sequence[FieldElement],
    alpha: FieldElement,
) -> tuple[list[FieldElement], list[FieldElement]]:
    """Fold evaluations by halving the domain."""
    if len(domain) != len(evaluations):
        raise ValueError("domain and evaluations must have equal length")
    n = len(domain)
    if n == 0 or (n & (n - 1)) != 0:
        raise ValueError("domain size must be a positive power of two")
    half = n // 2
    new_domain: list[FieldElement] = []
    new_evals: list[FieldElement] = []
    for i in range(half):
        x = domain[i]
        a = evaluations[i]
        b = evaluations[i + half]
        even = (a + b) * TWO_INV
        odd = (a - b) * (TWO_INV * x.inverse())
        new_evals.append(even + alpha * odd)
        new_domain.append(x * x)
    return new_domain, new_evals


@dataclass(frozen=True)
class FRILayer:
    """One FRI layer: domain, evaluations, and Merkle root."""

    domain: tuple[FieldElement, ...]
    evaluations: tuple[FieldElement, ...]
    merkle_root: bytes


@dataclass(frozen=True)
class FRIQueryOpening:
    """Per-query chain of (value, sibling_value, proof, neg_proof) over
    every FRI layer."""

    initial_index: int
    layer_openings: tuple[
        tuple[FieldElement, FieldElement, MerkleProof, MerkleProof], ...
    ]


@dataclass(frozen=True)
class FRIProof:
    """A complete FRI proof."""

    initial_domain: tuple[FieldElement, ...]
    layers: tuple[FRILayer, ...]
    final_coeffs: tuple[FieldElement, ...]
    alphas: tuple[FieldElement, ...]
    queries: tuple[FRIQueryOpening, ...]


def _domain_dump(domain: Sequence[FieldElement]) -> bytes:
    parts = []
    for x in domain:
        parts.append(str(x.value).encode())
        parts.append(b",")
    return b"".join(parts)


def _coeffs_dump(coeffs: Sequence[FieldElement]) -> bytes:
    parts = [str(len(coeffs)).encode(), b","]
    for c in coeffs:
        parts.append(str(c.value).encode())
        parts.append(b",")
    return b"".join(parts)


def _new_cur_idx(cur_idx: int, half: int) -> int:
    if half <= 1:
        return 0
    return cur_idx & (half - 1)


def _absorb_layer_commitments(
    transcript: Transcript,
    layers: Sequence[FRILayer],
) -> None:
    """Absorb the canonical representation of every layer's root."""
    transcript.append_message(b"FRI-layers", str(len(layers)).encode())
    for layer in layers:
        transcript.append_message(b"FRI-commit", layer.merkle_root)


def _absorb_alpha_round(transcript: Transcript, root: bytes) -> FieldElement:
    transcript.append_message(b"FRI-commit", root)
    return transcript.challenge_field(b"FRI-alpha")


def fri_prove(
    domain: Sequence[FieldElement],
    evaluations: Sequence[FieldElement],
    claimed_degree: int,
    transcript: Transcript,
    num_queries: int = 4,
) -> FRIProof:
    """Generate a FRI proof that `f` is a polynomial of degree <= `claimed_degree`.

    The transcript is updated with the initial domain, every layer's
    Merkle root, the final polynomial coefficients, and absorbs the
    query indices. Both sides must start with the same transcript state
    for verification.
    """
    if len(domain) != len(evaluations):
        raise ValueError("domain and evaluations lengths differ")
    n0 = len(domain)
    if n0 == 0 or (n0 & (n0 - 1)) != 0:
        raise ValueError("domain must have a positive power-of-two size")
    if claimed_degree < 0:
        raise ValueError("claimed_degree must be non-negative")
    stop_at_size = claimed_degree + 1

    transcript.append_message(b"FRI-initial-domain", _domain_dump(domain))

    layers: list[tuple[list[FieldElement], list[FieldElement]]] = [
        (list(domain), list(evaluations))
    ]
    alphas: list[FieldElement] = []
    while len(layers[-1][1]) > stop_at_size:
        prev_tree = MerkleTree(layers[-1][1])
        alpha = _absorb_alpha_round(transcript, prev_tree.root())
        alphas.append(alpha)
        new_domain, new_evals = fri_fold(*layers[-1], alpha)
        layers.append((new_domain, new_evals))

    layer_commits: list[FRILayer] = []
    for dom, evs in layers:
        tree = MerkleTree(evs)
        layer_commits.append(
            FRILayer(
                domain=tuple(dom),
                evaluations=tuple(evs),
                merkle_root=tree.root(),
            )
        )

    _absorb_layer_commitments(transcript, layer_commits[1:])

    last_layer = layers[-1]
    final_poly = Polynomial.lagrange_interpolate(
        [(last_layer[0][i], last_layer[1][i]) for i in range(len(last_layer[0]))]
    )
    final_coeffs = final_poly.coeffs
    transcript.append_message(b"FRI-final-coeffs", _coeffs_dump(final_coeffs))
    transcript.append_message(b"FRI-num-queries", str(num_queries).encode())
    query_indices: list[int] = [
        transcript.challenge_index(b"FRI-idx", n0) for _ in range(num_queries)
    ]

    queries: list[FRIQueryOpening] = []
    for idx in query_indices:
        cur_idx = idx
        openings: list[tuple[FieldElement, FieldElement, MerkleProof, MerkleProof]] = []
        for _, evs in layers:
            tree = MerkleTree(evs)
            half = len(evs) // 2
            sibling_idx = cur_idx ^ half
            val_pos = evs[cur_idx]
            val_neg = evs[sibling_idx]
            openings.append(
                (
                    val_pos,
                    val_neg,
                    tree.open(cur_idx),
                    tree.open(sibling_idx),
                )
            )
            cur_idx = _new_cur_idx(cur_idx, half)
        queries.append(
            FRIQueryOpening(
                initial_index=idx,
                layer_openings=tuple(openings),
            )
        )

    return FRIProof(
        initial_domain=tuple(domain),
        layers=tuple(layer_commits),
        final_coeffs=tuple(final_coeffs),
        alphas=tuple(alphas),
        queries=tuple(queries),
    )


def fri_verify(
    proof: FRIProof,
    root: bytes,
    domain_size: int,
    claimed_degree: int,
    transcript: Transcript,
) -> bool:
    """Verify a FRI proof. Both sides share the transcript state."""
    if domain_size == 0 or (domain_size & (domain_size - 1)) != 0:
        return False
    if len(proof.initial_domain) != domain_size:
        return False
    if root != proof.layers[0].merkle_root:
        return False

    stop_at_size = claimed_degree + 1
    if len(proof.layers[-1].evaluations) > stop_at_size:
        return False

    transcript.append_message(b"FRI-initial-domain", _domain_dump(proof.initial_domain))

    derived_alphas: list[FieldElement] = []
    for k in range(len(proof.alphas)):
        if k + 1 >= len(proof.layers):
            return False
        alpha = _absorb_alpha_round(transcript, proof.layers[k].merkle_root)
        derived_alphas.append(alpha)
    if tuple(derived_alphas) != proof.alphas:
        return False

    _absorb_layer_commitments(transcript, proof.layers[1:])

    transcript.append_message(b"FRI-final-coeffs", _coeffs_dump(proof.final_coeffs))
    transcript.append_message(b"FRI-num-queries", str(len(proof.queries)).encode())
    expected_indices = [
        transcript.challenge_index(b"FRI-idx", domain_size)
        for _ in range(len(proof.queries))
    ]
    if expected_indices != [q.initial_index for q in proof.queries]:
        return False

    layer_trees: list[MerkleTree] = []
    for layer in proof.layers:
        tree = MerkleTree(layer.evaluations)
        if tree.root() != layer.merkle_root:
            return False
        layer_trees.append(tree)

    last_layer = proof.layers[-1]
    final_poly = Polynomial(proof.final_coeffs)
    for i in range(len(last_layer.evaluations)):
        if final_poly.evaluate(last_layer.domain[i]) != last_layer.evaluations[i]:
            return False

    for query in proof.queries:
        cur_idx = query.initial_index
        if not (0 <= cur_idx < domain_size):
            return False
        previous_value: FieldElement | None = None
        for k, layer in enumerate(proof.layers):
            tree = layer_trees[k]
            n_k = len(layer.evaluations)
            half = n_k // 2
            if cur_idx >= n_k or (cur_idx ^ half) >= n_k:
                return False
            opening = query.layer_openings[k]
            val_pos, val_neg, proof_pos, proof_neg = opening
            if not proof_pos.verify(layer.merkle_root):
                return False
            if not proof_neg.verify(layer.merkle_root):
                return False
            if proof_pos.leaf_hash != hash_leaf(val_pos):
                return False
            if proof_neg.leaf_hash != hash_leaf(val_neg):
                return False

            if previous_value is not None and val_pos != previous_value:
                return False

            if k < len(proof.alphas):
                alpha = proof.alphas[k]
                x = layer.domain[cur_idx]
                even = (val_pos + val_neg) * TWO_INV
                odd = (val_pos - val_neg) * (TWO_INV * x.inverse())
                previous_value = even + alpha * odd

            cur_idx = _new_cur_idx(cur_idx, half)

    return True
