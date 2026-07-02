"""Tests for the stark-fibonacci CLI."""

from __future__ import annotations

import json
from pathlib import Path

from stark_fibonacci.cli import main


def _run(argv: list[str]) -> int:
    return main(argv)


def test_demo_runs(capsys: object) -> None:
    rc = _run(["demo"])
    assert rc == 0
    out, _ = capsys.readouterr()  # type: ignore[attr-defined]
    assert "STARK" in out
    assert "Honest proof" in out


def test_prove_then_verify(tmp_path: Path) -> None:
    proof_path = tmp_path / "proof.json"
    rc = _run(
        [
            "prove",
            "--c0",
            "1",
            "--c1",
            "1",
            "--n",
            "10",
            "--output",
            "89",
            "--proof",
            str(proof_path),
            "--blowup",
            "4",
            "--queries",
            "4",
            "--fri-degree",
            "4",
        ]
    )
    assert rc == 0
    assert proof_path.exists()
    payload = json.loads(proof_path.read_text())
    assert payload["public_inputs"]["c0"] == 1
    assert payload["public_inputs"]["c1"] == 1
    assert payload["public_inputs"]["n"] == 10
    assert payload["public_inputs"]["claimed_output"] == 89

    rc = _run(["verify", "--proof", str(proof_path)])
    assert rc == 0


def test_verify_rejects_tampered_proof(tmp_path: Path) -> None:
    proof_path = tmp_path / "proof.json"
    _run(
        [
            "prove",
            "--c0",
            "1",
            "--c1",
            "1",
            "--n",
            "7",
            "--output",
            "21",
            "--proof",
            str(proof_path),
            "--blowup",
            "4",
            "--queries",
            "4",
            "--fri-degree",
            "3",
        ]
    )
    payload = json.loads(proof_path.read_text())
    payload["public_inputs"]["n"] = 99
    proof_path.write_text(json.dumps(payload))
    rc = _run(["verify", "--proof", str(proof_path)])
    assert rc == 1


def test_invalid_subcommand(capsys: object) -> None:
    rc = _run(["bogus"])
    assert rc == 2


def test_wrong_n_rejected_at_prove_time(tmp_path: Path) -> None:
    proof_path = tmp_path / "bad-proof.json"
    # Wrong claimed_output: should raise and exit non-zero.
    rc = _run(
        [
            "prove",
            "--c0",
            "1",
            "--c1",
            "1",
            "--n",
            "7",
            "--output",
            "999",
            "--proof",
            str(proof_path),
        ]
    )
    assert rc != 0
    assert not proof_path.exists()


def test_main_entry_returns_int() -> None:
    assert isinstance(_run(["demo"]), int)


def test_main_accepts_argv() -> None:
    rc = main(["demo"])
    assert rc == 0
