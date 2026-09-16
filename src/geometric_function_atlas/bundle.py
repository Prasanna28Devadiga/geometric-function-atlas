"""Deterministic manifests for collaborator-ready research bundles.

A bundle is a directory of already-generated research artifacts plus one closed
JSON manifest.  The manifest records replay inputs and software identity and
checksums every artifact; it never executes the recorded entrypoint.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

from .contracts import CorruptArtifactError, InvalidInputError, ResourceLimitError
from .version import SOURCE_ARTIFACT_COMMIT, __version__

BUNDLE_MANIFEST_NAME = "research_bundle_manifest.json"
BUNDLE_SCHEMA_VERSION = 1
MAX_BUNDLE_ARTIFACTS = 256
MAX_BUNDLE_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_BUNDLE_TOTAL_BYTES = 256 * 1024 * 1024
MAX_BUNDLE_MANIFEST_BYTES = 4 * 1024 * 1024
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_MANIFEST_KEYS = {
    "schema_version",
    "bundle_type",
    "workflow",
    "entrypoint",
    "parameters",
    "primary_record",
    "software",
    "artifacts",
    "integrity",
}
_ARTIFACT_KEYS = {"path", "sha256", "size"}


def _path_has_symlink_component(path: Path) -> bool:
    """Return whether an absolute path or any of its parents is a symlink."""

    absolute = path.absolute()
    return any(candidate.is_symlink() for candidate in (absolute, *absolute.parents))


def _require_non_empty_text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError(f"{name} must be a non-empty string")
    return value


def _json_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(parameters, Mapping):
        raise InvalidInputError("parameters must be a JSON object")
    try:
        encoded = json.dumps(
            dict(parameters),
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
        )
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("parameters must contain only finite JSON values") from exc
    decoded = json.loads(encoded)
    if not isinstance(decoded, dict):
        raise InvalidInputError("parameters must be a JSON object")
    return decoded


def _artifact_path(root: Path, value: Any) -> tuple[str, Path]:
    name = _require_non_empty_text(value, "artifact path")
    if "\\" in name:
        raise InvalidInputError("artifact paths must use portable forward slashes")
    relative = PurePosixPath(name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise InvalidInputError(f"unsafe artifact path: {name!r}")
    normalized = relative.as_posix()
    if normalized == BUNDLE_MANIFEST_NAME:
        raise InvalidInputError("the bundle manifest cannot checksum itself")

    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise InvalidInputError(f"artifact path contains a symlink: {normalized}")
    try:
        candidate.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (FileNotFoundError, ValueError) as exc:
        raise InvalidInputError(
            f"artifact is missing or escapes the bundle directory: {normalized}"
        ) from exc
    if not candidate.is_file():
        raise InvalidInputError(f"artifact is not a regular file: {normalized}")
    return normalized, candidate


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_entry(root: Path, value: Any) -> dict[str, Any]:
    name, path = _artifact_path(root, value)
    size = path.stat().st_size
    if size > MAX_BUNDLE_ARTIFACT_BYTES:
        raise ResourceLimitError(
            f"artifact exceeds {MAX_BUNDLE_ARTIFACT_BYTES} bytes: {name}"
        )
    return {"path": name, "sha256": _sha256_file(path), "size": size}


def write_research_bundle_manifest(
    directory: str | Path,
    *,
    workflow: str,
    entrypoint: str,
    parameters: Mapping[str, Any],
    primary_record: str,
    artifacts: Sequence[str],
) -> Path:
    """Write a deterministic checksum manifest for existing workflow artifacts.

    Artifact names are POSIX-style paths relative to ``directory``.  Symlinks,
    traversal, absolute paths, the manifest itself, duplicates, missing files,
    and over-limit bundles are rejected.  The manifest excludes timestamps so
    identical artifacts and replay inputs produce identical bytes.
    """

    root = Path(directory)
    if _path_has_symlink_component(root):
        raise InvalidInputError("bundle directory path contains a symlink")
    if not root.is_dir():
        raise InvalidInputError("bundle directory must be an existing real directory")
    workflow_value = _require_non_empty_text(workflow, "workflow")
    entrypoint_value = _require_non_empty_text(entrypoint, "entrypoint")
    parameter_values = _json_parameters(parameters)
    if isinstance(artifacts, (str, bytes)) or not isinstance(artifacts, Sequence):
        raise InvalidInputError("artifacts must be a sequence of relative paths")
    if not 1 <= len(artifacts) <= MAX_BUNDLE_ARTIFACTS:
        raise ResourceLimitError(
            f"bundle must contain between 1 and {MAX_BUNDLE_ARTIFACTS} artifacts"
        )

    entries = [_artifact_entry(root, value) for value in artifacts]
    names = [entry["path"] for entry in entries]
    if len(set(names)) != len(names):
        raise InvalidInputError("artifact paths must be unique")
    primary_name, _ = _artifact_path(root, primary_record)
    if primary_name not in names:
        raise InvalidInputError("primary_record must also appear in artifacts")
    entries.sort(key=lambda item: item["path"])
    total_bytes = sum(int(item["size"]) for item in entries)
    if total_bytes > MAX_BUNDLE_TOTAL_BYTES:
        raise ResourceLimitError(
            f"bundle exceeds {MAX_BUNDLE_TOTAL_BYTES} total artifact bytes"
        )

    payload = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "bundle_type": "gft_research_bundle",
        "workflow": workflow_value,
        "entrypoint": entrypoint_value,
        "parameters": parameter_values,
        "primary_record": primary_name,
        "software": {
            "package": "geometric-function-atlas",
            "version": __version__,
            "source_artifact_commit": SOURCE_ARTIFACT_COMMIT,
        },
        "artifacts": entries,
        "integrity": {
            "algorithm": "sha256",
            "manifest_excluded": True,
            "total_bytes": total_bytes,
        },
    }
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_BUNDLE_MANIFEST_BYTES:
        raise ResourceLimitError("bundle manifest exceeds its size limit")

    destination = root / BUNDLE_MANIFEST_NAME
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=root,
            prefix=".research_bundle_manifest.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return destination


def _manifest_artifact_path(root: Path, value: Any) -> tuple[str, Path]:
    try:
        return _artifact_path(root, value)
    except InvalidInputError as exc:
        raise CorruptArtifactError(str(exc)) from exc


def verify_research_bundle_manifest(manifest: str | Path) -> dict[str, Any]:
    """Verify a research-bundle manifest and every declared artifact."""

    path = Path(manifest)
    if _path_has_symlink_component(path):
        raise CorruptArtifactError("bundle manifest path contains a symlink")
    if not path.is_file():
        raise CorruptArtifactError("bundle manifest must be a regular file")
    if path.stat().st_size > MAX_BUNDLE_MANIFEST_BYTES:
        raise CorruptArtifactError("bundle manifest exceeds its size limit")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CorruptArtifactError("bundle manifest is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or set(payload) != _MANIFEST_KEYS:
        raise CorruptArtifactError("bundle manifest has unknown or missing fields")
    if payload["schema_version"] != BUNDLE_SCHEMA_VERSION:
        raise CorruptArtifactError("unsupported bundle manifest schema version")
    if payload["bundle_type"] != "gft_research_bundle":
        raise CorruptArtifactError("bundle_type is not gft_research_bundle")
    for key in ("workflow", "entrypoint", "primary_record"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            raise CorruptArtifactError(f"manifest {key} must be a non-empty string")
    try:
        _json_parameters(payload["parameters"])
    except InvalidInputError as exc:
        raise CorruptArtifactError(str(exc)) from exc

    software = payload["software"]
    if not isinstance(software, dict) or set(software) != {
        "package",
        "version",
        "source_artifact_commit",
    }:
        raise CorruptArtifactError("manifest software identity is malformed")
    if software["package"] != "geometric-function-atlas" or any(
        not isinstance(software[key], str) or not software[key]
        for key in ("version", "source_artifact_commit")
    ):
        raise CorruptArtifactError("manifest software identity is malformed")

    integrity = payload["integrity"]
    if not isinstance(integrity, dict) or set(integrity) != {
        "algorithm",
        "manifest_excluded",
        "total_bytes",
    }:
        raise CorruptArtifactError("manifest integrity declaration is malformed")
    if integrity["algorithm"] != "sha256" or integrity["manifest_excluded"] is not True:
        raise CorruptArtifactError("manifest integrity algorithm/scope is unsupported")
    if isinstance(integrity["total_bytes"], bool) or not isinstance(
        integrity["total_bytes"], int
    ):
        raise CorruptArtifactError("manifest total_bytes must be an integer")

    entries = payload["artifacts"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_BUNDLE_ARTIFACTS:
        raise CorruptArtifactError("manifest artifact list is empty or over limit")
    observed_names: list[str] = []
    observed_total = 0
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != _ARTIFACT_KEYS:
            raise CorruptArtifactError("manifest artifact entry is malformed")
        name, artifact = _manifest_artifact_path(path.parent, entry["path"])
        expected_size = entry["size"]
        expected_hash = entry["sha256"]
        if isinstance(expected_size, bool) or not isinstance(expected_size, int):
            raise CorruptArtifactError(f"artifact size is malformed: {name}")
        if expected_size < 0 or expected_size > MAX_BUNDLE_ARTIFACT_BYTES:
            raise CorruptArtifactError(f"artifact size is outside limits: {name}")
        if not isinstance(expected_hash, str) or _SHA256_RE.fullmatch(expected_hash) is None:
            raise CorruptArtifactError(f"artifact checksum is malformed: {name}")
        observed_size = artifact.stat().st_size
        if observed_size != expected_size:
            raise CorruptArtifactError(f"size mismatch for artifact {name}")
        observed_hash = _sha256_file(artifact)
        if observed_hash != expected_hash:
            raise CorruptArtifactError(f"checksum mismatch for artifact {name}")
        observed_names.append(name)
        observed_total += observed_size
    if observed_names != sorted(observed_names) or len(set(observed_names)) != len(
        observed_names
    ):
        raise CorruptArtifactError("manifest artifact paths must be sorted and unique")
    if payload["primary_record"] not in observed_names:
        raise CorruptArtifactError("primary_record is not a declared artifact")
    if observed_total != integrity["total_bytes"]:
        raise CorruptArtifactError("manifest total_bytes does not match artifacts")
    if observed_total > MAX_BUNDLE_TOTAL_BYTES:
        raise CorruptArtifactError("bundle exceeds its total size limit")
    return payload
