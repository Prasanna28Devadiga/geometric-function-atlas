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

from .catalog import get_generator, list_generators
from .classes import (
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    list_classes,
)
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
from .counterexamples import find_counterexample, verify_counterexample
from .fekete_szego import fekete_szego
from .plotting import write_plot
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
    coefficients = None
    if args.coefficients is not None:
        coefficients = tuple(
            _comma_separated_numbers(args.coefficients, label="coefficients")
        )
    result = write_plot(
        args.kind,
        args.output,
        generator=args.generator,
        coefficients=coefficients,
        order=args.order,
        grid=args.grid,
        rmax=args.radius,
        rings=args.rings,
        spokes=args.spokes,
    )
    print(f"Wrote {result.output}")
    print(f"Kind: {args.kind}")
    print(f"Model: {result.approximation}")
    if args.kind == "domain":
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
        array, args.operation, gain=args.gain, taps=args.taps
    )
    np.save(args.output, output)
    print(f"Wrote {args.operation} transform {output.shape} to {args.output}")
    print("Scope: empirical convolution transform; not a GFT theorem")


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
        "plot", help="write an SVG plot (domain, coefficients, real-part, phase)"
    )
    plot.add_argument("kind", choices=["domain", "coefficients", "real-part", "phase"])
    plot.add_argument("generator", nargs="?", help="built-in generator")
    plot.add_argument("--coefficients", help="advanced: comma-separated a2,a3,...")
    plot.add_argument("--order", type=int, default=12)
    plot.add_argument("--grid", type=int, default=64)
    plot.add_argument("--radius", type=float, default=0.98)
    plot.add_argument("--rings", type=int, default=5)
    plot.add_argument("--spokes", type=int, default=12)
    plot.add_argument("--output", required=True, help="output SVG path")
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
    image_transform.set_defaults(handler=_image_lab)
    image_sample = image_sub.add_parser("sample", help="write a deterministic sample array")
    image_sample.add_argument("--output", required=True, help="output .npy file")
    image_sample.add_argument("--seed", type=int, default=0)
    image_sample.add_argument("--size", type=int, default=32)
    image_sample.set_defaults(handler=_image_lab)

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
    if isinstance(exc, ImportError):
        return FailureState.UNSUPPORTED.value
    return FailureState.INVALID_INPUT.value
