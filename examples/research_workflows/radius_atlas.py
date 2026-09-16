"""Export the immutable directed-radius snapshot as an evidence-labeled matrix."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from geometric_function_atlas import list_radii
from geometric_function_atlas.version import __version__

_STATUS_COLORS = {
    "touch_proven_exact": "#176b4d",
    "closed_form_confirmed": "#3975a8",
    "trivial_containment": "#7a5ba6",
    "unidentified": "#c48a1c",
    "audit_required": "#b33a3a",
    "missing_snapshot_row": "#d1d5db",
    "diagonal_not_a_radius_problem": "#f3f4f6",
}


def solve() -> dict:
    """Return every directed matrix cell without inventing missing records."""

    records = list_radii()
    classes = sorted(
        {record.source_class for record in records}
        | {record.target_class for record in records}
    )
    by_direction = {
        (record.source_class, record.target_class): record for record in records
    }
    cells = []
    for source in classes:
        for target in classes:
            record = by_direction.get((source, target))
            if source == target:
                cell = {
                    "source": source,
                    "target": target,
                    "direction": f"{source}->{target}",
                    "status": "diagonal_not_a_radius_problem",
                    "status_label": "diagonal; no directed inclusion problem stored",
                    "value_exact": None,
                    "value_decimal": None,
                    "has_replay_certificate": False,
                }
            elif record is None:
                cell = {
                    "source": source,
                    "target": target,
                    "direction": f"{source}->{target}",
                    "status": "missing_snapshot_row",
                    "status_label": "missing snapshot row",
                    "value_exact": None,
                    "value_decimal": None,
                    "has_replay_certificate": False,
                }
            else:
                cell = {
                    "source": source,
                    "target": target,
                    "direction": record.direction,
                    "status": record.status.value,
                    "status_label": record.status_label,
                    "value_exact": record.value_exact,
                    "value_decimal": record.value_decimal,
                    "has_replay_certificate": record.certificate is not None,
                }
            cells.append(cell)

    denominator = len(classes) * (len(classes) - 1)
    return {
        "workflow": "radius_atlas",
        "question": "Which directed class-inclusion radii are present, with what evidence?",
        "class_count": len(classes),
        "record_count": len(records),
        "directed_pair_denominator": denominator,
        "missing_pair_count": denominator - len(records),
        "replayable_certificate_count": sum(
            record.certificate is not None for record in records
        ),
        "status_counts": dict(
            sorted(Counter(record.status.value for record in records).items())
        ),
        "classes": classes,
        "cells": cells,
        "orientation": "source rows; target columns; direction is never symmetrized",
        "evidence_boundary": (
            "The matrix reproduces immutable snapshot rows. Only cells with "
            "has_replay_certificate=true have a bundled local certificate; colors do not "
            "upgrade evidence or establish literature novelty."
        ),
        "novelty_claim": False,
        "package_version": __version__,
    }


def write_svg(data: dict, path: Path) -> None:
    """Write a compact deterministic matrix whose cells retain status titles."""

    classes = data["classes"]
    cells = data["cells"]
    cell_size = 18
    left = 225
    top = 235
    width = left + cell_size * len(classes) + 300
    height = top + cell_size * len(classes) + 165
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<title>Directed inclusion-radius atlas</title>",
        (
            "<desc>Source rows and target columns. Cell colors are immutable snapshot "
            "evidence statuses; gray means a missing snapshot row.</desc>"
        ),
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="20" y="30" font-size="20" font-weight="bold">Directed inclusion-radius atlas</text>',
        '<text x="20" y="54">source rows; target columns; reverse directions are separate problems</text>',
        (
            f'<text x="20" y="76">{data["record_count"]} records over '
            f'{data["directed_pair_denominator"]} possible non-diagonal pairs; '
            f'{data["missing_pair_count"]} missing snapshot rows</text>'
        ),
    ]
    for index, name in enumerate(classes):
        y = top + index * cell_size + 13
        x = left + index * cell_size + 12
        parts.append(
            f'<text x="{left - 8}" y="{y}" text-anchor="end" font-size="9">{escape(name)}</text>'
        )
        parts.append(
            f'<text x="{x}" y="{top - 8}" font-size="9" transform="rotate(-60 {x} {top - 8})">{escape(name)}</text>'
        )
    for index, cell in enumerate(cells):
        row, column = divmod(index, len(classes))
        x = left + column * cell_size
        y = top + row * cell_size
        status = cell["status"]
        title = (
            f'{cell["direction"]}: {cell["status_label"]}; '
            f'exact={cell["value_exact"]}; replayable={cell["has_replay_certificate"]}'
        )
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
            f'fill="{_STATUS_COLORS[status]}" stroke="white" stroke-width="1">'
            f'<title>{escape(title)}</title></rect>'
        )

    legend_x = left + cell_size * len(classes) + 28
    legend_y = top
    labels = [
        ("touch_proven_exact", "touch proven exact"),
        ("closed_form_confirmed", "closed form confirmed"),
        ("trivial_containment", "trivial containment"),
        ("unidentified", "unidentified"),
        ("audit_required", "audit required"),
        ("missing_snapshot_row", "missing snapshot row"),
        ("diagonal_not_a_radius_problem", "diagonal (not a stored radius)"),
    ]
    for offset, (status, label) in enumerate(labels):
        y = legend_y + offset * 27
        parts.extend(
            [
                f'<rect x="{legend_x}" y="{y}" width="18" height="18" fill="{_STATUS_COLORS[status]}"/>',
                f'<text x="{legend_x + 27}" y="{y + 13}" font-size="11">{escape(label)}</text>',
            ]
        )
    parts.append(
        f'<text x="20" y="{height - 45}" font-size="11">Colors report stored evidence status, not a new proof. Only {data["replayable_certificate_count"]} cells carry locally replayable certificates.</text>'
    )
    parts.append(
        f'<text x="20" y="{height - 24}" font-size="11">Hover a cell for direction, exact value, status, and replayability.</text>'
    )
    parts.append("</svg>\n")
    path.write_text("".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    data = solve()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "radius_atlas.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    write_svg(data, args.output / "radius_atlas.svg")
    print(
        f"{data['record_count']}/{data['directed_pair_denominator']} directed pairs; "
        f"{data['missing_pair_count']} missing; "
        f"{data['replayable_certificate_count']} replayable certificates"
    )


if __name__ == "__main__":
    main()
