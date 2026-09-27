from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ACTION_REF = re.compile(r"uses:\s+[^\s@]+@([0-9a-f]{40})(?:\s+#\s+.+)?$")
RELEASE_COMMIT = "e3154d35cb49140a4ca45c5f5afaf5edc3e0bbd7"
RELEASE_ASSETS = {
    "wheel": {
        "name": "geometric_function_atlas-0.6.0-py3-none-any.whl",
        "sha256": "ef52bb424ab4b796841786999136f1923048d0198a700379685111dac5e45bea",
    },
    "sdist": {
        "name": "geometric_function_atlas-0.6.0.tar.gz",
        "sha256": "2467c17b2609dcd82046acc9b42589de9b085a2e1ee7314be51e1e23277b091c",
    },
    "checksums": {
        "name": "SHA256SUMS",
        "sha256": "a19038d63399d9c9f5f9f5f999e8532ec109ef33b621fd278d84a756cb5bc3a0",
    },
}


def _workflow(name: str) -> str:
    return (WORKFLOWS / name).read_text(encoding="utf-8")


def test_all_external_actions_are_pinned_by_full_commit_sha() -> None:
    for path in sorted(WORKFLOWS.glob("*.yml")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "uses:" in line:
                assert ACTION_REF.search(line), (
                    f"mutable Action reference in {path}: {line}"
                )


def test_ci_dependency_resolution_is_locked_and_cache_free() -> None:
    workflow = _workflow("ci.yml")

    assert "-latest" not in workflow
    assert 'version: "0.12.3"' in workflow
    assert "enable-cache: false" in workflow
    assert "uv sync --extra test --extra lab --locked" in workflow
    assert "uv sync --extra test --extra build --locked" in workflow
    assert workflow.count("uv run --frozen") >= 8


def test_pypi_manifest_pins_the_verified_release() -> None:
    manifest = json.loads((ROOT / ".github" / "pypi-publish.json").read_text())

    assert manifest == {
        "schema_version": 1,
        "project": "geometric-function-atlas",
        "tag": "v0.6.0",
        "commit": RELEASE_COMMIT,
        "assets": RELEASE_ASSETS,
    }


def test_pypi_workflow_is_fail_closed_to_the_frozen_manifest() -> None:
    workflow = _workflow("publish-pypi.yml")
    verify_block, publish_block = workflow.split("\n  publish:\n", maxsplit=1)

    assert "workflow_dispatch:" in workflow
    assert "inputs:" not in workflow
    assert "needs: verify" in publish_block
    assert workflow.count("id-token: write") == 1
    assert "id-token: write" not in verify_block
    assert "name: pypi" in publish_block
    assert "ubuntu-24.04" in workflow
    assert 'python-version: "3.12.13"' in workflow
    assert 'version: "0.12.3"' in workflow
    assert "enable-cache: false" in workflow
    assert "uv sync --extra build --locked" in verify_block
    assert verify_block.count("uv run --frozen") >= 2
    assert "git ls-remote --tags" in verify_block
    assert 'refs/tags/$RELEASE_TAG^{}' in verify_block
    assert 'refs/tags/$RELEASE_TAG"' in verify_block
    assert 'test "$tag_commit" = "$RELEASE_COMMIT"' in verify_block
    assert "RELEASE_COMMIT: ${{ steps.manifest.outputs.commit }}" in verify_block
    assert "isDraft or .isPrerelease" in verify_block

    manifest_text = (ROOT / ".github" / "pypi-publish.json").read_text()
    for asset in RELEASE_ASSETS.values():
        assert asset["name"] in manifest_text
        assert asset["sha256"] in manifest_text

    verify_digest_checks = [
        'printf \'%s  %s\\n\' "$WHEEL_SHA" "dist/$WHEEL_NAME" | sha256sum -c -',
        'printf \'%s  %s\\n\' "$SDIST_SHA" "dist/$SDIST_NAME" | sha256sum -c -',
        'printf \'%s  %s\\n\' "$CHECKSUMS_SHA" "dist/$CHECKSUMS_NAME" | sha256sum -c -',
    ]
    for check in verify_digest_checks:
        assert verify_block.count(check) == 1
        assert verify_block.index(check) < verify_block.index("twine check")

    assert "WHEEL_SHA: ${{ needs.verify.outputs.wheel_sha }}" in publish_block
    assert "SDIST_SHA: ${{ needs.verify.outputs.sdist_sha }}" in publish_block
    publish_digest_checks = verify_digest_checks[:2]
    for check in publish_digest_checks:
        assert publish_block.count(check) == 1
        assert publish_block.index(check) < publish_block.index("uv publish")

    assert "uv publish --trusted-publishing always" in publish_block
    assert "PYPI_API_TOKEN" not in workflow
    assert "UV_PUBLISH_TOKEN" not in workflow
    assert "TWINE_PASSWORD" not in workflow
