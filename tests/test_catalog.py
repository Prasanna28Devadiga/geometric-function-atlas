from __future__ import annotations

import pytest
import sympy as sp

from gft_registry import Generator, get_generator, list_generators, z


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
