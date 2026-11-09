"""Bounded exact Hadamard products of normalized analytic jets."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sympy as sp

from .coefficient_transforms import _exact_jet


def hadamard_coefficients(
    left: Sequence[Any], right: Sequence[Any],
) -> tuple[sp.Expr, ...]:
    """Return a_n*b_n for normalized jets a2..a9 and b2..b9.

    Both functions have implicit coefficients a0=b0=0, a1=b1=1.
    The supplied jet lengths must agree; absent terms are unknown, not zero.
    This exact finite transform is not ordinary multiplication, a certificate
    of disk analyticity/univalence, a convolution-duality theorem or a radius.
    """
    if len(left) != len(right):
        raise ValueError('supply equally long normalized jets')
    a = _exact_jet(left, maximum=8)
    b = _exact_jet(right, maximum=8)
    return tuple(sp.cancel(x*y) for x, y in zip(a, b))
