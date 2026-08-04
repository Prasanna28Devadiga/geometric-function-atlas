"""Curated Ma–Minda generators used by the published radius portfolio."""

from __future__ import annotations

import sympy as sp

from .models import Generator, Z
from .version import GENERATOR_CATALOG_VERSION

_GENERATORS = (
    Generator(
        key="starlike",
        name="Classical starlike class",
        expression=(1 + Z) / (1 - Z),
        citation="Classical starlike class; Janowski (1973) with A=1, B=-1",
    ),
    Generator(
        key="bell",
        name="Bell-number starlike class",
        expression=sp.exp(sp.exp(Z) - 1),
        citation="Cho, Kumar, Kumar & Ravichandran (2019)",
    ),
    Generator(
        key="cosh_sqrt",
        name="Cosh-square-root starlike class",
        expression=sp.cosh(sp.sqrt(Z)),
        citation="Mundalia & Swaminathan (2023)",
    ),
    Generator(
        key="crescent",
        name="Crescent (lune) starlike class",
        expression=Z + sp.sqrt(1 + Z**2),
        citation="Raina & Sokół (2015)",
    ),
    Generator(
        key="exponential",
        name="Exponential starlike class",
        expression=sp.exp(Z),
        citation="Mendiratta, Nagpal & Ravichandran (2015)",
    ),
    Generator(
        key="lemniscate",
        name="Lemniscate starlike class",
        expression=sp.sqrt(1 + Z),
        citation="Sokół & Stankiewicz (1996)",
    ),
    Generator(
        key="rational_kr",
        name="Kumar–Ravichandran rational starlike class",
        expression=(
            1
            + Z
            * ((1 + sp.sqrt(2)) + Z)
            / ((1 + sp.sqrt(2)) * ((1 + sp.sqrt(2)) - Z))
        ),
        citation="Kumar & Ravichandran (2016)",
    ),
    Generator(
        key="sigmoid",
        name="Modified-sigmoid starlike class",
        expression=2 / (1 + sp.exp(-Z)),
        citation="Goel & Kumar (2020)",
    ),
    Generator(
        key="sine",
        name="Sine starlike class",
        expression=1 + sp.sin(Z),
        citation="Cho, Kumar, Kumar & Ravichandran (2019)",
    ),
)

_BY_KEY = {generator.key: generator for generator in _GENERATORS}


def list_generators() -> tuple[Generator, ...]:
    """Return the built-in generators in stable key order."""

    return tuple(sorted(_GENERATORS, key=lambda generator: generator.key))


def get_generator(key: str) -> Generator:
    """Return a built-in generator or fail with a discoverable error."""

    try:
        return _BY_KEY[key]
    except KeyError as exc:
        available = ", ".join(sorted(_BY_KEY))
        raise KeyError(f"unknown generator {key!r}; available: {available}") from exc


def generator_artifact_version(generator: Generator) -> str:
    """Return the catalog version or identify a caller-supplied definition."""

    return (
        GENERATOR_CATALOG_VERSION
        if _BY_KEY.get(generator.key) == generator
        else "user-supplied"
    )
