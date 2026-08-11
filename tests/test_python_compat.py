from __future__ import annotations

from pathlib import Path


def test_snapshot_module_does_not_require_typing_self_on_python_310() -> None:
    source = (
        Path(__file__).parents[1] / "src" / "geometric_function_atlas" / "snapshot.py"
    ).read_text(encoding="utf-8")

    assert "from typing import Any, Self, cast" not in source
    assert "-> Self" not in source