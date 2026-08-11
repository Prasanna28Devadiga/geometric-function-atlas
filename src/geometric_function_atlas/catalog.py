"""Curated Ma–Minda generators used by the published radius portfolio.

The built-in catalog mirrors the named and parametric generator classes of the
website source catalog (``gft.maminda`` at source commit
:data:`~geometric_function_atlas.version.SOURCE_ARTIFACT_COMMIT`). Each entry is
an exact SymPy expression in :data:`~geometric_function_atlas.models.Z` with
bibliographic provenance; grid classes carry the same keys the website uses so
an expansion can be cross-checked against the site.
"""

from __future__ import annotations

import sympy as sp

from .models import Generator, Z
from .version import GENERATOR_CATALOG_VERSION


def _strongly_starlike(beta: sp.Expr) -> sp.Expr:
    return ((1 + Z) / (1 - Z)) ** beta


def _janowski(a: sp.Expr, b: sp.Expr) -> sp.Expr:
    return (1 + a * Z) / (1 + b * Z)


def _order_class(alpha: sp.Expr) -> sp.Expr:
    return (1 + (1 - 2 * alpha) * Z) / (1 - Z)


def _limacon(s: sp.Expr) -> sp.Expr:
    return (1 + s * Z) ** 2


def _booth(a: sp.Expr) -> sp.Expr:
    return 1 + Z / (1 - a * Z**2)


def _epicycloid(n: int) -> sp.Expr:
    return 1 + sp.Rational(n, n + 1) * Z + Z**n / (n + 1)


_NAMED = (
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
    Generator(
        key="cardioid",
        name="Cardioid starlike class",
        expression=1 + sp.Rational(4, 3) * Z + sp.Rational(2, 3) * Z**2,
        citation="Sharma, Jain & Ravichandran (2016)",
    ),
    Generator(
        key="nephroid",
        name="Nephroid starlike class",
        expression=1 + Z - Z**3 / 3,
        citation="Wani & Swaminathan (2021)",
    ),
    Generator(
        key="tanh",
        name="Tanh starlike class",
        expression=1 + sp.tanh(Z),
        citation="Ullah, Srivastava et al. (2021)",
    ),
    Generator(
        key="three_leaf",
        name="Three-leaf starlike class",
        expression=1 + sp.Rational(4, 5) * Z + Z**4 / 5,
        citation="Gandhi (2020)",
    ),
    Generator(
        key="parabolic",
        name="Parabolic (uniformly convex) class",
        expression=1 + (2 / sp.pi**2) * sp.log((1 + sp.sqrt(Z)) / (1 - sp.sqrt(Z))) ** 2,
        citation="Rønning (1993); Kanas & Wiśniowska conic domains",
    ),
    Generator(
        key="cardioid_exp",
        name="Cardioid-exponential class (1 + z*exp(z))",
        expression=1 + Z * sp.exp(Z),
        citation="Kumar & Gangania (2021)",
    ),
    Generator(
        key="petal_arcsinh",
        name="Petal class (1 + asinh z)",
        expression=1 + sp.asinh(Z),
        citation="Arora & Kumar (2022)",
    ),
    Generator(
        key="strip_arctan",
        name="Strip class (1 + arctan z)",
        expression=1 + sp.atan(Z),
        citation="Kumar & Verma (2023)",
    ),
    Generator(
        key="bean_tanh",
        name="Bean-shaped class (sqrt(1 + tanh z))",
        expression=sp.sqrt(1 + sp.tanh(Z)),
        citation="Kumar & Yadav (2024)",
    ),
    Generator(
        key="nonconvex_sec",
        name="Non-convex class ((1 + z)/cos z)",
        expression=(1 + Z) / sp.cos(Z),
        citation="Kumar & Giri (2024)",
    ),
    Generator(
        key="four_leaf",
        name="Four-leaf starlike class",
        expression=1 + sp.Rational(5, 6) * Z + Z**5 / 6,
        citation="Gandhi; Sunthrayuth et al. (2022)",
    ),
    Generator(
        key="cissoid_diocles",
        name="Cissoid-of-Diocles starlike class",
        expression=1 + Z / ((1 - Z) * (1 + Z / 3)),
        citation="Masih, Ebadian & Yalçın (2019)",
    ),
)

