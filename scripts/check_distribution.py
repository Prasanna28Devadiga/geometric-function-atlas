"""Check that built archives contain only the intended public package surface."""

from __future__ import annotations

import sys
import tarfile
import zipfile
from pathlib import Path


def _assert_common(names: list[str], *, archive: Path) -> None:
    joined = "\n".join(names)
    assert not any("gft_registry" in name for name in names), (
        f"{archive.name} contains the old import package"
    )
    assert not any(name.endswith(('.db', '.sqlite', '.env')) for name in names), (
        f"{archive.name} contains a private/data artifact"
    )
    assert "geometric_function_atlas/py.typed" in joined, (
        f"{archive.name} is missing py.typed"
    )


def check_wheel(archive: Path) -> None:
    with zipfile.ZipFile(archive) as handle:
        names = handle.namelist()
        metadata = next(
            handle.read(name).decode("utf-8")
            for name in names
            if name.endswith(".dist-info/METADATA")
        )
        entry_points = next(
            handle.read(name).decode("utf-8")
            for name in names
            if name.endswith(".dist-info/entry_points.txt")
        )
    _assert_common(names, archive=archive)
    assert "Name: geometric-function-atlas" in metadata
    assert "geometric-function-atlas = geometric_function_atlas.cli:main" in entry_points


def check_sdist(archive: Path) -> None:
    with tarfile.open(archive, "r:gz") as handle:
        names = handle.getnames()
    _assert_common(names, archive=archive)
    assert any(name.endswith("/src/geometric_function_atlas/__init__.py") for name in names)


def main() -> int:
    directory = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("dist")
    wheels = sorted(directory.glob("*.whl"))
    sdists = sorted(directory.glob("*.tar.gz"))
    assert len(wheels) == 1, f"expected one wheel in {directory}, found {len(wheels)}"
    assert len(sdists) == 1, f"expected one sdist in {directory}, found {len(sdists)}"
    check_wheel(wheels[0])
    check_sdist(sdists[0])
    print(f"distribution contents: PASS ({wheels[0].name}, {sdists[0].name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())