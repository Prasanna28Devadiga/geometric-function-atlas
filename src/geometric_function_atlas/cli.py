"""Command-line interface for independent reproduction workflows."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from collections.abc import Sequence
from typing import Any

from .catalog import get_generator, list_generators
from .coefficients import generator_series
from .contracts import (
    CorruptArtifactError,
    FailureState,
    InvalidInputError,
    ResourceLimitError,
    UnresolvedError,
    UnsupportedError,
    failure_payload,
    validate_error_payload,
)
from .counterexamples import verify_counterexample
from .fekete_szego import fekete_szego
from .plotting import write_domain_plot
from .version import __version__

EXIT_SUCCESS = 0
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
            print(f"{row['key']}: {row['formula']} — {row['citation']}")
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


def _plot(args: argparse.Namespace) -> None:
    supplied = None
    if args.coefficients is not None:
        supplied = tuple(
            _comma_separated_numbers(args.coefficients, label="coefficients")
        )
    result = write_domain_plot(
        args.output,
        generator=args.generator,
        coefficients=supplied,
        order=args.order,
        rmax=args.radius,
        rings=args.rings,
        spokes=args.spokes,
    )
    print(f"Wrote {result.output}")
    print(f"Model: {result.approximation}")
    print("Scope: visualization of a finite Taylor polynomial; not a proof of the full image domain")


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

    generators = subparsers.add_parser("generators", help="list built-in generators")
    generators.add_argument("--json", action="store_true", help="emit JSON")
    generators.set_defaults(handler=_generators)

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

    plot = subparsers.add_parser(
        "plot",
        help="draw the image of the disk as a standalone SVG",
    )
    plot.add_argument(
        "generator",
        nargs="?",
        help="built-in generator; plots the truncation f(z)=z*phi(z)",
    )
    plot.add_argument(
        "--coefficients",
        help="advanced: comma-separated a2,a3,... for f(z)=z+a2*z^2+...",
    )
    plot.add_argument("--order", type=int, default=12)
    plot.add_argument("--radius", type=float, default=0.98)
    plot.add_argument("--rings", type=int, default=5)
    plot.add_argument("--spokes", type=int, default=12)
    plot.add_argument("--output", required=True, help="output SVG path")
    plot.set_defaults(handler=_plot)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
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
    ) as exc:
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
    return FailureState.INVALID_INPUT.value
