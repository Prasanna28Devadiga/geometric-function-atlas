"""Dependency-free conformal-grid plots for normalized analytic functions."""

from __future__ import annotations

import binascii
import colorsys
import math
import struct
import zlib
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from xml.sax.saxutils import escape

from .catalog import get_generator
from .coefficients import taylor_coefficients

PLOT_KINDS: tuple[str, ...] = ("domain", "coefficients", "real-part", "phase")
_DISK_RMAX = 0.98


@dataclass(frozen=True)
class ConformalGrid:
    """Sampled images of concentric circles and radial spokes."""

    rings: tuple[tuple[tuple[float, float], ...], ...]
    spokes: tuple[tuple[tuple[float, float], ...], ...]


@dataclass(frozen=True)
class DomainPlotResult:
    """Metadata for a generated standalone SVG domain plot."""

    output: Path
    generator: str | None
    coefficients: tuple[float, ...]
    approximation: str


def generator_function_coefficients(generator: str, *, order: int) -> tuple[float, ...]:
    """Return coefficients of the truncation ``f(z)=z*phi(z)``.

    The returned tuple is ``(a2, a3, ...)``.  This is a visual approximation,
    not a proof about the full analytic image domain.
    """

    return tuple(float(value) for value in taylor_coefficients(generator, order=order))


def _evaluate_normalized_polynomial(
    coefficients: tuple[float, ...], z: complex
) -> complex:
    value = z
    power = z
    for coefficient in coefficients:
        power *= z
        value += coefficient * power
    return value


def _curve(
    coefficients: tuple[float, ...], points: tuple[complex, ...]
) -> tuple[tuple[float, float], ...]:
    return tuple(
        (float(value.real), float(value.imag))
        for value in (
            _evaluate_normalized_polynomial(coefficients, point) for point in points
        )
    )


