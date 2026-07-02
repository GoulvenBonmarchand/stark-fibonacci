"""STARK proof object structures and JSON (de)serialization.

The structures here are shared between the prover and the verifier.
The `to_dict`/`from_dict` methods produce JSON-friendly dictionaries in
which `bytes` are hex-encoded and `FieldElement` values are integers
in `[0, p)`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from stark_fibonacci.field import FieldElement
from stark_fibonacci.fri import (
    FRIProof,
    FRIQueryOpening,
    FRILayer,
)


@dataclass(frozen=True)
class PublicInputs:
    """The public statement that a Fibonacci STARK proves."""

    c0: int
    c1: int
    n: int
    claimed_output: int
    lde_domain_size: int
    fri_claimed_degree: int
    num_queries: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PublicInputs":
        return cls(**d)


def _hex(b: bytes) -> str:
    return b.hex()


def _unhex(s: str) -> bytes:
    return bytes.fromhex(s)


def merkle_proof_to_dict(proof) -> dict[str, Any]:
    return {
        "index": proof.index,
        "leaf_hash_hex": _hex(proof.leaf_hash),
        "siblings_hex": [_hex(s) for s in proof.siblings],
    }


def merkle_proof_from_dict(d: dict[str, Any]):
    from stark_fibonacci.merkle import MerkleProof

    return MerkleProof(
        index=d["index"],
        leaf_hash=_unhex(d["leaf_hash_hex"]),
        siblings=tuple(_unhex(s) for s in d["siblings_hex"]),
    )


def fri_query_to_dict(q: FRIQueryOpening) -> dict[str, Any]:
    return {
        "initial_index": q.initial_index,
        "layer_openings": [
            {
                "value_pos": op[0].value,
                "value_neg": op[1].value,
                "proof_pos": merkle_proof_to_dict(op[2]),
                "proof_neg": merkle_proof_to_dict(op[3]),
            }
            for op in q.layer_openings
        ],
    }


def fri_query_from_dict(d: dict[str, Any]) -> FRIQueryOpening:
    return FRIQueryOpening(
        initial_index=d["initial_index"],
        layer_openings=tuple(
            (
                FieldElement(op["value_pos"]),
                FieldElement(op["value_neg"]),
                merkle_proof_from_dict(op["proof_pos"]),
                merkle_proof_from_dict(op["proof_neg"]),
            )
            for op in d["layer_openings"]
        ),
    )


def fri_layer_to_dict(layer: FRILayer) -> dict[str, Any]:
    return {
        "domain": [x.value for x in layer.domain],
        "evaluations": [v.value for v in layer.evaluations],
        "merkle_root_hex": _hex(layer.merkle_root),
    }


def fri_layer_from_dict(d: dict[str, Any]) -> FRILayer:
    return FRILayer(
        domain=tuple(FieldElement(v) for v in d["domain"]),
        evaluations=tuple(FieldElement(v) for v in d["evaluations"]),
        merkle_root=_unhex(d["merkle_root_hex"]),
    )


def fri_proof_to_dict(proof: FRIProof) -> dict[str, Any]:
    return {
        "initial_domain": [x.value for x in proof.initial_domain],
        "layers": [fri_layer_to_dict(layer) for layer in proof.layers],
        "final_coeffs": [c.value for c in proof.final_coeffs],
        "alphas": [a.value for a in proof.alphas],
        "queries": [fri_query_to_dict(q) for q in proof.queries],
    }


def fri_proof_from_dict(d: dict[str, Any]) -> FRIProof:
    return FRIProof(
        initial_domain=tuple(FieldElement(v) for v in d["initial_domain"]),
        layers=tuple(fri_layer_from_dict(layer) for layer in d["layers"]),
        final_coeffs=tuple(FieldElement(v) for v in d["final_coeffs"]),
        alphas=tuple(FieldElement(v) for v in d["alphas"]),
        queries=tuple(fri_query_from_dict(q) for q in d["queries"]),
    )


@dataclass(frozen=True)
class StarkOpening:
    """Per-query opening: trace values + composition + FRI."""

    initial_index: int
    trace_x_value: int
    trace_gx_value: int
    trace_g2x_value: int
    trace_x_proof: object
    trace_gx_proof: object
    trace_g2x_proof: object
    composition_x_value: int
    composition_x_proof: object
    fri_opening: FRIQueryOpening

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_index": self.initial_index,
            "trace_x_value": self.trace_x_value,
            "trace_gx_value": self.trace_gx_value,
            "trace_g2x_value": self.trace_g2x_value,
            "trace_x_proof": merkle_proof_to_dict(self.trace_x_proof),
            "trace_gx_proof": merkle_proof_to_dict(self.trace_gx_proof),
            "trace_g2x_proof": merkle_proof_to_dict(self.trace_g2x_proof),
            "composition_x_value": self.composition_x_value,
            "composition_x_proof": merkle_proof_to_dict(self.composition_x_proof),
            "fri_opening": fri_query_to_dict(self.fri_opening),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StarkOpening":
        return cls(
            initial_index=d["initial_index"],
            trace_x_value=d["trace_x_value"],
            trace_gx_value=d["trace_gx_value"],
            trace_g2x_value=d["trace_g2x_value"],
            trace_x_proof=merkle_proof_from_dict(d["trace_x_proof"]),
            trace_gx_proof=merkle_proof_from_dict(d["trace_gx_proof"]),
            trace_g2x_proof=merkle_proof_from_dict(d["trace_g2x_proof"]),
            composition_x_value=d["composition_x_value"],
            composition_x_proof=merkle_proof_from_dict(d["composition_x_proof"]),
            fri_opening=fri_query_from_dict(d["fri_opening"]),
        )


@dataclass(frozen=True)
class StarkProof:
    """A complete STARK proof for the Fibonacci recurrence."""

    public_inputs: PublicInputs
    trace_merkle_root: bytes
    composition_merkle_root: bytes
    trace_domain_hex: str
    composition_domain_hex: str
    fri_proof: FRIProof
    openings: tuple[StarkOpening, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "public_inputs": self.public_inputs.to_dict(),
            "trace_merkle_root_hex": _hex(self.trace_merkle_root),
            "composition_merkle_root_hex": _hex(self.composition_merkle_root),
            "trace_domain_hex": self.trace_domain_hex,
            "composition_domain_hex": self.composition_domain_hex,
            "fri_proof": fri_proof_to_dict(self.fri_proof),
            "openings": [o.to_dict() for o in self.openings],
        }

    def to_json(self) -> str:
        import json

        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "StarkProof":
        return cls(
            public_inputs=PublicInputs.from_dict(d["public_inputs"]),
            trace_merkle_root=_unhex(d["trace_merkle_root_hex"]),
            composition_merkle_root=_unhex(d["composition_merkle_root_hex"]),
            trace_domain_hex=d["trace_domain_hex"],
            composition_domain_hex=d["composition_domain_hex"],
            fri_proof=fri_proof_from_dict(d["fri_proof"]),
            openings=tuple(StarkOpening.from_dict(o) for o in d["openings"]),
        )

    @classmethod
    def from_json(cls, s: str) -> "StarkProof":
        import json

        return cls.from_dict(json.loads(s))
