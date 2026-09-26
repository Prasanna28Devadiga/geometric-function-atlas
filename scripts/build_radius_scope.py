"""Rebuild/check the canonical analysis sidecar without rewriting radius rows.

Usage: python scripts/build_radius_scope.py [--check]
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "src/geometric_function_atlas/data"
OUTPUT = DATA / "radius_scope_2026_09_27.json"
ALIAS = {"janowski_A0_B-1": "order_0.5"}
UNFINISHED = {"unidentified", "audit_required"}


def build() -> dict:
    path = DATA / "radii_snapshot.json"
    source_bytes = path.read_bytes()
    snapshot = json.loads(source_bytes)
    catalog = json.loads((DATA / "classes.json").read_bytes())["classes"]
    rows = snapshot["radii"]
    sources = {r["inner"] for r in rows}
    targets = {r["target"] for r in rows}
    assert len(catalog) == 39 and len(sources) == 28 and len(targets) == 26
    assert len(rows) == snapshot["n"] == 702
    assert len({(r["inner"], r["target"]) for r in rows}) == len(rows)
    assert (sources - targets) == {"nephroid", "three_leaf"}
    assert targets == sources - {"nephroid", "three_leaf"}
    assert len(set(catalog) - sources) == 11
    assert len({ALIAS.get(k, k) for k in catalog}) == 38
    groups: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        direction = (ALIAS[row["inner"]] if row["inner"] in ALIAS else row["inner"],
                     ALIAS[row["target"]] if row["target"] in ALIAS else row["target"])
        groups.setdefault(direction, []).append(row)
    diagonal = [r for (a, b), group in groups.items() if a == b for r in group]
    assert len(diagonal) == 2 and all(r["value_exact"] == "1" for r in diagonal)
    canonical = {}
    for (a, b), group in sorted(groups.items()):
        if a == b:
            continue
        assert len(group) in (1, 2)
        assert len({r["value_str"] for r in group}) == 1, (a, b)
        # Paper review can upgrade one public alias row without upgrading its twin.
        # Prefer the named canonical key for analysis; retain both raw API rows.
        canonical[a, b] = next((r for r in group if r["inner"] != "janowski_A0_B-1"
                                 and r["target"] != "janowski_A0_B-1"), group[0])
    assert len(canonical) == 650
    eligible = {key: r for key, r in canonical.items() if r["status"] not in UNFINISHED}
    reciprocal = [(key, (key[1], key[0])) for key in eligible
                  if (key[1], key[0]) in eligible and key[0] < key[1]]
    unequal = sum(eligible[a]["value_str"] != eligible[b]["value_str"] for a, b in reciprocal)
    nontrivial = [r for r in eligible.values() if float(r["value_str"]) < 1 - 1e-10]
    frequency = Counter(r["value_str"] for r in nontrivial)
    shared = sum(frequency[r["value_str"]] > 1 for r in nontrivial)
    status = dict(sorted(Counter(r["status"] for r in canonical.values()).items()))
    table = {mode: dict(sorted(Counter(r["status"] for r in canonical.values()
                                      if ("real_axis" if r["mode"] in ("axis", "axis_bisect")
                                          else "off_axis") == mode
                                      and r["status"] not in ("trivial_containment", "audit_required")).items()))
             for mode in ("real_axis", "off_axis")}
    return {
        "schema_version": 1,
        "analysis_version": "2026.09.27-paper-review-canonical-v1",
        "source_snapshot_version": snapshot["snapshot_version"],
        "source_snapshot_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "canonical_aliases": ALIAS,
        "scope": {
            "source_key_count": len(sources), "target_key_count": len(targets),
            "source_keys": sorted(sources), "target_keys": sorted(targets),
            "never_source_keys": sorted(set(catalog) - sources),
            "never_target_among_source_keys": sorted(sources - targets),
            "full_catalog": False, "catalog_key_count": len(catalog),
            "distinct_catalog_generator_count": 38,
            "raw_grid_non_diagonal_key_questions": 28 * 26 - len(sources & targets),
            "unpopulated_incoming_key_directions": 2 * (28 - 1),
        },
        "counts": {
            "raw_key_rows": len(rows), "canonical_questions": len(canonical),
            "alias_identity_rows": len(diagonal),
            "eligible_closed_form_consistent": len(eligible),
            "reciprocal_unequal": unequal, "reciprocal_total": len(reciprocal),
            "nontrivial_shared": shared, "nontrivial_total": len(nontrivial),
            "nontrivial_shared_groups": sum(n > 1 for n in frequency.values()),
            "status_buckets": status, "contact_status_table": table,
        },
        "count_rules": {
            "eligible": "canonical off-diagonal status excludes unidentified and audit_required",
            "reciprocal": "both directions eligible; unequal when value_str differs",
            "nontrivial": "eligible and numerical radius < 1 - 1e-10; identical value_str groups",
            "contact_status_table": "nontrivial-status rows only, by axis/axis_bisect vs other mode; not a proof or coefficient-sign classification",
        },
        "next_release_todo": {
            "description": "Expand radii to every ordered non-self pair of 38 distinct generator classes",
            "distinct_classes": 38, "directed_questions": 38 * 37,
            "status": "not_in_this_release",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    blob = (json.dumps(build(), indent=2, sort_keys=True) + "\n").encode()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != blob:
            raise SystemExit("radius scope artifact is stale: run python scripts/build_radius_scope.py")
        print("radius scope artifact matches deterministic rebuild")
    else:
        OUTPUT.write_bytes(blob)
        print(f"wrote {OUTPUT.relative_to(ROOT)} sha256={hashlib.sha256(blob).hexdigest()}")


if __name__ == "__main__":
    main()