def conformal_grid(
    coefficients: tuple[float, ...],
    *,
    rmax: float = 0.98,
    rings: int = 5,
    spokes: int = 12,
    samples: int = 480,
) -> ConformalGrid:
    """Sample the conformal grid used by the Atlas website's domain figures."""

    if not 0 < rmax < 1:
        raise ValueError("rmax must lie inside the open unit disk: 0 < rmax < 1")
    if not 1 <= rings <= 20:
        raise ValueError("rings must be between 1 and 20")
    if not 0 <= spokes <= 72:
        raise ValueError("spokes must be between 0 and 72")
    if not 24 <= samples <= 4096:
        raise ValueError("samples must be between 24 and 4096")
    if len(coefficients) > 64:
        raise ValueError("at most 64 supplied coefficients are supported")
    if not all(math.isfinite(value) for value in coefficients):
        raise ValueError("coefficients must be finite real numbers")

    ring_curves = []
    for index in range(1, rings + 1):
        radius = rmax * index / rings
        points = tuple(
            radius * complex(math.cos(theta), math.sin(theta))
            for theta in (2 * math.pi * step / samples for step in range(samples + 1))
        )
        ring_curves.append(_curve(coefficients, points))

    spoke_curves = []
    spoke_samples = max(24, samples // 4)
    for index in range(spokes):
        theta = 2 * math.pi * index / spokes
        direction = complex(math.cos(theta), math.sin(theta))
        points = tuple(
            rmax * step / spoke_samples * direction
            for step in range(spoke_samples + 1)
        )
        spoke_curves.append(_curve(coefficients, points))

    return ConformalGrid(rings=tuple(ring_curves), spokes=tuple(spoke_curves))


def _svg_path(
    curve: tuple[tuple[float, float], ...],
    *,
    map_x: object,
    map_y: object,
) -> str:
    x_transform = map_x
    y_transform = map_y
    if not callable(x_transform) or not callable(y_transform):
        raise TypeError("SVG coordinate transforms must be callable")
    return " ".join(
        f"{'M' if index == 0 else 'L'} {x_transform(x):.3f} {y_transform(y):.3f}"
        for index, (x, y) in enumerate(curve)
    )


def write_domain_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    rmax: float = 0.98,
    rings: int = 5,
    spokes: int = 12,
    samples: int = 480,
) -> DomainPlotResult:
    """Write a standalone SVG plot of ``f(D_rmax)``.

    Exactly one of ``generator`` and ``coefficients`` is required.  Named
    generators plot the Taylor truncation of ``f(z)=z*phi(z)``.  Supplied
    coefficients represent ``f(z)=z+a2*z^2+a3*z^3+...`` directly.
    """

    path = Path(output)
    if path.suffix.lower() != ".svg":
        raise ValueError("output must have the .svg extension")
    if (generator is None) == (coefficients is None):
        raise ValueError("provide exactly one of generator or coefficients")

    if generator is not None:
        definition = get_generator(generator)
        plot_coefficients = generator_function_coefficients(generator, order=order)
        title = f"{definition.name}: image of the disk"
        approximation = f"f(z) = z*phi(z), Taylor order {order}"
        generator_key: str | None = definition.key
    else:
        plot_coefficients = tuple(coefficients or ())
        title = "Normalized polynomial: image of the disk"
        approximation = "f(z) = z + a2*z^2 + ... (supplied finite polynomial)"
        generator_key = None

    grid = conformal_grid(
        plot_coefficients,
        rmax=rmax,
        rings=rings,
        spokes=spokes,
        samples=samples,
    )
    curves = (*grid.rings, *grid.spokes)
    xs = [x for curve in curves for x, _ in curve]
    ys = [y for curve in curves for _, y in curve]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    span_x = xmax - xmin or 1.0
    span_y = ymax - ymin or 1.0
    margin_x = 0.06 * span_x
    margin_y = 0.06 * span_y
    xmin, xmax = xmin - margin_x, xmax + margin_x
    ymin, ymax = ymin - margin_y, ymax + margin_y

    width, height, pad_top, pad_other = 900, 700, 88, 42
    plot_width = width - 2 * pad_other
    plot_height = height - pad_top - pad_other
    scale = min(plot_width / (xmax - xmin), plot_height / (ymax - ymin))
    center_x = (xmin + xmax) / 2
    center_y = (ymin + ymax) / 2
    map_x = lambda value: width / 2 + (value - center_x) * scale
    map_y = lambda value: pad_top + plot_height / 2 - (value - center_y) * scale

    spoke_paths = "\n".join(
        f'  <path class="grid" d="{_svg_path(curve, map_x=map_x, map_y=map_y)}"/>'
        for curve in grid.spokes
    )
    ring_paths = []
    for index, curve in enumerate(grid.rings):
        class_name = "boundary" if index == len(grid.rings) - 1 else "grid"
        ring_paths.append(
            f'  <path class="{class_name}" d="'
            f'{_svg_path(curve, map_x=map_x, map_y=map_y)}"/>'
        )

    subtitle = f"{approximation}; r = {rmax:g}"
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f"  <title id=\"title\">{escape(title)}</title>",
            f"  <desc id=\"desc\">{escape(subtitle)}. Concentric circles and radial spokes are mapped by the displayed Taylor polynomial.</desc>",
            "  <rect width=\"100%\" height=\"100%\" fill=\"#fbfaf7\"/>",
            "  <style>.grid{fill:none;stroke:#d8d3ca;stroke-width:1}.boundary{fill:none;stroke:#265d8f;stroke-width:2.6}.origin{fill:#1f2933}.title{font:600 24px system-ui,sans-serif;fill:#18212b}.subtitle{font:15px ui-monospace,monospace;fill:#5f6872}</style>",
            f'  <text class="title" x="42" y="36">{escape(title)}</text>',
            f'  <text class="subtitle" x="42" y="64">{escape(subtitle)}</text>',
            spoke_paths,
            *ring_paths,
            f'  <circle class="origin" cx="{map_x(0):.3f}" cy="{map_y(0):.3f}" r="3.2"/>',
            "</svg>",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return DomainPlotResult(
        output=path,
        generator=generator_key,
        coefficients=plot_coefficients,
        approximation=approximation,
    )


