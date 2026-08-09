"""Public API for reproducible Geometric Function Atlas computations."""

from .catalog import get_generator, list_generators
from .coefficients import GeneratorSeriesResult, generator_series, taylor_coefficients
from .fekete_szego import FeketeSzegoResult, fekete_szego
from .models import Generator
from .models import Z as z
from .version import __version__

__all__ = [
    "FeketeSzegoResult",
    "Generator",
    "GeneratorSeriesResult",
    "__version__",
    "fekete_szego",
    "generator_series",
    "get_generator",
    "list_generators",
    "taylor_coefficients",
    "z",
]
