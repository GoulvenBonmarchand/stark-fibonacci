"""Tests for the SHA-256 Merkle tree."""

import pytest

from stark_fibonacci.merkle import MerkleTree


def test_root_deterministic():
    leaves = [b"a", b"b", b"c"]
    r1 = MerkleTree(leaves).root()
    r2 = MerkleTree(leaves).root()
    assert r1 == r2


def test_authentication_path_round_trip():
    leaves = [f"leaf-{i}".encode() for i in range(7)]
    tree = MerkleTree(leaves)
    root = tree.root()
    for i in range(len(leaves)):
        path = tree.get_authentication_path(i)
        assert MerkleTree.verify(root, i, leaves[i], path, tree.n_padded)


def test_authentication_path_rejects_tampering():
    leaves = [f"leaf-{i}".encode() for i in range(5)]
    tree = MerkleTree(leaves)
    root = tree.root()
    for i in range(len(leaves)):
        path = tree.get_authentication_path(i)
        tampered_leaf = b"tampered"
        assert not MerkleTree.verify(root, i, tampered_leaf, path, tree.n_padded)


def test_authentication_path_rejects_path_tampering():
    """Flipping a single byte of the auth path must produce a different root."""
    leaves = [f"leaf-{i}".encode() for i in range(5)]
    tree = MerkleTree(leaves)
    root = tree.root()
    for i in range(len(leaves)):
        path = [list(p) for p in tree.get_authentication_path(i)]
        if not path:
            continue
        # Flip one byte of the first sibling hash.
        sibling, position = path[0]
        tampered = bytes([sibling[0] ^ 1]) + sibling[1:]
        path[0] = (tampered, position)
        assert not MerkleTree.verify(root, i, leaves[i], path, tree.n_padded)


def test_pow_of_two_no_padding():
    leaves = [b"x"] * 8
    tree = MerkleTree(leaves)
    assert tree.n_original == 8
    assert tree.n_padded == 8


def test_non_power_of_two_pads():
    leaves = [b"x"] * 5
    tree = MerkleTree(leaves)
    assert tree.n_original == 5
    assert tree.n_padded == 8
    for i in range(5):
        path = tree.get_authentication_path(i)
        assert MerkleTree.verify(tree.root(), i, leaves[i], path, tree.n_padded)


def test_single_leaf():
    tree = MerkleTree([b"only"])
    assert tree.root() == b"only" or len(tree.root()) == 32
    # For a single leaf, the root is just the leaf hash.
    assert MerkleTree.verify(tree.root(), 0, b"only", [], tree.n_padded)


def test_empty_leaves_raises():
    with pytest.raises(ValueError):
        MerkleTree([])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])