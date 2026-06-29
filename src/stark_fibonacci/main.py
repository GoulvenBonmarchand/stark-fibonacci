"""End-to-end STARK demo for the Fibonacci recurrence.

The demo:
  1. Generates a Fibonacci trace.
  2. Runs the STARK prover.
  3. Runs the STARK verifier.
  4. Reports proof size and verification result.
  5. Tries a few tampered proofs to demonstrate soundness.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, replace
from typing import Any

from .field import FieldElement
from .stark import (
    StarkParams,
    StarkProof,
    generate_trace,
    prove_stark,
    verify_stark,
)


def _proof_size_bytes(proof: StarkProof) -> int:
    """Rough estimate of proof size in bytes (for reporting)."""
    import dataclasses

    def _size(obj: Any) -> int:
        if isinstance(obj, bytes):
            return len(obj)
        if isinstance(obj, (list, tuple)):
            return sum(_size(x) for x in obj)
        if isinstance(obj, (str, int)):
            return len(str(obj).encode())
        if dataclasses.is_dataclass(obj):
            return _size(dataclasses.asdict(obj))
        if isinstance(obj, dict):
            return sum(_size(k) + _size(v) for k, v in obj.items())
        return 0

    return _size(proof)


def _summary(proof: StarkProof) -> dict[str, Any]:
    n_queries = len(proof.queries)
    n_fri_layers = len(proof.fri_proof.layer_roots)
    return {
        "params": asdict(proof.params),
        "n_queries": n_queries,
        "n_fri_layers": n_fri_layers,
        "estimated_proof_size_bytes": _proof_size_bytes(proof),
        "trace_root": proof.trace_root.hex(),
        "comp_root": proof.comp_root.hex(),
    }


def main() -> None:
    print("=" * 72)
    print("STARK — Fibonacci recurrence (proof that u_N = C without recomputing)")
    print("=" * 72)

    # Statement (public).
    c0, c1, N = 1, 2, 31   # u_0 = 1, u_1 = 2, claimed final index N = 31
    prime = FieldElement(0).prime
    trace = generate_trace(c0, c1, N)
    C = int(trace[-1])     # the claim
    print(f"Statement: u_0 = {c0}, u_1 = {c1}, N = {N}, C = {C}")

    params = StarkParams(
        c0=c0,
        c1=c1,
        N=N,
        C=C,
        blowup_factor=4,
        num_queries=8,
        max_degree_plus_one=16,
        shift=3,
    )

    # Prove.
    t0 = time.perf_counter()
    proof = prove_stark(params)
    t_prove = time.perf_counter() - t0

    # Verify.
    t0 = time.perf_counter()
    ok = verify_stark(proof)
    t_verify = time.perf_counter() - t0

    print()
    print("Honest proof:")
    print(f"  prover time : {t_prove:.3f} s")
    print(f"  verifier OK : {ok}")
    print(f"  verifier t  : {t_verify:.3f} s")

    summary = _summary(proof)
    print()
    print("Proof summary:")
    print(json.dumps(summary, indent=2))

    # Tampering tests.
    print()
    print("Tampering tests (each should be rejected):")
    failures = 0
    for label, bad in [
        ("wrong C",       replace(proof, params=replace(proof.params, C=C + 1))),
        ("wrong c0",      replace(proof, params=replace(proof.params, c0=c0 + 1))),
        ("wrong N",       replace(proof, params=replace(proof.params, N=N - 1))),
    ]:
        rejected = not verify_stark(bad)
        if not rejected:
            failures += 1
        status = "REJECTED" if rejected else "ACCEPTED (!)"
        print(f"  {label:>10}: {status}")
    if failures == 0:
        print("All tampering attempts correctly rejected.")
    else:
        print(f"WARNING: {failures} tampered proof(s) were incorrectly accepted.")

    print()
    print("=" * 72)


if __name__ == "__main__":
    main()