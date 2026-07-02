"""Fibonacci AIR (Algebraic Intermediate Representation).

An AIR captures the algebraic constraints that a witness must satisfy.
The Fibonacci AIR enforces two kinds of constraints:

  * boundary:  u_0 = c0, u_1 = c1, u_N = C
  * transition: u_{i+2} = u_{i+1} + u_i for all i in [0, N - 2]

Both a trace-level view (for checkability) and a polynomial view
(for the STARK prover) are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from stark_fibonacci.field import FieldElement
from stark_fibonacci.polynomial import Polynomial


@dataclass(frozen=True)
class FibonacciAIR:
    """Fibonacci AIR defined by the public boundary and the trace length."""

    c0: FieldElement
    c1: FieldElement
    claimed_output: FieldElement
    trace_length: int

    def __post_init__(self) -> None:
        if self.trace_length < 2:
            raise ValueError(
                f"trace_length must be >= 2 (got {self.trace_length});"
                " we need at least u_0, u_1, u_2 for the recurrence"
            )

    def boundary_constraints(self) -> list[tuple[int, FieldElement]]:
        """The three boundary constraints as (index, value) pairs."""
        return [
            (0, self.c0),
            (1, self.c1),
            (self.trace_length, self.claimed_output),
        ]

    def verify_boundary(self, trace: list[FieldElement]) -> bool:
        """True iff every boundary constraint holds on `trace`."""
        for idx, value in self.boundary_constraints():
            if trace[idx] != value:
                return False
        return True

    def transition_evaluation(self, trace: list[FieldElement], i: int) -> FieldElement:
        """trace[i + 2] - trace[i + 1] - trace[i] (zero iff u_{i+2}=u_{i+1}+u_i)."""
        return trace[i + 2] - trace[i + 1] - trace[i]

    def transition_constraint(self) -> Callable[[list[FieldElement]], bool]:
        """Return a function that checks whether a trace satisfies the
        recurrence at every index i in [0, trace_length - 2].
        """

        def check(trace: list[FieldElement]) -> bool:
            if len(trace) < self.trace_length + 1:
                return False
            for i in range(self.trace_length - 1):
                if trace[i + 2] - trace[i + 1] - trace[i] != 0:
                    return False
            return True

        return check

    def verify(self, trace: list[FieldElement]) -> bool:
        """Check both boundary and transition constraints."""
        return self.verify_boundary(trace) and self.transition_constraint()(trace)

    def transition_polynomial(self, T: Polynomial, g: FieldElement) -> Polynomial:
        """T(g^2 X) - T(g X) - T(X) as a polynomial in X.

        This polynomial vanishes on x = g^i for every i in [0, N - 2]
        iff the trace satisfies the Fibonacci recurrence.
        """
        g2 = g * g
        coeffs = T.coeffs
        shifted_x = Polynomial([coeffs[i] * g**i for i in range(len(coeffs))])
        shifted_2x = Polynomial([coeffs[i] * g2**i for i in range(len(coeffs))])
        return shifted_2x - shifted_x - T