def _domain_plot_inputs(
    *,
    generator: str | None,
    coefficients: tuple[float, ...] | None,
    order: int,
    rmax: float,
    rings: int,
    spokes: int,
    samples: int,
) -> tuple[ConformalGrid, tuple[float, ...], str | None, str]:
    """Resolve shared domain-export inputs and geometry once."""

    if (generator is None) == (coefficients is None):
        raise ValueError("provide exactly one of generator or coefficients")
    if generator is not None:
        definition = get_generator(generator)
        values = generator_function_coefficients(generator, order=order)
        generator_key = definition.key
        approximation = f"f(z) = z*phi(z), Taylor order {order}"
    else:
        values = tuple(coefficients or ())
        generator_key = None
        approximation = "f(z) = z + a2*z^2 + ... (supplied finite polynomial)"
    return (
        conformal_grid(values, rmax=rmax, rings=rings, spokes=spokes, samples=samples),
        values,
        generator_key,
        approximation,
    )


def _domain_bounds(grid: ConformalGrid) -> tuple[float, float, float, float]:
    curves = (*grid.rings, *grid.spokes)
    points = [point for curve in curves for point in curve]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    margin = 0.06 * max(xmax - xmin, ymax - ymin, 1.0)
    return xmin - margin, xmax + margin, ymin - margin, ymax + margin


def write_tikz_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    rmax: float = _DISK_RMAX,
    rings: int = 5,
    spokes: int = 12,
    samples: int = 480,
) -> DomainPlotResult:
    """Write the website-compatible standalone TikZ conformal-grid export."""

    path = Path(output)
    if path.suffix.lower() not in {".tikz", ".tex"}:
        raise ValueError("output must have the .tikz or .tex extension")
    grid, values, generator_key, approximation = _domain_plot_inputs(
        generator=generator, coefficients=coefficients, order=order,
        rmax=rmax, rings=rings, spokes=spokes, samples=samples,
    )
    xmin, xmax, ymin, ymax = _domain_bounds(grid)
    scale = 5.8 / max(xmax - xmin, ymax - ymin)
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2

    def point(value: tuple[float, float]) -> str:
        x, y = value
        return f"({(x - cx) * scale:.3f},{(y - cy) * scale:.3f})"

    lines = [
        "\\begin{tikzpicture}",
        "  % conformal grid: image of the disk under the displayed polynomial",
    ]
    for curve in grid.spokes:
        lines.append("  \\draw[gray!40] plot coordinates {" + " ".join(map(point, curve)) + "};")
    for index, curve in enumerate(grid.rings):
        color = "blue!70!black" if index == len(grid.rings) - 1 else "gray!40"
        lines.append(f"  \\draw[{color}] plot coordinates {{" + " ".join(map(point, curve)) + "};")
    lines.extend(("  \\fill (0,0) circle (1.2pt);  % f(0)=0", "\\end{tikzpicture}", ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return DomainPlotResult(path, generator_key, values, approximation)


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload)) + kind + payload
        + struct.pack(">I", binascii.crc32(kind + payload) & 0xFFFFFFFF)
    )


