"""STARK prover and verifier for the Fibonacci recurrence.

Public statement:
    (c_0, c_1, N, C)  with the claim:
        u_0 = c_0, u_1 = c_1,
        u_{n} = u_{n-1} + u_{n-2}  for 2 <= n <= N,
        u_N = C.

Pipeline:
    1. Witness trace: [u_0, u_1, ..., u_N]  (length N+1)
    2. Choose a trace domain T (cyclic subgroup of size M = 2^k >= N+1).
    3. Build the trace polynomial T_p(x) interpolating (g^i, u_i) for i in
       [0, N] on the trace domain.
    4. Compose the constraints into one polynomial C_p(x) (boundary +
       transition).
    5. Low-degree-extend T_p and C_p to an LDE domain L of size
       blowup_factor * M.
    6. Commit T_p|_L and C_p|_L via Merkle trees.
    7. Apply FRI to C_p|_L to prove it is low-degree.
    8. Sample query positions on L. For each query, ship the value + auth
       path of T_p and C_p, plus the FRI opening.

Boundary constraints are checked at the corresponding points of T by the
verifier (using T_p on the LDE domain and the committed value).
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
from .fri import (
    FriProof,
    gen_domain,
    layer_domain_point,
    prove_fri,
    verify_fri,
)
from .merkle import MerkleTree
from .polynomial import (
    add_polys,
    eval_poly_at,
    interpolate_lagrange,
    mul_polys,
    poly_div,
    scalar_mul,
    strip,
    sub_polys,
)
from .utils import (
    field_elements_to_bytes,
    hash_many,
    sample_distinct_ints,
    sample_field_element,
)


# ---------------------------------------------------------------------------
# Public parameters
# ---------------------------------------------------------------------------

@dataclass
class StarkParams:
    """Public parameters for a STARK instance.

    All values are field elements or ints modulo the field prime.
    """
    c0: int  # u_0
    c1: int  # u_1
    N: int   # claimed index of u_N
    C: int   # claimed value of u_N
    blowup_factor: int = 4
    num_queries: int = 8
    max_degree_plus_one: int = 16
    shift: int = 3
    prime: int = DEFAULT_PRIME

    def __post_init__(self) -> None:
        if self.N < 2:
            raise ValueError("N must be >= 2")
        if not (self.blowup_factor & (self.blowup_factor - 1) == 0
                and self.blowup_factor >= 2):
            raise ValueError("blowup_factor must be a power of 2 >= 2")


# ---------------------------------------------------------------------------
# Witness / trace generation
# ---------------------------------------------------------------------------

def generate_trace(c0: int, c1: int, N: int, prime: int = DEFAULT_PRIME) -> list[FieldElement]:
    """Return [u_0, u_1, ..., u_N] for the Fibonacci recurrence."""
    if N < 1:
        raise ValueError("N must be >= 1")
    out: list[FieldElement] = [FieldElement(c0, prime), FieldElement(c1, prime)]
    for _ in range(N - 1):
        out.append(out[-1] + out[-2])
    return out


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------

def trace_domain_size(N: int) -> int:
    """Smallest power of 2 >= N+1, capped to MAX_TWO_ADIC_ORDER constraint."""
    if N < 1:
        raise ValueError("N must be >= 1")
    size = 1
    while size < N + 1:
        size *= 2
    return size


def build_trace_domain(N: int, prime: int = DEFAULT_PRIME, shift: int = 1) -> tuple[list[FieldElement], int, int]:
    """Build the trace domain of size M = smallest power of 2 >= N+1.

    Returns (domain_in_natural_index_order, log2_size, shift).
    """
    M = trace_domain_size(N)
    if M > (1 << MAX_TWO_ADIC_ORDER):
        raise ValueError(f"trace domain too large: N={N} would need 2^{M.bit_length()-1}")
    order = M.bit_length() - 1
    g = two_adic_generator(prime, order)
    coset = [FieldElement((shift * pow(g, i, prime)) % prime, prime) for i in range(M)]
    return coset, order, shift


# ---------------------------------------------------------------------------
# Composition polynomial
# ---------------------------------------------------------------------------

def compose_constraints(
    trace_coeffs: list[FieldElement],
    trace_domain_g: int,  # generator of the trace domain subgroup
    params: StarkParams,
) -> list[FieldElement]:
    """Build the composition polynomial C_p(x) for the Fibonacci STARK.

    C_p(x) = (T(g^2 x) - T(g x) - T(x)) / Z_transition(x)
             + alpha * ((T(x) - c_0) / (x - g^0)
                       + (T(x) - c_1) / (x - g^1)
                       + (T(x) - C) / (x - g^N))

    where Z_transition(x) = prod_{i in [0, N-2]} (x - g^i) is the vanishing
    polynomial of {g^0, ..., g^{N-2}}.

    In this minimal STARK we use ONE composition value and pick `alpha`
    deterministically from the public statement (no Fiat-Shamir mixing beyond
    what's in FRI; this suffices to combine the boundary constraints into a
    single low-degree check).

    Returns the coefficient list of C_p(x).
    """
    prime = params.prime
    N = params.N
    g = trace_domain_g

    # Build a polynomial helper for the trace polynomial T.
    # We don't materialize T(g x) and T(g^2 x) as coefficient lists; instead
    # we work symbolically via Horner-style substitution:
    #   T(g x) = sum_i trace_coeffs[i] * (g x)^i = sum_i trace_coeffs[i] * g^i * x^i
    # so its coefficients are trace_coeffs[i] * g^i.
    # T(g^2 x) = sum_i trace_coeffs[i] * g^(2i) * x^i.

    n = len(trace_coeffs)
    trans_coeffs: list[FieldElement] = []
    trans2_coeffs: list[FieldElement] = []
    g_pow = FieldElement(1, prime)
    g2_pow = FieldElement(1, prime)
    g_factor = FieldElement(g, prime)
    g2_factor = FieldElement((g * g) % prime, prime)
    for _ in range(n):
        trans_coeffs.append(trace_coeffs[_] * g_pow)
        trans2_coeffs.append(trace_coeffs[_] * g2_pow)
        g_pow = g_pow * g_factor
        g2_pow = g2_pow * g2_factor

    # transition_constraint(x) = T(g^2 x) - T(g x) - T(x)
    trans_constr = sub_polys(sub_polys(trans2_coeffs, trans_coeffs), trace_coeffs)

    # Z_transition(x) = prod_{i=0}^{N-2} (x - g^i)
    z_trans_coeffs = [FieldElement.one(prime)]
    for i in range(N - 1):
        g_i = FieldElement(pow(g, i, prime), prime)
        z_trans_coeffs = mul_polys(z_trans_coeffs, [-g_i, FieldElement.one(prime)])

    # quotient = transition_constraint / Z_transition (this division must be exact)
    q_trans, r_trans = poly_div(trans_constr, z_trans_coeffs)
    if not (len(r_trans) == 1 and r_trans[0].is_zero()):
        raise RuntimeError("transition constraint is not in the vanishing ideal")

    # Boundary: each boundary constraint is a degree-N+1 polynomial:
    # (T(x) - claimed) / (x - g^i), degree <= N.
    # Sum them into one polynomial of degree <= N.
    boundary_coeffs: list[FieldElement] = [FieldElement.zero(prime)]
    for i, claimed in [(0, params.c0), (1, params.c1), (N, params.C)]:
        # numerator: trace_coeffs - claimed
        const_poly = [FieldElement(-claimed % prime, prime)] + [FieldElement.zero(prime) for _ in range(len(trace_coeffs) - 1)]
        numerator = add_polys(trace_coeffs, const_poly)
        # denominator: (x - g^i)
        denom = [-FieldElement(pow(g, i, prime), prime), FieldElement.one(prime)]
        q_b, r_b = poly_div(numerator, denom)
        if not (len(r_b) == 1 and r_b[0].is_zero()):
            raise RuntimeError(f"boundary constraint at index {i} is not satisfied")
        # align degrees
        max_deg = max(len(boundary_coeffs), len(q_b))
        boundary_coeffs = boundary_coeffs + [FieldElement.zero(prime)] * (max_deg - len(boundary_coeffs))
        q_b = q_b + [FieldElement.zero(prime)] * (max_deg - len(q_b))
        boundary_coeffs = add_polys(boundary_coeffs, q_b)

    # Pick alpha as a deterministic value derived from the public statement.
    # (We don't need Fiat-Shamir for this in a teaching implementation.)
    alpha = sample_field_element(
        hash_many(b"STARK-alpha", str((params.c0, params.c1, params.N, params.C)).encode()),
        prime,
    )

    # Align degrees for q_trans and boundary_coeffs.
    max_deg = max(len(q_trans), len(boundary_coeffs))
    q_trans_a = q_trans + [FieldElement.zero(prime)] * (max_deg - len(q_trans))
    boundary_a = boundary_coeffs + [FieldElement.zero(prime)] * (max_deg - len(boundary_coeffs))

    composition = add_polys(q_trans_a, scalar_mul(boundary_a, alpha))
    return strip(composition)


# ---------------------------------------------------------------------------
# Proof data structures
# ---------------------------------------------------------------------------

@dataclass
class StarkQuery:
    initial_index: int  # index in the LDE domain
    # T(x), T(g*x), T(g^2*x): three trace evaluations at consecutive shifted
    # points in the LDE domain. Each comes with its own Merkle auth path so
    # the verifier can recompute the transition constraint directly.
    trace_x_index: int
    trace_x_value: FieldElement
    trace_x_auth_path: list[tuple[bytes, str]]
    trace_gx_index: int
    trace_gx_value: FieldElement
    trace_gx_auth_path: list[tuple[bytes, str]]
    trace_g2x_index: int
    trace_g2x_value: FieldElement
    trace_g2x_auth_path: list[tuple[bytes, str]]
    # C(x) at the original query point (recomputed by the verifier).
    comp_index: int
    comp_value: FieldElement
    comp_auth_path: list[tuple[bytes, str]]


@dataclass
class StarkProof:
    params: StarkParams
    # Public commitments
    trace_root: bytes
    comp_root: bytes
    # FRI proof on the composition polynomial
    fri_proof: FriProof
    # Query openings
    queries: list[StarkQuery]


# ---------------------------------------------------------------------------
# Prover
# ---------------------------------------------------------------------------

def prove_stark(params: StarkParams) -> StarkProof:
    """Build a STARK proof for the Fibonacci statement `params`."""
    prime = params.prime

    # 1) Trace.
    trace = generate_trace(params.c0, params.c1, params.N, prime)
    assert int(trace[-1]) == params.C % prime, "witness does not satisfy claimed u_N"

    # 2) Trace domain (cyclic subgroup of order M).
    M = trace_domain_size(params.N)
    trace_order = M.bit_length() - 1
    g_trace = two_adic_generator(prime, trace_order)
    trace_domain: list[FieldElement] = [
        FieldElement(pow(g_trace, i, prime), prime) for i in range(M)
    ]

    # 3) Trace polynomial interpolation on the trace domain.
    trace_coeffs = interpolate_lagrange(trace_domain, trace)

    # 4) Composition polynomial.
    comp_coeffs = compose_constraints(trace_coeffs, g_trace, params)

    # 5) Low-degree extension: build the LDE domain (coset of size blowup_factor * M).
    lde_size = params.blowup_factor * M
    lde_order = (blowup_order := lde_size.bit_length() - 1)
    g_lde = two_adic_generator(prime, lde_order)
    lde_shift = params.shift
    lde_domain: list[FieldElement] = [
        FieldElement((lde_shift * pow(g_lde, i, prime)) % prime, prime)
        for i in range(lde_size)
    ]

    # Evaluate trace_coeffs and comp_coeffs on the LDE domain.
    trace_lde = [eval_poly_at(trace_coeffs, x) for x in lde_domain]
    comp_lde = [eval_poly_at(comp_coeffs, x) for x in lde_domain]

    # 6) Merkle commitments over the LDE evaluations.
    trace_leaves = [
        hash_many(field_elements_to_bytes(x, y)) for x, y in zip(lde_domain, trace_lde)
    ]
    comp_leaves = [
        hash_many(field_elements_to_bytes(x, y)) for x, y in zip(lde_domain, comp_lde)
    ]
    trace_tree = MerkleTree(trace_leaves)
    comp_tree = MerkleTree(comp_leaves)

    # 7) FRI on the composition LDE evaluations.
    fri_proof = prove_fri(
        lde_domain,
        comp_lde,
        max_degree_plus_one=params.max_degree_plus_one,
        num_queries=params.num_queries,
        initial_shift=lde_shift,
    )

    # 8) Sample query positions over the LDE domain, derived from all commitments.
    transcript = hash_many(
        b"STARK-transcript",
        trace_tree.root(),
        comp_tree.root(),
        b"".join(fri_proof.layer_roots),
        field_elements_to_bytes(*fri_proof.final_poly_coeffs),
    )
    raw_indices = sample_distinct_ints(transcript, 0, lde_size - 1, params.num_queries)

    queries: list[StarkQuery] = []
    for idx in raw_indices:
        # Indices of T(g*x) and T(g^2*x) within the LDE domain. Since the
        # LDE subgroup generator g_lde has order blowup * M and the trace
        # generator has order M with g = g_lde^blowup, shifting by g advances
        # the LDE index by `blowup_factor`.
        gx_idx = (idx + params.blowup_factor) % lde_size
        g2x_idx = (idx + 2 * params.blowup_factor) % lde_size
        queries.append(StarkQuery(
            initial_index=idx,
            trace_x_index=idx,
            trace_x_value=trace_lde[idx],
            trace_x_auth_path=trace_tree.get_authentication_path(idx),
            trace_gx_index=gx_idx,
            trace_gx_value=trace_lde[gx_idx],
            trace_gx_auth_path=trace_tree.get_authentication_path(gx_idx),
            trace_g2x_index=g2x_idx,
            trace_g2x_value=trace_lde[g2x_idx],
            trace_g2x_auth_path=trace_tree.get_authentication_path(g2x_idx),
            comp_index=idx,
            comp_value=comp_lde[idx],
            comp_auth_path=comp_tree.get_authentication_path(idx),
        ))

    return StarkProof(
        params=params,
        trace_root=trace_tree.root(),
        comp_root=comp_tree.root(),
        fri_proof=fri_proof,
        queries=queries,
    )


# ---------------------------------------------------------------------------
# Verifier
# ---------------------------------------------------------------------------

def recompute_composition(
    trace_x: FieldElement,
    trace_gx: FieldElement,
    trace_g2x: FieldElement,
    x: FieldElement,
    params: StarkParams,
) -> FieldElement:
    """Recompute the composition polynomial at `x` from trace values.

    The composition is
        C(x) = (T(g^2 x) - T(g x) - T(x)) / Z_transition(x)
             + alpha * ((T(x) - c_0)/(x - g^0) + (T(x) - c_1)/(x - g^1)
                       + (T(x) - C)/(x - g^N))

    When the denominator is zero (i.e. x is a root of Z_transition or one of
    the (x - g^i) factors), the corresponding term is dropped (the boundary
    and transition constraints are local at those points and the composition
    is only defined elsewhere).
    """
    prime = params.prime
    N = params.N

    # Reconstruct trace-domain generator from the LDE layout.
    M = trace_domain_size(N)
    trace_order = M.bit_length() - 1
    g_trace = two_adic_generator(prime, trace_order)
    g0 = FieldElement(1, prime)
    g1 = FieldElement(g_trace, prime)
    gN = FieldElement(pow(g_trace, N, prime), prime)

    # Deterministic alpha (same recipe as the prover).
    alpha = sample_field_element(
        hash_many(b"STARK-alpha", str((params.c0, params.c1, params.N, params.C)).encode()),
        prime,
    )

    out = FieldElement.zero(prime)

    # Transition term (only if x is NOT a root of Z_transition).
    z_trans_val = FieldElement.one(prime)
    is_transition_root = False
    for i in range(N - 1):
        g_i = FieldElement(pow(g_trace, i, prime), prime)
        factor = x - g_i
        z_trans_val = z_trans_val * factor
        if factor.is_zero():
            is_transition_root = True
    if not is_transition_root:
        transition_num = trace_g2x - trace_gx - trace_x
        out = out + transition_num * z_trans_val.inverse()

    # Boundary terms (only when x != g^i).
    def _boundary_term(claimed: int, g_i: FieldElement) -> FieldElement:
        diff = x - g_i
        if diff.is_zero():
            return FieldElement.zero(prime)
        return (trace_x - FieldElement(claimed % prime, prime)) * diff.inverse()

    out = out + alpha * (
        _boundary_term(params.c0, g0)
        + _boundary_term(params.c1, g1)
        + _boundary_term(params.C, gN)
    )
    return out


def verify_stark(proof: StarkProof) -> bool:
    """Verify a STARK proof for the Fibonacci statement."""
    params = proof.params
    prime = params.prime

    M = trace_domain_size(params.N)
    lde_size = params.blowup_factor * M
    lde_order = lde_size.bit_length() - 1

    # Reconstruct the LDE domain (same construction as the prover).
    g_lde = two_adic_generator(prime, lde_order)
    lde_shift = proof.fri_proof.initial_domain_shift
    lde_domain: list[FieldElement] = [
        FieldElement((lde_shift * pow(g_lde, i, prime)) % prime, prime)
        for i in range(lde_size)
    ]

    # 1) Verify FRI.
    if not verify_fri(proof.fri_proof, max_degree_plus_one=params.max_degree_plus_one):
        return False

    # 2) Recompute the transcript and check the query indices match.
    transcript = hash_many(
        b"STARK-transcript",
        proof.trace_root,
        proof.comp_root,
        b"".join(proof.fri_proof.layer_roots),
        field_elements_to_bytes(*proof.fri_proof.final_poly_coeffs),
    )
    expected_indices = sample_distinct_ints(transcript, 0, lde_size - 1, len(proof.queries))
    if sorted(expected_indices) != sorted(q.initial_index for q in proof.queries):
        return False

    # 3) For each query, verify the trace values + composition recomputation.
    for q in proof.queries:
        x = lde_domain[q.initial_index]
        gx = lde_domain[q.trace_gx_index]
        g2x = lde_domain[q.trace_g2x_index]

        for pt, pt_idx, pt_val, pt_path in [
            (x, q.trace_x_index, q.trace_x_value, q.trace_x_auth_path),
            (gx, q.trace_gx_index, q.trace_gx_value, q.trace_gx_auth_path),
            (g2x, q.trace_g2x_index, q.trace_g2x_value, q.trace_g2x_auth_path),
        ]:
            leaf = hash_many(field_elements_to_bytes(pt, pt_val))
            if not MerkleTree.verify(proof.trace_root, pt_idx, leaf, pt_path, lde_size):
                return False

        comp_leaf = hash_many(field_elements_to_bytes(x, q.comp_value))
        if not MerkleTree.verify(proof.comp_root, q.comp_index, comp_leaf, q.comp_auth_path, lde_size):
            return False

        recomputed = recompute_composition(
            trace_x=q.trace_x_value,
            trace_gx=q.trace_gx_value,
            trace_g2x=q.trace_g2x_value,
            x=x,
            params=params,
        )
        if recomputed != q.comp_value:
            return False

    return True