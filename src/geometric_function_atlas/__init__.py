"""Public API for reproducible Geometric Function Atlas computations."""

from .catalog import get_generator, list_generators
from .coefficients import GeneratorSeriesResult, generator_series, taylor_coefficients
from .contracts import (  # noqa: F401
    RESULT_SCHEMA_VERSION,
    CheckStatus,
    CorruptArtifactError,
    FailureState,
    InvalidInputError,
    LiteratureStatus,
    ResourceLimitError,
    UnresolvedError,
    UnsupportedError,
    VerificationCheck,
    VerificationReport,
    failure_payload,
    load_error_schema,
    load_result_schema,
    validate_error_payload,
    validate_result_payload,
)
from .counterexamples import CounterexampleResult, verify_counterexample
from .fekete_szego import FeketeSzegoResult, fekete_szego
from .implementation_registry import (  # noqa: F401
    get_trusted_implementation,
    list_trusted_implementations,
)
from .models import Generator
from .models import Z as z
from .plotting import (
    ConformalGrid,
    DomainPlotResult,
    conformal_grid,
    generator_function_coefficients,
    write_domain_plot,
)
from .version import __version__

__all__ = [
    "ConformalGrid",
    "CounterexampleResult",
    "DomainPlotResult",
    "FeketeSzegoResult",
    "Generator",
    "GeneratorSeriesResult",
    "__version__",
    "conformal_grid",
    "fekete_szego",
    "generator_function_coefficients",
    "generator_series",
    "get_generator",
    "list_generators",
    "taylor_coefficients",
    "verify_counterexample",
    "write_domain_plot",
    "z",
]