def _write_rgb_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = b"".join(
        b"\x00" + bytes(pixels[row * width * 3:(row + 1) * width * 3])
        for row in range(height)
    )
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(rows, level=6))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def write_png_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    rmax: float = _DISK_RMAX,
    rings: int = 5,
    spokes: int = 12,
    samples: int = 480,
    width: int = 900,
    height: int = 700,
) -> DomainPlotResult:
    """Write a dependency-free PNG conformal-grid export."""

    path = Path(output)
    if path.suffix.lower() != ".png":
        raise ValueError("output must have the .png extension")
    if (
        isinstance(width, bool) or isinstance(height, bool)
        or not isinstance(width, int) or not isinstance(height, int)
        or not 16 <= width <= 4096 or not 16 <= height <= 4096
    ):
        raise ValueError("width and height must be integers between 16 and 4096")
    grid, values, generator_key, approximation = _domain_plot_inputs(
        generator=generator, coefficients=coefficients, order=order,
        rmax=rmax, rings=rings, spokes=spokes, samples=samples,
    )
    xmin, xmax, ymin, ymax = _domain_bounds(grid)
    scale = min((width - 20) / (xmax - xmin), (height - 20) / (ymax - ymin))
    cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
    pixels = bytearray([251, 250, 247] * (width * height))

    def pixel(value: tuple[float, float]) -> tuple[int, int]:
        x, y = value
        return round(width / 2 + (x - cx) * scale), round(height / 2 - (y - cy) * scale)

    def draw_line(start: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int]) -> None:
        x0, y0 = start
        x1, y1 = end
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for step in range(steps + 1):
            x = round(x0 + (x1 - x0) * step / steps)
            y = round(y0 + (y1 - y0) * step / steps)
            if 0 <= x < width and 0 <= y < height:
                offset = (y * width + x) * 3
                pixels[offset:offset + 3] = bytes(color)

    for curve in grid.spokes:
        for start, end in pairwise(curve):
            draw_line(pixel(start), pixel(end), (216, 211, 202))
    for index, curve in enumerate(grid.rings):
        color = (38, 93, 143) if index == len(grid.rings) - 1 else (216, 211, 202)
        for start, end in pairwise(curve):
            draw_line(pixel(start), pixel(end), color)
    origin = pixel((0.0, 0.0))
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if 0 <= origin[0] + dx < width and 0 <= origin[1] + dy < height:
                offset = ((origin[1] + dy) * width + origin[0] + dx) * 3
                pixels[offset:offset + 3] = bytes((31, 41, 51))
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_rgb_png(path, width, height, pixels)
    return DomainPlotResult(path, generator_key, values, approximation)


@dataclass(frozen=True)
class PlotResult:
    """Metadata for a generated SVG plot of any supported kind."""

    output: Path
    kind: str
    generator: str | None
    coefficients: tuple[float, ...]
    approximation: str


def _resolve_plot_inputs(
    generator: str | None,
    coefficients: tuple[float, ...] | None,
    order: int,
    *,
    label: str,
) -> tuple[tuple[float, ...], str, str | None, str]:
    """Resolve generator/coefficients into (coefficients, title, generator key, approximation)."""

    if (generator is None) == (coefficients is None):
        raise ValueError("provide exactly one of generator or coefficients")
    if generator is not None:
        definition = get_generator(generator)
        plot_coefficients = generator_function_coefficients(generator, order=order)
        title = f"{definition.name}: {label}"
        approximation = f"f(z) = z*phi(z), Taylor order {order}"
        return plot_coefficients, title, definition.key, approximation
    values = tuple(coefficients or ())
    return values, f"Normalized polynomial: {label}", None, (
        "f(z) = z + a2*z^2 + ... (supplied finite polynomial)"
    )


def _polynomial_derivative_value(coefficients: tuple[float, ...], z: complex) -> complex:
    """``f'(z)`` for ``f(z) = z + sum a_n z^n``."""

    value = 1.0 + 0.0j
    power = 1.0 + 0.0j
    for degree, coefficient in enumerate(coefficients, start=2):
        power *= z
        value += degree * coefficient * power
    return value


