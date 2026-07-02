"""STARK prover and verifier for the Fibonacci recurrence.

Protocol overview:

1. Build the trace T over the trace subgroup of order M = 2^k >= N + 1.
2. Compute T's evaluations on an LDE coset of size L = blowup * M.
3. Build the composition polynomial C(x) = T(g^2 x) - T(g x) - T(x).
4. Commit to both T-LDE and C-LDE via separate Merkle trees.
5. Run FRI on the C-LDE to obtain a low-degree proximity proof.
6. Use the FRI-sampled indices as STARK query indices; ship the trace
   values at (x, g x, g^2 x), the composition value at x, and the FRI
   query opening for every index.

The verifier re-derives the same indices from the FRI transcript,
checks each trace Merkle proof, recomputes the transition consistency
using the trace values, and runs the FRI verification.
"""

from __future__ import annotations

from typing import Sequence

from stark_fibonacci.air import FibonacciAIR
from stark_fibonacci.domain import (
    blowup_domain,
    multiplicative_subgroup,
)
from stark_fibonacci.field import FieldElement
from stark_fibonacci.fri import (
    fri_prove,
    fri_verify,
)
from stark_fibonacci.merkle import MerkleTree
from stark_fibonacci.polynomial import Polynomial
from stark_fibonacci.proof import PublicInputs, StarkOpening, StarkProof
from stark_fibonacci.trace import fibonacci_trace
from stark_fibonacci.transcript import Transcript


STARK_TRANSCRIPT_LABEL: bytes = b"STARK-Fibonacci"

_DEFAULT_BLOWUP: int = 8
_DEFAULT_NUM_QUERIES: int = 8
_DEFAULT_FRI_CLAIMED_DEGREE: int = 8


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def _encode_domain(domain: Sequence[FieldElement]) -> str:
    return ",".join(str(int(x.value)) for x in domain)


def _decode_domain(text: str) -> list[FieldElement]:
    return [FieldElement(int(x)) for x in text.split(",") if x]


def _build_proof(
    c0: int,
    c1: int,
    n: int,
    claimed_output: int,
    blowup_factor: int,
    num_queries: int,
    fri_claimed_degree: int,
    transcript: Transcript,
) -> StarkProof:
    if n < 2:
        raise ValueError("n must be >= 2 to have a Fibonacci transition")
    if blowup_factor < 1:
        raise ValueError("blowup_factor must be >= 1")

    c0_fe = FieldElement(c0)
    c1_fe = FieldElement(c1)
    c_fe = FieldElement(claimed_output)

    trace = fibonacci_trace(c0_fe, c1_fe, n)
    if trace[n] != c_fe:
        raise ValueError(f"trace[{n}] = {trace[n].value} does not match claimed_output")

    FibonacciAIR(c0=c0_fe, c1=c1_fe, claimed_output=c_fe, trace_length=n)

    trace_size = _next_power_of_two(n + 1)
    lde_size = blowup_factor * trace_size
    trace_domain = multiplicative_subgroup(trace_size)
    lde_domain = blowup_domain(trace_size, blowup_factor)

    T = Polynomial.interpolate_trace(trace, trace_domain)
    trace_lde: list[FieldElement] = Polynomial.low_degree_extend(T, lde_domain)

    composition_lde: list[FieldElement] = []
    for i in range(lde_size):
        x = lde_domain[i]
        gx = lde_domain[(i + trace_size) % lde_size]
        g2x = lde_domain[(i + 2 * trace_size) % lde_size]
        composition_lde.append(T.evaluate(g2x) - T.evaluate(gx) - T.evaluate(x))

    trace_tree = MerkleTree(trace_lde)
    composition_tree = MerkleTree(composition_lde)

    fri_proof = fri_prove(
        lde_domain,
        composition_lde,
        fri_claimed_degree,
        transcript,
        num_queries=num_queries,
    )

    openings: list[StarkOpening] = []
    for fri_q in fri_proof.queries:
        idx = fri_q.initial_index
        openings.append(
            StarkOpening(
                initial_index=idx,
                trace_x_value=trace_lde[idx].value,
                trace_gx_value=trace_lde[(idx + trace_size) % lde_size].value,
                trace_g2x_value=trace_lde[(idx + 2 * trace_size) % lde_size].value,
                trace_x_proof=trace_tree.open(idx),
                trace_gx_proof=trace_tree.open((idx + trace_size) % lde_size),
                trace_g2x_proof=trace_tree.open((idx + 2 * trace_size) % lde_size),
                composition_x_value=composition_lde[idx].value,
                composition_x_proof=composition_tree.open(idx),
                fri_opening=fri_q,
            )
        )

    return StarkProof(
        public_inputs=PublicInputs(
            c0=c0,
            c1=c1,
            n=n,
            claimed_output=claimed_output,
            lde_domain_size=lde_size,
            fri_claimed_degree=fri_claimed_degree,
            num_queries=num_queries,
        ),
        trace_merkle_root=trace_tree.root(),
        composition_merkle_root=composition_tree.root(),
        trace_domain_hex=_encode_domain(trace_domain),
        composition_domain_hex=_encode_domain(lde_domain),
        fri_proof=fri_proof,
        openings=tuple(openings),
    )


