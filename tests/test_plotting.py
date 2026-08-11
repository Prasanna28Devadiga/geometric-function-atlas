from __future__ import annotations

from pathlib import Path

import pytest

from geometric_function_atlas.plotting import (
    conformal_grid,
    generator_function_coefficients,
    write_domain_plot,
)


def test_generator_plot_coefficients_are_for_normalized_z_phi() -> None:
    assert generator_function_coefficients("sine", order=5) == pytest.approx(
        (1.0, 0.0, -1.0 / 6.0, 0.0, 1.0 / 120.0)
    )


def test_conformal_grid_preserves_origin_and_is_finite() -> None:
    grid = conformal_grid((1.0,), rmax=0.9, rings=3, spokes=4, samples=24)

    assert len(grid.rings) == 3
    assert len(grid.spokes) == 4
    assert grid.spokes[0][0] == (0.0, 0.0)
    assert all(
        abs(x) < 10 and abs(y) < 10
        for curve in (*grid.rings, *grid.spokes)
        for x, y in curve
    )


def test_write_domain_plot_creates_standalone_svg(tmp_path: Path) -> None:
    output = tmp_path / "sine-domain.svg"

    result = write_domain_plot(
        output,
        generator="sine",
        order=8,
        rmax=0.95,
        rings=5,
        spokes=12,
    )

    text = output.read_text(encoding="utf-8")
    assert result.output == output
    assert result.generator == "sine"
    assert result.approximation == "f(z) = z*phi(z), Taylor order 8"
    assert text.startswith("<svg")
    assert "Sine starlike class" in text
    assert "Taylor order 8" in text
    assert "<path" in text
    assert "nan" not in text.lower()
    assert "inf" not in text.lower()


def test_write_domain_plot_accepts_supplied_normalized_coefficients(
    tmp_path: Path,
) -> None:
    output = tmp_path / "polynomial.svg"

    result = write_domain_plot(output, coefficients=(1.0,), rmax=0.9)

    assert result.generator is None
    assert result.coefficients == (1.0,)
    assert "f(z) = z + a2*z^2 + ..." in result.approximation


def test_plot_validation_rejects_unsafe_or_ambiguous_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        write_domain_plot(tmp_path / "x.svg", generator="sine", coefficients=(1.0,))
    with pytest.raises(ValueError, match="inside the open unit disk"):
        write_domain_plot(tmp_path / "x.svg", generator="sine", rmax=1.0)
    with pytest.raises(ValueError, match=r"\.svg"):
        write_domain_plot(tmp_path / "x.png", generator="sine")
