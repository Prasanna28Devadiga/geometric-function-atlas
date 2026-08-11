"""Tests for the versioned baked-artifact API and fail-closed certificate replay."""

from __future__ import annotations

import json

import pytest
from jsonschema import Draft202012Validator

import geometric_function_atlas as gfa
from geometric_function_atlas import artifacts as artifacts_module
from geometric_function_atlas.contracts import (
    CorruptArtifactError,
    InvalidInputError,
    UnsupportedError,
)

# ── snapshot integrity ────────────────────────────────────────────────────────


def test_snapshot_verify_passes_every_shipped_artifact() -> None:
    record = gfa.snapshot_verify()

    assert record["files_verified"] == 8
    assert record["checks"]["success"] is True
    assert record["artifact_version"] == "2026.08.11"


def test_snapshot_info_reports_versioned_identity() -> None:
    record = gfa.snapshot_info()

    assert record["schema_version"] == 1
    assert record["artifact_version"] == "2026.08.11"
    assert record["source_commit"]
    assert set(record["files"]) == {
        "bounds.json",
        "certificates.json",
        "classes.json",
        "expansions.json",
        "open_problems.json",
        "proof_meta.json",
        "reconciliation.json",
        "references.md",
    }


def test_snapshot_verify_fails_closed_on_missing_artifact(
    monkeypatch, tmp_path
) -> None:
    nonexistent = tmp_path / "classes.json"  # never created

    def pointer(name: str):
        if name == "manifest.json":
            return artifacts_module._data_file("manifest.json")
        return nonexistent

    monkeypatch.setattr(artifacts_module, "_data_file", pointer)
    with pytest.raises(CorruptArtifactError, match="missing"):
        gfa.snapshot_verify()


def test_corrupt_artifact_fails_closed(monkeypatch, tmp_path) -> None:
    corrupt = tmp_path / "classes.json"
    corrupt.write_text("{not json", encoding="utf-8")

    def pointer(name: str):
        if name == "classes.json":
            return corrupt
        return artifacts_module._data_file(name)

    monkeypatch.setattr(artifacts_module, "_data_file", pointer)
    with pytest.raises(CorruptArtifactError, match="not valid JSON"):
        gfa.class_info("starlike")


# ── class catalog ─────────────────────────────────────────────────────────────


def test_list_classes_returns_the_thirty_nine_class_catalog() -> None:
    records = gfa.list_classes()

    assert len(records) == 39
    keys = [record["key"] for record in records]
    assert keys == sorted(keys)
    starlike = next(record for record in records if record["key"] == "starlike")
    assert starlike["phi_coeffs"] == ["2", "2", "2", "2", "2"]
    bell = next(record for record in records if record["key"] == "bell")
    assert bell["phi_coeffs"] == ["1", "1", "5/6", "5/8", "13/30"]


def test_class_info_round_trips_exact_phi_coefficients() -> None:
    record = gfa.class_info("lemniscate")

    assert record["name"] == "Lemniscate S*_L"
    assert record["phi_formula"] == "sqrt(1+z)"
    for text in record["phi_coeffs"]:
        gfa.parse_exact_expression(text)


def test_unknown_class_fails_closed() -> None:
    with pytest.raises(UnsupportedError, match="unknown class"):
        gfa.class_info("no_such_class")
    with pytest.raises(UnsupportedError, match="available classes"):
        gfa.expansion("no_such_class")


# ── expansions ────────────────────────────────────────────────────────────────


def test_expansion_lookup_returns_published_formulas() -> None:
    record = gfa.expansion("starlike")

    assert record["class_key"] == "starlike"
    assert record["phi_latex"] == r"\frac{1+z}{1-z}"
    assert record["coeffs"][0]["n"] == 2
    assert "gamma" in record["coeffs"][0]["latex"]


# ── coefficient bounds ────────────────────────────────────────────────────────


