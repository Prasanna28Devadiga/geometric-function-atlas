"""Crypto lab: deterministic S-box construction and benchmark metrics."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytest.importorskip("numpy")

from geometric_function_atlas.lab import (
    AES_SBOX,
    IDENTITY_SBOX,
    compare_sbox,
    construct_sbox,
    differential_distribution_table,
    linear_approximation_table,
    sbox_metrics,
    sbox_metrics_record,
    sbox_structure,
    website_leaderboard,
)
from geometric_function_atlas.records import validate_screen_record

ROOT = Path(__file__).resolve().parents[1]


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


def test_crypto_structure_exposes_website_sac_ddt_and_lat_views() -> None:
    structure = sbox_structure(IDENTITY_SBOX)

    assert len(structure["SAC"]) == 8
    assert len(structure["SAC"][0]) == 8
    assert len(structure["DDT"]) == 256
    assert len(structure["DDT"][0]) == 256
    assert len(structure["LAT"]) == 256
    assert len(structure["LAT"][0]) == 256
    assert structure["DDT"] == differential_distribution_table(IDENTITY_SBOX)
    assert structure["LAT"] == linear_approximation_table(IDENTITY_SBOX)
    assert structure["metrics"]["DU"] == 256


def test_lat_matches_direct_walsh_definition_and_rejects_false_correlations() -> None:
    def direct_lat(sbox: tuple[int, ...], input_mask: int, output_mask: int) -> int:
        total = 0
        for x, value in enumerate(sbox):
            input_parity = (input_mask & x).bit_count() & 1
            output_parity = (output_mask & value).bit_count() & 1
            total += 1 if input_parity == output_parity else -1
        return total // 2

    table = linear_approximation_table(IDENTITY_SBOX)

    for input_mask, output_mask in ((0, 0), (1, 1), (1, 2), (2, 1), (255, 255)):
        assert table[input_mask][output_mask] == direct_lat(
            IDENTITY_SBOX, input_mask, output_mask
        )

    # A wrong signed-input WHT implementation reports a large diagonal bias
    # with the wrong sign and can turn an off-diagonal zero into a correlation.
    assert table[0][0] == 128
    assert table[1][1] == 128
    assert table[1][2] == 0


def test_crypto_reference_comparison_is_explicitly_benchmark_only() -> None:
    comparison = compare_sbox(IDENTITY_SBOX)

    assert set(comparison["references"]) == {"AES", "identity"}
    assert comparison["metrics"]["LP"] == pytest.approx(0.5)
    assert comparison["delta"]["identity"]["LP"] == pytest.approx(0.0)
    assert set(comparison["paper_references"]) == {
        "AES",
        "DCT",
        "Skipjack",
        "Xyi",
        "Residue-Prime",
    }
    assert comparison["paper_references"]["DCT"]["reference_kind"] == "paper_reported"
    assert comparison["novelty_claim"] is False
    assert "security" in comparison["scope"]


def test_website_leaderboard_preserves_the_versioned_metric_snapshot() -> None:
    rows = website_leaderboard()

    assert len(rows) == 435
    assert rows[0]["key"] == "r525"
    assert rows[0]["source"] == "website_snapshot"
    assert rows[0]["NL_avg"] == pytest.approx(106.0)
    assert rows[0]["novelty_claim"] is False
    assert "security claim" in rows[0]["scope"]
    assert rows[-1]["key"] == "r391"
    assert all("sbox" not in row for row in rows)


def test_website_leaderboard_rows_match_the_website_artifact() -> None:
    source_path = ROOT.parent / "gft-registry" / "static-site" / "crypto_lab.json"
    if not source_path.is_file():
        pytest.skip("source website artifact is unavailable")
    source_rows = json.loads(source_path.read_text(encoding="utf-8"))["leaderboard"]

    rows = website_leaderboard()

    assert len(rows) == len(source_rows)
    for actual, expected in zip(rows, source_rows, strict=True):
        assert actual["key"] == expected["key"]
        assert actual["label"] == expected["label"]
        assert actual["family"] == expected["family"]
        assert actual["asha"] == expected["asha"]
        assert actual["NL_avg"] == pytest.approx(expected["NL"])
        assert actual["SAC_avg"] == pytest.approx(expected["SAC"])
        assert actual["BIC_avg"] == pytest.approx(expected["BIC"])
        assert actual["DP"] == pytest.approx(expected["DP"])
        assert actual["LP"] == pytest.approx(expected["LP"])
