"""SHA-256 Merkle tree over a list of leaves.

Leaves are arbitrary byte strings; intermediate nodes are SHA-256(left || right).
We use 32-byte SHA-256 throughout. The tree is built bottom-up; an
authentication path is a list of (sibling_hash, position) pairs from leaf to root.
"""

from __future__ import annotations

import hashlib
from typing import Sequence


def _hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(left + right).digest()


class MerkleTree:
    """Binary Merkle tree over a sequence of byte-string leaves.

    The number of leaves is NOT required to be a power of two: we pad the
    bottom-most layer by duplicating the last leaf so that every internal layer
    is binary. This keeps the implementation tiny and is adequate for a
    teaching repo (production STARKs avoid this padding).
    """

    def __init__(self, leaves: Sequence[bytes]) -> None:
        if len(leaves) == 0:
            raise ValueError("cannot build Merkle tree from empty leaves")
        # Pad up to next power of two by repeating last leaf.
        n = 1
        while n < len(leaves):
            n *= 2
        padded = list(leaves) + [leaves[-1]] * (n - len(leaves))
        self._layers: list[list[bytes]] = [padded]
        while len(self._layers[-1]) > 1:
            prev = self._layers[-1]
            if len(prev) % 2 != 0:
                raise RuntimeError("internal invariant violated")
            nxt = [_hash(prev[2 * i], prev[2 * i + 1]) for i in range(len(prev) // 2)]
            self._layers.append(nxt)
        self._n_original = len(leaves)
        self._n_padded = n

    # -- queries -------------------------------------------------------------

    def root(self) -> bytes:
        return self._layers[-1][0]

    def get_authentication_path(self, index: int) -> list[tuple[bytes, str]]:
        """Return sibling hashes from the leaf at `index` up to the root.

        Each entry is (sibling_hash, "left"|"right") where the position indicates
        on which side of the current node the sibling sits.
        """
        if not 0 <= index < self._n_padded:
            raise IndexError(f"index {index} out of [0, {self._n_padded})")
        path: list[tuple[bytes, str]] = []
        idx = index
        for layer in range(len(self._layers) - 1):
            cur = self._layers[layer]
            sib_idx = idx ^ 1
            position = "left" if idx % 2 == 1 else "right"
            path.append((cur[sib_idx], position))
            idx //= 2
        return path

    # -- verification --------------------------------------------------------

    @staticmethod
    def verify(
        root: bytes,
        index: int,
        leaf: bytes,
        path: Sequence[tuple[bytes, str]],
        domain_size: int,
    ) -> bool:
        """Recompute the root from a leaf and its authentication path."""
        # We don't need the domain_size argument for correctness, but a real
        # verifier uses it to know how many leaves were committed to.
        _ = domain_size
        h = leaf
        for sib, position in path:
            if position == "left":
                h = _hash(sib, h)
            elif position == "right":
                h = _hash(h, sib)
            else:
                raise ValueError(f"unknown position: {position}")
        return h == root

    @property
    def n_original(self) -> int:
        return self._n_original

    @property
    def n_padded(self) -> int:
        return self._n_padded