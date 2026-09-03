"""Command-line interface for independent reproduction workflows."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
from collections.abc import Sequence
from typing import Any

from . import artifacts as _artifact_data
from .catalog import get_generator, list_generators
from .citation import citation_export
from .classes import (
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    list_classes,
)
from .coefficients import generator_series
from .contracts import (
    CheckStatus,
    CorruptArtifactError,
    FailureState,
    InvalidInputError,
    ResourceLimitError,
    UnresolvedError,
    UnsupportedError,
    VerificationCheck,
    VerificationReport,
    failure_payload,
    validate_error_payload,
)
from .counterexamples import find_counterexample, verify_counterexample
from .fekete_szego import fekete_szego
from .lab import SPECIAL_FUNCTIONS
from .plotting import write_plot
from .radii import (
    RadiusStatus,
    audit_radius,
    identify_radius,
    list_radii,
    radius,
    recompute_radius,
    verify_radius_attainment,
    verify_radius_certificate,
)
from .snapshot import (
    RegistrySnapshot,
    install_snapshot,
    snapshot_info,
    verify_snapshot,
)
from .verify import verify_function
from .version import __version__

EXIT_SUCCESS = 0
EXIT_BROKEN_PIPE = 1
EXIT_INVALID_INPUT = 2
EXIT_UNSUPPORTED = 3
EXIT_UNRESOLVED = 4
EXIT_RESOURCE_LIMIT = 5
EXIT_CORRUPT_ARTIFACT = 6

EXIT_CODES = {
    FailureState.INVALID_INPUT.value: EXIT_INVALID_INPUT,
    FailureState.UNSUPPORTED.value: EXIT_UNSUPPORTED,
    FailureState.UNRESOLVED.value: EXIT_UNRESOLVED,
    FailureState.RESOURCE_LIMIT.value: EXIT_RESOURCE_LIMIT,
    FailureState.CORRUPT_ARTIFACT.value: EXIT_CORRUPT_ARTIFACT,
}


def _write(payload: Any, *, as_json: bool) -> None:
    if as_json:
        _write_utf8(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
        )
    elif isinstance(payload, list):
        for row in payload:
            label = (
                row.get("key")
                or row.get("canonical_key")
                or row.get("title")
                or row.get("kind")
            )
            detail = row.get("formula") or row.get("display_name") or row.get("name") or ""
            print(f"{label}: {detail}" if detail else str(label))
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


def _write_utf8(text: str, *, stream: Any = None) -> None:
    """Write JSON as UTF-8 even when the console locale is not UTF-8."""

    target = sys.stdout if stream is None else stream
    buffer = getattr(target, "buffer", None)
    if buffer is not None:
        buffer.write(text.encode("utf-8") + b"\n")
        buffer.flush()
    else:
        target.write(f"{text}\n")


def _generators(args: argparse.Namespace) -> None:
    payload = [
        {
            "key": generator.key,
            "name": generator.name,
            "formula": generator.formula,
            "citation": generator.citation,
            "reference_url": generator.reference_url,
        }
        for generator in list_generators()
    ]
    _write(payload, as_json=args.json)


def _walkthrough(_args: argparse.Namespace) -> None:
    """Run a concise first-use tour without exposing result envelopes."""

    generators = list_generators()
    series = generator_series(get_generator("sine"), order=5)
    fs = fekete_szego("exponential", mu="0")
    replay = verify_radius_certificate("sine", "sigmoid")
    if not replay.certified:
        raise UnresolvedError("the bundled sine-to-sigmoid certificate did not replay")

    coefficients = ", ".join(str(value) for value in series.coefficients)
    lines = [
        "Geometric Function Atlas: first-run walkthrough",
        "",
        f"1. Catalog: {len(generators)} registered Ma-Minda generators.",
        "   Starter keys: exponential, sine, cardioid, lemniscate, sigmoid",
        "",
        "2. Exact expansion for the sine generator phi(z) = 1 + sin(z):",
        f"   coefficients through z^4: {coefficients}",
        "",
        "3. Fekete-Szego for S*(exp(z)) with mu = 0:",
        f"   exact value: {fs.value}",
        f"   evidence: {fs.evidence_status}",
        "",
        "4. Directed radius certificate: sine -> sigmoid",
        f"   exact radius: {replay.expected_candidate}",
        f"   certificate: {replay.status.upper()} ({len(replay.steps)} checks passed)",
        "",
        "The replay checks the released certificate; it does not establish novelty",
        "or whether the assumptions match a different problem.",
        "",
        "Next commands:",
        "  gfa generators",
        "  gfa coefficients sine --order 5",
        "  gfa fekete-szego exponential --mu 0",
        "  gfa verify-radius-certificate sine sigmoid",
    ]
    _write_utf8("\n".join(lines))


def _citation(args: argparse.Namespace) -> None:
    metadata = {
        "key": args.key,
        "title": args.title,
        "author": args.author,
        "year": args.year,
        "url": args.url,
        "journal": args.journal,
        "doi": args.doi,
        "note": args.note,
    }
    bundle = citation_export(metadata, accessed=args.accessed)
    if args.format is not None:
        _write_utf8(bundle.formats[args.format])
    elif args.json:
        _write(bundle.to_dict(), as_json=True)
    else:
        _write(bundle.to_dict(), as_json=False)


def _coefficients(args: argparse.Namespace) -> None:
    result = generator_series(get_generator(args.generator), order=args.order)
    _write(result.to_dict(), as_json=args.json)


def _fekete_szego(args: argparse.Namespace) -> None:
    result = fekete_szego(args.generator, mu=args.mu)
    _write(result.to_dict(precision=args.precision), as_json=args.json)


def _comma_separated_numbers(value: str, *, label: str) -> list[float]:
    if len(value) > 4096:
        raise ResourceLimitError(f"{label} input is too long")
    parts = [part.strip() for part in value.split(",")]
    if not parts or any(not part for part in parts):
        raise InvalidInputError(f"{label} must be comma-separated real numbers")
    try:
        return [float(part) for part in parts]
    except ValueError as exc:
        raise InvalidInputError(
            f"{label} must be comma-separated real numbers"
        ) from exc


def _verify_counterexample(args: argparse.Namespace) -> None:
    coefficients = _comma_separated_numbers(
        args.coefficients, label="coefficients"
    )
    point = _comma_separated_numbers(args.point, label="point")
    if len(point) != 2:
        raise InvalidInputError("point must have the form real,imaginary")
    result = verify_counterexample(
        coefficients,
        point=(point[0], point[1]),
        property=args.property,
    )
    if args.json:
        _write(result.to_dict(), as_json=True)
        return

    if result.certified and result.property == "starlike":
        verdict = "CERTIFIED COUNTEREXAMPLE"
    elif result.certified:
        verdict = "CERTIFIED CRITERION VIOLATION"
    elif result.property == "starlike":
        verdict = "NO COUNTEREXAMPLE CERTIFIED AT THIS POINT"
    else:
        verdict = "NO CRITERION VIOLATION CERTIFIED AT THIS POINT"
    criterion_names = {
        "starlike": "starlikeness",
        "becker_univalent": "Becker criterion",
        "nehari_univalent": "Nehari criterion",
    }
    real, imaginary = result.point
    sign = "+" if imaginary >= 0 else "-"
    comparison = "<=" if result.property == "starlike" else ">"
    lines = [
        verdict,
        f"Criterion: {criterion_names[result.property]}",
        f"Witness: z = {real:g} {sign} {abs(imaginary):g}i",
        (
            "Certified value: "
            f"[{result.interval_lower:g}, {result.interval_upper:g}]"
        ),
        f"Counterexample condition: value {comparison} {result.threshold:g}",
    ]
    _write_utf8("\n".join(lines))


def _radii(args: argparse.Namespace) -> None:
    rows = list_radii(source=args.source, target=args.target, status=args.status)
    payload = [row.to_dict() for row in rows]
    if args.json:
        _write(payload, as_json=True)
        return
    for row in rows:
        value = row.value_exact or row.value_decimal or "unavailable"
        print(f"{row.direction}: {value} [{row.status.value}]")
        print(f"  {row.status_label}")


def _radius(args: argparse.Namespace) -> None:
    result = radius(args.source, args.target)
    _write(result.to_dict(), as_json=args.json)


def _radius_recompute(args: argparse.Namespace) -> None:
    result = recompute_radius(
        args.source,
        args.target,
        candidate=args.candidate,
        dps=args.dps,
        max_steps=args.max_steps,
    )
    payload = result.to_dict()
    if result.certified:
        if args.json:
            _write(payload, as_json=True)
        else:
            print(f"PROVEN: {result.direction}")
            for step in result.steps:
                print(f"  PASS {step.name}")
        return
    state = (
        result.failure_state.value
        if result.failure_state is not None
        else FailureState.UNRESOLVED.value
    )
    raise _CommandFailure(state, payload)


def _radius_attainment(args: argparse.Namespace) -> None:
    result = verify_radius_attainment(
        args.source,
        args.target,
        dps=args.dps,
        max_steps=args.max_steps,
    )
    payload = result.to_dict()
    if result.certified:
        if args.json:
            _write(payload, as_json=True)
        else:
            print(f"PROVEN ATTAINMENT: {result.direction}")
            for step in result.steps:
                print(f"  PASS {step.name}")
        return
    state = (
        result.failure_state.value
        if result.failure_state is not None
        else FailureState.UNRESOLVED.value
    )
    raise _CommandFailure(state, payload)


def _radius_identify(args: argparse.Namespace) -> None:
    value: str | float = args.value
    try:
        rows = identify_radius(value, tolerance=args.tolerance, limit=args.limit)
    except InvalidInputError:
        rows = ()
    if not rows:
        try:
            numeric = float(args.value)
        except ValueError as exc:
            raise InvalidInputError(
                "radius identification value must be an exact expression or finite number"
            ) from exc
        rows = identify_radius(numeric, tolerance=args.tolerance, limit=args.limit)
    _write([row.to_dict() for row in rows], as_json=args.json)


def _radius_audit(args: argparse.Namespace) -> None:
    payload = audit_radius(
        args.source,
        args.target,
        candidate=args.candidate,
        dps=args.dps,
        max_steps=args.max_steps,
    )
    if payload["status"] == "proven":
        _write(payload, as_json=args.json)
        return
    replay = payload.get("certificate_replay", {})
    state = replay.get("failure_state") or FailureState.UNRESOLVED.value
    raise _CommandFailure(state, payload)


class _CommandFailure(RuntimeError):
    """Internal bridge from a structured replay failure to a CLI exit code."""

    def __init__(self, state: str, payload: dict[str, Any]) -> None:
        self.state = state
        self.payload = payload
        super().__init__(state)


def _verify_radius_certificate(args: argparse.Namespace) -> None:
    result = verify_radius_certificate(
        args.source,
        args.target,
        candidate=args.candidate,
        dps=args.dps,
        max_steps=args.max_steps,
    )
    payload = result.to_dict()
    if not args.json:
        print(
            f"{result.status.upper()}: {result.direction}"
            + (f" — {result.error}" if result.error else "")
        )
        for step in result.steps:
            print(f"  {'PASS' if step.verified else 'FAIL'} {step.name}")
    if result.certified:
        if args.json:
            _write(payload, as_json=True)
        return
    state = (
        result.failure_state.value
        if result.failure_state is not None
        else FailureState.UNRESOLVED.value
    )
    raise _CommandFailure(state, payload)


def _snapshot_manifest(args: argparse.Namespace) -> str | None:
    return getattr(args, "manifest", None)


def _snapshot_info(args: argparse.Namespace) -> None:
    _write(
        snapshot_info(args.path, manifest=_snapshot_manifest(args)).to_dict(),
        as_json=args.json,
    )


def _snapshot_verify(args: argparse.Namespace) -> None:
    report = verify_snapshot(
        args.path,
        manifest=_snapshot_manifest(args),
        raise_on_error=True,
    )
    _write(report.to_dict(), as_json=args.json)


def _snapshot_install(args: argparse.Namespace) -> None:
    installed = install_snapshot(
        args.source,
        args.destination,
        manifest=args.manifest,
    )
    payload = {
        "installed": str(installed),
        "verification": verify_snapshot(installed, manifest=args.manifest).to_dict(),
    }
    _write(payload, as_json=args.json)


def _snapshot_stats(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(snapshot.stats().to_dict(), as_json=args.json)


def _snapshot_search(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.search(
                    args.query, kind=args.kind, limit=args.limit
                )
            ],
            as_json=args.json,
        )


def _snapshot_families(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.families(group=args.group, limit=args.limit)
            ],
            as_json=args.json,
        )


def _snapshot_family(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            snapshot.family(args.identifier, limit=args.limit).to_dict(),
            as_json=args.json,
        )


def _snapshot_facts(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.facts(
                    args.identifier,
                    property=args.property,
                    status=args.status,
                    limit=args.limit,
                )
            ],
            as_json=args.json,
        )


def _snapshot_evidence(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.evidence(args.identifier, limit=args.limit)
            ],
            as_json=args.json,
        )


def _snapshot_runs(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.runs(args.identifier, limit=args.limit)
            ],
            as_json=args.json,
        )


def _snapshot_papers(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.papers(
                    query=args.query,
                    author=args.author,
                    year=args.year,
                    journal=args.journal,
                    doi=args.doi,
                    citation=args.citation,
                    class_key=args.class_key,
                    tag=args.tag,
                    claim=args.claim,
                    decade=args.decade,
                    msc=args.msc,
                    has_theorems=args.has_theorems,
                    theorem=args.theorem,
                    sort=args.sort,
                    limit=args.limit,
                )
            ],
            as_json=args.json,
        )


def _snapshot_paper_facets(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(snapshot.paper_facets(), as_json=args.json)


def _snapshot_functions(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.legacy_functions(
                    args.query, tag=args.tag, category=args.category, limit=args.limit
                )
            ],
            as_json=args.json,
        )


def _snapshot_function(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(snapshot.function(args.identifier).to_dict(), as_json=args.json)


def _snapshot_tags(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.tags(args.query, category=args.category, limit=args.limit)
            ],
            as_json=args.json,
        )


def _snapshot_paper(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            snapshot.paper(args.identifier, limit=args.limit).to_dict(),
            as_json=args.json,
        )


def _snapshot_applications(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.applications(args.area, limit=args.limit)
            ],
            as_json=args.json,
        )


def _snapshot_counterexamples(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.counterexamples(
                    args.identifier,
                    property=args.property,
                    limit=args.limit,
                )
            ],
            as_json=args.json,
        )


def _snapshot_aliases(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [dict(item) for item in snapshot.aliases(args.query, limit=args.limit)],
            as_json=args.json,
        )


def _snapshot_normalize_class(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            {"input": args.text, "canonical_key": snapshot.normalize_class(args.text)},
            as_json=args.json,
        )


def _snapshot_hierarchy(args: argparse.Namespace) -> None:
    with RegistrySnapshot.open(
        args.snapshot, manifest=_snapshot_manifest(args)
    ) as snapshot:
        _write(
            [
                item.to_dict()
                for item in snapshot.hierarchy(args.property, limit=args.limit)
            ],
            as_json=args.json,
        )


def _add_snapshot_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--snapshot", required=True, help="path to a verified SQLite snapshot"
    )
    parser.add_argument("--manifest", help="path to the matching snapshot manifest")


def _add_limit(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--limit", type=int, default=100, help="maximum records to return"
    )


def _record_lines(payload: dict[str, Any]) -> list[str]:
    lines = [
        f"record_type: {payload['record_type']}",
        f"evidence_kind: {payload['evidence_kind']}",
        f"tier: {payload['tier']}",
    ]
    details = payload.get("details") or {}
    for key, value in sorted(details.items()):
        lines.append(f"  {key}: {value}")
    lines.append(f"verification: {payload['verification']['status']}")
    return lines


def _write_record(payload: dict[str, Any], *, as_json: bool) -> None:
    if as_json:
        _write(payload, as_json=True)
        return
    _write_utf8("\n".join(_record_lines(payload)))


def _classes(args: argparse.Namespace) -> None:
    payload = [
        {
            "key": item.key,
            "name": item.name,
            "formula": item.formula,
            "citation": item.citation,
        }
        for item in list_classes()
    ]
    _write(payload, as_json=args.json)


def _class_check(args: argparse.Namespace) -> None:
    result = class_admissibility(args.key)
    if args.json:
        _write(result.to_dict(), as_json=True)
        return
    lines = [
        f"Class {result.class_key}: admissible = {result.admissible}",
        f"  phi(0) = {result.exact_values['phi0']}",
        f"  phi'(0) = {result.exact_values['phi_prime0']}",
        (
            f"  min Re phi on grid = {result.margins['re_min']:.6g}"
            if result.margins["re_min"] == result.margins["re_min"]
            else "  min Re phi on grid = unresolved"
        ),
        (
            f"  min Re(z phi'/(phi-1)) = {result.margins['starlike_wrt_1_min']:.6g}"
            if result.margins["starlike_wrt_1_min"] == result.margins["starlike_wrt_1_min"]
            else "  min Re(z phi'/(phi-1)) = unresolved"
        ),
        "Evidence: exact normalization checks plus float region screens (not proofs)",
    ]
    _write_utf8("\n".join(lines))


def _class_member(args: argparse.Namespace) -> None:
    coefficients = _comma_separated_numbers(args.coefficients, label="coefficients")
    result = class_member_screen(args.key, coefficients)
    if args.json:
        _write(result.to_dict(), as_json=True)
        return
    verdict = "MEMBER (screen)" if result.member else "NOT A MEMBER (screen)"
    if result.member:
        detail = f"Min distance to boundary: {result.min_dist_to_boundary:.6g}"
    elif result.witness_w is not None:
        detail = f"Witness w = zf'/f: {result.witness_w[0]:g}, {result.witness_w[1]:g}i"
    else:
        detail = "No witness recorded"
    lines = [
        verdict,
        f"Class: {result.class_key}",
        f"Fraction inside: {result.fraction_inside:.4f}",
        detail,
        "Scope: sampled subordination screen, not a proof",
    ]
    _write_utf8("\n".join(lines))


def _compare(args: argparse.Namespace) -> None:
    result = class_containment_screen(args.inner, args.outer)
    if args.json:
        _write(result.to_dict(), as_json=True)
        return
    verdict = "CONTAINED (screen)" if result.contained else "NOT CONTAINED (screen)"
    if result.contained:
        detail = f"Margin: {result.margin:.6g}"
    elif result.witness_w is not None:
        detail = f"Boundary witness w: {result.witness_w[0]:g}, {result.witness_w[1]:g}i"
    else:
        detail = "No witness recorded"
    lines = [
        verdict,
        f"Inner: {result.inner}, outer: {result.outer}",
        f"Fraction inside: {result.fraction_inside:.4f}",
        detail,
        "Scope: sampled winding-number containment screen, not a theorem",
    ]
    _write_utf8("\n".join(lines))


def _extremal(args: argparse.Namespace) -> None:
    coefficients = class_extremal_coefficients(args.key, order=args.order)
    if args.json:
        _write_utf8(
            json.dumps(
                {"class_key": args.key, "order": args.order, "coefficients": [str(c) for c in coefficients]},
                indent=2,
                sort_keys=True,
            )
        )
        return
    _write_utf8(
        "Exact extremal coefficients of "
        f"{args.key}: {', '.join(str(value) for value in coefficients)}"
    )


def _verify(args: argparse.Namespace) -> None:
    coefficients = _comma_separated_numbers(args.coefficients, label="coefficients")
    result = verify_function(
        coefficients,
        property=args.property,
        max_cost=args.max_cost,
        truncation=args.truncation,
    )
    if args.json:
        _write(result.to_dict(), as_json=True)
        return
    labels = {
        "proven": "PROVEN (exact proof)",
        "passes_screen": "PASSES SCREEN (numerical)",
        "fails_screen": "FAILS SCREEN (numerical)",
        "certified_violation": "CERTIFIED CRITERION VIOLATION (rigorous)",
        "no_certified_violation_on_grid": "NO CERTIFIED VIOLATION ON GRID (rigorous)",
        "inconclusive_truncation": "INCONCLUSIVE (truncation; tail unknown)",
        "c01_fails_sufficient_condition": "SUFFICIENT CONDITION FAILS (not a disproof)",
        "undecidable": "UNDECIDABLE IN EXACT ARITHMETIC",
    }
    lines = [
        f"Outcome: {labels.get(result.outcome, result.outcome)}",
        f"Property: {result.property}, tier: {result.tier}",
        f"Evidence: {result.evidence_kind}",
    ]
    if result.witness_point is not None:
        real, imaginary = result.witness_point
        lines.append(f"Worst screened point: z = {real:g} {imaginary:g}i")
    lines.append("Numerical screens are never proofs; enclosures are not sharpness.")
    _write_utf8("\n".join(lines))


def _find_counterexample(args: argparse.Namespace) -> None:
    coefficients = _comma_separated_numbers(args.coefficients, label="coefficients")
    hint = None
    if args.hint is not None:
        parts = _comma_separated_numbers(args.hint, label="hint")
        if len(parts) != 2:
            raise InvalidInputError("hint must have the form real,imaginary")
        hint = (parts[0], parts[1])
    result = find_counterexample(
        coefficients, property=args.property, witness_hint=hint
    )
    if args.json:
        _write(result.to_dict(), as_json=True)
        return
    if result.certified:
        verdict = "CERTIFIED COUNTEREXAMPLE" if args.property == "starlike" else "CERTIFIED CRITERION VIOLATION"
    else:
        verdict = "NO CERTIFIED VIOLATION FOUND (screen only)"
    lines = [
        verdict,
        f"Property: {result.property}",
        (
            f"Certified point: z = {result.point[0]:g} {result.point[1]:g}i"
            if result.point is not None
            else "Certified point: none"
        ),
        f"Interval: [{result.interval_lower:g}, {result.interval_upper:g}]",
        f"Threshold: {result.threshold:g}, margin: {result.margin:g}",
        "Scope: grid locates the candidate; interval arithmetic certifies the final point",
    ]
    _write_utf8("\n".join(lines))


def _plot(args: argparse.Namespace) -> None:
    kind = args.kind
    generator = args.generator
    if kind not in {"domain", "coefficients", "real-part", "phase"}:
        if kind is not None and generator is None:
            generator = kind
        kind = "domain"
    if kind is None:
        kind = "domain"
    coefficients = None
    if args.coefficients is not None:
        coefficients = tuple(
            _comma_separated_numbers(args.coefficients, label="coefficients")
        )
    result = write_plot(
        kind,
        args.output,
        generator=generator,
        coefficients=coefficients,
        order=args.order,
        grid=args.grid,
        rmax=args.radius,
        rings=args.rings,
        spokes=args.spokes,
    )
    print(f"Wrote {result.output}")
    print(f"Kind: {kind}")
    print(f"Model: {result.approximation}")
    if kind == "domain":
        print("Scope: visualization of a finite Taylor polynomial; not a proof of the full image domain")
    else:
        print("Scope: sampled numerical visualization; not a proof")


def _parse_sbox(value: str) -> tuple[int, ...]:
    if len(value) > 4096:
        raise ResourceLimitError("sbox input is too long")
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 256 or any(not part for part in parts):
        raise InvalidInputError("sbox must be exactly 256 comma-separated integers")
    try:
        entries = [int(part) for part in parts]
    except ValueError as exc:
        raise InvalidInputError("sbox must be exactly 256 comma-separated integers") from exc
    if any(entry < 0 or entry > 255 for entry in entries):
        raise InvalidInputError("sbox entries must lie in [0, 255]")
    return tuple(entries)


def _crypto_lab(args: argparse.Namespace) -> None:
    from . import lab

    lab.require_lab()
    if args.action in {"structure", "compare"}:
        from .lab import AES_SBOX, IDENTITY_SBOX, sbox_structure

        if args.reference == "aes":
            selected = AES_SBOX
        elif args.reference == "identity":
            selected = IDENTITY_SBOX
        else:
            if args.sbox is None:
                raise InvalidInputError("provide --reference or --sbox")
            selected = _parse_sbox(args.sbox)
        if args.action == "structure":
            payload = sbox_structure(selected)
        else:
            from .lab import compare_sbox

            payload = compare_sbox(selected)
        if args.json:
            _write(payload, as_json=True)
        else:
            _write_utf8(
                "S-box diagnostic structure\n"
                f"  NL avg: {payload['metrics']['NL_avg']}\n"
                f"  SAC avg: {payload['metrics']['SAC_avg']:.4f}\n"
                f"  DDT/LAT: {len(payload.get('DDT', ())) or 'comparison only'}\n"
                "Benchmark diagnostics only; never a security claim."
            )
        return
    if args.action == "leaderboard":
        from .lab import leaderboard

        rows = list(leaderboard(scope=args.scope))
        if args.json:
            _write(rows, as_json=True)
        else:
            _write(rows, as_json=False)
        return
    if args.action == "metrics":
        if args.reference is not None:
            if args.reference == "aes":
                from .lab import AES_SBOX, sbox_metrics

                metrics = sbox_metrics(AES_SBOX)
                label = "aes"
            elif args.reference == "identity":
                from .lab import IDENTITY_SBOX, sbox_metrics

                metrics = sbox_metrics(IDENTITY_SBOX)
                label = "identity"
            else:
                raise InvalidInputError("reference must be 'aes' or 'identity'")
        else:
            from .lab import sbox_metrics

            metrics = sbox_metrics(_parse_sbox(args.sbox))
            label = "user-supplied"
        if args.json:
            from .lab import sbox_metrics_record

            _write(sbox_metrics_record(metrics, label=label), as_json=True)
            return
        lines = [
            f"S-box benchmark metrics ({label})",
            f"  bijection: {metrics['bijection']}",
            f"  NL (avg / min): {metrics['NL_avg']} / {metrics['NL_min']}",
            f"  SAC avg: {metrics['SAC_avg']:.4f}",
            f"  BIC avg: {metrics['BIC_avg']:.4f}",
            f"  DP: {metrics['DP']:.6g}",
            f"  LP: {metrics['LP']:.6g}",
            "Benchmark metrics only; never a security claim.",
        ]
        _write_utf8("\n".join(lines))
        return
    from .lab import construct_sbox, sbox_metrics

    sbox = construct_sbox(
        args.function, key=args.key.encode("utf-8"), construction=args.construction
    )
    metrics = sbox_metrics(sbox)
    if args.json:
        from .lab import sbox_metrics_record

        _write(
            sbox_metrics_record(
                metrics, label=f"constructed:{args.function}:{args.construction}"
            ),
            as_json=True,
        )
        return
    lines = [
        f"Constructed S-box from {args.function} ({args.construction})",
        f"  bijection: {metrics['bijection']}",
        f"  NL (avg / min): {metrics['NL_avg']} / {metrics['NL_min']}",
        f"  SAC avg: {metrics['SAC_avg']:.4f}",
        f"  BIC avg: {metrics['BIC_avg']:.4f}",
        f"  DP: {metrics['DP']:.6g}",
        f"  LP: {metrics['LP']:.6g}",
        "Benchmark metrics only; never a security claim.",
    ]
    _write_utf8("\n".join(lines))


def _image_lab(args: argparse.Namespace) -> None:
    from . import lab

    lab.require_lab()
    import numpy as np

    if args.action == "sample":
        from .lab import sample_image

        array = sample_image(seed=args.seed, size=args.size)
        np.save(args.output, array)
        print(f"Wrote deterministic sample {array.shape} to {args.output}")
        return
    if args.action == "metrics":
        from .lab import image_metrics, image_metrics_record

        reference = np.load(args.ref)
        test = np.load(args.test)
        metrics = image_metrics(reference, test)
        if args.json:
            _write(image_metrics_record(metrics), as_json=True)
            return
        lines = [
            "Image quality metrics (empirical)",
            (
                "  PSNR: inf"
                if metrics["PSNR"] == float("inf")
                else f"  PSNR: {metrics['PSNR']:.4f}"
            ),
            f"  SSIM: {metrics['SSIM']:.6f}",
            f"  GMSD: {metrics['GMSD']:.6f}",
            f"  MSE: {metrics['MSE']:.6g}",
            f"  RMSE: {metrics['RMSE']:.6g}",
            f"  PCC: {metrics['PCC']:.6f}",
            f"  MAE: {metrics['MAE']:.6g}",
            "Empirical image statistics, not a GFT theorem.",
        ]
        _write_utf8("\n".join(lines))
        return
    from .lab import apply_image_transform

    array = np.load(args.input)
    output = apply_image_transform(
        array,
        args.operation,
        gain=args.gain,
        taps=args.taps,
        function=args.function,
    )
    np.save(args.output, output)
    function_label = f" ({args.function})" if args.function else ""
    print(f"Wrote {args.operation}{function_label} transform {output.shape} to {args.output}")
    print("Scope: empirical convolution transform; not a GFT theorem")


_ARTIFACT_ASSUMPTIONS = (
    "records are transcribed from the versioned website snapshot",
    "sharpness, enclosure, and novelty semantics remain those of the source record",
)


def _artifact_emit(
    args: argparse.Namespace,
    *,
    result_type: str,
    record: Any,
    canonical_inputs: dict[str, Any] | None = None,
    evidence_status: str = "screened",
    record_count: int | None = None,
    verification: VerificationReport | None = None,
) -> None:
    if isinstance(record, list):
        record = {"count": len(record), "rows": record}
    if record_count is None:
        record_count = int(record.get("count", 1)) if isinstance(record, dict) else 1
    verification = verification or VerificationReport(
        (
            VerificationCheck(
                name="artifact_lookup",
                checked="requested baked artifact record",
                expected="present",
                observed="present",
                status=CheckStatus.PASS,
                scope="versioned package data lookup",
            ),
        )
    )
    payload = _artifact_data.snapshot_payload(
        result_type=result_type,
        canonical_inputs={
            key: value
            for key, value in (canonical_inputs or {}).items()
            if value is not None
        },
        record=record,
        evidence_status=evidence_status,
        assumptions=_ARTIFACT_ASSUMPTIONS,
        source_references=("Geometric Function Atlas versioned package snapshot",),
        verification=verification,
        record_count=record_count,
    )
    if args.json:
        _write(payload, as_json=True)
    else:
        _write(record, as_json=False)


def _artifact_snapshot(args: argparse.Namespace) -> None:
    record = (
        _artifact_data.snapshot_verify()
        if args.action == "verify"
        else _artifact_data.snapshot_info()
    )
    _artifact_emit(
        args,
        result_type="snapshot_verify",
        record=record,
        canonical_inputs={"action": args.action},
        record_count=record.get("files_verified", 1),
    )


def _artifact_classes(args: argparse.Namespace) -> None:
    records = _artifact_data.list_classes()
    _artifact_emit(args, result_type="classes", record=records, record_count=len(records))


def _artifact_class(args: argparse.Namespace) -> None:
    _artifact_emit(
        args,
        result_type="classes",
        record=_artifact_data.class_info(args.class_key),
        canonical_inputs={"class_key": args.class_key},
    )


def _artifact_expansion(args: argparse.Namespace) -> None:
    _artifact_emit(
        args,
        result_type="expansion",
        record=_artifact_data.expansion(args.class_key),
        canonical_inputs={"class_key": args.class_key},
    )


def _artifact_bound(args: argparse.Namespace) -> None:
    _artifact_emit(
        args,
        result_type="coefficient_bound",
        record=_artifact_data.coefficient_bound(args.class_key, args.functional_key),
        canonical_inputs={
            "class_key": args.class_key,
            "functional_key": args.functional_key,
        },
    )


def _artifact_proofs(args: argparse.Namespace) -> None:
    record = _artifact_data.list_proofs(
        class_key=args.class_key,
        functional_key=args.functional_key,
        status=args.status,
        search=args.search,
    )
    _artifact_emit(args, result_type="proofs", record=record, record_count=record["count"])


def _artifact_proof(args: argparse.Namespace) -> None:
    _artifact_emit(
        args,
        result_type="proof",
        record=_artifact_data.get_proof(args.name, raw=args.raw),
        canonical_inputs={"name": args.name, "raw": args.raw},
    )


def _artifact_open_problems(args: argparse.Namespace) -> None:
    record = _artifact_data.open_problems(args.kind)
    _artifact_emit(
        args,
        result_type="open_problems",
        record=record,
        canonical_inputs={"kind": args.kind},
        record_count=record["counts"]["enclosures"] + record["counts"]["numerical"],
    )


def _artifact_reconciliation(args: argparse.Namespace) -> None:
    record = _artifact_data.reconciliation(
        class_key=args.class_key,
        functional_key=args.functional_key,
        category=args.category,
    )
    _artifact_emit(
        args,
        result_type="reconciliation",
        record=record,
        canonical_inputs={
            "class_key": args.class_key,
            "functional_key": args.functional_key,
            "category": args.category,
        },
        record_count=record["total"],
    )


def _artifact_references(args: argparse.Namespace) -> None:
    _artifact_emit(args, result_type="references", record=_artifact_data.references())


def _artifact_certificate(args: argparse.Namespace) -> None:
    record = _artifact_data.verify_certificate(args.name)
    checks = [
        VerificationCheck(
            name="artifact_lookup",
            checked="requested certificate record",
            expected="present",
            observed=args.name,
            status=CheckStatus.PASS,
            scope="versioned package data lookup",
        ),
        VerificationCheck(
            name="candidate_attainment",
            checked="functional value matches the stored extremal candidate",
            expected=True,
            observed=record["attained_candidate"],
            status=CheckStatus.PASS if record["attained_candidate"] else CheckStatus.FAIL,
            scope="certificate replay (exact Schur machinery)",
            failure_reason=None if record["attained_candidate"] else "candidate mismatch",
        ),
        VerificationCheck(
            name="upper_bound_consistency",
            checked="replayed value lies within the declared upper bound + slack",
            expected=True,
            observed=record["upper_bound_consistent"],
            status=CheckStatus.PASS if record["upper_bound_consistent"] else CheckStatus.FAIL,
            scope="certificate replay (exact Schur machinery)",
            failure_reason=None if record["upper_bound_consistent"] else "upper-bound mismatch",
        ),
        VerificationCheck(
            name="upper_bound_certification",
            checked="source certificate declares a certified upper bound",
            expected=True,
            observed=record["upper_bound_certified"],
            status=CheckStatus.PASS if record["upper_bound_certified"] else CheckStatus.FAIL,
            scope="versioned certificate metadata; replay does not establish sharpness",
            failure_reason=None if record["upper_bound_certified"] else "upper bound is not certified",
        ),
        VerificationCheck(
            name="sharpness_proof",
            checked="stored certificate proves sharpness, rather than only attainment",
            expected=True,
            observed=record["sharpness_proven"],
            status=CheckStatus.PASS if record["sharpness_proven"] else CheckStatus.SKIP,
            scope="versioned certificate metadata",
            required=False,
        ),
    ]
    _artifact_emit(
        args,
        result_type="certificate_replay",
        record=record,
        canonical_inputs={"name": args.name},
        evidence_status=record["evidence_status"],
        verification=VerificationReport(tuple(checks)),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="geometric-function-atlas",
        description="Reproduce and review Geometric Function Atlas computations.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    walkthrough = subparsers.add_parser(
        "walkthrough", help="run a concise first-use tour with verified examples"
    )
    walkthrough.set_defaults(handler=_walkthrough)

    generators = subparsers.add_parser("generators", help="list built-in generators")
    generators.add_argument("--json", action="store_true", help="emit JSON")
    generators.set_defaults(handler=_generators)

    citation = subparsers.add_parser(
        "citation", help="export BibTeX, RIS, plain-text, or LaTeX citation formats"
    )
    citation.add_argument("--key", required=True)
    citation.add_argument("--title", required=True)
    citation.add_argument("--year", required=True)
    citation.add_argument("--author", default=None)
    citation.add_argument("--url", default="")
    citation.add_argument("--journal")
    citation.add_argument("--doi")
    citation.add_argument("--note")
    citation.add_argument("--accessed")
    citation.add_argument("--format", choices=["BibTeX", "RIS", "Plain", "LaTeX"])
    citation.add_argument("--json", action="store_true", help="emit JSON")
    citation.set_defaults(handler=_citation)

    coefficients = subparsers.add_parser(
        "coefficients", help="compute exact generator Taylor coefficients"
    )
    coefficients.add_argument("generator")
    coefficients.add_argument("--order", type=int, required=True)
    coefficients.add_argument("--json", action="store_true", help="emit JSON")
    coefficients.set_defaults(handler=_coefficients)

    fs = subparsers.add_parser(
        "fekete-szego", help="compute an exact Ma-Minda Fekete-Szego constant"
    )
    fs.add_argument("generator")
    fs.add_argument("--mu", required=True, help="real rational value, e.g. 1/2")
    fs.add_argument("--precision", type=int, default=16)
    fs.add_argument("--json", action="store_true", help="emit JSON")
    fs.set_defaults(handler=_fekete_szego)

    counterexample = subparsers.add_parser(
        "verify-counterexample",
        help="rigorously check a supplied counterexample witness",
    )
    counterexample.add_argument(
        "--coefficients",
        required=True,
        help="comma-separated a2,a3,... for f(z)=z+a2*z^2+...",
    )
    counterexample.add_argument(
        "--point",
        required=True,
        help="witness point as real,imaginary; use --point=-0.75,0 for negatives",
    )
    counterexample.add_argument("--property", default="starlike")
    counterexample.add_argument("--json", action="store_true", help="emit JSON")
    counterexample.set_defaults(handler=_verify_counterexample)

    radii = subparsers.add_parser("radii", help="list directed inclusion radii")
    radii.add_argument("--source")
    radii.add_argument("--target")
    radii.add_argument(
        "--status",
        choices=[status.value for status in RadiusStatus],
    )
    radii.add_argument("--json", action="store_true", help="emit JSON")
    radii.set_defaults(handler=_radii)

    one_radius = subparsers.add_parser(
        "radius", help="show one directed inclusion radius"
    )
    one_radius.add_argument("source")
    one_radius.add_argument("target")
    one_radius.add_argument("--json", action="store_true", help="emit JSON")
    one_radius.set_defaults(handler=_radius)

    radius_recompute = subparsers.add_parser(
        "radius-recompute", help="replay a bounded exact radius computation"
    )
    radius_recompute.add_argument("source")
    radius_recompute.add_argument("target")
    radius_recompute.add_argument("--candidate")
    radius_recompute.add_argument("--dps", type=int, default=50)
    radius_recompute.add_argument("--max-steps", type=int, default=128)
    radius_recompute.add_argument("--json", action="store_true", help="emit JSON")
    radius_recompute.set_defaults(handler=_radius_recompute)

    radius_attainment = subparsers.add_parser(
        "radius-attainment", help="verify a reviewed radius contact and attainment chain"
    )
    radius_attainment.add_argument("source")
    radius_attainment.add_argument("target")
    radius_attainment.add_argument("--dps", type=int, default=50)
    radius_attainment.add_argument("--max-steps", type=int, default=128)
    radius_attainment.add_argument("--json", action="store_true", help="emit JSON")
    radius_attainment.set_defaults(handler=_radius_attainment)

    radius_identify = subparsers.add_parser(
        "radius-identify", help="identify stored radii by exact expression or value"
    )
    radius_identify.add_argument("--value", required=True)
    radius_identify.add_argument("--tolerance", type=float, default=1e-12)
    radius_identify.add_argument("--limit", type=int, default=100)
    radius_identify.add_argument("--json", action="store_true", help="emit JSON")
    radius_identify.set_defaults(handler=_radius_identify)

    radius_audit = subparsers.add_parser(
        "radius-audit", help="audit one directed radius without promoting its status"
    )
    radius_audit.add_argument("source")
    radius_audit.add_argument("target")
    radius_audit.add_argument("--candidate")
    radius_audit.add_argument("--dps", type=int, default=50)
    radius_audit.add_argument("--max-steps", type=int, default=128)
    radius_audit.add_argument("--json", action="store_true", help="emit JSON")
    radius_audit.set_defaults(handler=_radius_audit)

    replay = subparsers.add_parser(
        "verify-radius-certificate",
        aliases=["verify-radius"],
        help="replay a reviewed exact directed-radius certificate",
    )
    replay.add_argument("source")
    replay.add_argument("target")
    replay.add_argument("--candidate")
    replay.add_argument("--dps", type=int, default=50)
    replay.add_argument("--max-steps", type=int, default=128)
    replay.add_argument("--json", action="store_true", help="emit JSON")
    replay.set_defaults(handler=_verify_radius_certificate)

    classes = subparsers.add_parser("classes", help="list Ma-Minda classes")
    classes.add_argument("--json", action="store_true", help="emit JSON")
    classes.set_defaults(handler=_classes)

    class_check = subparsers.add_parser(
        "class-check", help="check Ma-Minda admissibility for one class"
    )
    class_check.add_argument("key")
    class_check.add_argument("--json", action="store_true", help="emit JSON")
    class_check.set_defaults(handler=_class_check)

    class_member = subparsers.add_parser(
        "class-member", help="screen f in S*(phi) for one class"
    )
    class_member.add_argument("key")
    class_member.add_argument(
        "--coefficients",
        required=True,
        help="comma-separated a2,a3,... for f(z)=z+a2*z^2+...",
    )
    class_member.add_argument("--json", action="store_true", help="emit JSON")
    class_member.set_defaults(handler=_class_member)

    compare = subparsers.add_parser(
        "compare", help="screen phi_inner(D) subset phi_outer(D)"
    )
    compare.add_argument("inner")
    compare.add_argument("outer")
    compare.add_argument("--json", action="store_true", help="emit JSON")
    compare.set_defaults(handler=_compare)

    extremal = subparsers.add_parser(
        "extremal-coefficients", help="exact extremal coefficients of a class"
    )
    extremal.add_argument("key")
    extremal.add_argument("--order", type=int, default=8)
    extremal.add_argument("--json", action="store_true", help="emit JSON")
    extremal.set_defaults(handler=_extremal)

    verify = subparsers.add_parser(
        "verify", help="verify a function at a cost tier (screen/symbolic/rigorous)"
    )
    verify.add_argument(
        "--coefficients",
        required=True,
        help="comma-separated a2,a3,... for f(z)=z+a2*z^2+...",
    )
    verify.add_argument("--property", default="starlike")
    verify.add_argument("--max-cost", default="screen", choices=["screen", "symbolic", "rigorous"])
    verify.add_argument("--truncation", action="store_true")
    verify.add_argument("--json", action="store_true", help="emit JSON")
    verify.set_defaults(handler=_verify)

    search = subparsers.add_parser(
        "find-counterexample", help="search for and certify a violation point"
    )
    search.add_argument(
        "--coefficients",
        required=True,
        help="comma-separated a2,a3,... for f(z)=z+a2*z^2+...",
    )
    search.add_argument("--property", default="starlike")
    search.add_argument("--hint", help="optional witness hint as real,imaginary")
    search.add_argument("--json", action="store_true", help="emit JSON")
    search.set_defaults(handler=_find_counterexample)

    plot = subparsers.add_parser(
        "plot",
        help=(
            "write a plot (SVG for every kind; domain also supports PNG/TikZ)"
        ),
    )
    plot.add_argument(
        "kind",
        nargs="?",
        help="plot kind, or a generator name for the domain convenience form",
    )
    plot.add_argument("generator", nargs="?", help="built-in generator")
    plot.add_argument("--coefficients", help="advanced: comma-separated a2,a3,...")
    plot.add_argument("--order", type=int, default=12)
    plot.add_argument("--grid", type=int, default=64)
    plot.add_argument("--radius", type=float, default=0.98)
    plot.add_argument("--rings", type=int, default=5)
    plot.add_argument("--spokes", type=int, default=12)
    plot.add_argument(
        "--output",
        required=True,
        help="output path (.svg; domain also accepts .png, .tikz, or .tex)",
    )
    plot.set_defaults(handler=_plot)

    crypto_lab = subparsers.add_parser(
        "crypto-lab", help="S-box construction and benchmark metrics (lab extra)"
    )
    crypto_sub = crypto_lab.add_subparsers(dest="action", required=True)
    crypto_metrics = crypto_sub.add_parser("metrics", help="benchmark an S-box")
    crypto_metrics.add_argument(
        "--reference", choices=["aes", "identity"], help="deterministic reference anchor"
    )
    crypto_metrics.add_argument(
        "--sbox", help="256 comma-separated integers (alternative to --reference)"
    )
    crypto_metrics.add_argument("--json", action="store_true", help="emit JSON")
    crypto_metrics.set_defaults(handler=_crypto_lab)
    crypto_construct = crypto_sub.add_parser("construct", help="construct an S-box")
    crypto_construct.add_argument("function")
    crypto_construct.add_argument("--key", default="gft-registry")
    crypto_construct.add_argument("--construction", default="keyed", choices=["keyed", "direct"])
    crypto_construct.add_argument("--json", action="store_true", help="emit JSON")
    crypto_construct.set_defaults(handler=_crypto_lab)
    for action, help_text in (
        ("structure", "show SAC, DDT, and LAT diagnostic tables"),
        ("compare", "compare metrics with AES and identity references"),
    ):
        crypto_view = crypto_sub.add_parser(action, help=help_text)
        crypto_view.add_argument(
            "--reference", choices=["aes", "identity"], default="identity"
        )
        crypto_view.add_argument(
            "--sbox", help="256 comma-separated integers (alternative to --reference)"
        )
        crypto_view.add_argument("--json", action="store_true", help="emit JSON")
        crypto_view.set_defaults(handler=_crypto_lab)
    crypto_leaderboard = crypto_sub.add_parser(
        "leaderboard", help="rank package metrics or replay the website snapshot"
    )
    crypto_leaderboard.add_argument(
        "--scope",
        choices=["package", "website"],
        default="package",
        help="use the package construction set or the bundled website metric snapshot",
    )
    crypto_leaderboard.add_argument("--json", action="store_true", help="emit JSON")
    crypto_leaderboard.set_defaults(handler=_crypto_lab)

    image_lab = subparsers.add_parser(
        "image-lab", help="image metrics and transforms (lab extra)"
    )
    image_sub = image_lab.add_subparsers(dest="action", required=True)
    image_metrics_parser = image_sub.add_parser("metrics", help="full-reference metrics")
    image_metrics_parser.add_argument("--ref", required=True, help="reference .npy file")
    image_metrics_parser.add_argument("--test", required=True, help="test .npy file")
    image_metrics_parser.add_argument("--json", action="store_true", help="emit JSON")
    image_metrics_parser.set_defaults(handler=_image_lab)
    image_transform = image_sub.add_parser("transform", help="apply a convolution transform")
    image_transform.add_argument("--input", required=True, help="input .npy file")
    image_transform.add_argument("--output", required=True, help="output .npy file")
    image_transform.add_argument(
        "--operation", required=True, choices=["smooth", "sharpen", "edge"]
    )
    image_transform.add_argument("--gain", type=float, default=1.0)
    image_transform.add_argument("--taps", type=int, default=3, choices=[3, 5, 7])
    image_transform.add_argument("--function", choices=SPECIAL_FUNCTIONS)
    image_transform.set_defaults(handler=_image_lab)
    image_sample = image_sub.add_parser("sample", help="write a deterministic sample array")
    image_sample.add_argument("--output", required=True, help="output .npy file")
    image_sample.add_argument("--seed", type=int, default=0)
    image_sample.add_argument("--size", type=int, default=32)
    image_sample.set_defaults(handler=_image_lab)

    snapshot = subparsers.add_parser(
        "snapshot", help="install, inspect, or verify a registry snapshot"
    )
    snapshot_subparsers = snapshot.add_subparsers(
        dest="snapshot_command", required=True
    )

    snapshot_info_parser = snapshot_subparsers.add_parser(
        "info", help="inspect immutable SQLite metadata"
    )
    snapshot_info_parser.add_argument("path")
    snapshot_info_parser.add_argument("--manifest")
    snapshot_info_parser.add_argument("--json", action="store_true", help="emit JSON")
    snapshot_info_parser.set_defaults(handler=_snapshot_info)

    snapshot_verify_parser = snapshot_subparsers.add_parser(
        "verify", help="verify snapshot hashes and integrity"
    )
    snapshot_verify_parser.add_argument("path")
    snapshot_verify_parser.add_argument("--manifest", required=True)
    snapshot_verify_parser.add_argument("--json", action="store_true", help="emit JSON")
    snapshot_verify_parser.set_defaults(handler=_snapshot_verify)

    snapshot_install_parser = snapshot_subparsers.add_parser(
        "install", help="verify and atomically install a snapshot"
    )
    snapshot_install_parser.add_argument("source")
    snapshot_install_parser.add_argument("destination")
    snapshot_install_parser.add_argument("--manifest", required=True)
    snapshot_install_parser.add_argument("--json", action="store_true", help="emit JSON")
    snapshot_install_parser.set_defaults(handler=_snapshot_install)

    stats = subparsers.add_parser("stats", help="report registry snapshot statistics")
    _add_snapshot_options(stats)
    stats.add_argument("--json", action="store_true", help="emit JSON")
    stats.set_defaults(handler=_snapshot_stats)

    snapshot_search = subparsers.add_parser(
        "search", help="search families, papers, or evidence"
    )
    snapshot_search.add_argument("query")
    snapshot_search.add_argument("--kind", choices=("family", "paper", "proof"))
    _add_snapshot_options(snapshot_search)
    _add_limit(snapshot_search)
    snapshot_search.add_argument("--json", action="store_true", help="emit JSON")
    snapshot_search.set_defaults(handler=_snapshot_search)

    families = subparsers.add_parser("families", help="list function families")
    families.add_argument("--group")
    _add_snapshot_options(families)
    _add_limit(families)
    families.add_argument("--json", action="store_true", help="emit JSON")
    families.set_defaults(handler=_snapshot_families)

    family = subparsers.add_parser("family", help="inspect one function family")
    family.add_argument("identifier")
    _add_snapshot_options(family)
    _add_limit(family)
    family.add_argument("--json", action="store_true", help="emit JSON")
    family.set_defaults(handler=_snapshot_family)

    facts = subparsers.add_parser("facts", help="query family facts")
    facts.add_argument("identifier")
    facts.add_argument("--property")
    facts.add_argument("--status")
    _add_snapshot_options(facts)
    _add_limit(facts)
    facts.add_argument("--json", action="store_true", help="emit JSON")
    facts.set_defaults(handler=_snapshot_facts)

    evidence = subparsers.add_parser("evidence", help="query family evidence")
    evidence.add_argument("identifier")
    _add_snapshot_options(evidence)
    _add_limit(evidence)
    evidence.add_argument("--json", action="store_true", help="emit JSON")
    evidence.set_defaults(handler=_snapshot_evidence)

    runs = subparsers.add_parser("runs", help="query verification runs")
    runs.add_argument("identifier")
    _add_snapshot_options(runs)
    _add_limit(runs)
    runs.add_argument("--json", action="store_true", help="emit JSON")
    runs.set_defaults(handler=_snapshot_runs)

    papers = subparsers.add_parser("papers", help="search papers and facets")
    papers.add_argument("--query")
    papers.add_argument("--author")
    papers.add_argument("--year", type=int)
    papers.add_argument("--journal")
    papers.add_argument("--doi")
    papers.add_argument("--citation", help="search DOI, BibTeX, journal, or filename")
    papers.add_argument("--class-key")
    papers.add_argument("--tag")
    papers.add_argument("--claim")
    papers.add_argument("--decade", type=int)
    papers.add_argument("--msc")
    papers.add_argument("--theorem")
    papers.add_argument(
        "--has-theorems",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="filter papers by presence of structured theorem records",
    )
    papers.add_argument(
        "--sort", choices=("relevance", "year", "title"), default="relevance"
    )
    _add_snapshot_options(papers)
    _add_limit(papers)
    papers.add_argument("--json", action="store_true", help="emit JSON")
    papers.set_defaults(handler=_snapshot_papers)

    paper_facets = subparsers.add_parser(
        "paper-facets", help="list website paper-explorer facet populations"
    )
    _add_snapshot_options(paper_facets)
    paper_facets.add_argument("--json", action="store_true", help="emit JSON")
    paper_facets.set_defaults(handler=_snapshot_paper_facets)

    functions = subparsers.add_parser(
        "functions", help="list legacy registry function rows"
    )
    functions.add_argument("--query")
    functions.add_argument("--tag")
    functions.add_argument("--category")
    _add_snapshot_options(functions)
    _add_limit(functions)
    functions.add_argument("--json", action="store_true", help="emit JSON")
    functions.set_defaults(handler=_snapshot_functions)

    function = subparsers.add_parser("function", help="show one legacy function row")
    function.add_argument("identifier")
    _add_snapshot_options(function)
    function.add_argument("--json", action="store_true", help="emit JSON")
    function.set_defaults(handler=_snapshot_function)

    tags = subparsers.add_parser("tags", help="list registry tags and populations")
    tags.add_argument("--query")
    tags.add_argument("--category")
    _add_snapshot_options(tags)
    _add_limit(tags)
    tags.add_argument("--json", action="store_true", help="emit JSON")
    tags.set_defaults(handler=_snapshot_tags)

    paper = subparsers.add_parser("paper", help="inspect one paper and its claims")
    paper.add_argument("identifier")
    _add_snapshot_options(paper)
    _add_limit(paper)
    paper.add_argument("--json", action="store_true", help="emit JSON")
    paper.set_defaults(handler=_snapshot_paper)

    applications = subparsers.add_parser(
        "applications", help="list conservative application associations"
    )
    applications.add_argument("area", nargs="?")
    _add_snapshot_options(applications)
    _add_limit(applications)
    applications.add_argument("--json", action="store_true", help="emit JSON")
    applications.set_defaults(handler=_snapshot_applications)

    stored_counterexamples = subparsers.add_parser(
        "counterexamples", help="list stored counterexample records"
    )
    stored_counterexamples.add_argument("identifier", nargs="?")
    stored_counterexamples.add_argument("--property")
    _add_snapshot_options(stored_counterexamples)
    _add_limit(stored_counterexamples)
    stored_counterexamples.add_argument("--json", action="store_true", help="emit JSON")
    stored_counterexamples.set_defaults(handler=_snapshot_counterexamples)

    aliases = subparsers.add_parser("aliases", help="list snapshot class aliases")
    aliases.add_argument("query", nargs="?")
    _add_snapshot_options(aliases)
    _add_limit(aliases)
    aliases.add_argument("--json", action="store_true", help="emit JSON")
    aliases.set_defaults(handler=_snapshot_aliases)

    normalize_class = subparsers.add_parser(
        "normalize-class", help="normalize a stored class name"
    )
    normalize_class.add_argument("text")
    _add_snapshot_options(normalize_class)
    normalize_class.add_argument("--json", action="store_true", help="emit JSON")
    normalize_class.set_defaults(handler=_snapshot_normalize_class)

    hierarchy = subparsers.add_parser(
        "hierarchy", help="list stored property implications"
    )
    hierarchy.add_argument("property", nargs="?")
    _add_snapshot_options(hierarchy)
    _add_limit(hierarchy)
    hierarchy.add_argument("--json", action="store_true", help="emit JSON")
    hierarchy.set_defaults(handler=_snapshot_hierarchy)

    artifact_snapshot = subparsers.add_parser(
        "artifact-snapshot", help="inspect or verify the baked scientific artifacts"
    )
    artifact_snapshot.add_argument("action", choices=["info", "verify"])
    artifact_snapshot.add_argument("--json", action="store_true", help="emit JSON")
    artifact_snapshot.set_defaults(handler=_artifact_snapshot)

    artifact_classes = subparsers.add_parser(
        "artifact-classes", help="list the exact baked 39-class catalog"
    )
    artifact_classes.add_argument("--json", action="store_true", help="emit JSON")
    artifact_classes.set_defaults(handler=_artifact_classes)

    artifact_class = subparsers.add_parser(
        "class", help="show one baked class and its exact generator coefficients"
    )
    artifact_class.add_argument("class_key")
    artifact_class.add_argument("--json", action="store_true", help="emit JSON")
    artifact_class.set_defaults(handler=_artifact_class)

    expansion = subparsers.add_parser(
        "expansion", help="look up a baked Schur-parameter expansion"
    )
    expansion.add_argument("class_key")
    expansion.add_argument("--json", action="store_true", help="emit JSON")
    expansion.set_defaults(handler=_artifact_expansion)

    bound = subparsers.add_parser(
        "coefficient-bound", help="look up a baked coefficient bound"
    )
    bound.add_argument("class_key")
    bound.add_argument("functional_key", nargs="?")
    bound.add_argument("--json", action="store_true", help="emit JSON")
    bound.set_defaults(handler=_artifact_bound)

    proofs = subparsers.add_parser("proofs", help="list baked proof certificates")
    proofs.add_argument("--class", dest="class_key")
    proofs.add_argument("--functional", dest="functional_key")
    proofs.add_argument("--status")
    proofs.add_argument("--search")
    proofs.add_argument("--json", action="store_true", help="emit JSON")
    proofs.set_defaults(handler=_artifact_proofs)

    proof = subparsers.add_parser("proof", help="show one baked proof certificate")
    proof.add_argument("name")
    proof.add_argument("--raw", action="store_true")
    proof.add_argument("--json", action="store_true", help="emit JSON")
    proof.set_defaults(handler=_artifact_proof)

    open_problems = subparsers.add_parser(
        "open-problems", help="list baked enclosures and numerical conjectures"
    )
    open_problems.add_argument(
        "--kind", default="all", choices=["all", "enclosure", "numerical"]
    )
    open_problems.add_argument("--json", action="store_true", help="emit JSON")
    open_problems.set_defaults(handler=_artifact_open_problems)

    reconciliation = subparsers.add_parser(
        "reconciliation", help="show baked literature-reconciliation rows"
    )
    reconciliation.add_argument("--class", dest="class_key")
    reconciliation.add_argument("--functional", dest="functional_key")
    reconciliation.add_argument("--category")
    reconciliation.add_argument("--json", action="store_true", help="emit JSON")
    reconciliation.set_defaults(handler=_artifact_reconciliation)

    references = subparsers.add_parser(
        "references", help="print the baked method-reference document"
    )
    references.add_argument("--json", action="store_true", help="emit JSON")
    references.set_defaults(handler=_artifact_references)

    certificate = subparsers.add_parser(
        "verify-certificate", help="replay one baked Schur certificate"
    )
    certificate.add_argument("name")
    certificate.add_argument("--json", action="store_true", help="emit JSON")
    certificate.set_defaults(handler=_artifact_certificate)

    return parser


def _silence_broken_pipe() -> None:
    """Redirect a dead stdout to devnull so shutdown flush stays quiet."""

    try:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
    except (AttributeError, OSError, ValueError):
        pass


def main(argv: Sequence[str] | None = None) -> int:
    try:
        return _main(argv)
    except BrokenPipeError:
        # A closed consumer pipe (for example `gfa ... | head`) is an I/O
        # condition, not an operation failure: exit quietly with the
        # dedicated code and no traceback.
        _silence_broken_pipe()
        return EXIT_BROKEN_PIPE


def _main(argv: Sequence[str] | None) -> int:
    parser = _parser()
    command_line = list(sys.argv[1:] if argv is None else argv)
    wants_json = "--json" in command_line
    if wants_json:
        parse_errors = io.StringIO()
        try:
            with contextlib.redirect_stderr(parse_errors):
                args = parser.parse_args(command_line)
        except SystemExit as exc:
            if exc.code == 0:
                raise
            payload = failure_payload(
                FailureState.INVALID_INPUT,
                parse_errors.getvalue().strip() or "invalid command-line arguments",
            )
            validate_error_payload(payload)
            _write_utf8(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                )
            )
            return EXIT_INVALID_INPUT
    else:
        args = parser.parse_args(command_line)
    try:
        args.handler(args)
    except (
        CorruptArtifactError,
        UnresolvedError,
        UnsupportedError,
        ResourceLimitError,
        InvalidInputError,
        KeyError,
        TypeError,
        ValueError,
        ImportError,
        _CommandFailure,
    ) as exc:
        if isinstance(exc, _CommandFailure):
            if getattr(args, "json", False):
                _write(exc.payload, as_json=True)
            return EXIT_CODES[exc.state]
        state = _failure_state(exc)
        if getattr(args, "json", False):
            payload = failure_payload(state, str(exc))
            validate_error_payload(payload)
            _write_utf8(
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                )
            )
            return EXIT_CODES[state]
        print(f"{parser.prog}: error: {exc}", file=sys.stderr)
        return EXIT_CODES[state]
    return EXIT_SUCCESS


def _failure_state(exc: Exception) -> str:
    if isinstance(exc, CorruptArtifactError):
        return FailureState.CORRUPT_ARTIFACT.value
    if isinstance(exc, UnresolvedError):
        return FailureState.UNRESOLVED.value
    if isinstance(exc, UnsupportedError):
        return FailureState.UNSUPPORTED.value
    if isinstance(exc, ResourceLimitError):
        return FailureState.RESOURCE_LIMIT.value
    if isinstance(exc, ImportError):
        return FailureState.UNSUPPORTED.value
    return FailureState.INVALID_INPUT.value