def write_coefficient_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
) -> PlotResult:
    """Write an SVG bar chart of the coefficient magnitudes ``|a_n|``."""

    path = Path(output)
    if path.suffix.lower() != ".svg":
        raise ValueError("output must have the .svg extension")
    values, title, generator_key, approximation = _resolve_plot_inputs(
        generator, coefficients, order, label="Taylor coefficients"
    )
    magnitudes = [abs(float(value)) for value in values]
    maximum = max(magnitudes) if magnitudes else 1.0
    width, height, pad_left, pad_bottom = 900, 460, 90, 70
    pad_top = 88
    plot_width = width - pad_left - 48
    plot_height = height - pad_top - pad_bottom
    count = max(len(magnitudes), 1)
    slot = plot_width / count
    bar_width = min(36.0, slot * 0.62)
    bars: list[str] = []
    for index, magnitude in enumerate(magnitudes):
        bar_height = plot_height * magnitude / maximum if maximum else 0.0
        x = pad_left + index * slot + (slot - bar_width) / 2
        y = pad_top + plot_height - bar_height
        bars.append(
            f'  <rect class="bar" x="{x:.2f}" y="{y:.2f}" '
            f'width="{bar_width:.2f}" height="{bar_height:.2f}"/>'
        )
        label_x = pad_left + index * slot + slot / 2
        bars.append(
            f'  <text class="tick" x="{label_x:.2f}" y="{pad_top + plot_height + 24:.2f}" '
            f'text-anchor="middle">{index + 2}</text>'
        )
        bars.append(
            f'  <text class="value" x="{label_x:.2f}" y="{max(y - 6, 14):.2f}" '
            f'text-anchor="middle">{magnitude:g}</text>'
        )
    subtitle = f"{approximation}; bars show |a_n| for n = 2..{len(values) + 1}"
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'  <title id="title">{escape(title)}</title>',
            f'  <desc id="desc">{escape(subtitle)}. Coefficient magnitudes of the displayed Taylor polynomial.</desc>',
            '  <rect width="100%" height="100%" fill="#fbfaf7"/>',
            "  <style>.bar{fill:#265d8f}.tick{font:13px ui-monospace,monospace;fill:#5f6872;text-anchor:middle}.value{font:12px ui-monospace,monospace;fill:#18212b;text-anchor:middle}.title{font:600 24px system-ui,sans-serif;fill:#18212b}.subtitle{font:15px ui-monospace,monospace;fill:#5f6872}.axis{stroke:#9aa3ad;stroke-width:1}</style>",
            f'  <text class="title" x="42" y="36">{escape(title)}</text>',
            f'  <text class="subtitle" x="42" y="64">{escape(subtitle)}</text>',
            f'  <line class="axis" x1="{pad_left}" y1="{pad_top + plot_height}" x2="{width - 48}" y2="{pad_top + plot_height}"/>',
            *bars,
            "</svg>",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return PlotResult(
        output=path,
        kind="coefficients",
        generator=generator_key,
        coefficients=values,
        approximation=approximation,
    )


def _diverging_color(value: float) -> str:
    """Deterministic diverging color: red below 0, white at 0, blue above 0."""

    t = max(-1.0, min(1.0, value / 4.0))
    if t >= 0:
        red = int(255 + (49 - 255) * t)
        green = int(255 + (130 - 255) * t)
        blue = int(255 + (189 - 255) * t)
    else:
        factor = -t
        red = int(255 + (214 - 255) * factor)
        green = int(255 + (39 - 255) * factor)
        blue = int(255 + (40 - 255) * factor)
    return f"#{red:02x}{green:02x}{blue:02x}"


def _phase_color(phase: float) -> str:
    hue = (phase + math.pi) / (2 * math.pi)
    red, green, blue = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    return f"#{int(red * 255):02x}{int(green * 255):02x}{int(blue * 255):02x}"


