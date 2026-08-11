from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from geometric_function_atlas import (
    RegistrySnapshot,
    SnapshotIntegrityError,
    SnapshotManifest,
    SnapshotManifestError,
    SnapshotResourceLimitError,
    install_snapshot,
    verify_snapshot,
)

SCHEMA = """
CREATE TABLE function_families (
    id INTEGER PRIMARY KEY, canonical_key TEXT UNIQUE, name TEXT UNIQUE,
    display_name TEXT, closed_form TEXT, generating_def TEXT,
    is_parametric INTEGER DEFAULT 0, param_spec_json TEXT, arity INTEGER DEFAULT 0,
    family_group TEXT, is_polynomial INTEGER DEFAULT 0, is_entire INTEGER DEFAULT 0,
    coeff_formula TEXT, coeff_decay TEXT, notes TEXT, legacy_function_id INTEGER,
    created_at TEXT, updated_at TEXT, application_areas_json TEXT
);
CREATE TABLE function_instances (
    id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL, param_values_json TEXT,
    coefficients_json TEXT, num_terms INTEGER, coeff_source TEXT,
    coeff_fingerprint TEXT, created_at TEXT
);
CREATE TABLE gft_properties (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE, symbol TEXT, defining_condition TEXT,
    key_quantity TEXT, is_parameterized INTEGER, parameter_name TEXT,
    parameter_range TEXT, category TEXT
);
CREATE TABLE facts (
    id INTEGER PRIMARY KEY, family_id INTEGER, instance_id INTEGER,
    param_region_json TEXT, property_id INTEGER NOT NULL, property_param REAL,
    fact_kind TEXT NOT NULL, holds INTEGER, value REAL, value_exact TEXT,
    disk_radius REAL, is_sharp INTEGER, provenance TEXT NOT NULL,
    status TEXT NOT NULL, confidence TEXT, fact_hash TEXT UNIQUE,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE verification_runs (
    id INTEGER PRIMARY KEY, fact_id INTEGER NOT NULL, instance_id INTEGER,
    verifier TEXT NOT NULL, direction TEXT NOT NULL, outcome TEXT NOT NULL,
    margin REAL, domain_radius REAL, witness_json TEXT, tail_bound REAL,
    engine_version TEXT NOT NULL, params_json TEXT, runtime_ms INTEGER, created_at TEXT
);
CREATE TABLE papers (
    id INTEGER PRIMARY KEY, title TEXT, authors TEXT, year INTEGER, journal TEXT,
    filename TEXT, bibtex TEXT, abstract TEXT, created_at TEXT,
    structured_json TEXT, doi TEXT
);
CREATE TABLE paper_claims (
    id INTEGER PRIMARY KEY, paper_id INTEGER, function_name TEXT, claim_type TEXT,
    claim_text TEXT, function_id INTEGER, verified_match INTEGER,
    extraction_source TEXT, statement_human TEXT
);
CREATE TABLE evidence (
    id INTEGER PRIMARY KEY, fact_id INTEGER, relation_id INTEGER, paper_id INTEGER,
    theorem_number TEXT, page_number INTEGER, statement_text TEXT,
    evidence_type TEXT, legacy_claim_id INTEGER
);
CREATE TABLE paper_family_links (
    id INTEGER PRIMARY KEY, paper_id INTEGER NOT NULL, family_id INTEGER NOT NULL,
    match_type TEXT NOT NULL, functional_type TEXT, score REAL, theorem_snippet TEXT
);
CREATE TABLE paper_class_tags (
    id INTEGER PRIMARY KEY, paper_id INTEGER NOT NULL, class_key TEXT NOT NULL,
    family_id INTEGER, evidence TEXT, confidence TEXT, provenance TEXT
);
CREATE TABLE function_aliases (
    id INTEGER PRIMARY KEY, family_id INTEGER NOT NULL, alias TEXT NOT NULL,
    paper_id INTEGER
);
CREATE TABLE property_implications (
    id INTEGER PRIMARY KEY, from_prop_id INTEGER NOT NULL, to_prop_id INTEGER NOT NULL,
    condition TEXT, source TEXT
);
CREATE TABLE functions (
    id INTEGER PRIMARY KEY, name TEXT NOT NULL, display_name TEXT, category TEXT,
    dlmf_ref TEXT, power_series_json TEXT, description TEXT, source_type TEXT,
    source_ref TEXT, created_at TEXT
);
CREATE TABLE properties (
    id INTEGER PRIMARY KEY, function_id INTEGER NOT NULL, is_starlike INTEGER,
    starlike_confidence TEXT, starlike_order REAL, is_convex INTEGER,
    convex_confidence TEXT, is_univalent INTEGER, univalent_confidence TEXT,
    radius_starlikeness REAL, radius_confidence TEXT, c01_sum REAL,
    c01_satisfied INTEGER, c02_sum REAL, c02_satisfied INTEGER,
    coefficient_bounds_hold INTEGER, max_an_ratio REAL, min_re_zf_over_f REAL,
    min_re_convexity REAL, grid_resolution INTEGER, error_estimate REAL,
    params_json TEXT, verified_at TEXT, verification_status TEXT,
    quick_result_json TEXT, rigorous_result_json TEXT, symbolic_result_json TEXT,
    boundary_status TEXT, boundary_disk_radius REAL, boundary_witness_json TEXT,
    boundary_result_json TEXT, boundary_method TEXT, boundary_verified_at TEXT
);
CREATE TABLE tags (id INTEGER PRIMARY KEY, name TEXT NOT NULL, category TEXT);
CREATE TABLE function_tags (function_id INTEGER, tag_id INTEGER);
CREATE TABLE paper_tags (paper_id INTEGER, tag_id INTEGER);
"""