def test_coefficient_bound_preserves_sharp_vs_enclosure() -> None:
    sharp = gfa.coefficient_bound("bean_tanh", "fekete_szego_mu1")
    enclosure = gfa.coefficient_bound("bean_tanh", "hankel2_2")

    assert sharp["sharp"] is True
    assert sharp["value_exact"] == "1/4"
    assert enclosure["sharp"] is False
    assert enclosure["value_exact"] is None
    assert enclosure["bound"] == "1/16"


def test_coefficient_bound_catalog_lists_every_functional() -> None:
    record = gfa.coefficient_bound("bean_tanh")

    assert record["class_key"] == "bean_tanh"
    assert record["count"] == len(record["entries"])
    assert "fekete_szego_mu0" in record["entries"]
    assert record["entries"]["hankel2_2"]["sharp"] is False


def test_coefficient_bound_unknown_functional_fails_closed() -> None:
    with pytest.raises(UnsupportedError, match="no bound for functional"):
        gfa.coefficient_bound("starlike", "hankel3_1")


# ── proofs gallery and detail ─────────────────────────────────────────────────


def test_proof_gallery_reports_corpus_size() -> None:
    record = gfa.list_proofs()

    assert record["count"] == 306
    assert len(record["rows"]) == 306
    assert all(row["status"] == "PROVED" for row in record["rows"])


def test_proof_gallery_filters_are_exact() -> None:
    by_class = gfa.list_proofs(class_key="bean_tanh")
    by_functional = gfa.list_proofs(functional_key="hankel2_2")

    assert all(row["class_key"] == "bean_tanh" for row in by_class["rows"])
    assert all(
        row["functional_key"] == "hankel2_2" for row in by_functional["rows"]
    )
    assert by_functional["count"] == 11
    assert by_class["count"] < 306


def test_proof_gallery_empty_match_set_is_a_valid_result() -> None:
    record = gfa.list_proofs(search="no_such_certificate_exists")

    assert record["count"] == 0
    assert record["rows"] == []


def test_proof_gallery_unknown_filter_fails_closed() -> None:
    with pytest.raises(UnsupportedError, match="unknown class"):
        gfa.list_proofs(class_key="nope")
    with pytest.raises(UnsupportedError, match="unknown functional"):
        gfa.list_proofs(functional_key="hankel3_1")
    with pytest.raises(UnsupportedError, match="unknown proof status"):
        gfa.list_proofs(status="WISHED")


def test_proof_detail_reports_certificate_semantics() -> None:
    record = gfa.get_proof("bean_tanh__hankel2_2")

    assert record["status"] == "PROVED"
    # The candidate is an exact constant, but sharpness is not proven: the
    # record stays a certified upper enclosure and the two flags stay distinct.
    assert record["sharp"]["proven"] is not True
    assert record["sharp"]["exact"] is True
    assert record["sharp"]["candidate_exact"] == "1/16"
    assert record["n_leaves_parts"] == 5
    assert "certificate" not in record


def test_proof_raw_retains_the_full_record() -> None:
    record = gfa.get_proof("starlike__fekete_szego_mu1", raw=True)

    assert record["certificate"]["class"] == "starlike"
    assert record["certificate"]["functional"] == "fekete_szego_mu1"
    assert record["certificate"]["status"] == "PROVED"
    assert "leaves_parts" not in record["certificate"]


def test_unknown_proof_fails_closed() -> None:
    with pytest.raises(UnsupportedError, match="unknown proof"):
        gfa.get_proof("no_such_proof")


# ── open problems ─────────────────────────────────────────────────────────────


def test_open_problems_preserve_two_categories() -> None:
    record = gfa.open_problems()

    assert record["counts"] == {"enclosures": 12, "numerical": 97}
    assert len(record["enclosures"]) == 12
    assert len(record["conjectures"]) == 97


