from __future__ import annotations

import struct

from geometric_function_atlas.plotting import (
    write_plot,
    write_png_plot,
    write_tikz_plot,
)


def test_domain_plot_supports_website_tikz_export(tmp_path) -> None:
    output = tmp_path / "domain.tikz"
    result = write_tikz_plot(output, generator="starlike", samples=24, rings=2, spokes=3)

    assert result.output == output
    assert "\\begin{tikzpicture}" in output.read_text(encoding="utf-8")
    assert "\\draw" in output.read_text(encoding="utf-8")


def test_domain_plot_supports_dependency_free_png_export(tmp_path) -> None:
    output = tmp_path / "domain.png"
    result = write_png_plot(output, coefficients=(1.0,), width=96, height=80, samples=24)

    assert result.output == output
    assert output.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", output.read_bytes()[16:24])
    assert (width, height) == (96, 80)


def test_write_plot_selects_export_from_domain_suffix(tmp_path) -> None:
    output = tmp_path / "domain.tikz"
    write_plot("domain", output, coefficients=(1.0,), samples=24, rings=1, spokes=1)

    assert output.exists()
