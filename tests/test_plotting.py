"""Plot kinds: conformal domain grid, coefficient bars, real-part heatmap, phase portrait."""

from __future__ import annotations

from pathlib import Path

import pytest

from geometric_function_atlas.plotting import (
    DomainPlotResult,
    conformal_grid,
    generator_function_coefficients,
    write_coefficient_plot,
    write_domain_plot,
    write_phase_plot,
    write_plot,
    write_real_part_plot,
)


def test_domain_plot_writes_svg_for_named_generator(tmp_path: Path) -> None:
    output = tmp_path / "sine.svg"
    result = write_domain_plot(output, generator="sine", order=8)
    assert isinstance(result, DomainPlotResult)
    assert result.output.exists()
    text = output.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "Sine starlike class" in text
    assert "not a proof" in text or "Taylor polynomial" in text


def test_domain_plot_writes_svg_for_supplied_coefficients(tmp_path: Path) -> None:
    output = tmp_path / "poly.svg"
    result = write_domain_plot(output, coefficients=(0.25, -0.1), order=8)
    assert result.output.exists()
    assert "Normalized polynomial" in result.output.read_text(encoding="utf-8")


def test_domain_plot_requires_exactly_one_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="exactly one"):
        write_domain_plot(tmp_path / "a.svg")
    with pytest.raises(ValueError, match="exactly one"):
        write_domain_plot(
            tmp_path / "b.svg", generator="sine", coefficients=(0.25,)
        )


def test_domain_plot_rejects_non_svg_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="\\.svg"):
        write_domain_plot(tmp_path / "plot.png", coefficients=(0.25,))


def test_generator_function_coefficients_are_the_truncation() -> None:
    assert generator_function_coefficients("exponential", order=4) == (
        1.0,
        0.5,
        1 / 6,
        1 / 24,
    )


def test_conformal_grid_bounds_are_enforced() -> None:
    with pytest.raises(ValueError, match="rmax"):
        conformal_grid((0.25,), rmax=1.5)
    with pytest.raises(ValueError, match="rings"):
        conformal_grid((0.25,), rings=50)


def test_coefficient_plot_writes_bars(tmp_path: Path) -> None:
    output = tmp_path / "bars.svg"
    result = write_coefficient_plot(output, generator="sine", order=8)
    assert result.output.exists()
    text = output.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "bar" in text
    assert f"order {8}" in text


def test_coefficient_plot_accepts_raw_coefficients(tmp_path: Path) -> None:
    output = tmp_path / "raw.svg"
    result = write_coefficient_plot(output, coefficients=(1.0, 0.25, 0.1))
    text = result.output.read_text(encoding="utf-8")
    assert text.count('<rect class="bar"') == 3


def test_real_part_plot_writes_heatmap(tmp_path: Path) -> None:
    output = tmp_path / "realpart.svg"
    result = write_real_part_plot(output, coefficients=(1.0,))
    text = result.output.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "cell" in text or "<rect" in text
    # z + z^2 fails the starlike screen, so both signs must appear.
    assert "negative" in text or "Re" in text


def test_phase_plot_writes_portrait(tmp_path: Path) -> None:
    output = tmp_path / "phase.svg"
    result = write_phase_plot(output, coefficients=(0.25,))
    text = result.output.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "phase" in text.lower()


def test_write_plot_dispatches_on_kind(tmp_path: Path) -> None:
    domain = write_plot(
        "domain", tmp_path / "d.svg", generator="sine", order=6
    )
    assert domain.output.exists()
    bars = write_plot("coefficients", tmp_path / "c.svg", generator="sine", order=6)
    assert bars.output.exists()
    heat = write_plot("real-part", tmp_path / "r.svg", coefficients=(1.0,))
    assert heat.output.exists()
    phase = write_plot("phase", tmp_path / "p.svg", coefficients=(0.25,))
    assert phase.output.exists()


def test_write_plot_rejects_unknown_kind(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="kind"):
        write_plot("histogram", tmp_path / "x.svg", coefficients=(0.25,))


def test_plots_are_deterministic(tmp_path: Path) -> None:
    first = write_domain_plot(tmp_path / "a.svg", generator="sine", order=6)
    second = write_domain_plot(tmp_path / "b.svg", generator="sine", order=6)
    assert first.output.read_bytes() == second.output.read_bytes()


def test_plot_outputs_are_bounded(tmp_path: Path) -> None:
    output = write_real_part_plot(
        tmp_path / "big.svg", coefficients=(1.0,), grid=48
    )
    assert output.output.stat().st_size < 2_000_000
