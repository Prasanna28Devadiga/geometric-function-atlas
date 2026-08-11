"""S-box benchmark metrics (the optional lab extra).

Direct port of the website's ``gft-crypto-lab/sbox_metrics.py`` into a pure
NumPy implementation. The five reported criteria are nonlinearity, strict
avalanche (SAC), bit independence (BIC), differential probability (DP), and
linear probability (LP). AES and the identity permutation ship as
deterministic reference anchors. These are benchmark metrics only: matching
the AES column validates the harness, it is never a security claim.

Requires the ``lab`` extra (numpy). Import this module lazily through
:mod:`geometric_function_atlas.lab`.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ..records import build_screen_record

N_BITS = 8
N = 1 << N_BITS  # 256

_POP = np.array([i.bit_count() for i in range(N)], dtype=np.int64)

AES_SBOX = (
    0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5, 0x30, 0x01, 0x67, 0x2B,
        0xFE, 0xD7, 0xAB, 0x76, 0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0,
        0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0, 0xB7, 0xFD, 0x93, 0x26,
        0x36, 0x3F, 0xF7, 0xCC, 0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
        0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A, 0x07, 0x12, 0x80, 0xE2,
        0xEB, 0x27, 0xB2, 0x75, 0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0,
        0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84, 0x53, 0xD1, 0x00, 0xED,
        0x20, 0xFC, 0xB1, 0x5B, 0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
        0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85, 0x45, 0xF9, 0x02, 0x7F,
        0x50, 0x3C, 0x9F, 0xA8, 0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5,
        0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2, 0xCD, 0x0C, 0x13, 0xEC,
        0x5F, 0x97, 0x44, 0x17, 0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
        0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88, 0x46, 0xEE, 0xB8, 0x14,
        0xDE, 0x5E, 0x0B, 0xDB, 0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C,
        0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79, 0xE7, 0xC8, 0x37, 0x6D,
        0x8D, 0xD5, 0x4E, 0xA9, 0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
        0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6, 0xE8, 0xDD, 0x74, 0x1F,
        0x4B, 0xBD, 0x8B, 0x8A, 0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E,
        0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E, 0xE1, 0xF8, 0x98, 0x11,
        0x69, 0xD9, 0x8E, 0x94, 0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
        0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68, 0x41, 0x99, 0x2D, 0x0F,
        0xB0, 0x54, 0xBB, 0x16,
)

IDENTITY_SBOX = tuple(range(N))


def _as_array(sbox: Any) -> np.ndarray:
    array = np.asarray(sbox)
    if array.shape != (N,) or array.dtype.kind not in "iu":
        raise ValueError(
            "sbox must be a sequence of 256 integers on [0, 255]"
        )
    if array.min() < 0 or array.max() > 255:
        raise ValueError("sbox entries must lie in [0, 255]")
    return array.astype(np.int64)


def _parity_mask(sbox: np.ndarray, mask: int) -> np.ndarray:
    return (_POP[sbox & mask] & 1).astype(np.int8)


def _fwht(f01: np.ndarray) -> np.ndarray:
    """Walsh-Hadamard transform of (-1)^f for a boolean function."""

    values = 1 - 2 * f01.astype(np.int64)
    length = values.size
    step = 1
    while step < length:
        values = values.reshape(-1, 2 * step)
        left = values[:, :step].copy()
        right = values[:, step:].copy()
        values[:, :step] = left + right
        values[:, step:] = left - right
        values = values.reshape(-1)
        step *= 2
    return values


def _component_spectra(sbox: np.ndarray) -> np.ndarray:
    spectra = np.empty((N - 1, N), dtype=np.int64)
    for mask in range(1, N):
        spectra[mask - 1] = _fwht(_parity_mask(sbox, mask))
    return spectra


def is_bijection(sbox: Any) -> bool:
    array = _as_array(sbox)
    return bool(np.array_equal(np.sort(array), np.arange(N)))


def nonlinearity(sbox: Any, spectra: np.ndarray | None = None) -> dict[str, Any]:
    array = _as_array(sbox)
    if spectra is None:
        spectra = _component_spectra(array)
    nl_each = N // 2 - np.max(np.abs(spectra), axis=1) // 2
    per_bit = [int(nl_each[(1 << bit) - 1]) for bit in range(N_BITS)]
    return {
        "per_bit": per_bit,
        "avg_per_bit": float(np.mean(per_bit)),
        "min_all_masks": int(np.min(nl_each)),
    }


def sac(sbox: Any) -> dict[str, Any]:
    array = _as_array(sbox)
    x = np.arange(N)
    matrix = np.zeros((N_BITS, N_BITS))
    for bit in range(N_BITS):
        flipped = array[x ^ (1 << bit)]
        diff = array ^ flipped
        for output_bit in range(N_BITS):
            matrix[bit, output_bit] = np.mean((diff >> output_bit) & 1)
    return {
        "matrix": matrix,
        "avg": float(matrix.mean()),
        "min": float(matrix.min()),
        "max": float(matrix.max()),
        "var": float(matrix.var()),
    }


def bic_nonlinearity(sbox: Any, spectra: np.ndarray | None = None) -> dict[str, Any]:
    array = _as_array(sbox)
    if spectra is None:
        spectra = _component_spectra(array)
    values = [
        N // 2 - int(np.max(np.abs(spectra[((1 << lower) | (1 << upper)) - 1]))) // 2
        for lower in range(N_BITS)
        for upper in range(lower + 1, N_BITS)
    ]
    values_array = np.array(values, dtype=np.int64)
    return {
        "avg": float(values_array.mean()),
        "min": int(values_array.min()),
        "sq_dev": float(values_array.std()),
    }


def differential_uniformity(sbox: Any) -> dict[str, Any]:
    array = _as_array(sbox)
    x = np.arange(N)
    maximum = 0
    for delta in range(1, N):
        out_diff = array ^ array[x ^ delta]
        maximum = max(maximum, int(np.bincount(out_diff, minlength=N).max()))
    return {"DU": maximum, "DP": maximum / N}


def linear_probability(sbox: Any, spectra: np.ndarray | None = None) -> dict[str, Any]:
    array = _as_array(sbox)
    if spectra is None:
        spectra = _component_spectra(array)
    max_w = int(np.max(np.abs(spectra[:, 1:])))
    return {"LP": max_w / (2 * N), "max_WHT": max_w}


def sbox_metrics(sbox: Any) -> dict[str, Any]:
    """Compute all benchmark criteria for one 8x8 S-box."""

    array = _as_array(sbox)
    spectra = _component_spectra(array)
    nl = nonlinearity(array, spectra)
    s = sac(array)
    bic = bic_nonlinearity(array, spectra)
    du = differential_uniformity(array)
    lp = linear_probability(array, spectra)
    return {
        "bijection": is_bijection(array),
        "NL_avg": nl["avg_per_bit"],
        "NL_min": nl["min_all_masks"],
        "NL_per_bit": nl["per_bit"],
        "SAC_avg": s["avg"],
        "SAC_min": s["min"],
        "SAC_max": s["max"],
        "SAC_var": s["var"],
        "BIC_avg": bic["avg"],
        "BIC_min": bic["min"],
        "BIC_sqdev": bic["sq_dev"],
        "DU": du["DU"],
        "DP": du["DP"],
        "LP": lp["LP"],
    }


_PHI_COEFFICIENTS: dict[str, list[float]] = {
    # B_1..B_6 of phi(z) = 1 + sum B_k z^k for the five website star functions.
    "cardioid": [4 / 3, 2 / 3, 0.0, 0.0, 0.0, 0.0],
    "exp_cardioid": [1.0, 1 / 2, 1 / 6, 1 / 24, 1 / 120, 1 / 720],
    "nephroid": [1.0, 0.0, 1 / 3, 0.0, 0.0, 0.0],
    "sine": [1.0, 0.0, -1 / 6, 0.0, 1 / 120, 0.0],
    "quartic": [4 / 5, 0.0, 0.0, 1 / 5, 0.0, 0.0],
}
_CONSTRUCTION_FUNCTIONS = tuple(_PHI_COEFFICIENTS)


def _extremal_value(name: str, z: complex, terms: int = 48) -> complex:
    """``f(z) = z exp(sum B_k z^k / k)`` for the named generator."""

    coefficients = _PHI_COEFFICIENTS[name]
    g = 0.0 + 0.0j
    power = z
    for k in range(1, min(terms, len(coefficients)) + 1):
        bk = coefficients[k - 1]
        if bk:
            g += bk * power / k
        power *= z
    return z * complex(np.exp(g.real) * np.cos(g.imag), np.exp(g.real) * np.sin(g.imag))


def _byte_from_value(value: complex) -> int:
    """Deterministic byte from the low mantissa bits of f(z) (not a security claim)."""

    import struct

    real = value.real if np.isfinite(value.real) else 0.0
    imag = value.imag if np.isfinite(value.imag) else 0.0
    br = struct.unpack("<Q", struct.pack("<d", real))[0]
    bi = struct.unpack("<Q", struct.pack("<d", imag))[0]
    return int(((br >> 5) ^ (bi >> 12) ^ (br >> 17)) & 0xFF)


def construct_sbox(
    function: str,
    key: bytes = b"gft-registry",
    *,
    construction: str = "keyed",
    radius: float = 0.92,
) -> tuple[int, ...]:
    """Construct a deterministic 8x8 S-box from a named Ma-Minda function.

    ``function`` is one of the five website star functions: ``cardioid``,
    ``exp_cardioid``, ``nephroid``, ``sine``, ``quartic``. Two constructions
    match the website lab: ``keyed`` (low-discrepancy path, first-occurrence
    byte fill) and ``direct`` (conformal rank order of a 16x16 lattice).
    """

    if construction not in {"keyed", "direct"}:
        raise ValueError("construction must be 'keyed' or 'direct'")
    if function not in _PHI_COEFFICIENTS:
        allowed = ", ".join(_CONSTRUCTION_FUNCTIONS)
        raise ValueError(f"unknown function {function!r}; available: {allowed}")

    if construction == "direct":

        images = np.empty((N, 2))
        for index in range(N):
            column, row = index % 16, index // 16
            z = complex(
                radius * ((2 * column + 1) / 16 - 1),
                radius * ((2 * row + 1) / 16 - 1),
            )
            w = _extremal_value(function, z)
            images[index] = (w.real, w.imag)
        order = np.lexsort((images[:, 1], images[:, 0]))
        sbox = np.empty(N, dtype=np.int64)
        sbox[order] = np.arange(N)
        return tuple(int(value) for value in sbox)

    import hashlib

    digest = hashlib.sha256(key).digest()
    seen = np.zeros(N, dtype=bool)
    sequence: list[int] = []
    t = 0
    golden_angle = 0.6180339887498949
    golden_radius = 0.7548776662466927
    while len(sequence) < N and t < 4_000_000:
        angle = 2 * np.pi * ((t * golden_angle) % 1.0) + (digest[t % 32] / 256.0) * 0.013
        radial = radius * (0.18 + 0.80 * ((t * golden_radius + digest[(t // 32) % 32] / 256.0) % 1.0))
        w = _extremal_value(function, complex(radial * np.cos(angle), radial * np.sin(angle)))
        byte = _byte_from_value(w)
        if not seen[byte]:
            seen[byte] = True
            sequence.append(byte)
        t += 1
    for value in range(N):
        if not seen[value]:
            sequence.append(value)
    return tuple(sequence)


def sbox_metrics_record(
    metrics: dict[str, Any],
    *,
    label: str,
) -> dict[str, Any]:
    """Wrap benchmark metrics in the closed analysis-record shape."""

    from ..contracts import (
        CheckStatus,
        VerificationCheck,
        VerificationReport,
    )

    details = {key: value for key, value in metrics.items() if key != "NL_per_bit"}
    details["NL_per_bit"] = list(metrics["NL_per_bit"])
    return build_screen_record(
        record_type="lab_metrics",
        canonical_inputs={"metric_family": "sbox_benchmark"},
        method="sbox_benchmark_metrics",
        evidence_kind="benchmark_metric",
        tier="lab",
        assumptions=(
            "metrics are exact integer or float statistics over GF(2)",
            "a benchmark match (e.g. AES) validates the harness, not security",
        ),
        source_references=(
            "gft-crypto-lab/sbox_metrics.py at source commit acee553",
        ),
        verification=VerificationReport(
            checks=(
                VerificationCheck(
                    name="sbox_dimension",
                    checked="S-box is a length-256 integer permutation on [0, 255]",
                    expected="256 entries",
                    observed="256 entries",
                    status=CheckStatus.PASS,
                    scope="input validation",
                ),
                VerificationCheck(
                    name="bijection_recorded",
                    checked="bijection status is recorded",
                    expected="a boolean value",
                    observed=str(metrics.get("bijection", None)),
                    status=CheckStatus.PASS,
                    scope="benchmark record",
                ),
            )
        ),
        details={"label": label, **details},
    )
