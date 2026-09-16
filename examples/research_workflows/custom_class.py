"""Investigate an exact caller-defined Ma–Minda class end to end.

The template specializes the starlike-of-order-alpha generator

    phi_alpha(z) = (1 + (1 - 2*alpha) z) / (1 - z)

at an exact rational alpha.  Edit ``build_generator`` to study another exact
parameter specialization; free symbolic parameters are deliberately rejected
by :class:`Generator` because the numerical screens require concrete values.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sympy as sp

from geometric_function_atlas import (
    Generator,
    class_admissibility,
    class_containment_screen,
    class_extremal_coefficients,
    class_member_screen,
    fekete_szego,
    write_domain_plot,
    write_research_bundle_manifest,
    z,
)
from geometric_function_atlas.version import __version__


def build_generator(alpha: sp.Rational) -> Generator:
    """Construct one exact starlike-of-order-alpha generator."""

    if not isinstance(alpha, sp.Rational):
        raise TypeError("alpha must be an exact SymPy Rational")
    if not 0 <= alpha < 1:
        raise ValueError("alpha must satisfy 0 <= alpha < 1")
    return Generator(
        key=f"starlike_order_{alpha.p}_{alpha.q}",
        name=f"Starlike of order {alpha}",
        expression=(1 + (1 - 2 * alpha) * z) / (1 - z),
        citation=f"Caller-defined exact specialization alpha={alpha}",
    )


def solve(
    alpha: sp.Rational | None = None, order: int = 4
) -> tuple[dict, Generator]:
    """Return exact results, explicitly labeled screens, and provenance."""

    if alpha is None:
        default_alpha = sp.Rational(1, 4)
        if not isinstance(default_alpha, sp.Rational):
            raise ArithmeticError("SymPy failed to construct the default rational")
        alpha = default_alpha
    if not isinstance(alpha, sp.Rational):
        raise TypeError("alpha must be an exact SymPy Rational")
    if isinstance(order, bool) or not isinstance(order, int) or not 2 <= order <= 12:
        raise ValueError("order must be an integer between 2 and 12")
    generator = build_generator(alpha)
    admissibility = class_admissibility(generator)
    coefficients = class_extremal_coefficients(generator, order=order)
    member = sp.simplify(z / (1 - z) ** (2 * (1 - alpha)))
    residual = sp.simplify(z * sp.diff(member, z) / member - generator.expression)
    if residual != 0:
        raise ArithmeticError("canonical-member logarithmic derivative identity failed")

    mu_values = (sp.Integer(0), sp.Rational(1, 2), sp.Integer(1))
    bounds = []
    for mu in mu_values:
        result = fekete_szego(generator, mu=str(mu))
        bounds.append(
            {
                "mu": str(mu),
                "bound": str(result.value),
                "record": result.to_dict(),
            }
        )

    # This is only a screen of a finite Taylor truncation on |z| <= 1/2.
    # The exact residual above—not this screen—establishes the displayed full
    # analytic canonical member's defining identity.
    truncation_screen = class_member_screen(
        generator,
        [float(value) for value in coefficients],
        max_r=0.5,
    )
    containment_screen = class_containment_screen(
        generator,
        "starlike",
        r_inner=0.9,
    )
    admissibility_record = admissibility.to_dict()
    identity = admissibility_record["canonical_inputs"]["class_key"]
    if any(
        item["record"]["canonical_inputs"]["generator"] != identity
        for item in bounds
    ):
        raise ArithmeticError("custom generator identity drifted between operations")

    return (
        {
            "workflow": "custom_class",
            "question": "What can be established for an exact caller-defined Ma-Minda class?",
            "parameter": {"alpha": str(alpha), "domain": "0 <= alpha < 1"},
            "generator": {
                "key": generator.key,
                "identity": identity,
                "name": generator.name,
                "formula": generator.formula,
                "citation": generator.citation,
                "provenance": "caller_supplied",
            },
            "admissibility_screen": admissibility_record,
            "canonical_member": {
                "formula": str(member),
                "logarithmic_derivative_identity_residual": str(residual),
                "coefficients_a2_onward": [str(value) for value in coefficients],
                "status": "exact identity and exact coefficients",
            },
            "fekete_szego": bounds,
            "finite_truncation_membership_screen": truncation_screen.to_dict(),
            "containment_screen": containment_screen.to_dict(),
            "plot_objects": {},
            "assumptions": [
                "alpha is specialized to an exact rational before computation",
                "admissibility, finite-polynomial membership, and containment are numerical screens with reported checks",
                "Fekete-Szego uses the stated Ma-Minda theorem hypotheses and exact coefficient arithmetic",
                "SVGs are finite Taylor visualizations, not proofs of full image geometry",
            ],
            "novelty_claim": False,
            "package_version": __version__,
        },
        generator,
    )


def write_artifacts(data: dict, generator: Generator, output: Path, *, order: int) -> None:
    """Write deterministic JSON and one domain SVG for each plot object."""

    output.mkdir(parents=True, exist_ok=True)
    for object_name in ("phi", "z*phi", "f_phi"):
        stem = object_name.replace("*", "_times_")
        filename = f"custom_class_{stem}.svg"
        result = write_domain_plot(
            output / filename,
            generator=generator,
            object=object_name,
            order=order,
        )
        data["plot_objects"][object_name] = {
            "artifact": filename,
            "generator_identity": result.generator,
            "object": result.object,
            "approximation": result.approximation,
            "status": "sampled finite-Taylor visualization",
        }
    (output / "custom_class.json").write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    write_research_bundle_manifest(
        output,
        workflow="custom_class",
        entrypoint="examples/research_workflows/custom_class.py",
        parameters={"alpha": data["parameter"]["alpha"], "order": order},
        primary_record="custom_class.json",
        artifacts=(
            "custom_class.json",
            "custom_class_phi.svg",
            "custom_class_z_times_phi.svg",
            "custom_class_f_phi.svg",
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", default="1/4", help="exact rational, for example 1/4")
    parser.add_argument("--order", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        parsed_alpha = sp.Rational(args.alpha)
    except (TypeError, ValueError) as exc:
        parser.error(f"--alpha must be an exact rational: {exc}")
    if not isinstance(parsed_alpha, sp.Rational):
        parser.error("--alpha must be a finite exact rational")
    alpha = parsed_alpha
    data, generator = solve(alpha, args.order)
    write_artifacts(data, generator, args.output, order=args.order)
    print(
        f"{generator.name}: identity={data['generator']['identity']}; "
        f"Fekete-Szego values={[item['bound'] for item in data['fekete_szego']]}"
    )
    print(f"Artifacts: {args.output.resolve()}")


if __name__ == "__main__":
    main()
