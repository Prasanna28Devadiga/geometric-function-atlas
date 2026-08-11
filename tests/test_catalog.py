from __future__ import annotations

import pytest
import sympy as sp

from geometric_function_atlas import Generator, get_generator, list_generators, z


def test_portfolio_generators_are_available_with_exact_normalization() -> None:
    expected = {
        "bell",
        "cosh_sqrt",
        "crescent",
        "exponential",
        "lemniscate",
        "rational_kr",
        "sigmoid",
        "sine",
    }

    assert expected <= {generator.key for generator in list_generators()}
    for key in expected:
        generator = get_generator(key)
        assert isinstance(generator, Generator)
        assert sp.simplify(generator.expression.subs(generator.variable, 0) - 1) == 0
        assert generator.citation


def test_unknown_generator_fails_with_available_keys() -> None:
    with pytest.raises(KeyError, match="unknown generator 'missing'.*available"):
        get_generator("missing")


def test_generator_is_immutable() -> None:
    generator = get_generator("sine")
    with pytest.raises((AttributeError, TypeError)):
        generator.key = "changed"  # type: ignore[misc]


def test_generator_rejects_string_expression_instead_of_parsing_it() -> None:
    with pytest.raises(TypeError, match="preconstructed SymPy expression"):
        Generator(
            key="unsafe",
            name="Unsafe string",
            expression="1 + z",  # type: ignore[arg-type]
            citation="User supplied",
        )


def test_generator_rejects_undeclared_free_symbols() -> None:
    parameter = sp.Symbol("a")
    with pytest.raises(ValueError, match="undeclared free symbols: a"):
        Generator(
            key="parametric",
            name="Implicit parameter",
            expression=1 + parameter * z,
            citation="User supplied",
        )


def test_same_as_catalog_value_is_still_caller_supplied() -> None:
    from geometric_function_atlas.catalog import generator_artifact_version

    built_in = get_generator("sine")
    clone = Generator(
        key=built_in.key,
        name=built_in.name,
        expression=built_in.expression,
        citation=built_in.citation,
    )

    assert generator_artifact_version(built_in) != "user-supplied"
    assert generator_artifact_version(clone) == "user-supplied"


def test_generator_rejects_evaluate_false_huge_integer_exponent() -> None:
    expression = sp.Add(
        1,
        sp.Mul(
            sp.Pow(sp.Integer(10), sp.Integer(1_000_000_000), evaluate=False),
            z,
            evaluate=False,
        ),
        evaluate=False,
    )

    with pytest.raises(ValueError, match="exponents.*256"):
        Generator(key="huge", name="Huge", expression=expression, citation="Test")


EXPECTED_FULL_CATALOG_KEYS = {
    # named classes from the website source catalog (gft.maminda _NAMED)
    "starlike",
    "lemniscate",
    "exponential",
    "cardioid",
    "sine",
    "rational_kr",
    "crescent",
    "nephroid",
    "sigmoid",
    "bell",
    "tanh",
    "three_leaf",
    "parabolic",
    "cosh_sqrt",
    "cardioid_exp",
    "petal_arcsinh",
    "strip_arctan",
    "bean_tanh",
    "nonconvex_sec",
    "four_leaf",
    "cissoid_diocles",
    # parametric grid classes (same keys as the website source catalog)
    "order_0.25",
    "order_0.5",
    "order_0.75",
    "janowski_A1_B0",
    "janowski_A0.5_B-0.5",
    "janowski_A1_B-0.5",
    "janowski_A0.75_B-0.25",
    "janowski_A0_B-1",
    "strongly_0.25",
    "strongly_0.5",
    "strongly_0.75",
    "limacon_0.3",
    "limacon_0.5",
    "limacon_0.707",
    "booth_0.3",
    "booth_0.7",
    "epicycloid_3",
    "epicycloid_6",
}


def test_full_catalog_matches_website_class_keys() -> None:
    assert {generator.key for generator in list_generators()} == EXPECTED_FULL_CATALOG_KEYS


def test_every_catalog_generator_is_exactly_normalized() -> None:
    for key in EXPECTED_FULL_CATALOG_KEYS:
        generator = get_generator(key)
        assert sp.simplify(generator.expression.subs(generator.variable, 0) - 1) == 0
        assert generator.citation


def test_every_catalog_generator_has_positive_real_first_coefficient() -> None:
    from geometric_function_atlas.coefficients import taylor_coefficients

    for key in EXPECTED_FULL_CATALOG_KEYS:
        b1 = taylor_coefficients(key, order=2)[0]
        assert b1.is_real is True, key
        assert b1.is_positive is True, key


def test_new_function_classes_are_dag_serializable() -> None:
    from geometric_function_atlas.models import canonical_expression_dag

    for key in ("petal_arcsinh", "strip_arctan", "tanh", "bean_tanh", "parabolic"):
        generator = get_generator(key)
        dag = canonical_expression_dag({"phi": generator.expression})
        assert dag["version"] == 1
        assert dag["roots"]["phi"]


def test_catalog_version_identifies_the_expanded_catalog() -> None:
    from geometric_function_atlas.version import GENERATOR_CATALOG_VERSION

    assert len(GENERATOR_CATALOG_VERSION) == len("2026.08.04")