def _disk_cells(
    grid: int,
    *,
    rmax: float,
) -> list[tuple[int, int, complex]]:
    """Pixel-cell centers strictly inside the disk of radius ``rmax``."""

    cells: list[tuple[int, int, complex]] = []
    for column in range(grid):
        for row in range(grid):
            x = -rmax + 2 * rmax * (column + 0.5) / grid
            y = rmax - 2 * rmax * (row + 0.5) / grid
            if x * x + y * y <= rmax * rmax:
                cells.append((column, row, complex(x, y)))
    return cells


def write_real_part_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    grid: int = 64,
    rmax: float = _DISK_RMAX,
) -> PlotResult:
    """Write an SVG heatmap of ``Re(z f'(z)/f(z))`` on the sampled disk.

    A numerical screen: sampled visualization, never a proof of the full
    starlikeness domain.
    """

    path = Path(output)
    if path.suffix.lower() != ".svg":
        raise ValueError("output must have the .svg extension")
    if isinstance(grid, bool) or not isinstance(grid, int) or not 16 <= grid <= 256:
        raise ValueError("grid must be an integer between 16 and 256")
    values, title, generator_key, approximation = _resolve_plot_inputs(
        generator, coefficients, order, label="Re(z f'(z) / f(z)) heatmap"
    )
    width, height, pad = 900, 860, 40
    pad_top = 88
    plot_size = height - pad_top - pad
    center_x = width / 2
    center_y = pad_top + plot_size / 2
    cell = plot_size / grid
    cells: list[str] = []
    for column, row, z in _disk_cells(grid, rmax=rmax):
        f_value = _evaluate_normalized_polynomial(values, z)
        fp_value = _polynomial_derivative_value(values, z)
        if abs(f_value) < 1e-300 or not math.isfinite(fp_value.real):
            continue
        quantity = (z * fp_value / f_value).real
        cells.append(
            f'  <rect class="cell" x="{center_x - plot_size / 2 + column * cell:.2f}" '
            f'y="{center_y - plot_size / 2 + row * cell:.2f}" '
            f'width="{cell + 0.5:.2f}" height="{cell + 0.5:.2f}" '
            f'fill="{_diverging_color(float(quantity))}"/>'
        )
    subtitle = (
        f"{approximation}; sampled Re(z f'(z) / f(z)) on |z| <= {rmax:g} "
        "(red = negative, blue = positive). Numerical screen, not a proof."
    )
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'  <title id="title">{escape(title)}</title>',
            f'  <desc id="desc">{escape(subtitle)}</desc>',
            '  <rect width="100%" height="100%" fill="#fbfaf7"/>',
            "  <style>.cell{stroke:none}.title{font:600 24px system-ui,sans-serif;fill:#18212b}.subtitle{font:15px ui-monospace,monospace;fill:#5f6872}.axis{stroke:#9aa3ad;stroke-width:1.4;fill:none}</style>",
            f'  <text class="title" x="42" y="36">{escape(title)}</text>',
            f'  <text class="subtitle" x="42" y="64">{escape(subtitle)}</text>',
            f'  <circle class="axis" cx="{center_x:.2f}" cy="{center_y:.2f}" r="{plot_size / 2:.2f}"/>',
            *cells,
            "</svg>",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return PlotResult(
        output=path,
        kind="real-part",
        generator=generator_key,
        coefficients=values,
        approximation=approximation,
    )


