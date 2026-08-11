"""Crypto lab: deterministic S-box construction and benchmark metrics."""

from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from geometric_function_atlas.lab import (
    AES_SBOX,
    IDENTITY_SBOX,
    construct_sbox,
    sbox_metrics,
    sbox_metrics_record,
)
from geometric_function_atlas.records import validate_screen_record


def test_aes_anchor_matches_known_benchmark_values() -> None:
    metrics = sbox_metrics(AES_SBOX)
    assert metrics["bijection"] is True
    assert metrics["NL_min"] == 112
    assert metrics["NL_avg"] == 112.0
    assert metrics["DP"] == pytest.approx(4 / 256)
    assert metrics["LP"] == pytest.approx(0.0625)
    assert metrics["BIC_avg"] == pytest.approx(112.0, abs=0.01)
    assert metrics["SAC_avg"] == pytest.approx(0.504, abs=0.005)


def test_identity_anchor_is_a_poor_box_by_construction() -> None:
    metrics = sbox_metrics(IDENTITY_SBOX)
    assert metrics["bijection"] is True
    assert metrics["NL_min"] == 0
    assert metrics["LP"] == pytest.approx(0.5)
    assert metrics["DU"] == 256
    assert metrics["DP"] == 1.0
    assert metrics["SAC_avg"] == pytest.approx(1 / 8)


def test_construction_is_deterministic_and_a_bijection() -> None:
    first = construct_sbox("sine", key=b"gft-registry")
    second = construct_sbox("sine", key=b"gft-registry")
    assert first == second
    assert len(first) == 256
    assert sorted(first) == list(range(256))
    assert sbox_metrics(first)["bijection"] is True


def test_key_changes_the_constructed_box() -> None:
    assert construct_sbox("sine", key=b"key-a") != construct_sbox(
        "sine", key=b"key-b"
    )


def test_direct_construction_is_deterministic() -> None:
    first = construct_sbox("cardioid", construction="direct")
    second = construct_sbox("cardioid", construction="direct")
    assert first == second
    assert sbox_metrics(first)["bijection"] is True


def test_unknown_function_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown function"):
        construct_sbox("riemann_zeta")


def test_unknown_construction_is_rejected() -> None:
    with pytest.raises(ValueError, match="construction"):
        construct_sbox("sine", construction="magic")  # type: ignore[arg-type]


def test_malformed_sbox_is_rejected() -> None:
    with pytest.raises(ValueError, match="256 integers"):
        sbox_metrics([1, 2, 3])
    with pytest.raises(ValueError, match="256 integers"):
        sbox_metrics(list(range(255)))


def test_metrics_record_is_closed_and_not_a_security_claim() -> None:
    metrics = sbox_metrics(AES_SBOX)
    record = sbox_metrics_record(metrics, label="aes")
    assert record["record_type"] == "lab_metrics"
    assert record["evidence_kind"] == "benchmark_metric"
    assert record["details"]["label"] == "aes"
    assert record["details"]["NL_min"] == 112
    assert record["novelty_claim"] is False
    validate_screen_record(record)
