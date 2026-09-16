"""Plot-object selector: generator ``phi``, normalized ``z*phi``, extremal ``f_phi``.

These three named-generator plot objects are genuinely different functions
(with different constant terms), so the plotting API computes the finite Taylor
polynomial of the selected object and labels every output with it. The legacy
no-selector behavior stays ``z*phi`` and existing assets remain byte-identical.
"""

from __future__ import annotations

import struct
import subprocess
import sys
import zlib
from pathlib import Path
from xml.etree import ElementTree

import pytest
import sympy as sp

import geometric_function_atlas as gfa
from geometric_function_atlas.plotting import (
    PLOT_OBJECTS,
    DomainPlotResult,
    conformal_grid,
    plot_object_coefficients,
    resolve_plot_object,
    write_coefficient_plot,
    write_domain_plot,
    write_phase_plot,
    write_plot,
    write_png_plot,
    write_real_part_plot,
    write_tikz_plot,
)

ROOT = Path(__file__).resolve().parents[1]
SVG_NS = "{http://www.w3.org/2000/svg}"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "geometric_function_atlas", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def _svg_title(path: Path) -> str:
    root = ElementTree.parse(path).getroot()
    element = root.find(f"{SVG_NS}title")
    return "" if element is None or element.text is None else element.text


def _svg_desc(path: Path) -> str:
    root = ElementTree.parse(path).getroot()
    element = root.find(f"{SVG_NS}desc")
    return "" if element is None or element.text is None else element.text


def _exact(values: tuple[sp.Expr, ...]) -> tuple[sp.Expr, ...]:
    return tuple(sp.simplify(value) for value in values)


def _stem(key: str) -> str:
    return key.replace("*", "_")


