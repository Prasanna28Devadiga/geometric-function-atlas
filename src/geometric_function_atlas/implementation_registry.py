"""Closed registry of package-owned computation implementations.

The registry is deliberately explicit. Serialized records may identify an
operation for auditing, but they never provide an import path or executable
code.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .coefficients import generator_series
from .fekete_szego import fekete_szego

_TRUSTED_IMPLEMENTATIONS: dict[str, Callable[..., Any]] = {
    "generator_series": generator_series,
    "fekete_szego": fekete_szego,
}


def list_trusted_implementations() -> tuple[str, ...]:
    """Return the stable names accepted by the trusted implementation registry."""

    return tuple(sorted(_TRUSTED_IMPLEMENTATIONS))


def get_trusted_implementation(name: str) -> Callable[..., Any]:
    """Resolve a package-owned implementation by a closed registry name."""

    try:
        return _TRUSTED_IMPLEMENTATIONS[name]
    except KeyError as exc:
        available = ", ".join(list_trusted_implementations())
        raise KeyError(
            f"unknown trusted implementation {name!r}; available: {available}"
        ) from exc