def test_open_problems_kind_filters() -> None:
    enclosures = gfa.open_problems(kind="enclosure")
    numerical = gfa.open_problems(kind="numerical")

    assert "conjectures" not in enclosures
    assert "enclosures" not in numerical
    assert len(enclosures["enclosures"]) == 12
    assert len(numerical["conjectures"]) == 97


def test_open_problems_never_merge_categories() -> None:
    record = gfa.open_problems()

    enclosure_pairs = {
        (row["class_key"], row["functional_key"]) for row in record["enclosures"]
    }
    conjecture_pairs = {
        (row["class_key"], row["functional_key"]) for row in record["conjectures"]
    }
    assert enclosure_pairs.isdisjoint(conjecture_pairs)
    for row in record["enclosures"]:
        assert row["candidate_exact"] is not None


def test_open_problems_invalid_kind_fails_closed() -> None:
    with pytest.raises(InvalidInputError):
        gfa.open_problems(kind="solved")


# ── reconciliation rows ───────────────────────────────────────────────────────


def test_reconciliation_reports_counts_and_rows() -> None:
    record = gfa.reconciliation()

    assert record["counts"] == {"A": 216, "B": 14, "C": 8, "D": 12}
    assert record["total"] == 227
    assert len(record["rows"]) == 227


def test_reconciliation_filters_rows() -> None:
    record = gfa.reconciliation(category="D")

    assert record["total"] == 227
    assert len(record["rows"]) == 12
    # Rows may carry compound buckets such as "B+D"; the letter filter matches
    # every row whose bucket includes the requested letter.
    for row in record["rows"]:
        assert "D" in row["category"].replace("*", "").split("+")


def test_reconciliation_invalid_category_fails_closed() -> None:
    with pytest.raises(InvalidInputError, match="unknown reconciliation category"):
        gfa.reconciliation(category="X")


# ── references document ───────────────────────────────────────────────────────


def test_references_document_is_versioned_and_substantial() -> None:
    record = gfa.references()

    assert record["document"].startswith("# References for the machine-certification method")
    assert len(record["document"]) > 1000
    assert "Versioned companion" in record["document"]


# ── certificate replay ────────────────────────────────────────────────────────


def test_certificate_replay_passes_for_sharp_certificate() -> None:
    record = gfa.verify_certificate("starlike__fekete_szego_mu1")

    assert record["matched"] is True
    assert record["functional_value_exact"] == "1"
    assert record["candidate_exact"] == "1"
    assert record["sharp"] is True


def test_certificate_replay_passes_for_float_gamma_enclosure() -> None:
    # bean_tanh__hankel2_2 stores extremal gammas as 0.0/1.0 floats.
    record = gfa.verify_certificate("bean_tanh__hankel2_2")

    assert record["matched"] is True
    assert record["functional_value_exact"] == "1/16"
    assert record["candidate_exact"] == "1/16"
    assert record["sharp"] is False


def test_certificate_replay_covers_the_entire_corpus() -> None:
    certificates = artifacts_module._load_json(
        "certificates.json"
    )["certificates"]

    for name in sorted(certificates):
        record = gfa.verify_certificate(name)
        assert record["matched"] is True, name


def test_certificate_replay_unknown_name_fails_closed() -> None:
    with pytest.raises(UnsupportedError, match="unknown certificate"):
        gfa.verify_certificate("no_such_certificate")


def test_certificate_replay_unsupported_functional_fails_closed(
    monkeypatch,
) -> None:
    def synthetic_certificates() -> dict:
        return {
            "fake__hankel3_1": {
                "class": "starlike",
                "functional": "hankel3_1",
                "status": "PROVED",
                "bound": "1",
                "bound_float": 1.0,
                "slack": 0.0,
                "sharp": {
                    "proven": False,
                    "exact": True,
                    "candidate": {"value_exact": "1", "value_float": 1.0},
                    "extremal_gammas": ["0", "1"],
                },
            }
        }

    monkeypatch.setattr(artifacts_module, "_certificates", synthetic_certificates)
    with pytest.raises(UnsupportedError, match="unsupported functional"):
        gfa.verify_certificate("fake__hankel3_1")


