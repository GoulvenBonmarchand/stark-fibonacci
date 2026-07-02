"""Tests for the Merkle tree commitment scheme."""

from __future__ import annotations

import hashlib

import pytest

from stark_fibonacci.field import FieldElement
from stark_fibonacci.merkle import MerkleProof, MerkleTree, hash_leaf


def _build(n: int) -> MerkleTree:
    return MerkleTree([FieldElement(i + 1) for i in range(n)])


def test_root_deterministic() -> None:
    t1 = _build(8)
    t2 = _build(8)
    assert t1.root() == t2.root()


def test_root_different_leaves_differ() -> None:
    a = _build(8)
    b = MerkleTree([FieldElement(i + 2) for i in range(8)])
    assert a.root() != b.root()


def test_open_and_verify_each_leaf_powers_of_two() -> None:
    for size in [1, 2, 4, 8, 16]:
        tree = _build(size)
        root = tree.root()
        for i in range(size):
            proof = tree.open(i)
            assert proof.verify(root)


def test_open_and_verify_odd_leaf_count() -> None:
    tree = _build(3)
    root = tree.root()
    for i in range(3):
        proof = tree.open(i)
        assert proof.verify(root)


def test_open_and_verify_other_odd_counts() -> None:
    for size in [5, 6, 7, 9, 13]:
        tree = _build(size)
        root = tree.root()
        for i in range(size):
            proof = tree.open(i)
            assert proof.verify(root)


def test_modified_leaf_rejected() -> None:
    tree = _build(8)
    proof = tree.open(0)
    tampered = MerkleProof(
        index=proof.index,
        leaf_hash=hashlib.sha256(b"wrong").digest(),
        siblings=proof.siblings,
    )
    assert not tampered.verify(tree.root())


def test_modified_index_rejected() -> None:
    tree = _build(8)
    proof = tree.open(0)
    tampered = MerkleProof(
        index=proof.index + 1,
        leaf_hash=proof.leaf_hash,
        siblings=proof.siblings,
    )
    assert not tampered.verify(tree.root())


def test_modified_sibling_rejected() -> None:
    tree = _build(8)
    proof = tree.open(0)
    new_siblings = (hashlib.sha256(b"bad").digest(),) + proof.siblings[1:]
    tampered = MerkleProof(
        index=proof.index,
        leaf_hash=proof.leaf_hash,
        siblings=new_siblings,
    )
    assert not tampered.verify(tree.root())


def test_modified_last_sibling_rejected() -> None:
    tree = _build(8)
    proof = tree.open(0)
    bad_sibling = (
        (proof.siblings[0],) + proof.siblings[1:-1] + (hashlib.sha256(b"bad").digest(),)
    )
    tampered = MerkleProof(
        index=proof.index,
        leaf_hash=proof.leaf_hash,
        siblings=bad_sibling,
    )
    assert not tampered.verify(tree.root())


def test_wrong_root_rejected() -> None:
    tree = _build(8)
    proof = tree.open(0)
    assert not proof.verify(b"\x00" * 32)


def test_out_of_range_index_raises() -> None:
    tree = _build(4)
    with pytest.raises(IndexError):
        tree.open(4)
    with pytest.raises(IndexError):
        tree.open(-1)


def test_empty_leaves_rejected() -> None:
    with pytest.raises(ValueError):
        MerkleTree([])


def test_leaf_hash_deterministic() -> None:
    assert hash_leaf(FieldElement(42)) == hash_leaf(FieldElement(42))
    assert hash_leaf(FieldElement(42)) != hash_leaf(FieldElement(43))


def test_serialization_avoids_collisions() -> None:
    # FieldElement values that stringify identically should still collide;
    # the byte-different value representation matters.
    assert hash_leaf(FieldElement(1)) == hash_leaf(FieldElement(1))
    assert hash_leaf(FieldElement(10)) != hash_leaf(FieldElement(100))
