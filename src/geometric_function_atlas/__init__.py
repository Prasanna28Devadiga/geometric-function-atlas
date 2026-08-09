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
from .fekete_szego import FeketeSzegoResult, fekete_szego
from .implementation_registry import (  # noqa: F401
    get_trusted_implementation,
    list_trusted_implementations,
)
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