def test_certificate_replay_rejects_inconsistent_candidate(
    monkeypatch,
) -> None:
    def inconsistent_certificates() -> dict:
        return {
            "fake__fekete_szego_mu0": {
                "class": "starlike",
                "functional": "fekete_szego_mu0",
                "status": "PROVED",
                "bound": "1",
                "bound_float": 1.0,
                "slack": 0.0,
                "sharp": {
                    "proven": True,
                    "exact": True,
                    "candidate": {"value_exact": "99/100", "value_float": 0.99},
                    "extremal_gammas": ["0", "1"],
                },
            }
        }

    monkeypatch.setattr(artifacts_module, "_certificates", inconsistent_certificates)
    with pytest.raises(CorruptArtifactError, match="failed replay"):
        gfa.verify_certificate("fake__fekete_szego_mu0")


# ── snapshot result envelope ──────────────────────────────────────────────────


def _sample_payload() -> dict:
    return gfa.snapshot_payload(
        result_type="expansion",
        canonical_inputs={"class_key": "starlike"},
        record=gfa.expansion("starlike"),
        evidence_status="screened",
        assumptions=("transcribed from the versioned website snapshot",),
        source_references=("Geometric Function Atlas website snapshot",),
        verification=gfa.VerificationReport(
            (
                gfa.VerificationCheck(
                    name="artifact_checksum",
                    checked="shipped data checksums",
                    expected="match",
                    observed="verified",
                    status=gfa.CheckStatus.PASS,
                    scope="snapshot integrity",
                ),
            )
        ),
        record_count=4,
    )


def test_snapshot_payload_is_closed_and_versioned() -> None:
    payload = _sample_payload()

    assert payload["schema_version"] == 1
    assert payload["result_type"] == "expansion"
    assert payload["novelty_claim"] is False
    assert payload["failure_state"] is None
    assert payload["evidence_status"] == "screened"
    assert payload["verification"]["success"] is True
    assert payload["artifact_versions"]["snapshot_date"] == "2026-08-11"
    gfa.validate_snapshot_payload(payload)


def test_snapshot_payload_rejects_unknown_keys() -> None:
    payload = _sample_payload()
    payload["forged"] = True

    with pytest.raises(ValueError, match="unexpected keys"):
        gfa.validate_snapshot_payload(payload)


def test_snapshot_payload_rejects_unknown_result_type() -> None:
    payload = _sample_payload()
    payload["result_type"] = "forged_operation"

    with pytest.raises(ValueError, match="unsupported snapshot result_type"):
        gfa.validate_snapshot_payload(payload)


def test_snapshot_payload_rejects_affirmative_novelty_claim() -> None:
    payload = _sample_payload()
    payload["novelty_claim"] = True

    with pytest.raises(ValueError, match="novelty_claim"):
        gfa.validate_snapshot_payload(payload)


def test_all_cli_snapshot_payloads_validate_against_the_shipped_schema() -> None:
    validator = Draft202012Validator(gfa.load_result_schema())
    commands = (
        ("expansion", "starlike"),
        ("coefficient-bound", "starlike"),
        ("proofs",),
        ("proof", "starlike__fekete_szego_mu1"),
        ("open-problems",),
        ("reconciliation",),
        ("references",),
        ("verify-certificate", "starlike__fekete_szego_mu1"),
        ("artifact-snapshot", "verify"),
    )
    for command in commands:
        payload = _payload_for(command)
        validator.validate(payload)


def _payload_for(command: tuple[str, ...]) -> dict:
    import contextlib
    import io

    from geometric_function_atlas.cli import main

    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        exit_code = main([*command, "--json"])
    assert exit_code == 0, (command, stdout.getvalue())
    return json.loads(stdout.getvalue())
