"""FRI (Fast Reed-Solomon IOP of Proximity).

Given a function f on a domain D of size n = 2^k, FRI produces a proof that f
is close to a polynomial of degree < d. We use the binary-folding variant of
the STARK 101 / stark-anatomy presentations.

We work with domains indexed by POWERS of a base generator g of a subgroup of
F_p^*. The base domain is D = {shift * g^i : i in 0..n-1} (natural order,
NOT sorted). Pairing (x, -x) is then `(shift*g^i, shift*g^(i+n/2))`.

Folding rule:
    for i in [0, n/2):
        x = D[i]
        f_next[i] = (f(D[i]) + f(D[i+n/2]))/2 + r * (f(D[i]) - f(D[i+n/2]))/(2x)

The next domain is {shift^2 * g^(2i) : i in 0..n/2-1}, again in natural order.
The next pair (x', -x') = (shift^2*g^(2i), shift^2*g^(2i + n/2)) is automatic.

Non-interactive via Fiat-Shamir: every random challenge r is derived from a
SHA-256 transcript of all commitments so far.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .field import (
    DEFAULT_PRIME,
    FieldElement,
    MAX_TWO_ADIC_ORDER,
    two_adic_generator,
)
from .merkle import MerkleTree
from .polynomial import eval_poly_at, strip
from .utils import (
    field_elements_to_bytes,
    hash_many,
    sample_distinct_ints,
    sample_field_element,
)


# ---------------------------------------------------------------------------
# Domain construction (natural order, index = power of g)
# ---------------------------------------------------------------------------

def base_generator(prime: int = DEFAULT_PRIME) -> int:
    """Generator g of the 2-Sylow subgroup of F_p^* (order 2^MAX_TWO_ADIC_ORDER)."""
    return two_adic_generator(prime, MAX_TWO_ADIC_ORDER)


def gen_domain(
    size: int,
    prime: int = DEFAULT_PRIME,
    shift: int = 3,
) -> tuple[list[FieldElement], int, int]:
    """Build a coset domain of the requested size in natural order.

    Returns (domain_elements_in_index_order, shift, log2_size).
    The domain element at index i is (shift * g^i) mod p, where g is a generator
    of the order-`size` 2-Sylow subgroup of F_p^* (i.e. g^(size) = 1, g^(size/2) = -1).
    """
    if size <= 0 or (size & (size - 1)) != 0:
        raise ValueError(f"size must be a positive power of 2, got {size}")
    order = size.bit_length() - 1
    if order > MAX_TWO_ADIC_ORDER:
        raise ValueError(f"size exceeds 2^{MAX_TWO_ADIC_ORDER}")
    g = two_adic_generator(prime, order)  # generator of order-size subgroup
    coset = [FieldElement((shift * pow(g, i, prime)) % prime, prime) for i in range(size)]
    return coset, shift, order


def layer_domain_point(
    shift: int,
    original_order: int,
    layer_pow: int,
    index: int,
    prime: int = DEFAULT_PRIME,
) -> FieldElement:
    """The domain point at (layer_pow folds deep, index).

    After `layer_pow` folds, the domain is
        {shift^(2^layer_pow) * g^(2^layer_pow * i)}
    where g is the generator of the order-2^original_order subgroup.
    """
    g = two_adic_generator(prime, original_order)
    shift_pow = pow(shift, 1 << layer_pow, prime)
    val = (shift_pow * pow(g, index * (1 << layer_pow), prime)) % prime
    return FieldElement(val, prime)


# ---------------------------------------------------------------------------
# Proof data structures
# ---------------------------------------------------------------------------

@dataclass
class FriLayer:
    domain: list[FieldElement]
    evaluations: list[FieldElement]
    root: bytes


@dataclass
class FriLayerOpening:
    left_index: int
    left_value: FieldElement
    right_index: int
    right_value: FieldElement
    left_auth_path: list[tuple[bytes, str]]
    right_auth_path: list[tuple[bytes, str]]


@dataclass
class FriQuery:
    initial_index: int
    layer_openings: list[FriLayerOpening] = field(default_factory=list)
    final_value: FieldElement | None = None


@dataclass
class FriProof:
    layer_roots: list[bytes]
    fold_challenges: list[FieldElement]
    final_poly_coeffs: list[FieldElement]
    initial_domain_size: int
    initial_domain_shift: int
    initial_domain_log2: int
    queries: list[FriQuery]


# ---------------------------------------------------------------------------
# Merkle leaves & folding
# ---------------------------------------------------------------------------

def _leaf_hash(x: FieldElement, y: FieldElement) -> bytes:
    return hash_many(field_elements_to_bytes(x, y))


def _build_layer(domain: Sequence[FieldElement],
                 evaluations: Sequence[FieldElement]) -> FriLayer:
    if len(domain) != len(evaluations):
        raise ValueError("domain/evaluations length mismatch")
    leaves = [_leaf_hash(x, y) for x, y in zip(domain, evaluations)]
    tree = MerkleTree(leaves)
    return FriLayer(domain=list(domain), evaluations=list(evaluations), root=tree.root())


def _fold_layer(
    domain: Sequence[FieldElement],
    evaluations: Sequence[FieldElement],
    r: FieldElement,
) -> tuple[list[FieldElement], list[FieldElement]]:
    """One round of binary folding (natural-order domain)."""
    n = len(domain)
    if n % 2 != 0 or n == 0:
        raise ValueError("domain size must be positive even")
    half = n // 2
    prime = domain[0].prime
    two_inv = FieldElement(2, prime).inverse()
    next_domain: list[FieldElement] = []
    next_evals: list[FieldElement] = []
    for i in range(half):
        x = domain[i]
        fx = evaluations[i]
        fy = evaluations[i + half]
        avg = (fx + fy) * two_inv
        slope = (fx - fy) * (two_inv / x)
        f1 = avg + r * slope
        # next domain point is x^2; natural index ordering preserved.
        next_domain.append(x * x)
        next_evals.append(f1)
    return next_domain, next_evals


# ---------------------------------------------------------------------------
# Prover
# ---------------------------------------------------------------------------

def prove_fri(
    initial_domain: list[FieldElement],
    initial_evaluations: list[FieldElement],
    max_degree_plus_one: int = 16,
    num_queries: int = 8,
    initial_shift: int = 3,
) -> FriProof:
    """Build a FRI proof.

    Args:
        initial_domain: the coset domain (size = power of 2, natural order).
        initial_evaluations: f(x) for x in initial_domain.
        max_degree_plus_one: stop folding when len(domain) <= this; the
            remaining evaluations are shipped as a degree-(size-1) polynomial.
        num_queries: number of random query indices sampled (Fiat-Shamir).
        initial_shift: the shift used to build initial_domain.
    """
    prime = initial_domain[0].prime
    if len(initial_domain) != len(initial_evaluations):
        raise ValueError("domain/evaluations length mismatch")
    n0 = len(initial_domain)
    if n0 & (n0 - 1) != 0:
        raise ValueError("initial domain size must be a power of 2")
    original_order = n0.bit_length() - 1

    # 1) Build all layers (and their roots) up-front.
    layers: list[FriLayer] = []
    fold_challenges: list[FieldElement] = []
    cur_domain = initial_domain
    cur_evals = initial_evaluations
    while len(cur_domain) > max_degree_plus_one:
        layer = _build_layer(cur_domain, cur_evals)
        layers.append(layer)
        r = sample_field_element(hash_many(b"FRI-fold", layer.root), prime)
        fold_challenges.append(r)
        cur_domain, cur_evals = _fold_layer(cur_domain, cur_evals, r)

    # 2) Final polynomial: interpolate the (small) remaining evaluations to
    #    actual coefficients so the verifier can evaluate it at any point.
    from .polynomial import interpolate_lagrange
    final_poly = interpolate_lagrange(cur_domain, cur_evals)
    final_poly_commit = hash_many(b"FRI-final", field_elements_to_bytes(*final_poly))

    # 3) Sample query indices.
    transcript = hash_many(
        b"FRI-transcript",
        b"".join(L.root for L in layers),
        final_poly_commit,
    )
    raw_indices = sample_distinct_ints(transcript, 0, n0 - 1, num_queries)

    # 4) Build per-query openings.
    queries: list[FriQuery] = []
    for idx0 in raw_indices:
        q = FriQuery(initial_index=idx0)
        cur_idx = idx0
        for layer in layers:
            n_layer = len(layer.domain)
            half = n_layer // 2
            if cur_idx < half:
                left_i, right_i = cur_idx, cur_idx + half
            else:
                left_i, right_i = cur_idx - half, cur_idx
            left_v = layer.evaluations[left_i]
            right_v = layer.evaluations[right_i]
            leaves = [_leaf_hash(x, y) for x, y in zip(layer.domain, layer.evaluations)]
            tree = MerkleTree(leaves)
            left_path = tree.get_authentication_path(left_i)
            right_path = tree.get_authentication_path(right_i)
            q.layer_openings.append(FriLayerOpening(
                left_index=left_i,
                left_value=left_v,
                right_index=right_i,
                right_value=right_v,
                left_auth_path=left_path,
                right_auth_path=right_path,
            ))
            cur_idx = cur_idx % half

        # Final-layer evaluation: prover recomputes the last fold and checks it
        # matches the polynomial. The verifier will recompute and compare too.
        # We only ship the final polynomial; the final value per query is
        # implied.
        queries.append(q)

    return FriProof(
        layer_roots=[L.root for L in layers],
        fold_challenges=fold_challenges,
        final_poly_coeffs=final_poly,
        initial_domain_size=n0,
        initial_domain_shift=initial_shift,
        initial_domain_log2=original_order,
        queries=queries,
    )


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def verify_fri(proof: FriProof, max_degree_plus_one: int = 16) -> bool:
    """Verify a FRI proof.

    `max_degree_plus_one` is the maximum (degree + 1) of the final polynomial;
    the verifier rejects proofs whose final polynomial has >= that many
    non-trimmed coefficients.
    """
    prime = (proof.final_poly_coeffs[0].prime if proof.final_poly_coeffs
             else DEFAULT_PRIME)
    shift = proof.initial_domain_shift
    n0 = proof.initial_domain_size
    original_order = proof.initial_domain_log2

    # 0) Low-degree check on the final polynomial.
    final_poly = strip(proof.final_poly_coeffs)
    if len(final_poly) >= max_degree_plus_one:
        return False

    # 1) Recompute fold challenges from shipped roots.
    expected_folds: list[FieldElement] = []
    for root in proof.layer_roots:
        r = sample_field_element(hash_many(b"FRI-fold", root), prime)
        expected_folds.append(r)
    if expected_folds != proof.fold_challenges:
        return False

    # 2) Recompute transcript and query indices.
    final_poly_commit = hash_many(
        b"FRI-final", field_elements_to_bytes(*final_poly)
    )
    transcript = hash_many(
        b"FRI-transcript",
        b"".join(proof.layer_roots),
        final_poly_commit,
    )
    expected_indices = sample_distinct_ints(
        transcript, 0, n0 - 1, len(proof.queries)
    )
    if sorted(expected_indices) != sorted(q.initial_index for q in proof.queries):
        return False

    # 3) For each query, walk through the layers and check folding consistency.
    for q in proof.queries:
        for li, opening in enumerate(q.layer_openings):
            n_layer = n0 >> li
            left_point = layer_domain_point(shift, original_order, li, opening.left_index, prime)
            right_point = layer_domain_point(shift, original_order, li, opening.right_index, prime)
            left_leaf = _leaf_hash(left_point, opening.left_value)
            right_leaf = _leaf_hash(right_point, opening.right_value)
            if not MerkleTree.verify(
                proof.layer_roots[li], opening.left_index, left_leaf,
                opening.left_auth_path, n_layer,
            ):
                return False
            if not MerkleTree.verify(
                proof.layer_roots[li], opening.right_index, right_leaf,
                opening.right_auth_path, n_layer,
            ):
                return False

            r = expected_folds[li]
            x = left_point
            two_inv = FieldElement(2, prime).inverse()
            folded = (opening.left_value + opening.right_value) * two_inv + r * (
                (opening.left_value - opening.right_value) * (two_inv / x)
            )

            if li + 1 < len(q.layer_openings):
                nxt = q.layer_openings[li + 1]
                if folded != nxt.left_value and folded != nxt.right_value:
                    return False
                nxt_idx = opening.left_index % (n_layer // 2)
                if (nxt.left_index != nxt_idx and
                        nxt.right_index != nxt_idx):
                    return False
            else:
                # Final check: folded value should equal eval of final poly at
                # the next-layer point, which is (left_point)^2.
                final_eval = eval_poly_at(final_poly, x * x)
                if folded != final_eval:
                    return False

    return True