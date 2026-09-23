"""Deterministic collaborator bundle manifests fail closed on changed files."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from geometric_function_atlas import (
    CorruptArtifactError,
    InvalidInputError,
    verify_research_bundle_manifest,
    write_research_bundle_manifest,
)

ROOT = Path(__file__).resolve().parents[1]


def _bundle_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "result.json").write_text(
        json.dumps(
            {
                "exact_expression": "15/8",
                "assumptions": ["alpha=1/4 exactly"],
                "source": "Ma-Minda theorem provenance",
                "novelty_claim": False,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    (directory / "plot.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><title>Exact anchor</title></svg>\n',
        encoding="utf-8",
    )


def test_research_bundle_manifest_is_deterministic_and_verifiable(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    _bundle_files(left)
    _bundle_files(right)

    kwargs = {
        "workflow": "custom_class",
        "entrypoint": "examples/research_workflows/custom_class.py",
        "parameters": {"alpha": "1/4", "order": 4},
        "primary_record": "result.json",
        "artifacts": ("plot.svg", "result.json"),
    }
    left_manifest = write_research_bundle_manifest(left, **kwargs)
    right_manifest = write_research_bundle_manifest(right, **kwargs)

    assert left_manifest.name == "research_bundle_manifest.json"
    assert left_manifest.read_bytes() == right_manifest.read_bytes()
    payload = verify_research_bundle_manifest(left_manifest)
    assert payload["schema_version"] == 1
    assert payload["bundle_type"] == "gft_research_bundle"
    assert payload["workflow"] == "custom_class"
    assert payload["parameters"] == {"alpha": "1/4", "order": 4}
    assert payload["primary_record"] == "result.json"
    assert [item["path"] for item in payload["artifacts"]] == [
        "plot.svg",
        "result.json",
    ]
    assert all(len(item["sha256"]) == 64 for item in payload["artifacts"])
    assert payload["integrity"]["manifest_excluded"] is True
    assert payload["software"]["package"] == "geometric-function-atlas"


def test_research_bundle_verification_rejects_mutation(tmp_path: Path) -> None:
    _bundle_files(tmp_path)
    manifest = write_research_bundle_manifest(
        tmp_path,
        workflow="custom_class",
        entrypoint="examples/research_workflows/custom_class.py",
        parameters={"alpha": "1/4"},
        primary_record="result.json",
        artifacts=("result.json", "plot.svg"),
    )
    plot = tmp_path / "plot.svg"
    plot.write_bytes(plot.read_bytes().replace(b"Exact", b"Other"))

    with pytest.raises(CorruptArtifactError, match="checksum mismatch.*plot.svg"):
        verify_research_bundle_manifest(manifest)


@pytest.mark.parametrize(
    "artifact",
    ("../outside.txt", "/absolute.txt", "research_bundle_manifest.json"),
)
def test_research_bundle_rejects_unsafe_artifact_paths(
    tmp_path: Path, artifact: str
) -> None:
    _bundle_files(tmp_path)
    with pytest.raises(InvalidInputError):
        write_research_bundle_manifest(
            tmp_path,
            workflow="custom_class",
            entrypoint="example.py",
            parameters={},
            primary_record="result.json",
            artifacts=("result.json", artifact),
        )


def test_research_bundle_rejects_symlink_artifact(tmp_path: Path) -> None:
    _bundle_files(tmp_path)
    outside = tmp_path.parent / "outside-bundle.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (tmp_path / "linked.txt").symlink_to(outside)

    with pytest.raises(InvalidInputError, match="symlink"):
        write_research_bundle_manifest(
            tmp_path,
            workflow="custom_class",
            entrypoint="example.py",
            parameters={},
            primary_record="result.json",
            artifacts=("result.json", "linked.txt"),
        )


def test_research_bundle_verifier_rejects_symlinked_parent_directory(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    _bundle_files(real)
    manifest = write_research_bundle_manifest(
        real,
        workflow="custom_class",
        entrypoint="example.py",
        parameters={},
        primary_record="result.json",
        artifacts=("result.json", "plot.svg"),
    )
    alias = tmp_path / "alias"
    alias.symlink_to(real, target_is_directory=True)

    with pytest.raises(CorruptArtifactError, match="symlink"):
        verify_research_bundle_manifest(alias / manifest.name)


def test_bundle_reference_explains_verification_plainly() -> None:
    guide = (ROOT / "docs" / "reference" / "bundles-and-records.md").read_text(
        encoding="utf-8"
    )
    plain_guide = " ".join(guide.lower().split())

    assert "verify_research_bundle_manifest" in guide
    assert "checks the files, not the mathematics" in plain_guide
    assert "does not run the recorded workflow" in plain_guide
    assert "research_bundle_manifest.json" in guide
