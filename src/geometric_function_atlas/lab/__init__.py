"""Optional application labs behind the ``lab`` extra.

Crypto metrics are benchmark metrics, never security claims; image outputs
are empirical. Attribute access is lazy: importing this package does not
import numpy; numpy is loaded on first use of a lab operation.
"""

from __future__ import annotations

from typing import Any

_CRYPTO_EXPORTS = frozenset(
    {
        "AES_SBOX",
        "IDENTITY_SBOX",
        "construct_sbox",
        "sbox_metrics",
        "sbox_metrics_record",
    }
)
_IMAGE_EXPORTS = frozenset(
    {
        "apply_image_transform",
        "image_metrics",
        "image_metrics_record",
        "sample_image",
        "transform_record",
    }
)


def lab_available() -> bool:
    """Return whether the optional numpy dependency is importable."""

    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return True


def require_lab() -> None:
    """Raise a clear error when the optional lab dependency is missing."""

    if not lab_available():
        raise ImportError(
            "the lab operations require the 'lab' extra: install with "
            "'pip install geometric-function-atlas[lab]' or add --extra lab"
        )


def __getattr__(name: str) -> Any:
    if name in _CRYPTO_EXPORTS:
        from . import crypto

        return getattr(crypto, name)
    if name in _IMAGE_EXPORTS:
        from . import image

        return getattr(image, name)
    raise AttributeError(f"geometric_function_atlas.lab has no attribute {name!r}")


__all__ = ("lab_available", "require_lab") + tuple(
    sorted(_CRYPTO_EXPORTS)
) + tuple(sorted(_IMAGE_EXPORTS))