def _png_pixel(path: Path, x: int, y: int) -> tuple[int, int, int]:
    payload = path.read_bytes()
    offset = 8
    width = 0
    idat = bytearray()
    while offset < len(payload):
        length = struct.unpack(">I", payload[offset:offset + 4])[0]
        kind = payload[offset + 4:offset + 8]
        chunk = payload[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width = struct.unpack(">I", chunk[:4])[0]
        elif kind == b"IDAT":
            idat.extend(chunk)
        elif kind == b"IEND":
            break
    rows = zlib.decompress(bytes(idat))
    stride = 1 + width * 3
    assert rows[y * stride] == 0
    start = y * stride + 1 + x * 3
    pixel = rows[start:start + 3]
    return pixel[0], pixel[1], pixel[2]


def _export_bounds(
    result: DomainPlotResult,
    *,
    rings: int,
    spokes: int,
    samples: int,
    per_axis_margin: bool,
) -> tuple[float, float, float, float]:
    """Recompute the data bounds a domain export used for its own sampling.

    Mirrors the writers: the SVG pads each axis by 6 % of its own span, while
    the PNG and TikZ exports pad uniformly by 6 % of the larger span (floored
    at 1 unit).  Used to place the mapped domain origin independently.
    """

    grid = conformal_grid(
        result.coefficients,
        constant=result.constant,
        linear=result.linear,
        rings=rings,
        spokes=spokes,
        samples=samples,
    )
    points = [point for curve in (*grid.rings, *grid.spokes) for point in curve]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if per_axis_margin:
        span_x = xmax - xmin or 1.0
        span_y = ymax - ymin or 1.0
        xmin, xmax = xmin - 0.06 * span_x, xmax + 0.06 * span_x
        ymin, ymax = ymin - 0.06 * span_y, ymax + 0.06 * span_y
    else:
        margin = 0.06 * max(xmax - xmin, ymax - ymin, 1.0)
        xmin, xmax = xmin - margin, xmax + margin
        ymin, ymax = ymin - margin, ymax + margin
    return xmin, xmax, ymin, ymax


def test_plot_objects_selector_is_closed() -> None:
    assert PLOT_OBJECTS == ("phi", "z*phi", "f_phi")
    for key in PLOT_OBJECTS:
        assert resolve_plot_object(key) == key
    assert resolve_plot_object(None) == "z*phi"
    with pytest.raises(ValueError, match="phi"):
        resolve_plot_object("normalized")


def test_normalized_polynomial_is_not_an_accepted_selector(tmp_path: Path) -> None:
    """The supplied-polynomial metadata value must not become a selector."""

    with pytest.raises(ValueError, match="plot object"):
        resolve_plot_object("normalized_polynomial")
    with pytest.raises(ValueError, match="plot object"):
        write_domain_plot(
            tmp_path / "rejected.svg",
            generator="sine",
            object="normalized_polynomial",
        )


def test_exponential_objects_have_distinct_exact_polynomials() -> None:
    phi = plot_object_coefficients("exponential", object="phi", order=3)
    zphi = plot_object_coefficients("exponential", object="z*phi", order=3)
    fphi = plot_object_coefficients("exponential", object="f_phi", order=3)

    assert _exact(phi) == (
        sp.Integer(1),
        sp.Integer(1),
        sp.Rational(1, 2),
        sp.Rational(1, 6),
    )
    assert _exact(zphi) == (
        sp.Integer(0),
        sp.Integer(1),
        sp.Integer(1),
        sp.Rational(1, 2),
        sp.Rational(1, 6),
    )
    assert _exact(fphi) == (
        sp.Integer(0),
        sp.Integer(1),
        sp.Integer(1),
        sp.Rational(3, 4),
        sp.Rational(17, 36),
    )
    assert _exact(plot_object_coefficients("exponential", order=3)) == _exact(zphi)


def test_f_phi_object_keeps_exact_algebraic_coefficients() -> None:
    coefficients = plot_object_coefficients("limacon_0.707", object="f_phi", order=3)

    assert not any(isinstance(value, sp.Float) for value in coefficients)
    assert sp.simplify(coefficients[2] ** 2 - 2) == 0


def test_caller_generator_supports_all_three_plot_objects(tmp_path: Path) -> None:
    alpha = sp.Rational(1, 4)
    custom = gfa.Generator(
        key="order_quarter",
        name="Starlike of order 1/4",
        expression=(1 + (1 - 2 * alpha) * gfa.z) / (1 - gfa.z),
        citation="Caller-specified family: alpha = 1/4",
    )

    assert _exact(plot_object_coefficients(custom, object="phi", order=3)) == (
        sp.Integer(1),
        sp.Rational(3, 2),
        sp.Rational(3, 2),
        sp.Rational(3, 2),
    )
    assert _exact(plot_object_coefficients(custom, object="f_phi", order=3)) == (
        sp.Integer(0),
        sp.Integer(1),
        sp.Rational(3, 2),
        sp.Rational(15, 8),
        sp.Rational(35, 16),
    )

    results = {
        key: write_domain_plot(
            tmp_path / f"{_stem(key)}.svg",
            generator=custom,
            object=key,
            order=3,
        )
        for key in PLOT_OBJECTS
    }
    assert len({result.output.read_bytes() for result in results.values()}) == 3
    assert all(
        result.generator is not None
        and result.generator.startswith("user:order_quarter:")
        for result in results.values()
    )
    assert "Starlike of order 1/4" in _svg_title(results["phi"].output)


def test_writers_reject_unknown_object(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="plot object"):
        write_domain_plot(tmp_path / "x.svg", generator="sine", object="normalized")


def test_object_selector_requires_named_generator(tmp_path: Path) -> None:
    for key in PLOT_OBJECTS:
        with pytest.raises(ValueError, match="object selector"):
            write_domain_plot(tmp_path / f"{_stem(key)}.svg", coefficients=(1.0,), object=key)
    with pytest.raises(ValueError, match="object selector"):
        write_coefficient_plot(tmp_path / "bars.svg", coefficients=(1.0,), object="phi")


def test_supplied_coefficients_report_arbitrary_normalized_polynomial(tmp_path: Path) -> None:
    result = write_domain_plot(tmp_path / "custom.svg", coefficients=(0.25,))

    assert result.generator is None
    assert result.object == "normalized_polynomial"
    assert _svg_title(result.output) == "Normalized polynomial: image of the disk"


def test_cli_supplied_coefficients_report_arbitrary_normalized_polynomial(
    tmp_path: Path,
) -> None:
    completed = run_cli(
        "plot",
        "--coefficients",
        "0.25",
        "--output",
        str(tmp_path / "custom.svg"),
    )

    assert completed.returncode == 0, completed.stderr
    assert "Object: normalized_polynomial" in completed.stdout


def test_cli_rejects_normalized_polynomial_selector(tmp_path: Path) -> None:
    output = tmp_path / "bogus.svg"
    completed = run_cli(
        "plot",
        "domain",
        "sine",
        "--object",
        "normalized_polynomial",
        "--output",
        str(output),
    )

    assert completed.returncode == 2
    assert "plot object" in completed.stderr
    assert not output.exists()


def test_supplied_coefficients_report_normalized_polynomial_in_every_kind(
    tmp_path: Path,
) -> None:
    results = (
        write_domain_plot(tmp_path / "domain.svg", coefficients=(0.25,)),
        write_coefficient_plot(tmp_path / "bars.svg", coefficients=(0.25,)),
        write_real_part_plot(tmp_path / "real-part.svg", coefficients=(0.25,), grid=16),
        write_phase_plot(tmp_path / "phase.svg", coefficients=(0.25,), grid=16),
    )

    for result in results:
        assert result.object == "normalized_polynomial"
        assert result.generator is None
        assert result.constant == 0.0
        assert result.linear == 1.0


def test_object_selector_is_rejected_without_a_generator(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires a named generator"):
        write_domain_plot(tmp_path / "empty.svg", object="phi")


def test_domain_plot_metadata_selects_object(tmp_path: Path) -> None:
    expected = {
        "z*phi": (0.0, 1.0, (1.0, 0.5, 1.0 / 6.0)),
        "phi": (1.0, 1.0, (0.5, 1.0 / 6.0)),
        "f_phi": (0.0, 1.0, (1.0, 0.75, 17.0 / 36.0)),
    }
    descriptions = {}
    for key, (constant, linear, coefficients) in expected.items():
        result = write_domain_plot(
            tmp_path / f"{_stem(key)}.svg",
            generator="exponential",
            object=key,
            order=3,
        )
        assert result.object == key
        assert result.constant == pytest.approx(constant)
        assert result.linear == pytest.approx(linear)
        assert result.coefficients == pytest.approx(coefficients)
        descriptions[key] = _svg_desc(result.output)
        assert "Taylor order 3" in descriptions[key]

    assert descriptions["z*phi"].startswith("f(z) = z*phi(z), Taylor order 3")
    assert descriptions["phi"].startswith("phi(z) = 1 + B_1*z")
    assert descriptions["f_phi"].startswith("f_phi(z) = z*exp")
    assert len(set(descriptions.values())) == 3


def test_domain_plots_of_the_three_objects_differ(tmp_path: Path) -> None:
    outputs = {
        key: write_domain_plot(
            tmp_path / f"{_stem(key)}.svg",
            generator="exponential",
            object=key,
            order=3,
        ).output
        for key in PLOT_OBJECTS
    }

    assert len({path.read_bytes() for path in outputs.values()}) == 3


def test_phi_svg_marks_the_image_of_domain_origin(tmp_path: Path) -> None:
    result = write_domain_plot(
        tmp_path / "phi.svg",
        generator="exponential",
        object="phi",
        order=3,
        rings=1,
        spokes=0,
        samples=24,
    )
    root = ElementTree.parse(result.output).getroot()
    marker = root.find(f"{SVG_NS}circle[@class='origin']")
    assert marker is not None

    xmin, xmax, ymin, ymax = _export_bounds(
        result, rings=1, spokes=0, samples=24, per_axis_margin=True
    )
    scale = min((900 - 84) / (xmax - xmin), (700 - 88 - 42) / (ymax - ymin))
    cx, cy = (xmin + xmax) / 2.0, (ymin + ymax) / 2.0
    map_x = lambda x: 450 + (x - cx) * scale
    map_y = lambda y: 88 + (700 - 88 - 42) / 2 - (y - cy) * scale

    assert float(marker.attrib["cx"]) == pytest.approx(map_x(result.constant), abs=1e-3)
    assert float(marker.attrib["cy"]) == pytest.approx(map_y(0.0), abs=1e-3)
    assert float(marker.attrib["cx"]) != pytest.approx(map_x(0.0), abs=1e-3)


def test_svg_origin_marker_sits_on_the_spoke_origin_for_every_object(
    tmp_path: Path,
) -> None:
    """Every sampled spoke starts at P(0), so the marker must sit there too.

    A geometry invariant rather than a copied transform: it fails whenever the
    marker is drawn elsewhere (for ``phi`` the constant term is 1, so
    image-plane 0 is not the image of the domain origin).
    """

    for key in PLOT_OBJECTS:
        result = write_domain_plot(
            tmp_path / f"{_stem(key)}.svg",
            generator="exponential",
            object=key,
            order=3,
        )
        root = ElementTree.parse(result.output).getroot()
        marker = root.find(f"{SVG_NS}circle[@class='origin']")
        spoke = root.find(f"{SVG_NS}path[@class='grid']")
        assert marker is not None and spoke is not None
        start = spoke.attrib["d"].split()
        assert start[0] == "M"
        assert float(marker.attrib["cx"]) == pytest.approx(float(start[1]), abs=1e-3)
        assert float(marker.attrib["cy"]) == pytest.approx(float(start[2]), abs=1e-3)


def test_generic_grid_path_supports_constant_and_linear_coefficients() -> None:
    legacy = conformal_grid((0.5,), rmax=0.5, rings=1, spokes=1, samples=48)
    assert legacy.rings[0][0] == pytest.approx((0.625, 0.0))

    shifted = conformal_grid(
        (2.0,), constant=1.0, linear=2.0, rmax=0.5, rings=1, spokes=1, samples=48
    )
    assert shifted.rings[0][0] == pytest.approx((2.5, 0.0))


@pytest.mark.parametrize(
    ("constant", "linear"),
    ((float("nan"), 1.0), (float("inf"), 1.0), (0.0, float("nan")), (0.0, float("inf"))),
)
def test_generic_grid_rejects_nonfinite_constant_and_linear(
    constant: float, linear: float
) -> None:
    with pytest.raises(ValueError, match="finite"):
        conformal_grid((0.5,), constant=constant, linear=linear)


def test_starlike_generator_phi_has_linear_coefficient_two(tmp_path: Path) -> None:
    result = write_domain_plot(
        tmp_path / "starlike-phi.svg", generator="starlike", object="phi", order=3
    )

    assert result.constant == 1.0
    assert result.linear == pytest.approx(2.0)
    assert result.coefficients == pytest.approx((2.0, 2.0))


def test_legacy_domain_default_matches_checked_in_asset(tmp_path: Path) -> None:
    result = write_plot("domain", tmp_path / "sine-domain.svg", generator="sine", order=12)

    assert result.output.read_bytes() == (ROOT / "docs/assets/sine-domain.svg").read_bytes()


def test_legacy_supplied_coefficients_match_checked_in_asset(tmp_path: Path) -> None:
    result = write_plot(
        "domain", tmp_path / "polynomial.svg", coefficients=(1.0, -0.25)
    )

    assert result.output.read_bytes() == (ROOT / "docs/assets/polynomial.svg").read_bytes()


def test_legacy_domain_labels_are_unchanged(tmp_path: Path) -> None:
    result = write_domain_plot(tmp_path / "sine.svg", generator="sine", order=8)

    assert _svg_title(result.output) == "Sine starlike class: image of the disk"
    assert _svg_desc(result.output) == (
        "f(z) = z*phi(z), Taylor order 8; r = 0.98. Concentric circles and radial "
        "spokes are mapped by the displayed Taylor polynomial."
    )


def test_explicit_zphi_selector_is_byte_identical_to_legacy_default(tmp_path: Path) -> None:
    default = write_domain_plot(tmp_path / "default.svg", generator="sine", order=8)
    explicit = write_domain_plot(
        tmp_path / "explicit.svg", generator="sine", order=8, object="z*phi"
    )

    assert default.output.read_bytes() == explicit.output.read_bytes()
    assert default.object == explicit.object == "z*phi"


def test_legacy_coefficient_labels_are_unchanged(tmp_path: Path) -> None:
    result = write_coefficient_plot(tmp_path / "bars.svg", generator="sine", order=8)

    assert result.object == "z*phi"
    assert _svg_desc(result.output) == (
        "f(z) = z*phi(z), Taylor order 8; bars show |a_n| for n = 2..9. "
        "Coefficient magnitudes of the displayed Taylor polynomial."
    )


def test_legacy_real_part_and_phase_labels_are_unchanged(tmp_path: Path) -> None:
    real_part = write_real_part_plot(tmp_path / "rp.svg", generator="sine", grid=16)
    phase = write_phase_plot(tmp_path / "phase.svg", generator="sine", grid=16)

    assert _svg_desc(real_part.output) == (
        "f(z) = z*phi(z), Taylor order 12; sampled Re(z f'(z) / f(z)) on |z| <= 0.98 "
        "(red = negative, blue = positive). Numerical screen, not a proof."
    )
    assert _svg_desc(phase.output) == (
        "f(z) = z*phi(z), Taylor order 12; hue = arg f(z) on |z| <= 0.98. "
        "Empirical visualization, not a proof."
    )


def test_legacy_tikz_header_is_unchanged(tmp_path: Path) -> None:
    result = write_tikz_plot(
        tmp_path / "domain.tikz", generator="sine", order=4, samples=96, rings=2, spokes=3
    )
    lines = result.output.read_text(encoding="utf-8").splitlines()

    assert lines[0] == "\\begin{tikzpicture}"
    assert lines[1] == (
        "  % conformal grid: image of the disk under the displayed polynomial"
    )
    assert any("% f(0)=0" in line for line in lines)


def test_legacy_tikz_origin_marker_line_is_unchanged(tmp_path: Path) -> None:
    exports = (
        write_tikz_plot(
            tmp_path / "zphi.tikz",
            generator="exponential",
            order=3,
            samples=96,
            rings=2,
            spokes=3,
        ),
        write_tikz_plot(
            tmp_path / "fphi.tikz",
            generator="exponential",
            object="f_phi",
            order=3,
            samples=96,
            rings=2,
            spokes=3,
        ),
        write_tikz_plot(
            tmp_path / "supplied.tikz",
            coefficients=(0.25,),
            samples=96,
            rings=2,
            spokes=3,
        ),
    )

    for export in exports:
        assert (
            "  \\fill (0,0) circle (1.2pt);  % f(0)=0"
            in export.output.read_text(encoding="utf-8")
        )


def test_explicit_zphi_selector_is_byte_identical_across_domain_exports(
    tmp_path: Path,
) -> None:
    svg = (
        write_domain_plot(tmp_path / "a.svg", generator="exponential", order=4),
        write_domain_plot(
            tmp_path / "b.svg", generator="exponential", order=4, object="z*phi"
        ),
    )
    tikz = (
        write_tikz_plot(
            tmp_path / "a.tikz",
            generator="exponential",
            order=4,
            samples=96,
            rings=2,
            spokes=3,
        ),
        write_tikz_plot(
            tmp_path / "b.tikz",
            generator="exponential",
            order=4,
            samples=96,
            rings=2,
            spokes=3,
            object="z*phi",
        ),
    )
    png = (
        write_png_plot(
            tmp_path / "a.png",
            generator="exponential",
            order=4,
            width=96,
            height=80,
            samples=48,
            rings=1,
            spokes=1,
        ),
        write_png_plot(
            tmp_path / "b.png",
            generator="exponential",
            order=4,
            width=96,
            height=80,
            samples=48,
            rings=1,
            spokes=1,
            object="z*phi",
        ),
    )

    for default, explicit in (svg, tikz, png):
        assert default.output.read_bytes() == explicit.output.read_bytes()
        assert default.object == explicit.object == "z*phi"


def test_coefficient_bars_follow_the_selected_object(tmp_path: Path) -> None:
    legacy = write_coefficient_plot(tmp_path / "legacy.svg", generator="exponential", order=3)
    phi = write_coefficient_plot(
        tmp_path / "phi.svg", generator="exponential", object="phi", order=3
    )
    f_phi = write_coefficient_plot(
        tmp_path / "fphi.svg", generator="exponential", object="f_phi", order=3
    )

    assert legacy.object == "z*phi"
    assert _svg_desc(legacy.output).endswith(
        "bars show |a_n| for n = 2..4. Coefficient magnitudes of the displayed "
        "Taylor polynomial."
    )

    assert phi.object == "phi"
    phi_desc = _svg_desc(phi.output)
    assert "phi(z) = 1 + B_1*z" in phi_desc
    assert "bars show |B_n| for n = 1..3" in phi_desc
    assert phi.output.read_text(encoding="utf-8").count('<rect class="bar"') == 3

    assert f_phi.object == "f_phi"
    f_phi_desc = _svg_desc(f_phi.output)
    assert "f_phi(z) = z*exp" in f_phi_desc
    assert "bars show |a_n| for n = 2..4" in f_phi_desc

    assert len({_svg_desc(path) for path in
                (legacy.output, phi.output, f_phi.output)}) == 3


def test_real_part_and_phase_plots_name_the_object(tmp_path: Path) -> None:
    phi = write_real_part_plot(
        tmp_path / "phi-rp.svg", generator="exponential", object="phi", grid=16
    )
    f_phi = write_real_part_plot(
        tmp_path / "fphi-rp.svg", generator="exponential", object="f_phi", grid=16
    )
    phase = write_phase_plot(
        tmp_path / "phi-phase.svg", generator="exponential", object="phi", grid=16
    )

    assert "phi(z) = 1 + B_1*z" in _svg_desc(phi.output)
    assert "Re(z phi'(z) / phi(z))" in _svg_desc(phi.output)
    assert "f_phi(z) = z*exp" in _svg_desc(f_phi.output)
    assert "arg phi(z)" in _svg_desc(phase.output)


def test_tikz_export_names_non_default_object(tmp_path: Path) -> None:
    result = write_tikz_plot(
        tmp_path / "phi.tikz",
        generator="exponential",
        object="phi",
        order=3,
        samples=96,
        rings=2,
        spokes=3,
    )
    text = result.output.read_text(encoding="utf-8")

    assert "% object: phi;" in text
    assert "phi(z) = 1 + B_1*z" in text
    assert "Taylor order 3" in text
    assert "% phi(0)=1" in text
    assert result.object == "phi"
    assert result.constant == 1.0

    grid = conformal_grid(
        result.coefficients,
        constant=result.constant,
        linear=result.linear,
        rings=2,
        spokes=3,
        samples=96,
    )
    points = [point for curve in (*grid.rings, *grid.spokes) for point in curve]
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    margin = 0.06 * max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    xmin, xmax = min(xs) - margin, max(xs) + margin
    ymin, ymax = min(ys) - margin, max(ys) + margin
    scale = 5.8 / max(xmax - xmin, ymax - ymin)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    expected_origin = (
        f"({(result.constant - cx) * scale:.3f},{(0.0 - cy) * scale:.3f})"
    )
    assert f"\\fill {expected_origin} circle" in text
    assert "\\fill (0,0) circle" not in text


def test_png_export_metadata_selects_object(tmp_path: Path) -> None:
    legacy = write_png_plot(
        tmp_path / "legacy.png",
        generator="exponential",
        order=3,
        width=64,
        height=64,
        samples=48,
        rings=1,
        spokes=1,
    )
    phi = write_png_plot(
        tmp_path / "phi.png",
        generator="exponential",
        object="phi",
        order=3,
        width=64,
        height=64,
        samples=48,
        rings=1,
        spokes=1,
    )

    assert legacy.object == "z*phi"
    assert phi.object == "phi"
    assert phi.constant == 1.0
    assert phi.linear == 1.0
    assert phi.coefficients == pytest.approx((0.5, 1.0 / 6.0))
    assert legacy.output.read_bytes() != phi.output.read_bytes()


def test_phi_png_marks_the_image_of_domain_origin(tmp_path: Path) -> None:
    width, height = 96, 80
    result = write_png_plot(
        tmp_path / "phi.png",
        generator="exponential",
        object="phi",
        order=3,
        width=width,
        height=height,
        rings=1,
        spokes=0,
        samples=24,
    )
    xmin, xmax, ymin, ymax = _export_bounds(
        result, rings=1, spokes=0, samples=24, per_axis_margin=False
    )
    scale = min((width - 20) / (xmax - xmin), (height - 20) / (ymax - ymin))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    pixel = lambda x, y: (
        round(width / 2 + (x - cx) * scale),
        round(height / 2 - (y - cy) * scale),
    )
    mapped_origin = pixel(result.constant, 0.0)
    image_plane_zero = pixel(0.0, 0.0)

    assert mapped_origin != image_plane_zero
    assert _png_pixel(result.output, *mapped_origin) == (31, 41, 51)
    assert _png_pixel(result.output, *image_plane_zero) != (31, 41, 51)


def test_legacy_png_origin_marker_stays_at_the_image_of_zero(tmp_path: Path) -> None:
    """The legacy object keeps its marker at P(0) = 0, byte-compatible."""

    width, height = 96, 80
    result = write_png_plot(
        tmp_path / "zphi.png",
        generator="exponential",
        order=3,
        width=width,
        height=height,
        rings=1,
        spokes=0,
        samples=24,
    )

    assert result.object == "z*phi"
    xmin, xmax, ymin, ymax = _export_bounds(
        result, rings=1, spokes=0, samples=24, per_axis_margin=False
    )
    scale = min((width - 20) / (xmax - xmin), (height - 20) / (ymax - ymin))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    origin = (
        round(width / 2 + (0.0 - cx) * scale),
        round(height / 2 - (0.0 - cy) * scale),
    )

    assert _png_pixel(result.output, *origin) == (31, 41, 51)


def test_write_plot_dispatches_object_to_each_kind(tmp_path: Path) -> None:
    bars = write_plot(
        "coefficients", tmp_path / "bars.svg", generator="exponential", object="phi", order=3
    )
    real_part = write_plot(
        "real-part", tmp_path / "rp.svg", generator="exponential", object="f_phi", grid=16
    )
    phase = write_plot(
        "phase", tmp_path / "phase.svg", generator="exponential", object="phi", grid=16
    )
    png = write_plot(
        "domain",
        tmp_path / "domain.png",
        generator="exponential",
        object="f_phi",
        order=3,
        samples=48,
        rings=1,
        spokes=1,
    )

    assert bars.object == "phi"
    assert real_part.object == "f_phi"
    assert phase.object == "phi"
    assert png.object == "f_phi"


def test_cli_plot_object_selector_reports_the_object(tmp_path: Path) -> None:
    output = tmp_path / "phi.svg"
    completed = run_cli(
        "plot",
        "domain",
        "exponential",
        "--object",
        "phi",
        "--order",
        "3",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert "Object: phi" in completed.stdout
    text = output.read_text(encoding="utf-8")
    assert "phi(z) = 1 + B_1*z" in text
    assert "Taylor order 3" in text


def test_cli_plot_object_f_phi_computes_the_extremal(tmp_path: Path) -> None:
    output = tmp_path / "fphi.svg"
    completed = run_cli(
        "plot",
        "domain",
        "exponential",
        "--object",
        "f_phi",
        "--order",
        "3",
        "--output",
        str(output),
    )

    assert completed.returncode == 0, completed.stderr
    assert "Object: f_phi" in completed.stdout
    assert "f_phi(z) = z*exp" in output.read_text(encoding="utf-8")


def test_cli_legacy_forms_keep_the_z_phi_object(tmp_path: Path) -> None:
    convenience = tmp_path / "convenience.svg"
    explicit = tmp_path / "explicit.svg"
    named = tmp_path / "named.svg"

    first = run_cli("plot", "exponential", "--order", "3", "--output", str(convenience))
    second = run_cli(
        "plot", "domain", "exponential", "--order", "3", "--output", str(explicit)
    )
    third = run_cli(
        "plot",
        "domain",
        "exponential",
        "--object",
        "z*phi",
        "--order",
        "3",
        "--output",
        str(named),
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert third.returncode == 0, third.stderr
    assert "Object: z*phi" in first.stdout
    assert convenience.read_bytes() == explicit.read_bytes() == named.read_bytes()
    assert "f(z) = z*phi(z), Taylor order 3" in convenience.read_text(encoding="utf-8")


def test_cli_phi_and_zphi_plots_differ(tmp_path: Path) -> None:
    phi = tmp_path / "phi.svg"
    zphi = tmp_path / "zphi.svg"

    first = run_cli("plot", "domain", "exponential", "--object", "phi", "--output", str(phi))
    second = run_cli(
        "plot", "domain", "exponential", "--object", "z*phi", "--output", str(zphi)
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert phi.read_bytes() != zphi.read_bytes()


def test_cli_rejects_unknown_object(tmp_path: Path) -> None:
    output = tmp_path / "bogus.svg"
    completed = run_cli(
        "plot", "domain", "exponential", "--object", "normalized", "--output", str(output)
    )

    assert completed.returncode == 2
    assert "plot object" in completed.stderr
    assert not output.exists()


def test_cli_rejects_object_with_supplied_coefficients(tmp_path: Path) -> None:
    output = tmp_path / "conflict.svg"
    completed = run_cli(
        "plot",
        "--object",
        "phi",
        "--coefficients",
        "1,-0.25",
        "--output",
        str(output),
    )

    assert completed.returncode == 2
    assert "object selector" in completed.stderr
    assert not output.exists()


def test_cli_plot_help_documents_object_choices() -> None:
    completed = run_cli("plot", "--help")

    assert completed.returncode == 0
    for key in PLOT_OBJECTS:
        assert key in completed.stdout


def test_package_root_exposes_the_selector() -> None:
    import geometric_function_atlas as gfa

    assert gfa.PLOT_OBJECTS == PLOT_OBJECTS
    assert gfa.resolve_plot_object(None) == "z*phi"
    assert _exact(gfa.plot_object_coefficients("exponential", object="phi", order=2)) == (
        sp.Integer(1),
        sp.Integer(1),
        sp.Rational(1, 2),
    )


def test_readme_documents_the_three_plot_objects() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "sampled finite-truncation visualization" in readme
    assert "gfa plot domain exponential --object phi --output phi-domain.svg" in readme
    assert "gfa plot domain exponential --object 'z*phi' --output zphi-domain.svg" in readme
    assert "gfa plot domain exponential --object f_phi --output fphi-domain.svg" in readme
