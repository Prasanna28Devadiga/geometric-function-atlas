"""Command-line interface for independent reproduction workflows."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from typing import Any

from .catalog import get_generator, list_generators
from .coefficients import generator_series
from .fekete_szego import fekete_szego


def _write(payload: Any, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif isinstance(payload, list):
        for row in payload:
            print(f"{row['key']}: {row['formula']} — {row['citation']}")
    else:
        for key, value in payload.items():
            print(f"{key}: {value}")


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


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gft-registry",
        description="Reproduce and review GFT Registry computations.",
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except (KeyError, TypeError, ValueError) as exc:
        parser.error(str(exc))
    return 0