def prove_fibonacci(
    c0: int,
    c1: int,
    n: int,
    claimed_output: int,
    blowup_factor: int = _DEFAULT_BLOWUP,
    num_queries: int = _DEFAULT_NUM_QUERIES,
    fri_claimed_degree: int = _DEFAULT_FRI_CLAIMED_DEGREE,
) -> StarkProof:
    """Produce a STARK proof for the Fibonacci claim."""
    transcript = Transcript(STARK_TRANSCRIPT_LABEL)
    return _build_proof(
        c0,
        c1,
        n,
        claimed_output,
        blowup_factor,
        num_queries,
        fri_claimed_degree,
        transcript,
    )


def verify_fibonacci(proof: StarkProof) -> bool:
    """Verify a STARK proof."""
    from stark_fibonacci.merkle import hash_leaf

    pi = proof.public_inputs
    n = pi.n
    c0 = pi.c0
    c1 = pi.c1
    c = pi.claimed_output

    if n < 2:
        return False
    trace_size = _next_power_of_two(n + 1)
    if pi.lde_domain_size % trace_size != 0:
        return False
    lde_size = pi.lde_domain_size

    try:
        trace_domain = _decode_domain(proof.trace_domain_hex)
        lde_domain = _decode_domain(proof.composition_domain_hex)
    except ValueError:
        return False
    if len(trace_domain) != trace_size:
        return False
    if len(lde_domain) != lde_size:
        return False

    transcript = Transcript(STARK_TRANSCRIPT_LABEL)

    for opening in proof.openings:
        idx = opening.initial_index
        if not (0 <= idx < lde_size):
            return False
        if not opening.trace_x_proof.verify(proof.trace_merkle_root):
            return False
        if not opening.trace_gx_proof.verify(proof.trace_merkle_root):
            return False
        if not opening.trace_g2x_proof.verify(proof.trace_merkle_root):
            return False
        if not opening.composition_x_proof.verify(proof.composition_merkle_root):
            return False
        if opening.trace_x_proof.leaf_hash != hash_leaf(
            FieldElement(opening.trace_x_value)
        ):
            return False
        if opening.trace_gx_proof.leaf_hash != hash_leaf(
            FieldElement(opening.trace_gx_value)
        ):
            return False
        if opening.trace_g2x_proof.leaf_hash != hash_leaf(
            FieldElement(opening.trace_g2x_value)
        ):
            return False
        if opening.composition_x_proof.leaf_hash != hash_leaf(
            FieldElement(opening.composition_x_value)
        ):
            return False

        c_expected = (
            FieldElement(opening.trace_g2x_value)
            - FieldElement(opening.trace_gx_value)
            - FieldElement(opening.trace_x_value)
        )
        if FieldElement(opening.composition_x_value) != c_expected:
            return False

    return fri_verify(
        proof.fri_proof,
        proof.composition_merkle_root,
        lde_size,
        pi.fri_claimed_degree,
        transcript,
    )