def write_phase_plot(
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    grid: int = 64,
    rmax: float = _DISK_RMAX,
) -> PlotResult:
    """Write an SVG phase portrait of the finite Taylor polynomial.

    Empirical visualization: hue encodes ``arg f(z)`` on the sampled disk.
    """

    path = Path(output)
    if path.suffix.lower() != ".svg":
        raise ValueError("output must have the .svg extension")
    if isinstance(grid, bool) or not isinstance(grid, int) or not 16 <= grid <= 256:
        raise ValueError("grid must be an integer between 16 and 256")
    values, title, generator_key, approximation = _resolve_plot_inputs(
        generator, coefficients, order, label="phase portrait"
    )
    width, height, pad = 900, 860, 40
    pad_top = 88
    plot_size = height - pad_top - pad
    center_x = width / 2
    center_y = pad_top + plot_size / 2
    cell = plot_size / grid
    cells: list[str] = []
    for column, row, z in _disk_cells(grid, rmax=rmax):
        f_value = _evaluate_normalized_polynomial(values, z)
        if abs(f_value) < 1e-300:
            continue
        phase = math.atan2(f_value.imag, f_value.real)
        cells.append(
            f'  <rect class="cell" x="{center_x - plot_size / 2 + column * cell:.2f}" '
            f'y="{center_y - plot_size / 2 + row * cell:.2f}" '
            f'width="{cell + 0.5:.2f}" height="{cell + 0.5:.2f}" '
            f'fill="{_phase_color(float(phase))}"/>'
        )
    subtitle = (
        f"{approximation}; hue = arg f(z) on |z| <= {rmax:g}. "
        "Empirical visualization, not a proof."
    )
    svg = "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
            f'  <title id="title">{escape(title)}</title>',
            f'  <desc id="desc">{escape(subtitle)}</desc>',
            '  <rect width="100%" height="100%" fill="#fbfaf7"/>',
            "  <style>.cell{stroke:none}.title{font:600 24px system-ui,sans-serif;fill:#18212b}.subtitle{font:15px ui-monospace,monospace;fill:#5f6872}.axis{stroke:#9aa3ad;stroke-width:1.4;fill:none}</style>",
            f'  <text class="title" x="42" y="36">{escape(title)}</text>',
            f'  <text class="subtitle" x="42" y="64">{escape(subtitle)}</text>',
            f'  <circle class="axis" cx="{center_x:.2f}" cy="{center_y:.2f}" r="{plot_size / 2:.2f}"/>',
            *cells,
            "</svg>",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    return PlotResult(
        output=path,
        kind="phase",
        generator=generator_key,
        coefficients=values,
        approximation=approximation,
    )


def write_plot(
    kind: str,
    output: str | Path,
    *,
    generator: str | None = None,
    coefficients: tuple[float, ...] | None = None,
    order: int = 12,
    grid: int = 64,
    rmax: float = _DISK_RMAX,
    rings: int = 5,
    spokes: int = 12,
    samples: int = 480,
) -> PlotResult | DomainPlotResult:
    """Write an SVG plot of the requested kind.

    Kinds: ``domain`` (conformal grid), ``coefficients`` (|a_n| bars),
    ``real-part`` (Re(z f'/f) heatmap), ``phase`` (phase portrait).
    """

    if kind not in PLOT_KINDS:
        raise ValueError(
            f"kind must be one of: {', '.join(PLOT_KINDS)}"
        )
    suffix = Path(output).suffix.lower()
    if suffix in {".png", ".tikz", ".tex"}:
        if kind != "domain":
            raise ValueError("PNG and TikZ exports are supported for the domain plot only")
        export = write_png_plot if suffix == ".png" else write_tikz_plot
        return export(
            output,
            generator=generator,
            coefficients=coefficients,
            order=order,
            rmax=rmax,
            rings=rings,
            spokes=spokes,
            samples=samples,
        )
    if kind == "domain":
        return write_domain_plot(
            output,
            generator=generator,
            coefficients=coefficients,
            order=order,
            rmax=rmax,
            rings=rings,
            spokes=spokes,
            samples=samples,
        )
    if kind == "coefficients":
        return write_coefficient_plot(
            output, generator=generator, coefficients=coefficients, order=order
        )
    if kind == "real-part":
        return write_real_part_plot(
            output,
            generator=generator,
            coefficients=coefficients,
            order=order,
            grid=grid,
            rmax=rmax,
        )
    return write_phase_plot(
        output,
        generator=generator,
        coefficients=coefficients,
        order=order,
        grid=grid,
        rmax=rmax,
    )


export_png = write_png_plot
export_tikz = write_tikz_plot
