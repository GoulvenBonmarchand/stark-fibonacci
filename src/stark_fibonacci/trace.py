"""Generation of the Fibonacci trace over F_p.

The trace is the witness sequence [u_0, u_1, ..., u_N] where
    u_0 = c0, u_1 = c1, u_{i+2} = u_{i+1} + u_i.
"""

from __future__ import annotations

from stark_fibonacci.field import FieldElement


def fibonacci_trace(
    c0: FieldElement | int,
    c1: FieldElement | int,
    n: int,
) -> list[FieldElement]:
    """Compute [u_0, u_1, ..., u_N] (length n+1) over F_p.

    n is the largest index. c0, c1 may be plain Python ints; they are
    reduced modulo p on construction.
    """
    if n < 0:
        raise ValueError("n must be >= 0")
    a = c0 if isinstance(c0, FieldElement) else FieldElement(c0)
    b = c1 if isinstance(c1, FieldElement) else FieldElement(c1)
    if n == 0:
        return [a]
    trace: list[FieldElement] = [a, b]
    for _ in range(n - 1):
        trace.append(trace[-1] + trace[-2])
    return trace