def make_snapshot(tmp_path: Path) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = tmp_path / "atlas.sqlite"
    connection = sqlite3.connect(database)
    connection.executescript(SCHEMA)
    connection.executescript(
        """
        INSERT INTO function_families VALUES
          (1, 'sine', 'sine', 'Sine family', 'z + sin(z)', NULL, 0, NULL, 0,
           'Elementary', 0, 1, NULL, NULL, 'demo family', NULL, NULL, NULL,
           '["image_processing", "signal_processing"]'),
          (2, 'identity', 'identity', 'Identity', 'z', NULL, 0, NULL, 0,
           'Elementary', 1, 1, NULL, 'finite', NULL, NULL, NULL, NULL, NULL);
        INSERT INTO function_instances VALUES
          (1, 1, '{"alpha": 1}', '[1, 0, -0.1666666667]', 3, 'exact_form', 'fp', NULL);
        INSERT INTO gft_properties VALUES
          (1, 'starlike', 'S*', 'Re(zf''/f)>0', 'zf''/f', 0, NULL, NULL, 'geometric'),
          (2, 'convex', 'K', 'Re(1+zf''''/f'')>0', '1+zf''''/f''', 0, NULL, NULL, 'geometric');
        INSERT INTO facts VALUES
          (1, 1, 1, NULL, 1, NULL, 'membership', 0, 0.5, NULL, 0.95, NULL,
           'computational_screen', 'disproven', 'numerical_strong', 'fact-1', NULL, NULL);
        INSERT INTO verification_runs VALUES
          (1, 1, 1, 'boundary_scan', 'screens', 'pass', 0.2, 0.95, '{"theta": 1}', NULL,
           'test-1', '{}', 2, NULL);
        INSERT INTO papers VALUES
          (1, 'Sine families in image processing', 'A. Author', 2024, 'Journal',
           'paper.pdf', '@article{sine}', 'A short paper.', NULL, '{"theorems": []}', '10/demo');
        INSERT INTO paper_claims VALUES
          (1, 1, 'sine', 'starlike', '{"bound": "1/2"}', NULL, 1, 'fixture',
           'The sine family is starlike in the declared range.');
        INSERT INTO evidence VALUES
          (1, 1, NULL, 1, 'Theorem 1', 4, 'The cited statement.', 'citation', 1);
        INSERT INTO paper_family_links VALUES
          (1, 1, 1, 'specific_term', 'starlike', 1.0, 'Theorem 1');
        INSERT INTO paper_class_tags VALUES
          (1, 1, 'sine', 1, 'exact class name', 'high', 'fixture');
        INSERT INTO function_aliases VALUES (1, 1, 'Sine class', NULL);
        INSERT INTO property_implications VALUES (1, 2, 1, NULL, 'fixture theorem');
        """
    )
    connection.commit()
    connection.close()
    digest = hashlib.sha256(database.read_bytes()).hexdigest()
    row_counts: dict[str, int] = {}
    connection = sqlite3.connect(database)
    for (table,) in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ):
        row_counts[table] = connection.execute(f' SELECT count(*) FROM "{table}"').fetchone()[0]
    connection.close()
    manifest = tmp_path / "atlas.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "manifest_schema_version": 1,
                "dataset_version": "fixture-2026.08.11",
                "database": {
                    "filename": database.name,
                    "bytes": database.stat().st_size,
                    "sha256": digest,
                    "application_tables": sorted(row_counts),
                    "row_counts": row_counts,
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return database, manifest


def test_snapshot_verification_is_fail_closed_and_reports_population(tmp_path: Path) -> None:
    database, manifest = make_snapshot(tmp_path)

    report = verify_snapshot(database, manifest=manifest)

    assert report.success is True
    payload = report.to_dict()
    assert payload["dataset_version"] == "fixture-2026.08.11"
    assert payload["database"]["row_counts"]["function_families"] == 2
    assert payload["checks"]["sha256"] == "pass"
    assert payload["checks"]["integrity_check"] == "pass"

    database.write_bytes(database.read_bytes() + b"mutation")
    with pytest.raises(SnapshotIntegrityError):
        verify_snapshot(database, manifest=manifest, raise_on_error=True)


def test_snapshot_install_copies_verified_database_without_write_access(tmp_path: Path) -> None:
    source, manifest = make_snapshot(tmp_path / "source")
    destination = tmp_path / "installed" / "registry.sqlite"

    installed = install_snapshot(source, destination, manifest=manifest)

    assert installed == destination
    with RegistrySnapshot.open(destination, manifest=manifest) as snapshot:
        with pytest.raises(sqlite3.OperationalError):
            snapshot.connection.execute("DELETE FROM function_families")
        assert snapshot.stats().families == 2


def test_typed_snapshot_queries_cover_the_website_registry_surface(tmp_path: Path) -> None:
    database, manifest = make_snapshot(tmp_path)

    with RegistrySnapshot.open(database, manifest=manifest) as snapshot:
        assert snapshot.search("Sine")[0].kind == "family"
        assert snapshot.families()[0].canonical_key == "identity"
        detail = snapshot.family("sine")
        assert detail.instances[0].coefficients == [1, 0, -0.1666666667]
        assert snapshot.facts("sine")[0].status == "disproven"
        assert snapshot.evidence("sine")[0].evidence_type == "citation"
        assert snapshot.runs("sine")[0].direction == "screens"
        assert snapshot.papers(query="image processing")[0].id == 1
        assert snapshot.paper(1).claims[0].claim_type == "starlike"
        assert snapshot.applications("image_processing")[0].family_key == "sine"
        assert snapshot.counterexamples("sine")[0].property_name == "starlike"
        assert snapshot.normalize_class("Sine class") == "sine"
        assert snapshot.hierarchy("convex")[0].to_property == "starlike"


def test_cli_snapshot_and_queries_use_the_same_read_only_backend(tmp_path: Path) -> None:
    database, manifest = make_snapshot(tmp_path)

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "geometric_function_atlas", *args],
            check=False,
            capture_output=True,
            text=True,
        )

    info = run("snapshot", "info", str(database), "--manifest", str(manifest), "--json")
    stats = run("stats", "--snapshot", str(database), "--manifest", str(manifest), "--json")
    search = run("search", "Sine", "--snapshot", str(database), "--manifest", str(manifest), "--json")

    assert info.returncode == 0, info.stderr
    assert json.loads(info.stdout)["dataset_version"] == "fixture-2026.08.11"
    assert stats.returncode == 0, stats.stderr
    assert json.loads(stats.stdout)["families"] == 2
    assert search.returncode == 0, search.stderr
    assert json.loads(search.stdout)[0]["canonical_key"] == "sine"


