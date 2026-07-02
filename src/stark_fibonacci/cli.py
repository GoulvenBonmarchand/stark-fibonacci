"""Command-line interface for the Fibonacci STARK prover/verifier."""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import replace
from typing import Sequence

from stark_fibonacci.proof import StarkProof
from stark_fibonacci.stark import prove_fibonacci, verify_fibonacci
from stark_fibonacci.trace import fibonacci_trace


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stark-fibonacci",
        description=(
            "STARK prover and verifier for the Fibonacci recurrence. "
            "Proves that the sequence defined by u_0 = c0, u_1 = c1, "
            "u_{i+2} = u_{i+1} + u_i satisfies u_N = C, without "
            "recomputing the entire sequence."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser(
        "demo",
        help="Generate and verify an honest proof, then a few tampered ones.",
    )

    prove_p = sub.add_parser(
        "prove",
        help="Generate a STARK proof and write it to a JSON file.",
    )
    prove_p.add_argument("--c0", type=int, required=True, help="Initial value u_0.")
    prove_p.add_argument("--c1", type=int, required=True, help="Initial value u_1.")
    prove_p.add_argument(
        "--n", type=int, required=True, help="Index N of the claimed term."
    )
    prove_p.add_argument(
        "--output",
        type=int,
        required=True,
        dest="claimed_output",
        help="Claimed value of u_N.",
    )
    prove_p.add_argument(
        "--proof",
        type=str,
        default="proof.json",
        help="Output path for the JSON proof (default: proof.json).",
    )
    prove_p.add_argument(
        "--blowup",
        type=int,
        default=8,
        help="LDE blowup factor (default: 8).",
    )
    prove_p.add_argument(
        "--queries",
        type=int,
        default=8,
        help="Number of STARK/FRI queries (default: 8).",
    )
    prove_p.add_argument(
        "--fri-degree",
        type=int,
        default=8,
        dest="fri_claimed_degree",
        help="FRI claimed degree of the composition polynomial.",
    )

    verify_p = sub.add_parser(
        "verify",
        help="Verify a STARK proof from a JSON file.",
    )
    verify_p.add_argument(
        "--proof",
        type=str,
        required=True,
        help="Path to the JSON proof file.",
    )

    return parser


def _run_demo() -> int:
    print("=" * 78)
    print("STARK — Fibonacci recurrence (proof that u_N = C without recomputing)")
    print("=" * 78)

    c0 = 1
    c1 = 1
    n = 31
    trace = fibonacci_trace(c0, c1, n)
    claimed = int(trace[n].value)
    print(f"Statement: u_0 = {c0}, u_1 = {c1}, N = {n}, C = {claimed}")

    t0 = time.perf_counter()
    proof = prove_fibonacci(
        c0=c0,
        c1=c1,
        n=n,
        claimed_output=claimed,
        blowup_factor=4,
        num_queries=4,
        fri_claimed_degree=8,
    )
    prover_time = time.perf_counter() - t0

    t0 = time.perf_counter()
    ok = verify_fibonacci(proof)
    verifier_time = time.perf_counter() - t0

    print("\nHonest proof:")
    print(f"  prover time : {prover_time:.3f} s")
    print(f"  verifier OK : {ok}")
    print(f"  verifier t  : {verifier_time:.3f} s")

    print("\nTampering tests (verifier can read each variant independently):")
    tampering: list[tuple[str, StarkProof]] = [
        (
            "wrong C:",
            replace(
                proof,
                public_inputs=replace(proof.public_inputs, claimed_output=999_999),
            ),
        ),
        (
            "wrong c0:",
            replace(proof, public_inputs=replace(proof.public_inputs, c0=99)),
        ),
        (
            "wrong N:",
            replace(proof, public_inputs=replace(proof.public_inputs, n=7)),
        ),
    ]
    for label, bad in tampering:
        verdict = (
            "REJECTED"
            if not verify_fibonacci(bad)
            else "ACCEPTED (boundary not enforced)"
        )
        print(f"     {label} {verdict}")

    print(
        "\nNote: the verifier never iterates over u_0, u_1, ..., u_N; "
        "it inspects only the proof's commitments and random openings."
    )
    return 0


def _run_prove(args: argparse.Namespace) -> int:
    proof = prove_fibonacci(
        c0=args.c0,
        c1=args.c1,
        n=args.n,
        claimed_output=args.claimed_output,
        blowup_factor=args.blowup,
        num_queries=args.queries,
        fri_claimed_degree=args.fri_claimed_degree,
    )
    with open(args.proof, "w", encoding="utf-8") as f:
        f.write(proof.to_json())
    print(f"Proof written to {args.proof}")
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    with open(args.proof, encoding="utf-8") as f:
        proof = StarkProof.from_json(f.read())
    ok = verify_fibonacci(proof)
    print("Verifier:", "OK" if ok else "REJECTED")
    return 0 if ok else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if isinstance(e.code, int) else 2
    try:
        if args.cmd == "demo":
            return _run_demo()
        if args.cmd == "prove":
            return _run_prove(args)
        if args.cmd == "verify":
            return _run_verify(args)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
