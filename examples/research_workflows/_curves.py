"""Lightweight shared rendering for the explicitly sampled workflow curves."""

from __future__ import annotations

import math
from pathlib import Path
from xml.sax.saxutils import escape


def write_panels(path: Path, title: str, panels: list[dict]) -> None:
    """Render equal-unit complex planes; each panel may have a different range."""
    width = 420 * len(panels)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="650" viewBox="0 0 {width} 650">',
        f'<title>{escape(title)}</title><desc>Sampled curves, not a proof. Equal real and imaginary units within each panel.</desc>',
        f'<rect width="{width}" height="650" fill="#fafbfc"/>',
        f'<text x="25" y="34" font-size="22" fill="#17233b">{escape(title)}</text>',
        '<text x="25" y="62" font-size="14">Blue: reference function. Orange: comparison. Equal units per panel; panel ranges may differ.</text>',
    ]
    for index, panel in enumerate(panels):
        curves = panel["curves"]
        points = [p for curve in curves for p in curve["points"]]
        if not points or not all(math.isfinite(v) for p in points for v in p):
            raise ValueError("plot requires finite nonempty curves")
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        span = max(xmax - xmin, ymax - ymin, 0.1) * 1.15
        cx, cy = (xmin + xmax) / 2, (ymin + ymax) / 2
        left, top, side = 30 + index * 420, 135, 350

        def project(x: float, y: float, *, left=left, side=side, cx=cx, cy=cy, span=span, top=top) -> tuple[float, float]:
            return left + side / 2 + side * (x - cx) / span, top + side / 2 - side * (y - cy) / span

        parts.append(f'<text x="{left}" y="110" font-size="17">{escape(panel["title"])}</text>')
        parts.append(f'<rect x="{left}" y="{top}" width="{side}" height="{side}" fill="white" stroke="#c4cbd4"/>')
        px0, py0 = project(0, 0)
        if left <= px0 <= left + side:
            parts.append(f'<line x1="{px0:.3f}" y1="{top}" x2="{px0:.3f}" y2="{top+side}" stroke="#d3d8df"/>')
        if top <= py0 <= top + side:
            parts.append(f'<line x1="{left}" y1="{py0:.3f}" x2="{left+side}" y2="{py0:.3f}" stroke="#d3d8df"/>')
        for curve in curves:
            coords = " ".join(f"{x:.3f},{y:.3f}" for x, y in (project(*p) for p in curve["points"]))
            dash = ' stroke-dasharray="5 3"' if curve.get("comparison") else ""
            color = "#ba561b" if curve.get("comparison") else "#2457a7"
            parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.5"{dash}><title>{escape(curve["label"])}</title></polyline>')
        parts.append(f'<text x="{left}" y="510" font-size="12">Re: [{cx-span/2:.3g}, {cx+span/2:.3g}]</text>')
        parts.append(f'<text x="{left}" y="529" font-size="12">Im: [{cy-span/2:.3g}, {cy+span/2:.3g}]</text>')
        for line_index, line in enumerate(panel.get("notes", [])):
            parts.append(f'<text x="{left}" y="{555+18*line_index}" font-size="12">{escape(line)}</text>')
    parts.append('<text x="25" y="628" font-size="13">Visualization is not a proof. Exact objects, sampling domain, comparisons and limitations are in the accompanying JSON.</text></svg>\n')
    path.write_text("".join(parts), encoding="utf-8")