def test_manifest_rejects_unsupported_schema_and_missing_population_fields() -> None:
    with pytest.raises(SnapshotManifestError):
        SnapshotManifest.from_dict({"manifest_schema_version": 999})


def test_verify_rejects_a_database_mutation_even_when_hash_is_recomputed(tmp_path: Path) -> None:
    database, manifest = make_snapshot(tmp_path)
    connection = sqlite3.connect(database)
    connection.execute("DROP TABLE papers")
    connection.commit()
    connection.close()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["database"]["bytes"] = database.stat().st_size
    payload["database"]["sha256"] = hashlib.sha256(database.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    report = verify_snapshot(database, manifest=manifest)

    assert report.success is False
    assert report.checks["required_tables"] == "fail"
    assert any("papers" in error for error in report.errors)


@pytest.mark.skipif(shutil.which("zstd") is None, reason="zstd executable is not installed")
def test_install_supports_zstd_with_a_decompressed_resource_limit(tmp_path: Path) -> None:
    database, manifest = make_snapshot(tmp_path)
    compressed = tmp_path / "atlas.sqlite.zst"
    subprocess.run(["zstd", "-q", "-f", str(database), "-o", str(compressed)], check=True)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["compressed_asset"] = {
        "filename": compressed.name,
        "bytes": compressed.stat().st_size,
        "sha256": hashlib.sha256(compressed.read_bytes()).hexdigest(),
    }
    manifest.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(SnapshotResourceLimitError):
        install_snapshot(
            compressed,
            tmp_path / "too-small.sqlite",
            manifest=manifest,
            max_decompressed_bytes=database.stat().st_size - 1,
        )
    destination = install_snapshot(compressed, tmp_path / "installed.sqlite", manifest=manifest)
    assert destination.is_file()
