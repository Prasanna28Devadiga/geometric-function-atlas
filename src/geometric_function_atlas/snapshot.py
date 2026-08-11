"""Immutable registry snapshots and typed, local-only queries.

The website database is a separately versioned data artifact.  This module never
ships a database in the wheel and never opens a snapshot for writing.  A caller
must provide a manifest when installing or verifying an artifact; ordinary query
operations can open an already trusted local SQLite file without network access.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import urllib.parse
import urllib.request
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
from shutil import which
from types import MappingProxyType, TracebackType
from typing import Any, Self, cast

from .contracts import CorruptArtifactError, ResourceLimitError, UnsupportedError

MANIFEST_SCHEMA_VERSION = 1
DEFAULT_MAX_COMPRESSED_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_DECOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
_SHA256_LENGTH = 64


class SnapshotError(CorruptArtifactError):
    """Base class for invalid, unverifiable, or unusable snapshots."""


class SnapshotIntegrityError(SnapshotError):
    """Raised when a snapshot or manifest fails a required integrity check."""


class SnapshotManifestError(SnapshotIntegrityError):
    """Raised when a manifest is malformed or missing a required field."""


class SnapshotResourceLimitError(ResourceLimitError):
    """Raised before a download or decompression can exceed its byte bound."""


@dataclass(frozen=True, slots=True)
class SnapshotManifest:
    """The minimum identity and population contract for a registry snapshot."""

    dataset_version: str
    database_filename: str
    database_bytes: int
    database_sha256: str
    application_tables: tuple[str, ...]
    row_counts: Mapping[str, int]
    manifest_schema_version: int = MANIFEST_SCHEMA_VERSION
    compressed_filename: str | None = None
    compressed_bytes: int | None = None
    compressed_sha256: str | None = None
    package_commit: str | None = None

    def __post_init__(self) -> None:
        if self.manifest_schema_version != MANIFEST_SCHEMA_VERSION:
            raise SnapshotManifestError(
                f"manifest schema version {self.manifest_schema_version} is unsupported"
            )
        if not self.dataset_version or not isinstance(self.dataset_version, str):
            raise SnapshotManifestError("manifest dataset_version is required")
        if not isinstance(self.database_filename, str) or not self.database_filename or Path(self.database_filename).name != self.database_filename:
            raise SnapshotManifestError("database filename must be a basename")
        _validate_size(self.database_bytes, "database.bytes")
        _validate_hash(self.database_sha256, "database.sha256")
        if not self.application_tables:
            raise SnapshotManifestError("database.application_tables must not be empty")
        if any(not isinstance(table, str) or not table for table in self.application_tables):
            raise SnapshotManifestError("database.application_tables must contain strings")
        if len(set(self.application_tables)) != len(self.application_tables):
            raise SnapshotManifestError("database.application_tables must be unique")
        if set(self.row_counts) != set(self.application_tables):
            missing = sorted(set(self.application_tables) - set(self.row_counts))
            extra = sorted(set(self.row_counts) - set(self.application_tables))
            raise SnapshotManifestError(
                f"database.row_counts must match application_tables (missing={missing}, extra={extra})"
            )
        for table, count in self.row_counts.items():
            if not isinstance(table, str) or not table:
                raise SnapshotManifestError("row-count table names must be non-empty strings")
            if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                raise SnapshotManifestError(f"row count for {table!r} must be a non-negative integer")
        if self.compressed_filename is not None:
            if not isinstance(self.compressed_filename, str) or Path(self.compressed_filename).name != self.compressed_filename:
                raise SnapshotManifestError("compressed filename must be a basename")
            if self.compressed_bytes is None or self.compressed_sha256 is None:
                raise SnapshotManifestError("compressed bytes and sha256 must be paired")
            _validate_size(self.compressed_bytes, "compressed.bytes")
            _validate_hash(self.compressed_sha256, "compressed.sha256")
        elif self.compressed_bytes is not None or self.compressed_sha256 is not None:
            raise SnapshotManifestError("compressed metadata is incomplete")
        object.__setattr__(self, "application_tables", tuple(sorted(self.application_tables)))
        object.__setattr__(self, "row_counts", MappingProxyType(dict(sorted(self.row_counts.items()))))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> Self:
        if not isinstance(payload, Mapping):
            raise SnapshotManifestError("manifest must be a JSON object")
        # The audited release nests the useful fields under `snapshot`; accepting
        # that shape keeps the validator useful for the real historical asset.
        root: Mapping[str, Any] = payload.get("snapshot", payload)
        version = root.get("manifest_schema_version", payload.get("manifest_schema_version"))
        if version != MANIFEST_SCHEMA_VERSION:
            raise SnapshotManifestError(f"manifest schema version {version!r} is unsupported")
        database = root.get("database")
        if not isinstance(database, Mapping):
            raise SnapshotManifestError("manifest.database is required")
        dataset_version = root.get("dataset_version", payload.get("dataset_version"))
        tables = database.get("application_tables")
        row_counts = database.get("row_counts")
        if not isinstance(tables, list) or not isinstance(row_counts, Mapping):
            raise SnapshotManifestError("manifest database populations are required")
        compressed = root.get("compressed_asset")
        if compressed is not None and not isinstance(compressed, Mapping):
            raise SnapshotManifestError("manifest.compressed_asset must be an object")
        package = payload.get("package_association")
        package_commit = None
        if isinstance(package, Mapping):
            package_commit = package.get("manifest_package_commit")
        package_root = root.get("package")
        if package_commit is None and isinstance(package_root, Mapping):
            package_commit = package_root.get("commit")
        return cls(
            dataset_version=dataset_version,
            database_filename=cast(str, database.get("filename")),
            database_bytes=cast(int, database.get("bytes")),
            database_sha256=cast(str, database.get("sha256")),
            application_tables=tuple(tables),
            row_counts=dict(row_counts),
            manifest_schema_version=version,
            compressed_filename=(compressed or {}).get("filename"),
            compressed_bytes=(compressed or {}).get("bytes"),
            compressed_sha256=(compressed or {}).get("sha256"),
            package_commit=package_commit,
        )

    @classmethod
    def load(cls, path: str | os.PathLike[str]) -> Self:
        manifest_path = Path(path)
        try:
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise SnapshotManifestError(f"manifest not found: {manifest_path}") from exc
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SnapshotManifestError(f"cannot read manifest {manifest_path}: {exc}") from exc
        return cls.from_dict(payload)

    def to_dict(self) -> dict[str, Any]:
        database: dict[str, Any] = {
            "filename": self.database_filename,
            "bytes": self.database_bytes,
            "sha256": self.database_sha256,
            "application_tables": list(self.application_tables),
            "row_counts": dict(self.row_counts),
        }
        result: dict[str, Any] = {
            "manifest_schema_version": self.manifest_schema_version,
            "dataset_version": self.dataset_version,
            "database": database,
        }
        if self.compressed_filename is not None:
            result["compressed_asset"] = {
                "filename": self.compressed_filename,
                "bytes": self.compressed_bytes,
                "sha256": self.compressed_sha256,
            }
        if self.package_commit is not None:
            result["package"] = {"commit": self.package_commit}
        return result


@dataclass(frozen=True, slots=True)
class SnapshotVerification:
    """Machine-readable result of all required snapshot checks."""

    path: str
    dataset_version: str
    checks: Mapping[str, str]
    errors: tuple[str, ...]
    database: Mapping[str, Any]

    @property
    def success(self) -> bool:
        return not self.errors and all(value == "pass" for value in self.checks.values())

    @property
    def status(self) -> str:
        return "passed" if self.success else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "success": self.success,
            "path": self.path,
            "dataset_version": self.dataset_version,
            "checks": dict(self.checks),
            "errors": list(self.errors),
            "database": dict(self.database),
        }


@dataclass(frozen=True, slots=True)
class SnapshotInfo:
    """SQLite metadata and populations exposed by ``snapshot info``."""

    path: str
    dataset_version: str | None
    sha256: str
    bytes: int
    sqlite_version: str
    user_version: int
    page_size: int
    page_count: int
    freelist_count: int
    quick_check: str
    integrity_check: str
    application_tables: tuple[str, ...]
    row_counts: Mapping[str, int]
    verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "dataset_version": self.dataset_version,
            "sha256": self.sha256,
            "bytes": self.bytes,
            "sqlite_version": self.sqlite_version,
            "user_version": self.user_version,
            "page_size": self.page_size,
            "page_count": self.page_count,
            "freelist_count": self.freelist_count,
            "quick_check": self.quick_check,
            "integrity_check": self.integrity_check,
            "application_tables": list(self.application_tables),
            "row_counts": dict(self.row_counts),
            "verified": self.verified,
        }


@dataclass(frozen=True, slots=True)
class SnapshotStats:
    dataset_version: str | None
    families: int
    instances: int
    facts: int
    proven_facts: int
    disproven_facts: int
    verification_runs: int
    evidence: int
    papers: int
    paper_claims: int
    row_counts: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_version": self.dataset_version,
            "families": self.families,
            "function_families": self.families,
            "instances": self.instances,
            "function_instances": self.instances,
            "facts": self.facts,
            "proven_facts": self.proven_facts,
            "disproven_facts": self.disproven_facts,
            "verification_runs": self.verification_runs,
            "evidence": self.evidence,
            "papers": self.papers,
            "paper_claims": self.paper_claims,
            "row_counts": dict(self.row_counts),
        }

    @property
    def function_families(self) -> int:
        return self.families


@dataclass(frozen=True, slots=True)
class FunctionFamily:
    id: int
    canonical_key: str
    name: str
    display_name: str | None
    closed_form: str | None
    generating_def: str | None
    is_parametric: bool
    param_spec: Any
    arity: int
    family_group: str | None
    is_polynomial: bool
    is_entire: bool
    coeff_formula: str | None
    coeff_decay: str | None
    notes: str | None
    application_areas: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "canonical_key": self.canonical_key,
            "name": self.name,
            "display_name": self.display_name,
            "closed_form": self.closed_form,
            "generating_def": self.generating_def,
            "is_parametric": self.is_parametric,
            "param_spec": self.param_spec,
            "arity": self.arity,
            "family_group": self.family_group,
            "is_polynomial": self.is_polynomial,
            "is_entire": self.is_entire,
            "coeff_formula": self.coeff_formula,
            "coeff_decay": self.coeff_decay,
            "notes": self.notes,
            "application_areas": list(self.application_areas),
        }


@dataclass(frozen=True, slots=True)
class FunctionInstance:
    id: int
    family_id: int
    param_values: Any
    coefficients: Any
    num_terms: int | None
    coeff_source: str | None
    coeff_fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family_id": self.family_id,
            "param_values": self.param_values,
            "coefficients": self.coefficients,
            "num_terms": self.num_terms,
            "coeff_source": self.coeff_source,
            "coeff_fingerprint": self.coeff_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class Fact:
    id: int
    family_id: int | None
    instance_id: int | None
    property_id: int
    property_name: str | None
    property_param: float | None
    fact_kind: str
    holds: bool | None
    value: float | None
    value_exact: str | None
    disk_radius: float | None
    is_sharp: bool | None
    provenance: str
    status: str
    confidence: str | None
    fact_hash: str | None
    family_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "family_id": self.family_id,
            "instance_id": self.instance_id,
            "property_id": self.property_id,
            "property_name": self.property_name,
            "property_param": self.property_param,
            "fact_kind": self.fact_kind,
            "holds": self.holds,
            "value": self.value,
            "value_exact": self.value_exact,
            "disk_radius": self.disk_radius,
            "is_sharp": self.is_sharp,
            "provenance": self.provenance,
            "status": self.status,
            "confidence": self.confidence,
            "fact_hash": self.fact_hash,
            "family_key": self.family_key,
        }


@dataclass(frozen=True, slots=True)
class Evidence:
    id: int
    fact_id: int | None
    relation_id: int | None
    paper_id: int | None
    theorem_number: str | None
    page_number: int | None
    statement_text: str | None
    evidence_type: str | None
    legacy_claim_id: int | None
    family_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fact_id": self.fact_id,
            "relation_id": self.relation_id,
            "paper_id": self.paper_id,
            "theorem_number": self.theorem_number,
            "page_number": self.page_number,
            "statement_text": self.statement_text,
            "evidence_type": self.evidence_type,
            "legacy_claim_id": self.legacy_claim_id,
            "family_key": self.family_key,
        }


@dataclass(frozen=True, slots=True)
class VerificationRun:
    id: int
    fact_id: int
    instance_id: int | None
    verifier: str
    direction: str
    outcome: str
    margin: float | None
    domain_radius: float | None
    witness: Any
    tail_bound: float | None
    engine_version: str
    params: Any
    runtime_ms: int | None
    family_key: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "fact_id": self.fact_id,
            "instance_id": self.instance_id,
            "verifier": self.verifier,
            "direction": self.direction,
            "outcome": self.outcome,
            "margin": self.margin,
            "domain_radius": self.domain_radius,
            "witness": self.witness,
            "tail_bound": self.tail_bound,
            "engine_version": self.engine_version,
            "params": self.params,
            "runtime_ms": self.runtime_ms,
            "family_key": self.family_key,
        }


@dataclass(frozen=True, slots=True)
class PaperClaim:
    id: int
    paper_id: int | None
    function_name: str | None
    claim_type: str | None
    claim_text: str | None
    verified_match: bool | None
    extraction_source: str | None
    statement_human: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "paper_id": self.paper_id,
            "function_name": self.function_name,
            "claim_type": self.claim_type,
            "claim_text": self.claim_text,
            "verified_match": self.verified_match,
            "extraction_source": self.extraction_source,
            "statement_human": self.statement_human,
        }


@dataclass(frozen=True, slots=True)
class Paper:
    id: int
    title: str | None
    authors: str | None
    year: int | None
    journal: str | None
    filename: str | None
    bibtex: str | None
    abstract: str | None
    structured: Any
    doi: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "journal": self.journal,
            "filename": self.filename,
            "bibtex": self.bibtex,
            "abstract": self.abstract,
            "structured": self.structured,
            "doi": self.doi,
        }


@dataclass(frozen=True, slots=True)
class PaperDetail:
    paper: Paper
    claims: tuple[PaperClaim, ...]
    class_tags: tuple[Mapping[str, Any], ...]
    family_links: tuple[Mapping[str, Any], ...]
    evidence: tuple[Evidence, ...]

    @property
    def id(self) -> int:
        return self.paper.id

    @property
    def title(self) -> str | None:
        return self.paper.title

    def to_dict(self) -> dict[str, Any]:
        result = self.paper.to_dict()
        result.update(
            {
                "claims": [claim.to_dict() for claim in self.claims],
                "class_tags": [dict(tag) for tag in self.class_tags],
                "family_links": [dict(link) for link in self.family_links],
                "evidence": [item.to_dict() for item in self.evidence],
            }
        )
        return result


@dataclass(frozen=True, slots=True)
class FamilyDetail:
    family: FunctionFamily
    instances: tuple[FunctionInstance, ...]
    facts: tuple[Fact, ...]
    evidence: tuple[Evidence, ...]
    runs: tuple[VerificationRun, ...]
    papers: tuple[Paper, ...]
    aliases: tuple[str, ...]

    @property
    def id(self) -> int:
        return self.family.id

    @property
    def canonical_key(self) -> str:
        return self.family.canonical_key

    @property
    def name(self) -> str:
        return self.family.name

    def to_dict(self) -> dict[str, Any]:
        result = self.family.to_dict()
        result.update(
            {
                "instances": [item.to_dict() for item in self.instances],
                "facts": [item.to_dict() for item in self.facts],
                "evidence": [item.to_dict() for item in self.evidence],
                "runs": [item.to_dict() for item in self.runs],
                "papers": [item.to_dict() for item in self.papers],
                "aliases": list(self.aliases),
            }
        )
        return result


@dataclass(frozen=True, slots=True)
class SearchResult:
    kind: str
    id: int
    canonical_key: str | None = None
    name: str | None = None
    display_name: str | None = None
    title: str | None = None
    year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "id": self.id,
            "canonical_key": self.canonical_key,
            "name": self.name,
            "display_name": self.display_name,
            "title": self.title,
            "year": self.year,
        }


@dataclass(frozen=True, slots=True)
class Application:
    area: str
    family_id: int
    family_key: str
    family_name: str
    source: str
    paper_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "area": self.area,
            "family_id": self.family_id,
            "family_key": self.family_key,
            "family_name": self.family_name,
            "source": self.source,
            "paper_count": self.paper_count,
        }


@dataclass(frozen=True, slots=True)
class Counterexample:
    fact: Fact
    property_name: str | None
    runs: tuple[VerificationRun, ...]

    @property
    def id(self) -> int:
        return self.fact.id

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact": self.fact.to_dict(),
            "property_name": self.property_name,
            "runs": [run.to_dict() for run in self.runs],
        }


@dataclass(frozen=True, slots=True)
class PropertyImplication:
    id: int
    from_property: str
    to_property: str
    condition: str | None
    source: str | None

    @property
    def from_property_name(self) -> str:
        return self.from_property

    @property
    def to_property_name(self) -> str:
        return self.to_property

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "from_property": self.from_property,
            "to_property": self.to_property,
            "condition": self.condition,
            "source": self.source,
        }


def _validate_size(value: Any, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise SnapshotManifestError(f"{label} must be a non-negative integer")


def _validate_hash(value: Any, label: str) -> None:
    if not isinstance(value, str) or len(value) != _SHA256_LENGTH:
        raise SnapshotManifestError(f"{label} must be a 64-character SHA-256 hex digest")
    try:
        int(value, 16)
    except ValueError as exc:
        raise SnapshotManifestError(f"{label} must be hexadecimal") from exc


def _sha256(path: Path, *, max_bytes: int = DEFAULT_MAX_COMPRESSED_BYTES) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise SnapshotResourceLimitError(f"artifact exceeds {max_bytes} byte limit")
                digest.update(chunk)
    except FileNotFoundError as exc:
        raise SnapshotIntegrityError(f"artifact not found: {path}") from exc
    return size, digest.hexdigest()


def _manifest_for(path: Path, manifest: SnapshotManifest | Mapping[str, Any] | str | os.PathLike[str] | None) -> SnapshotManifest | None:
    if isinstance(manifest, SnapshotManifest):
        return manifest
    if isinstance(manifest, Mapping):
        return SnapshotManifest.from_dict(manifest)
    if manifest is not None:
        return SnapshotManifest.load(manifest)
    candidates = [
        Path(f"{path}.manifest.json"),
        path.with_suffix(".manifest.json"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return SnapshotManifest.load(candidate)
    return None


def _file_uri(path: Path) -> str:
    return f"file:{urllib.parse.quote(str(path.resolve()))}?mode=ro&immutable=1"


def _json_value(value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list, int, float, bool)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _bool_value(value: Any) -> bool | None:
    if value is None:
        return None
    return bool(value)


def _table_exists(connection: sqlite3.Connection, table: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        is not None
    )


def _require_tables(connection: sqlite3.Connection, *tables: str) -> None:
    missing = [table for table in tables if not _table_exists(connection, table)]
    if missing:
        raise UnsupportedError(
            "snapshot does not provide required table(s): " + ", ".join(missing)
        )


def _limit(value: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > 10_000:
        raise ResourceLimitError("limit must be an integer between 1 and 10000")
    return value


def _family_id(connection: sqlite3.Connection, identifier: int | str) -> int:
    _require_tables(connection, "function_families")
    if isinstance(identifier, int) and not isinstance(identifier, bool):
        row = connection.execute("SELECT id FROM function_families WHERE id=?", (identifier,)).fetchone()
    elif isinstance(identifier, str) and identifier.strip():
        value = identifier.strip()
        row = connection.execute(
            "SELECT id FROM function_families WHERE canonical_key=? OR name=? OR CAST(id AS TEXT)=?",
            (value, value, value),
        ).fetchone()
    else:
        raise KeyError(f"unknown family {identifier!r}")
    if row is None:
        raise KeyError(f"unknown family {identifier!r}")
    return int(row[0])


def _family_from_row(row: sqlite3.Row) -> FunctionFamily:
    areas = _json_value(row["application_areas_json"], []) or []
    if not isinstance(areas, list):
        areas = []
    return FunctionFamily(
        id=int(row["id"]),
        canonical_key=row["canonical_key"] or row["name"],
        name=row["name"] or row["canonical_key"],
        display_name=row["display_name"],
        closed_form=row["closed_form"],
        generating_def=row["generating_def"],
        is_parametric=bool(row["is_parametric"]),
        param_spec=_json_value(row["param_spec_json"]),
        arity=int(row["arity"] or 0),
        family_group=row["family_group"],
        is_polynomial=bool(row["is_polynomial"]),
        is_entire=bool(row["is_entire"]),
        coeff_formula=row["coeff_formula"],
        coeff_decay=row["coeff_decay"],
        notes=row["notes"],
        application_areas=tuple(str(area) for area in areas if isinstance(area, str)),
    )


def _fact_from_row(row: sqlite3.Row) -> Fact:
    return Fact(
        id=int(row["id"]),
        family_id=int(row["family_id"]) if row["family_id"] is not None else None,
        instance_id=int(row["instance_id"]) if row["instance_id"] is not None else None,
        property_id=int(row["property_id"]),
        property_name=row["property_name"],
        property_param=row["property_param"],
        fact_kind=row["fact_kind"],
        holds=_bool_value(row["holds"]),
        value=row["value"],
        value_exact=row["value_exact"],
        disk_radius=row["disk_radius"],
        is_sharp=_bool_value(row["is_sharp"]),
        provenance=row["provenance"],
        status=row["status"],
        confidence=row["confidence"],
        fact_hash=row["fact_hash"],
        family_key=row["family_key"],
    )


def _run_from_row(row: sqlite3.Row) -> VerificationRun:
    return VerificationRun(
        id=int(row["id"]),
        fact_id=int(row["fact_id"]),
        instance_id=int(row["instance_id"]) if row["instance_id"] is not None else None,
        verifier=row["verifier"],
        direction=row["direction"],
        outcome=row["outcome"],
        margin=row["margin"],
        domain_radius=row["domain_radius"],
        witness=_json_value(row["witness_json"]),
        tail_bound=row["tail_bound"],
        engine_version=row["engine_version"],
        params=_json_value(row["params_json"], {}),
        runtime_ms=row["runtime_ms"],
        family_key=row["family_key"],
    )


def _paper_from_row(row: sqlite3.Row) -> Paper:
    return Paper(
        id=int(row["id"]),
        title=row["title"],
        authors=row["authors"],
        year=int(row["year"]) if row["year"] is not None else None,
        journal=row["journal"],
        filename=row["filename"],
        bibtex=row["bibtex"],
        abstract=row["abstract"],
        structured=_json_value(row["structured_json"]),
        doi=row["doi"],
    )


def _evidence_from_row(row: sqlite3.Row) -> Evidence:
    return Evidence(
        id=int(row["id"]),
        fact_id=int(row["fact_id"]) if row["fact_id"] is not None else None,
        relation_id=int(row["relation_id"]) if row["relation_id"] is not None else None,
        paper_id=int(row["paper_id"]) if row["paper_id"] is not None else None,
        theorem_number=row["theorem_number"],
        page_number=row["page_number"],
        statement_text=row["statement_text"],
        evidence_type=row["evidence_type"],
        legacy_claim_id=row["legacy_claim_id"],
        family_key=row["family_key"],
    )


class RegistrySnapshot:
    """A context-managed, immutable SQLite view of a verified snapshot."""

    def __init__(self, path: Path, connection: sqlite3.Connection, manifest: SnapshotManifest | None) -> None:
        self.path = path
        self.connection = connection
        self.manifest = manifest

    @classmethod
    def open(
        cls,
        path: str | os.PathLike[str],
        *,
        manifest: SnapshotManifest | Mapping[str, Any] | str | os.PathLike[str] | None = None,
        max_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
    ) -> Self:
        snapshot_path = Path(path)
        if not snapshot_path.is_file():
            raise SnapshotIntegrityError(f"snapshot not found: {snapshot_path}")
        size, _ = _sha256(snapshot_path, max_bytes=max_bytes)
        if size < 100:
            raise SnapshotIntegrityError("snapshot is too small to be a SQLite database")
        parsed_manifest = _manifest_for(snapshot_path, manifest)
        if parsed_manifest is not None:
            verify_snapshot(snapshot_path, manifest=parsed_manifest, max_bytes=max_bytes, raise_on_error=True)
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(_file_uri(snapshot_path), uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
        except sqlite3.Error as exc:
            if connection is not None:
                connection.close()
            raise SnapshotIntegrityError(f"cannot open immutable SQLite snapshot: {exc}") from exc
        return cls(snapshot_path, connection, parsed_manifest)

    @classmethod
    def _unchecked_connection(cls, path: Path) -> sqlite3.Connection:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(_file_uri(path), uri=True)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only=ON")
            connection.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone()
            return connection
        except sqlite3.Error as exc:
            if connection is not None:
                connection.close()
            raise SnapshotIntegrityError(f"cannot open immutable SQLite snapshot: {exc}") from exc

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def info(self) -> SnapshotInfo:
        size, digest = _sha256(self.path)
        tables = tuple(
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        )
        counts = {
            table: int(self.connection.execute(f' SELECT count(*) FROM "{table}"').fetchone()[0])
            for table in tables
        }
        return SnapshotInfo(
            path=str(self.path),
            dataset_version=self.manifest.dataset_version if self.manifest else None,
            sha256=digest,
            bytes=size,
            sqlite_version=str(self.connection.execute("SELECT sqlite_version()").fetchone()[0]),
            user_version=int(self.connection.execute("PRAGMA user_version").fetchone()[0]),
            page_size=int(self.connection.execute("PRAGMA page_size").fetchone()[0]),
            page_count=int(self.connection.execute("PRAGMA page_count").fetchone()[0]),
            freelist_count=int(self.connection.execute("PRAGMA freelist_count").fetchone()[0]),
            quick_check=str(self.connection.execute("PRAGMA quick_check").fetchone()[0]),
            integrity_check=str(self.connection.execute("PRAGMA integrity_check").fetchone()[0]),
            application_tables=tables,
            row_counts=MappingProxyType(counts),
            verified=self.manifest is not None,
        )

    def stats(self) -> SnapshotStats:
        info = self.info()
        counts = info.row_counts
        facts = counts.get("facts", 0)
        proven = 0
        disproven = 0
        if _table_exists(self.connection, "facts"):
            proven = int(self.connection.execute("SELECT count(*) FROM facts WHERE status='proven'").fetchone()[0])
            disproven = int(
                self.connection.execute("SELECT count(*) FROM facts WHERE status='disproven'").fetchone()[0]
            )
        return SnapshotStats(
            dataset_version=info.dataset_version,
            families=counts.get("function_families", 0),
            instances=counts.get("function_instances", 0),
            facts=facts,
            proven_facts=proven,
            disproven_facts=disproven,
            verification_runs=counts.get("verification_runs", 0),
            evidence=counts.get("evidence", 0),
            papers=counts.get("papers", 0),
            paper_claims=counts.get("paper_claims", 0),
            row_counts=info.row_counts,
        )

    def families(
        self,
        *,
        group: str | None = None,
        setting: str | None = None,
        limit: int = 10_000,
    ) -> tuple[FunctionFamily, ...]:
        _require_tables(self.connection, "function_families")
        limit = _limit(limit)
        clauses: list[str] = []
        params: list[Any] = []
        selected_group = group if group is not None else setting
        if selected_group is not None:
            clauses.append("family_group=?")
            params.append(selected_group)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            f"SELECT * FROM function_families{where} ORDER BY canonical_key, id LIMIT ?",
            (*params, limit),
        ).fetchall()
        return tuple(_family_from_row(row) for row in rows)

    def family(self, identifier: int | str, *, limit: int = 10_000) -> FamilyDetail:
        family_id = _family_id(self.connection, identifier)
        row = self.connection.execute("SELECT * FROM function_families WHERE id=?", (family_id,)).fetchone()
        assert row is not None
        family = _family_from_row(row)
        instances = self._instances(family_id, limit=limit)
        facts = self.facts(family_id, limit=limit)
        evidence = self.evidence(family_id, limit=limit)
        runs = self.runs(family_id, limit=limit)
        papers = self._papers_for_family(family_id, limit=limit)
        aliases = self._aliases_for_family(family_id)
        return FamilyDetail(family, instances, facts, evidence, runs, papers, aliases)

    def _instances(self, family_id: int, *, limit: int) -> tuple[FunctionInstance, ...]:
        _require_tables(self.connection, "function_instances")
        rows = self.connection.execute(
            "SELECT * FROM function_instances WHERE family_id=? ORDER BY id LIMIT ?",
            (family_id, _limit(limit)),
        ).fetchall()
        return tuple(
            FunctionInstance(
                id=int(row["id"]),
                family_id=int(row["family_id"]),
                param_values=_json_value(row["param_values_json"]),
                coefficients=_json_value(row["coefficients_json"]),
                num_terms=row["num_terms"],
                coeff_source=row["coeff_source"],
                coeff_fingerprint=row["coeff_fingerprint"],
            )
            for row in rows
        )

    def facts(
        self,
        family: int | str | None = None,
        *,
        property: str | None = None,
        status: str | None = None,
        limit: int = 10_000,
    ) -> tuple[Fact, ...]:
        _require_tables(self.connection, "facts", "gft_properties")
        limit = _limit(limit)
        clauses: list[str] = []
        params: list[Any] = []
        if family is not None:
            clauses.append("f.family_id=?")
            params.append(_family_id(self.connection, family))
        if property is not None:
            clauses.append("gp.name=?")
            params.append(property)
        if status is not None:
            clauses.append("f.status=?")
            params.append(status)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            f"""SELECT f.*, gp.name AS property_name, ff.canonical_key AS family_key
                FROM facts f JOIN gft_properties gp ON gp.id=f.property_id
                LEFT JOIN function_families ff ON ff.id=f.family_id
                {where} ORDER BY f.id LIMIT ?""",
            (*params, limit),
        ).fetchall()
        return tuple(_fact_from_row(row) for row in rows)

    def evidence(
        self,
        family: int | str | None = None,
        *,
        paper: int | None = None,
        limit: int = 10_000,
    ) -> tuple[Evidence, ...]:
        _require_tables(self.connection, "evidence")
        limit = _limit(limit)
        clauses: list[str] = []
        params: list[Any] = []
        joins = "LEFT JOIN facts f ON f.id=e.fact_id LEFT JOIN function_families ff ON ff.id=f.family_id"
        if family is not None:
            clauses.append("f.family_id=?")
            params.append(_family_id(self.connection, family))
        if paper is not None:
            clauses.append("e.paper_id=?")
            params.append(paper)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            f"""SELECT e.*, ff.canonical_key AS family_key FROM evidence e {joins}
                {where} ORDER BY e.id LIMIT ?""",
            (*params, limit),
        ).fetchall()
        return tuple(_evidence_from_row(row) for row in rows)

    def runs(
        self,
        family: int | str | None = None,
        *,
        limit: int = 10_000,
    ) -> tuple[VerificationRun, ...]:
        _require_tables(self.connection, "verification_runs")
        limit = _limit(limit)
        clauses: list[str] = []
        params: list[Any] = []
        joins = "LEFT JOIN facts f ON f.id=r.fact_id LEFT JOIN function_families ff ON ff.id=f.family_id"
        if family is not None:
            clauses.append("f.family_id=?")
            params.append(_family_id(self.connection, family))
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            f"""SELECT r.*, ff.canonical_key AS family_key FROM verification_runs r {joins}
                {where} ORDER BY r.id LIMIT ?""",
            (*params, limit),
        ).fetchall()
        return tuple(_run_from_row(row) for row in rows)

    def papers(
        self,
        query: str | None = None,
        *,
        author: str | None = None,
        year: int | None = None,
        class_key: str | None = None,
        tag: str | None = None,
        claim: str | None = None,
        sort: str = "relevance",
        limit: int = 10_000,
    ) -> tuple[Paper, ...]:
        _require_tables(self.connection, "papers")
        limit = _limit(limit)
        clauses: list[str] = []
        params: list[Any] = []
        if query:
            needle = f"%{query.strip().lower()}%"
            clauses.append("lower(coalesce(p.title,'') || ' ' || coalesce(p.authors,'') || ' ' || coalesce(p.abstract,'')) LIKE ?")
            params.append(needle)
        if author:
            clauses.append("lower(coalesce(p.authors,'')) LIKE ?")
            params.append(f"%{author.lower()}%")
        if year is not None:
            clauses.append("p.year=?")
            params.append(year)
        if class_key:
            _require_tables(self.connection, "paper_class_tags")
            clauses.append("EXISTS (SELECT 1 FROM paper_class_tags pct WHERE pct.paper_id=p.id AND pct.class_key=?)")
            params.append(class_key)
        if tag:
            _require_tables(self.connection, "paper_tags", "tags")
            clauses.append("EXISTS (SELECT 1 FROM paper_tags pt JOIN tags t ON t.id=pt.tag_id WHERE pt.paper_id=p.id AND lower(t.name)=lower(?))")
            params.append(tag)
        if claim:
            _require_tables(self.connection, "paper_claims")
            clauses.append("EXISTS (SELECT 1 FROM paper_claims pc WHERE pc.paper_id=p.id AND lower(coalesce(pc.claim_text,'') || ' ' || coalesce(pc.statement_human,'')) LIKE ?)")
            params.append(f"%{claim.lower()}%")
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        order = {"relevance": "p.year DESC, p.id", "year": "p.year DESC, p.id", "title": "lower(p.title), p.id"}.get(sort)
        if order is None:
            raise ValueError("sort must be one of relevance, year, title")
        rows = self.connection.execute(
            f"SELECT p.* FROM papers p{where} ORDER BY {order} LIMIT ?", (*params, limit)
        ).fetchall()
        return tuple(_paper_from_row(row) for row in rows)

    def paper(self, identifier: int | str, *, limit: int = 10_000) -> PaperDetail:
        _require_tables(self.connection, "papers")
        if isinstance(identifier, int) and not isinstance(identifier, bool):
            row = self.connection.execute("SELECT * FROM papers WHERE id=?", (identifier,)).fetchone()
        else:
            row = self.connection.execute(
                "SELECT * FROM papers WHERE CAST(id AS TEXT)=? OR title=?", (str(identifier), identifier)
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown paper {identifier!r}")
        paper = _paper_from_row(row)
        claims: tuple[PaperClaim, ...] = ()
        if _table_exists(self.connection, "paper_claims"):
            claims = tuple(
                PaperClaim(
                    id=int(item["id"]), paper_id=item["paper_id"], function_name=item["function_name"],
                    claim_type=item["claim_type"], claim_text=item["claim_text"],
                    verified_match=_bool_value(item["verified_match"]),
                    extraction_source=item["extraction_source"], statement_human=item["statement_human"],
                )
                for item in self.connection.execute("SELECT * FROM paper_claims WHERE paper_id=? ORDER BY id LIMIT ?", (paper.id, _limit(limit)))
            )
        tags = self._paper_class_tags(paper.id, limit=limit)
        links = self._paper_family_links(paper.id, limit=limit)
        return PaperDetail(paper, claims, tags, links, self.evidence(paper=paper.id, limit=limit))

    def applications(
        self,
        area: str | None = None,
        family: int | str | None = None,
        *,
        limit: int = 10_000,
    ) -> tuple[Application, ...]:
        _require_tables(self.connection, "function_families")
        family_id = _family_id(self.connection, family) if family is not None else None
        result: list[Application] = []
        # The website's applications page is a paper-tag/evidence cross-tab.
        # Prefer that normalized relation when present; family JSON is retained
        # as a fallback for smaller snapshots that only carry family metadata.
        if all(
            _table_exists(self.connection, table)
            for table in ("tags", "paper_tags", "papers", "evidence", "facts")
        ):
            clauses = ["t.category='application'"]
            params: list[Any] = []
            if family_id is not None:
                clauses.append("f.family_id=?")
                params.append(family_id)
            if area is not None:
                clauses.append("t.name=?")
                params.append(area)
            rows = self.connection.execute(
                f"""SELECT t.name AS area, ff.id AS family_id,
                           ff.canonical_key AS family_key, ff.name AS family_name,
                           COUNT(DISTINCT ev.paper_id) AS paper_count
                    FROM tags t JOIN paper_tags pt ON pt.tag_id=t.id
                    JOIN papers p ON p.id=pt.paper_id
                    JOIN evidence ev ON ev.paper_id=p.id
                    JOIN facts f ON f.id=ev.fact_id
                    JOIN function_families ff ON ff.id=f.family_id
                    WHERE {' AND '.join(clauses)}
                    GROUP BY t.name, ff.id ORDER BY t.name, ff.id LIMIT ?""",
                (*params, _limit(limit)),
            ).fetchall()
            result.extend(
                Application(
                    row["area"], int(row["family_id"]), row["family_key"], row["family_name"],
                    "paper_tags(category=application)+evidence", int(row["paper_count"]),
                )
                for row in rows
            )
            if result:
                return tuple(result)
        for item in self.families(limit=limit):
            if family_id is not None and item.id != family_id:
                continue
            for item_area in item.application_areas:
                if area is None or item_area == area:
                    result.append(Application(item_area, item.id, item.canonical_key, item.name, "family.application_areas_json"))
                    if len(result) >= limit:
                        return tuple(result)
        return tuple(result)

    def counterexamples(
        self,
        family: int | str | None = None,
        *,
        property: str | None = None,
        limit: int = 10_000,
    ) -> tuple[Counterexample, ...]:
        facts = self.facts(family, property=property, limit=limit)
        runs = self.runs(family, limit=limit) if _table_exists(self.connection, "verification_runs") else ()
        runs_by_fact: dict[int, list[VerificationRun]] = {}
        for run in runs:
            runs_by_fact.setdefault(run.fact_id, []).append(run)
        results: list[Counterexample] = []
        for fact in facts:
            related = tuple(runs_by_fact.get(fact.id, ()))
            is_counterexample = fact.status == "disproven" or fact.holds is False or any(
                run.direction == "disproves" and run.outcome == "pass" for run in related
            )
            if is_counterexample:
                results.append(Counterexample(fact, fact.property_name, related))
        return tuple(results[:limit])

    def search(
        self,
        query: str,
        *,
        kind: str | None = None,
        limit: int = 100,
    ) -> tuple[SearchResult, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("search query must not be empty")
        limit = _limit(limit)
        normalized = query.strip().lower()
        if kind not in (None, "family", "paper", "proof"):
            raise ValueError("kind must be one of family, paper, proof")
        results: list[SearchResult] = []
        if kind in (None, "family") and _table_exists(self.connection, "function_families"):
            for row in self.connection.execute(
                """SELECT id, canonical_key, name, display_name FROM function_families
                   WHERE lower(coalesce(canonical_key,'') || ' ' || coalesce(name,'') || ' ' || coalesce(display_name,'')) LIKE ?
                   ORDER BY canonical_key, id LIMIT ?""",
                (f"%{normalized}%", limit),
            ):
                results.append(SearchResult("family", int(row["id"]), row["canonical_key"], row["name"], row["display_name"]))
        if kind in (None, "paper") and _table_exists(self.connection, "papers"):
            remaining = max(0, limit - len(results))
            for row in self.connection.execute(
                """SELECT id, title, authors, year FROM papers
                   WHERE lower(coalesce(title,'') || ' ' || coalesce(authors,'') || ' ' || coalesce(abstract,'')) LIKE ?
                   ORDER BY year DESC, id LIMIT ?""",
                (f"%{normalized}%", remaining),
            ):
                results.append(SearchResult("paper", int(row["id"]), title=row["title"], year=row["year"]))
        if kind == "proof" and _table_exists(self.connection, "evidence"):
            remaining = max(0, limit - len(results))
            for row in self.connection.execute(
                """SELECT e.id, e.statement_text, ff.canonical_key
                   FROM evidence e LEFT JOIN facts f ON f.id=e.fact_id
                   LEFT JOIN function_families ff ON ff.id=f.family_id
                   WHERE lower(coalesce(e.statement_text,'')) LIKE ?
                   ORDER BY e.id LIMIT ?""",
                (f"%{normalized}%", remaining),
            ):
                results.append(SearchResult("proof", int(row["id"]), canonical_key=row["canonical_key"], display_name=row["statement_text"]))
        return tuple(results[:limit])

    def aliases(self, query: str | None = None, *, limit: int = 10_000) -> tuple[Mapping[str, Any], ...]:
        _require_tables(self.connection, "function_aliases", "function_families")
        clauses = ""
        params: tuple[Any, ...] = ()
        if query:
            clauses = " WHERE lower(fa.alias) LIKE ?"
            params = (f"%{query.lower()}%",)
        rows = self.connection.execute(
            f"""SELECT fa.id, fa.alias, fa.family_id, ff.canonical_key, ff.name
                FROM function_aliases fa JOIN function_families ff ON ff.id=fa.family_id
                {clauses} ORDER BY lower(fa.alias), fa.id LIMIT ?""",
            (*params, _limit(limit)),
        ).fetchall()
        return tuple(MappingProxyType(dict(row)) for row in rows)

    def normalize_class(self, text: str) -> str:
        if not isinstance(text, str) or not text.strip():
            raise ValueError("class name must not be empty")
        normalized = " ".join(text.strip().lower().replace("_", " ").replace("-", " ").split())
        if _table_exists(self.connection, "function_families"):
            row = self.connection.execute(
                """SELECT canonical_key FROM function_families
                   WHERE lower(canonical_key)=? OR lower(name)=? OR lower(display_name)=?""",
                (normalized, normalized, normalized),
            ).fetchone()
            if row is not None:
                return str(row[0])
        if _table_exists(self.connection, "function_aliases"):
            for alias in self.aliases(limit=10_000):
                if " ".join(str(alias["alias"]).lower().replace("-", " ").split()) == normalized:
                    return str(alias["canonical_key"])
        return normalized.replace(" ", "_")

    def hierarchy(self, property: str | None = None, *, limit: int = 10_000) -> tuple[PropertyImplication, ...]:
        _require_tables(self.connection, "property_implications", "gft_properties")
        clauses: list[str] = []
        params: list[Any] = []
        if property:
            clauses.append("(pfrom.name=? OR pto.name=?)")
            params.extend([property, property])
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        rows = self.connection.execute(
            f"""SELECT pi.id, pfrom.name AS from_property, pto.name AS to_property,
                       pi.condition, pi.source
                FROM property_implications pi
                JOIN gft_properties pfrom ON pfrom.id=pi.from_prop_id
                JOIN gft_properties pto ON pto.id=pi.to_prop_id
                {where} ORDER BY pfrom.name, pto.name, pi.id LIMIT ?""",
            (*params, _limit(limit)),
        ).fetchall()
        return tuple(PropertyImplication(int(row["id"]), row["from_property"], row["to_property"], row["condition"], row["source"]) for row in rows)

    def _aliases_for_family(self, family_id: int) -> tuple[str, ...]:
        if not _table_exists(self.connection, "function_aliases"):
            return ()
        return tuple(row[0] for row in self.connection.execute("SELECT alias FROM function_aliases WHERE family_id=? ORDER BY lower(alias)", (family_id,)))

    def _papers_for_family(self, family_id: int, *, limit: int) -> tuple[Paper, ...]:
        if not _table_exists(self.connection, "paper_family_links") or not _table_exists(self.connection, "papers"):
            return ()
        rows = self.connection.execute(
            """SELECT p.* FROM papers p JOIN paper_family_links pfl ON pfl.paper_id=p.id
               WHERE pfl.family_id=? ORDER BY p.year DESC, p.id LIMIT ?""", (family_id, _limit(limit))
        ).fetchall()
        return tuple(_paper_from_row(row) for row in rows)

    def _paper_class_tags(self, paper_id: int, *, limit: int) -> tuple[Mapping[str, Any], ...]:
        if not _table_exists(self.connection, "paper_class_tags"):
            return ()
        rows = self.connection.execute("SELECT * FROM paper_class_tags WHERE paper_id=? ORDER BY id LIMIT ?", (paper_id, _limit(limit))).fetchall()
        return tuple(MappingProxyType(dict(row)) for row in rows)

    def _paper_family_links(self, paper_id: int, *, limit: int) -> tuple[Mapping[str, Any], ...]:
        if not _table_exists(self.connection, "paper_family_links"):
            return ()
        rows = self.connection.execute(
            """SELECT pfl.*, ff.canonical_key AS family_key FROM paper_family_links pfl
               LEFT JOIN function_families ff ON ff.id=pfl.family_id
               WHERE pfl.paper_id=? ORDER BY pfl.id LIMIT ?""", (paper_id, _limit(limit))
        ).fetchall()
        return tuple(MappingProxyType(dict(row)) for row in rows)


def verify_snapshot(
    path: str | os.PathLike[str],
    *,
    manifest: SnapshotManifest | Mapping[str, Any] | str | os.PathLike[str] | None = None,
    max_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
    raise_on_error: bool = False,
) -> SnapshotVerification:
    """Verify hashes, populations, and SQLite integrity without mutating a file."""
    snapshot_path = Path(path)
    parsed_manifest = _manifest_for(snapshot_path, manifest)
    if parsed_manifest is None:
        raise SnapshotManifestError("a manifest is required to verify a snapshot")
    checks: dict[str, str] = {}
    errors: list[str] = []
    database: dict[str, Any] = {}
    try:
        size, digest = _sha256(snapshot_path, max_bytes=max_bytes)
        database.update({"bytes": size, "sha256": digest})
        checks["bytes"] = "pass" if size == parsed_manifest.database_bytes else "fail"
        if size != parsed_manifest.database_bytes:
            errors.append(f"database byte count mismatch: expected {parsed_manifest.database_bytes}, got {size}")
        checks["sha256"] = "pass" if digest == parsed_manifest.database_sha256 else "fail"
        if digest != parsed_manifest.database_sha256:
            errors.append("database SHA-256 does not match manifest")
    except (SnapshotError, SnapshotResourceLimitError) as exc:
        checks["bytes"] = "fail"
        checks["sha256"] = "fail"
        errors.append(str(exc))
    if not snapshot_path.is_file():
        checks.setdefault("sqlite_header", "fail")
        errors.append(f"snapshot not found: {snapshot_path}")
    else:
        try:
            with closing(RegistrySnapshot._unchecked_connection(snapshot_path)) as connection:
                header = connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
                checks["sqlite_header"] = "pass" if header is not None else "fail"
                quick = str(connection.execute("PRAGMA quick_check").fetchone()[0])
                integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
                database.update(
                    {
                        "sqlite_version": str(connection.execute("SELECT sqlite_version()").fetchone()[0]),
                        "quick_check": quick,
                        "integrity_check": integrity,
                        "user_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
                    }
                )
                checks["quick_check"] = "pass" if quick == "ok" else "fail"
                checks["integrity_check"] = "pass" if integrity == "ok" else "fail"
                if quick != "ok":
                    errors.append(f"PRAGMA quick_check returned {quick!r}")
                if integrity != "ok":
                    errors.append(f"PRAGMA integrity_check returned {integrity!r}")
                actual_tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    )
                }
                missing = sorted(set(parsed_manifest.application_tables) - actual_tables)
                checks["required_tables"] = "pass" if not missing else "fail"
                if missing:
                    errors.append("required table(s) missing: " + ", ".join(missing))
                counts = {
                    table: int(connection.execute(f' SELECT count(*) FROM "{table}"').fetchone()[0])
                    for table in parsed_manifest.application_tables
                    if table in actual_tables
                }
                database["row_counts"] = counts
                mismatches = [
                    f"{table}: expected {expected}, got {counts.get(table)}"
                    for table, expected in parsed_manifest.row_counts.items()
                    if counts.get(table) != expected
                ]
                checks["row_counts"] = "pass" if not mismatches else "fail"
                if mismatches:
                    errors.append("row count mismatch: " + "; ".join(mismatches))
        except (sqlite3.Error, OSError, SnapshotError) as exc:
            checks.setdefault("sqlite_header", "fail")
            checks["quick_check"] = "fail"
            checks["integrity_check"] = "fail"
            checks["required_tables"] = "fail"
            checks["row_counts"] = "fail"
            errors.append(f"cannot inspect SQLite snapshot: {exc}")
    result = SnapshotVerification(
        path=str(snapshot_path),
        dataset_version=parsed_manifest.dataset_version,
        checks=MappingProxyType(checks),
        errors=tuple(dict.fromkeys(errors)),
        database=MappingProxyType(database),
    )
    if raise_on_error and not result.success:
        raise SnapshotIntegrityError("snapshot verification failed: " + "; ".join(result.errors))
    return result


def _download(url: str, destination: Path, *, max_bytes: int) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "geometric-function-atlas"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response, destination.open("wb") as stream:
            total = 0
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    raise SnapshotResourceLimitError(f"download exceeds {max_bytes} byte limit")
                stream.write(chunk)
    except SnapshotResourceLimitError:
        raise
    except Exception as exc:
        raise SnapshotIntegrityError(f"snapshot download failed: {exc}") from exc


def _source_to_file(source: str | os.PathLike[str], directory: Path, *, max_bytes: int) -> tuple[Path, bool]:
    source_text = os.fspath(source)
    parsed = urllib.parse.urlparse(source_text)
    if parsed.scheme in {"http", "https"}:
        target = directory / (Path(parsed.path).name or "download")
        _download(source_text, target, max_bytes=max_bytes)
        return target, True
    source_path = Path(source_text)
    if not source_path.is_file():
        raise SnapshotIntegrityError(f"snapshot source not found: {source_path}")
    size, _ = _sha256(source_path, max_bytes=max_bytes)
    if size > max_bytes:
        raise SnapshotResourceLimitError(f"source exceeds {max_bytes} byte limit")
    return source_path, False


def _decompress_zstd(source: Path, destination: Path, *, max_bytes: int) -> None:
    executable = which("zstd")
    if executable is None:
        try:
            import zstandard  # type: ignore[import-not-found]
        except ImportError as exc:
            raise UnsupportedError("Zstandard snapshots require the zstd command or the zstandard package") from exc
        try:
            decompressor = zstandard.ZstdDecompressor()
            with (
                source.open("rb") as source_stream,
                destination.open("wb") as destination_stream,
                decompressor.stream_reader(source_stream) as reader,
            ):
                total = 0
                while chunk := reader.read(1024 * 1024):
                    total += len(chunk)
                    if total > max_bytes:
                        raise SnapshotResourceLimitError(f"decompressed snapshot exceeds {max_bytes} byte limit")
                    destination_stream.write(chunk)
            return
        except SnapshotResourceLimitError:
            raise
        except Exception as exc:
            raise SnapshotIntegrityError(f"Zstandard decompression failed: {exc}") from exc
    process = subprocess.Popen(
        [executable, "-q", "-d", "-c", str(source)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    total = 0
    stderr = ""
    return_code: int | None = None
    try:
        with destination.open("wb") as stream:
            assert process.stdout is not None
            while chunk := process.stdout.read(1024 * 1024):
                total += len(chunk)
                if total > max_bytes:
                    process.kill()
                    process.wait()
                    raise SnapshotResourceLimitError(f"decompressed snapshot exceeds {max_bytes} byte limit")
                stream.write(chunk)
        stderr = process.stderr.read().decode("utf-8", "replace") if process.stderr else ""
        return_code = process.wait()
    except SnapshotResourceLimitError:
        process.kill()
        process.wait()
        raise
    except OSError as exc:
        process.kill()
        process.wait()
        raise SnapshotIntegrityError(f"cannot write decompressed snapshot: {exc}") from exc
    finally:
        if process.stdout is not None:
            process.stdout.close()
        if process.stderr is not None:
            process.stderr.close()
    if return_code != 0:
        raise SnapshotIntegrityError(f"Zstandard decompression failed: {stderr.strip() or return_code}")


def install_snapshot(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    *,
    manifest: SnapshotManifest | Mapping[str, Any] | str | os.PathLike[str] | None = None,
    max_compressed_bytes: int = DEFAULT_MAX_COMPRESSED_BYTES,
    max_decompressed_bytes: int = DEFAULT_MAX_DECOMPRESSED_BYTES,
) -> Path:
    """Download/copy, verify, and atomically install an immutable snapshot.

    The destination is a plain SQLite file.  The source may be a local SQLite or
    Zstandard file, or an HTTPS URL.  A manifest is mandatory so an untrusted or
    mutable database can never silently become the active snapshot.
    """
    if manifest is None:
        raise SnapshotManifestError("manifest is required to install a snapshot")
    parsed_manifest: SnapshotManifest
    if isinstance(manifest, (str, os.PathLike)):
        manifest_text = os.fspath(manifest)
        if urllib.parse.urlparse(manifest_text).scheme in {"http", "https"}:
            with tempfile.TemporaryDirectory(prefix="gfa-manifest-") as temp:
                manifest_path = Path(temp) / "manifest.json"
                _download(manifest_text, manifest_path, max_bytes=2 * 1024 * 1024)
                parsed_manifest = SnapshotManifest.load(manifest_path)
                return _install_snapshot_with_manifest(source, destination, parsed_manifest, max_compressed_bytes, max_decompressed_bytes)
        parsed_manifest = SnapshotManifest.load(manifest)
    elif isinstance(manifest, SnapshotManifest):
        parsed_manifest = manifest
    else:
        parsed_manifest = SnapshotManifest.from_dict(manifest)
    return _install_snapshot_with_manifest(source, destination, parsed_manifest, max_compressed_bytes, max_decompressed_bytes)


def _install_snapshot_with_manifest(
    source: str | os.PathLike[str],
    destination: str | os.PathLike[str],
    manifest: SnapshotManifest,
    max_compressed_bytes: int,
    max_decompressed_bytes: int,
) -> Path:
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="gfa-snapshot-") as temp_name:
        temp_dir = Path(temp_name)
        source_path, _ = _source_to_file(source, temp_dir, max_bytes=max_compressed_bytes)
        source_size, source_digest = _sha256(source_path, max_bytes=max_compressed_bytes)
        is_compressed = source_path.name.lower().endswith((".zst", ".zstd"))
        if is_compressed:
            if manifest.compressed_sha256 is not None and (
                source_size != manifest.compressed_bytes or source_digest != manifest.compressed_sha256
            ):
                raise SnapshotIntegrityError("compressed snapshot does not match manifest")
            raw_path = temp_dir / manifest.database_filename
            _decompress_zstd(source_path, raw_path, max_bytes=max_decompressed_bytes)
        else:
            raw_path = temp_dir / manifest.database_filename
            shutil.copyfile(source_path, raw_path)
        verify_snapshot(raw_path, manifest=manifest, max_bytes=max_decompressed_bytes, raise_on_error=True)
        staging = destination_path.with_name(destination_path.name + ".tmp")
        try:
            shutil.copyfile(raw_path, staging)
            os.replace(staging, destination_path)
        finally:
            try:
                staging.unlink()
            except FileNotFoundError:
                pass
    return destination_path


def snapshot_info(
    path: str | os.PathLike[str],
    *,
    manifest: SnapshotManifest | Mapping[str, Any] | str | os.PathLike[str] | None = None,
) -> SnapshotInfo:
    """Return immutable SQLite metadata; no network access is performed."""
    with RegistrySnapshot.open(path, manifest=manifest) as snapshot:
        return snapshot.info()


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "Application",
    "Counterexample",
    "Evidence",
    "Fact",
    "FamilyDetail",
    "FunctionFamily",
    "FunctionInstance",
    "Paper",
    "PaperClaim",
    "PaperDetail",
    "PropertyImplication",
    "RegistrySnapshot",
    "SearchResult",
    "SnapshotError",
    "SnapshotInfo",
    "SnapshotIntegrityError",
    "SnapshotManifest",
    "SnapshotManifestError",
    "SnapshotResourceLimitError",
    "SnapshotStats",
    "SnapshotVerification",
    "VerificationRun",
    "install_snapshot",
    "snapshot_info",
    "verify_snapshot",
]
