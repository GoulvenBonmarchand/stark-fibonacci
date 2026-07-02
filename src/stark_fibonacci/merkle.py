"""Merkle tree commitment scheme over SHA-256.

Leaves are SHA-256 hashes of the deterministic serialization of the
FieldElement values, prefixed with a domain separator byte (0x00 for
leaves, 0x01 for internal nodes) so that no leaf hash can collide with
an internal hash.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Sequence


from stark_fibonacci.field import FieldElement


_LEAF_PREFIX: bytes = b"\x00"
_NODE_PREFIX: bytes = b"\x01"


def _serialize_value(value: FieldElement) -> bytes:
    """Deterministic byte encoding for a FieldElement value (decimal)."""
    return str(value.value).encode("ascii")


def hash_leaf(value: FieldElement) -> bytes:
    """SHA-256 of `value` under the leaf prefix."""
    return hashlib.sha256(_LEAF_PREFIX + _serialize_value(value)).digest()


def hash_node(left: bytes, right: bytes) -> bytes:
    """SHA-256 of two child hashes under the node prefix."""
    return hashlib.sha256(_NODE_PREFIX + left + right).digest()


@dataclass(frozen=True)
class MerkleProof:
    """A Merkle authentication path from a leaf to the tree root."""

    index: int
    leaf_hash: bytes
    siblings: tuple[bytes, ...]

    def verify(self, root: bytes) -> bool:
        """Reconstruct the root from the proof and compare it to `root`."""
        current = self.leaf_hash
        idx = self.index
        for sibling in self.siblings:
            if idx & 1 == 0:
                current = hash_node(current, sibling)
            else:
                current = hash_node(sibling, current)
            idx >>= 1
        return current == root


class MerkleTree:
    """A binary Merkle tree built from a sequence of FieldElement leaves.

    Trees with a non-power-of-two number of leaves are right-padded
    with copies of the last leaf, so internal-layer sizes are always a
    power of two.
    """

    def __init__(self, leaves: Sequence[FieldElement]) -> None:
        if not leaves:
            raise ValueError("Merkle tree requires at least one leaf")
        self._leaves: tuple[FieldElement, ...] = tuple(leaves)
        layer: list[bytes] = [hash_leaf(leaf) for leaf in self._leaves]
        while len(layer) > 1 and (len(layer) & (len(layer) - 1)) != 0:
            layer.append(layer[-1])
        self._layers: list[list[bytes]] = [layer]
        while len(self._layers[-1]) > 1:
            prev = self._layers[-1]
            nxt = [hash_node(prev[i], prev[i + 1]) for i in range(0, len(prev), 2)]
            self._layers.append(nxt)

    @property
    def leaf_count(self) -> int:
        return len(self._leaves)

    def root(self) -> bytes:
        return self._layers[-1][0]

    def open(self, index: int) -> MerkleProof:
        """Return the authentication path for `leaves[index]`."""
        if not 0 <= index < len(self._leaves):
            raise IndexError(
                f"index {index} out of range for {len(self._leaves)} leaves"
            )
        siblings: list[bytes] = []
        cur_index = index
        for layer in self._layers[:-1]:
            sibling_index = cur_index ^ 1
            if sibling_index >= len(layer):
                sibling_index = cur_index
            siblings.append(layer[sibling_index])
            cur_index //= 2
        return MerkleProof(
            index=index,
            leaf_hash=hash_leaf(self._leaves[index]),
            siblings=tuple(siblings),
        )
