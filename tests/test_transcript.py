"""Tests for the Fiat-Shamir transcript."""

from __future__ import annotations

import pytest

from stark_fibonacci.transcript import Transcript


def test_determinism_same_seed() -> None:
    t1 = Transcript(b"start")
    t2 = Transcript(b"start")
    t1.append_message(b"m", b"hello")
    t2.append_message(b"m", b"hello")
    assert t1.challenge_field(b"alpha") == t2.challenge_field(b"alpha")
    assert t1.challenge_index(b"idx", 100) == t2.challenge_index(b"idx", 100)


def test_different_messages_different_challenges() -> None:
    t1 = Transcript(b"start")
    t2 = Transcript(b"start")
    t1.append_message(b"m", b"hello")
    t2.append_message(b"m", b"hellp")
    assert t1.challenge_field(b"c") != t2.challenge_field(b"c")


def test_label_separation() -> None:
    t1 = Transcript(b"start")
    t1.append_message(b"m", b"x")
    t2 = Transcript(b"start")
    t2.append_message(b"m", b"x")
    c1 = t1.challenge_field(b"alpha")
    c2 = t2.challenge_field(b"beta")
    assert c1 != c2


def test_state_evolves_with_repeated_calls() -> None:
    t = Transcript(b"start")
    c1 = t.challenge_field(b"alpha")
    c2 = t.challenge_field(b"alpha")
    assert c1 != c2


def test_challenge_index_in_range() -> None:
    t = Transcript(b"start")
    for ub in [1, 2, 3, 7, 16, 100, 1000, 2**16]:
        for _ in range(20):
            i = t.challenge_index(b"idx", ub)
            assert 0 <= i < ub


def test_challenge_index_distribution() -> None:
    t = Transcript(b"start")
    counts = [0] * 8
    for _ in range(200):
        i = t.challenge_index(b"idx", 8)
        counts[i] += 1
    # very loose distribution check
    assert all(c > 0 for c in counts)


def test_invalid_upper_bound() -> None:
    t = Transcript(b"start")
    with pytest.raises(ValueError):
        t.challenge_index(b"x", 0)
    with pytest.raises(ValueError):
        t.challenge_index(b"x", -1)


def test_initial_state_changes_with_seed() -> None:
    a = Transcript(b"alpha")
    b = Transcript(b"beta")
    assert a.state != b.state


def test_append_changes_state() -> None:
    t = Transcript(b"start")
    s0 = t.state
    t.append_message(b"m", b"hello")
    s1 = t.state
    assert s0 != s1


def test_message_after_challenge_consumed() -> None:
    t1 = Transcript(b"start")
    t1.append_message(b"m", b"x")
    t1.challenge_field(b"alpha")
    t2 = Transcript(b"start")
    t2.append_message(b"m", b"x")
    t2.challenge_field(b"alpha")
    t1.append_message(b"m2", b"y")
    t2.append_message(b"m2", b"y")
    assert t1.challenge_field(b"final") == t2.challenge_field(b"final")