_GRID = (
    Generator(
        key="order_0.25",
        name="Starlike of order 1/4",
        expression=_order_class(sp.Rational(1, 4)),
        citation="Robertson (1936), order alpha",
    ),
    Generator(
        key="order_0.5",
        name="Starlike of order 1/2",
        expression=_order_class(sp.Rational(1, 2)),
        citation="Robertson (1936), order alpha",
    ),
    Generator(
        key="order_0.75",
        name="Starlike of order 3/4",
        expression=_order_class(sp.Rational(3, 4)),
        citation="Robertson (1936), order alpha",
    ),
    Generator(
        key="janowski_A1_B0",
        name="Janowski class S*[1, 0]",
        expression=_janowski(sp.Integer(1), sp.Integer(0)),
        citation="Janowski (1973)",
    ),
    Generator(
        key="janowski_A0.5_B-0.5",
        name="Janowski class S*[1/2, -1/2]",
        expression=_janowski(sp.Rational(1, 2), sp.Rational(-1, 2)),
        citation="Janowski (1973)",
    ),
    Generator(
        key="janowski_A1_B-0.5",
        name="Janowski class S*[1, -1/2]",
        expression=_janowski(sp.Integer(1), sp.Rational(-1, 2)),
        citation="Janowski (1973)",
    ),
    Generator(
        key="janowski_A0.75_B-0.25",
        name="Janowski class S*[3/4, -1/4]",
        expression=_janowski(sp.Rational(3, 4), sp.Rational(-1, 4)),
        citation="Janowski (1973)",
    ),
    Generator(
        key="janowski_A0_B-1",
        name="Janowski class S*[0, -1]",
        expression=_janowski(sp.Integer(0), sp.Integer(-1)),
        citation="Janowski (1973)",
    ),
    Generator(
        key="strongly_0.25",
        name="Strongly starlike class SS*(1/4)",
        expression=_strongly_starlike(sp.Rational(1, 4)),
        citation="Brannan & Kirwan (1969); Stankiewicz",
    ),
    Generator(
        key="strongly_0.5",
        name="Strongly starlike class SS*(1/2)",
        expression=_strongly_starlike(sp.Rational(1, 2)),
        citation="Brannan & Kirwan (1969); Stankiewicz",
    ),
    Generator(
        key="strongly_0.75",
        name="Strongly starlike class SS*(3/4)",
        expression=_strongly_starlike(sp.Rational(3, 4)),
        citation="Brannan & Kirwan (1969); Stankiewicz",
    ),
    Generator(
        key="limacon_0.3",
        name="Limacon class (1 + 3z/10)^2",
        expression=_limacon(sp.Rational(3, 10)),
        citation="Masih & Kanas (2020)",
    ),
    Generator(
        key="limacon_0.5",
        name="Limacon class (1 + z/2)^2",
        expression=_limacon(sp.Rational(1, 2)),
        citation="Masih & Kanas (2020)",
    ),
    Generator(
        key="limacon_0.707",
        name="Limacon class (1 + sqrt(2) z/2)^2",
        expression=_limacon(sp.sqrt(2) / 2),
        citation="Masih & Kanas (2020)",
    ),
    Generator(
        key="booth_0.3",
        name="Booth lemniscate class BS(3/10)",
        expression=_booth(sp.Rational(3, 10)),
        citation="Kargar, Ebadian & Sokół (2019)",
    ),
    Generator(
        key="booth_0.7",
        name="Booth lemniscate class BS(7/10)",
        expression=_booth(sp.Rational(7, 10)),
        citation="Kargar, Ebadian & Sokół (2019)",
    ),
    Generator(
        key="epicycloid_3",
        name="Epicycloid class (2 cusps)",
        expression=_epicycloid(3),
        citation="Gandhi, Gupta, Nagpal & Ravichandran (2022)",
    ),
    Generator(
        key="epicycloid_6",
        name="Epicycloid class (5 cusps)",
        expression=_epicycloid(6),
        citation="Gandhi, Gupta, Nagpal & Ravichandran (2022)",
    ),
)

_GENERATORS = _NAMED + _GRID

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
        if _BY_KEY.get(generator.key) is generator
        else "user-supplied"
    )
