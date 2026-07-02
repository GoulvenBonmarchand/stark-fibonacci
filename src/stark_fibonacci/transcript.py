"""Fiat-Shamir transcript for non-interactive STARK challenges.

The transcript maintains a hash chain: every `append_message` absorbs
`(state || label || message)` into the new state, and `challenge_*`
methods extract field/index challenges from a state updated under
their own label.  This gives the standard separation properties needed
to prevent adversarial challenge grinding.
"""

from __future__ import annotations

import hashlib

from stark_fibonacci.field import FieldElement


class Transcript:
    """A SHA-256 Fiat-Shamir transcript."""

    def __init__(self, label: bytes = b"STARK-transcript") -> None:
        self._state = hashlib.sha256(label).digest()

    def append_message(self, label: bytes, message: bytes) -> None:
        """Absorb an externally provided message tagged with `label`."""
        self._state = hashlib.sha256(self._state + label + message).digest()

    def _absorb(self, label: bytes) -> bytes:
        new_state = hashlib.sha256(self._state + label).digest()
        self._state = new_state
        return new_state

    def challenge_field(self, label: bytes) -> FieldElement:
        """Derive a uniform-looking FieldElement under `label`."""
        h = self._absorb(label)
        return FieldElement(int.from_bytes(h, "big"))

    def challenge_index(self, label: bytes, upper_bound: int) -> int:
        """Derive an integer in [0, upper_bound) under `label`.

        Naive modulo; bias is negligible since upper_bound << 2**256.
        """
        if upper_bound <= 0:
            raise ValueError("upper_bound must be positive")
        h = self._absorb(label)
        return int.from_bytes(h, "big") % upper_bound

    @property
    def state(self) -> bytes:
        """Current transcript state (for diagnostics only)."""
        return self._state
