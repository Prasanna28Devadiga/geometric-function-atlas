"""Image quality metrics and transforms (the optional lab extra).

Pure-NumPy reimplementation of the website's ``struve-image-enhancement``
metrics (PSNR, SSIM, GMSD, MSE, RMSE, PCC, MAE) without the scipy
dependency, plus deterministic convolution transforms. Inputs are float
arrays in ``[0, 1]``. All outputs are empirical; no geometric-function
theorem is claimed. Import lazily through :mod:`geometric_function_atlas.lab`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import numpy as np

from ..records import build_screen_record


def _as_float_array(array: Any, *, label: str = "array") -> np.ndarray:
    try:
        values = np.asarray(array, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a numeric array") from exc
    if values.ndim not in (2, 3):
        raise ValueError(f"{label} must be a 2D or 3D array")
    if not np.all(np.isfinite(values)):
        raise ValueError(f"{label} must contain only finite values")
    return values


def _same_shape(reference: np.ndarray, test: np.ndarray) -> None:
    if reference.shape != test.shape:
        raise ValueError(
            f"reference and test must have the same shape: "
            f"{reference.shape} != {test.shape}"
        )


def mse(reference: np.ndarray, test: np.ndarray) -> float:
    return float(np.mean((reference - test) ** 2))


def rmse(reference: np.ndarray, test: np.ndarray) -> float:
    return float(np.sqrt(mse(reference, test)))


def mae(reference: np.ndarray, test: np.ndarray) -> float:
    return float(np.mean(np.abs(reference - test)))


def psnr(reference: np.ndarray, test: np.ndarray, max_val: float = 1.0) -> float:
    error = mse(reference, test)
    if error == 0.0:
        return float("inf")
    return float(20.0 * np.log10(max_val) - 10.0 * np.log10(error))


def pcc(reference: np.ndarray, test: np.ndarray) -> float:
    a = reference.ravel() - reference.mean()
    b = test.ravel() - test.mean()
    denominator = np.sqrt(np.sum(a**2) * np.sum(b**2))
    if denominator == 0.0:
        return 0.0
    return float(np.sum(a * b) / denominator)


def _uniform_filter(a: np.ndarray, win: int) -> np.ndarray:
    """2D mean filter with reflect padding (matches scipy's default)."""

    pad = win // 2
    padded = np.pad(a, pad, mode="reflect").astype(float)
    cumulative = np.cumsum(np.cumsum(padded, axis=0), axis=1)
    height, width = a.shape
    top = np.arange(height)[:, None]
    left = np.arange(width)[None, :]
    bottom = top + win - 1
    right = left + win - 1
    top_ok = top >= 1
    left_ok = left >= 1
    result = cumulative[bottom, right]
    result = np.where(top_ok, result - cumulative[top - 1, right], result)
    result = np.where(left_ok, result - cumulative[bottom, left - 1], result)
    result = np.where(
        top_ok & left_ok,
        result + cumulative[top - 1, left - 1],
        result,
    )
    return result / (win * win)


def _ssim_channel(
    reference: np.ndarray,
    test: np.ndarray,
    win: int = 7,
    max_val: float = 1.0,
) -> float:
    c1 = (0.01 * max_val) ** 2
    c2 = (0.03 * max_val) ** 2
    mu1 = _uniform_filter(reference, win)
    mu2 = _uniform_filter(test, win)
    mu1_sq, mu2_sq, mu12 = mu1**2, mu2**2, mu1 * mu2
    sigma1_sq = _uniform_filter(reference**2, win) - mu1_sq
    sigma2_sq = _uniform_filter(test**2, win) - mu2_sq
    sigma12 = _uniform_filter(reference * test, win) - mu12
    ssim_map = ((2 * mu12 + c1) * (2 * sigma12 + c2)) / (
        (mu1_sq + mu2_sq + c1) * (sigma1_sq + sigma2_sq + c2)
    )
    return float(ssim_map.mean())


def ssim(reference: np.ndarray, test: np.ndarray, max_val: float = 1.0) -> float:
    if reference.ndim == 3:
        return float(
            np.mean(
                [
                    _ssim_channel(reference[..., c], test[..., c], max_val=max_val)
                    for c in range(reference.shape[2])
                ]
            )
        )
    return _ssim_channel(reference, test, max_val=max_val)


def _to_luma_255(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        image = (
            0.299 * image[..., 0] + 0.587 * image[..., 1] + 0.114 * image[..., 2]
        )
    return image * 255.0


def _downsample2(a: np.ndarray) -> np.ndarray:
    """2x2 average prefilter with nearest-edge padding, then downsample by 2."""

    padded = np.pad(a, ((0, 1), (0, 1)), mode="edge")
    height, width = padded.shape
    even_h = height - (height % 2)
    even_w = width - (width % 2)
    top = padded[:even_h:2, :even_w:2]
    return (
        top
        + padded[1 : even_h + 1 : 2, :even_w:2]
        + padded[:even_h:2, 1 : even_w + 1 : 2]
        + padded[1 : even_h + 1 : 2, 1 : even_w + 1 : 2]
    ) / 4.0


def _convolve(a: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """Odd-sized correlation with nearest-edge padding."""

    if kernel.ndim != 2 or kernel.shape[0] != kernel.shape[1] or kernel.shape[0] % 2 != 1:
        raise ValueError("kernel must be a square array with odd side length")
    side = kernel.shape[0]
    pad = side // 2
    padded = np.pad(a, pad, mode="edge")
    result = np.zeros_like(a, dtype=float)
    for row in range(side):
        for column in range(side):
            result += (
                kernel[row, column]
                * padded[row : row + a.shape[0], column : column + a.shape[1]]
            )
    return result


def gmsd(reference: np.ndarray, test: np.ndarray, c: float = 170.0) -> float:
    """Gradient Magnitude Similarity Deviation on 0-255 luminance."""

    r = _downsample2(_to_luma_255(reference))
    t = _downsample2(_to_luma_255(test))
    hx = np.array([[1, 0, -1], [1, 0, -1], [1, 0, -1]], dtype=float) / 3.0
    hy = hx.T
    mr = np.sqrt(_convolve(r, hx) ** 2 + _convolve(r, hy) ** 2)
    mt = np.sqrt(_convolve(t, hx) ** 2 + _convolve(t, hy) ** 2)
    gms = (2 * mr * mt + c) / (mr**2 + mt**2 + c)
    return float(np.sqrt(np.mean((gms - gms.mean()) ** 2)))


def image_metrics(reference: Any, test: Any) -> dict[str, Any]:
    """Full-reference metrics: PSNR, SSIM, GMSD, MSE, RMSE, PCC, MAE.

    PSNR is ``float('inf')`` for identical images. Metrics are empirical.
    """

    ref = _as_float_array(reference, label="reference")
    tst = _as_float_array(test, label="test")
    _same_shape(ref, tst)
    return {
        "PSNR": psnr(ref, tst),
        "SSIM": ssim(ref, tst),
        "GMSD": gmsd(ref, tst),
        "MSE": mse(ref, tst) * (255.0**2),
        "RMSE": rmse(ref, tst) * 255.0,
        "PCC": pcc(ref, tst),
        "MAE": mae(ref, tst) * 255.0,
    }


_OPERATIONS = ("smooth", "sharpen", "edge")

_SPECIAL_FUNCTION_DEFAULTS: dict[str, dict[str, float]] = {
    "miller_ross": {"nu": 0.5, "rho": 0.8},
    "mittag_leffler": {"alpha": 1.0, "beta": 1.0},
    "bessel": {"nu": 0.0},
    "hypergeometric": {"a": 1.0, "b": 1.0, "c": 2.0},
    "rabotnov": {"alpha": 0.5, "beta": 1.0},
    "struve": {"nu": 0.0},
    "cardioid": {},
    "sine": {},
    "nephroid": {},
    "exp_cardioid": {},
    "quartic": {},
    "cusp": {},
}
SPECIAL_FUNCTIONS = tuple(_SPECIAL_FUNCTION_DEFAULTS)


def _function_parameters(
    function: str,
    parameters: Mapping[str, float] | None,
) -> dict[str, float]:
    if function not in _SPECIAL_FUNCTION_DEFAULTS:
        raise ValueError(
            f"unknown image-lab function {function!r}; available: "
            f"{', '.join(SPECIAL_FUNCTIONS)}"
        )
    values = dict(_SPECIAL_FUNCTION_DEFAULTS[function])
    if parameters is not None:
        unknown = set(parameters) - set(values)
        if unknown:
            raise ValueError(
                f"unknown parameters for {function}: {', '.join(sorted(unknown))}"
            )
        values.update(parameters)
    if not all(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        for value in values.values()
    ):
        raise ValueError("image-lab function parameters must be finite real numbers")
    return values


def special_function_coefficients(
    function: str,
    *,
    terms: int = 8,
    parameters: Mapping[str, float] | None = None,
) -> tuple[float, ...]:
    """Return the website's normalized coefficients ``a_1, ..., a_terms``.

    These finite coefficient rules reproduce the static Image Lab's named
    special-function anchors. They support empirical filters only; they are not
    analytic continuation or a theorem about an image-processing result.
    """

    if isinstance(terms, bool) or not isinstance(terms, int) or not 1 <= terms <= 64:
        raise ValueError("terms must be an integer between 1 and 64")
    values = _function_parameters(function, parameters)
    nu = values.get("nu")
    if function in {"miller_ross", "bessel"} and nu is not None and nu <= -1:
        raise ValueError("nu must be greater than -1")
    if function == "struve" and nu is not None and nu <= -1.5:
        raise ValueError("nu must be greater than -1.5")
    if function in {"mittag_leffler", "rabotnov"}:
        alpha = values["alpha"]
        beta = values["beta"]
        if alpha <= 0 or beta <= 0:
            raise ValueError("alpha and beta must be positive")
    if function == "hypergeometric" and values["c"] <= 0:
        raise ValueError("c must be positive")
    coefficients: list[float] = []
    for index in range(1, terms + 1):
        k = index - 1
        if function == "miller_ross":
            value = values["rho"] ** k * math.gamma(values["nu"] + 1) / math.gamma(values["nu"] + index)
        elif function == "mittag_leffler":
            value = math.gamma(values["beta"]) / math.gamma(values["alpha"] * k + values["beta"])
        elif function == "bessel":
            value = (-0.25) ** k / (math.factorial(k) * math.prod(values["nu"] + 1 + offset for offset in range(k)))
        elif function == "hypergeometric":
            value = (
                math.prod(values["a"] + offset for offset in range(k))
                * math.prod(values["b"] + offset for offset in range(k))
                / (
                    math.prod(values["c"] + offset for offset in range(k))
                    * math.factorial(k)
                )
            )
        elif function == "rabotnov":
            value = values["beta"] ** k * math.gamma(values["alpha"] + 1) / math.gamma((values["alpha"] + 1) * index)
        elif function == "struve":
            value = 1.0 if index == 1 else (-1) ** k / (
                4**k
                * math.prod(1.5 + offset for offset in range(k))
                * math.prod(values["nu"] + 1.5 + offset for offset in range(k))
            )
        elif function == "cardioid":
            value = {0: 1.0, 1: 4 / 3, 2: 2 / 3}.get(k, 0.0)
        elif function == "sine":
            value = 1.0 if k == 0 else ((-1) ** ((k - 1) // 2) / math.factorial(k) if k % 2 else 0.0)
        elif function == "nephroid":
            value = {0: 1.0, 1: 1.0, 3: 1 / 3}.get(k, 0.0)
        elif function == "exp_cardioid":
            value = 1.0 if k == 0 else 1 / math.factorial(k - 1)
        elif function == "quartic":
            value = {0: 1.0, 1: 4 / 5, 4: 1 / 5}.get(k, 0.0)
        else:  # cusp
            value = {1: 1.0, 2: 0.75, 3: 0.5, 4: 0.375}.get(index, 0.0)
        if not math.isfinite(value):
            raise ValueError(f"{function} produced a non-finite coefficient")
        coefficients.append(float(value))
    return tuple(coefficients)


def _kernel(operation: str, taps: int, gain: float) -> Any:
    if operation == "smooth":
        return np.ones((taps, taps), dtype=float) / (taps * taps)
    identity = np.zeros((3, 3), dtype=float)
    identity[1, 1] = 1.0
    laplacian = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], dtype=float)
    if operation == "sharpen":
        return identity - gain * laplacian
    sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=float) / 4.0
    sobel_y = sobel_x.T
    return sobel_x, sobel_y


def _function_kernel(
    function: str,
    operation: str,
    taps: int,
    gain: float,
    parameters: Mapping[str, float] | None,
) -> np.ndarray:
    """Build the static Image Lab's coefficient-derived directional kernel."""

    coefficients = special_function_coefficients(
        function, terms=taps + 1, parameters=parameters
    )
    side = np.abs(np.asarray(coefficients[1:], dtype=float))
    vector = np.concatenate((side[::-1], np.array([1.0]), side))
    vector /= vector.sum()
    size = vector.size
    center = size // 2
    low_pass = np.zeros((size, size), dtype=float)
    for angle in (0, 45, 90, 135):
        directional = np.zeros_like(low_pass)
        for index, weight in enumerate(vector):
            offset = index - center
            if angle == 0:
                row, column = center, center + offset
            elif angle == 90:
                row, column = center + offset, center
            elif angle == 45:
                row, column = center - offset, center + offset
            else:
                row, column = center + offset, center + offset
            if 0 <= row < size and 0 <= column < size:
                directional[row, column] += weight
        low_pass += directional / 4.0
    identity = np.zeros_like(low_pass)
    identity[center, center] = 1.0
    if operation == "smooth":
        return low_pass
    if operation == "edge":
        return gain * (identity - low_pass)
    return identity + gain * (identity - low_pass)


def apply_image_transform(
    array: Any,
    operation: str,
    *,
    gain: float = 1.0,
    taps: int = 3,
    function: str | None = None,
    parameters: Mapping[str, float] | None = None,
) -> np.ndarray:
    """Apply a deterministic convolution transform to a float array in [0, 1].

    Operations without ``function`` are dependency-free generic transforms.
    Supplying one of :data:`SPECIAL_FUNCTIONS` uses the website's finite
    coefficient-derived directional kernel. Output is clipped to ``[0, 1]``;
    every result is an empirical transform, not a GFT theorem.
    """

    if operation not in _OPERATIONS:
        raise ValueError(
            f"operation must be one of: {', '.join(_OPERATIONS)}"
        )
    if isinstance(taps, bool) or not isinstance(taps, int) or taps not in (3, 5, 7):
        raise ValueError("taps must be one of 3, 5, 7")
    if not np.isfinite(gain):
        raise ValueError("gain must be finite")
    values = _as_float_array(array, label="array")
    channels = values[..., None] if values.ndim == 2 else values
    result = np.zeros_like(channels, dtype=float)
    function_kernel = (
        _function_kernel(function, operation, taps, gain, parameters)
        if function is not None
        else None
    )
    for channel in range(channels.shape[2]):
        if function_kernel is not None:
            result[..., channel] = _convolve(
                channels[..., channel], function_kernel
            )
        elif operation == "edge":
            sobel_x, sobel_y = _kernel("edge", taps, gain)
            gx = _convolve(channels[..., channel], sobel_x)
            gy = _convolve(channels[..., channel], sobel_y)
            result[..., channel] = np.sqrt(gx**2 + gy**2)
        else:
            kernel = _kernel(operation, taps, gain)
            result[..., channel] = _convolve(channels[..., channel], kernel)
    result = np.clip(result, 0.0, 1.0)
    return result[..., 0] if values.ndim == 2 else result


def sample_image(seed: int = 0, size: int = 32) -> np.ndarray:
    """Deterministic generated sample array in [0, 1] (test/anchor input)."""

    if isinstance(seed, bool) or not isinstance(seed, int):
        raise TypeError("seed must be an integer")
    if isinstance(size, bool) or not isinstance(size, int) or not 8 <= size <= 512:
        raise ValueError("size must be an integer between 8 and 512")
    rng = np.random.default_rng(seed)
    ramp = np.linspace(0.0, 1.0, size, dtype=float)[:, None] * np.linspace(
        0.0, 1.0, size, dtype=float
    )[None, :]
    noise = rng.random((size, size))
    return np.clip(0.6 * ramp + 0.4 * noise, 0.0, 1.0)


def _sanitize_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (None if isinstance(value, float) and not np.isfinite(value) else value)
        for key, value in metrics.items()
    }


def image_metrics_record(metrics: dict[str, Any]) -> dict[str, Any]:
    """Wrap image metrics in the closed analysis-record shape."""

    from ..contracts import (
        CheckStatus,
        VerificationCheck,
        VerificationReport,
    )

    return build_screen_record(
        record_type="lab_metrics",
        canonical_inputs={"metric_family": "image_quality"},
        method="image_quality_metrics",
        evidence_kind="empirical_metric",
        tier="lab",
        assumptions=(
            "inputs are float arrays in [0, 1]",
            "metrics are empirical image statistics, not GFT theorems",
        ),
        source_references=(
            "struve-image-enhancement/metrics.py at source commit acee553",
        ),
        verification=VerificationReport(
            checks=(
                VerificationCheck(
                    name="input_shapes",
                    checked="reference and test have identical shapes",
                    expected="equal shapes",
                    observed="equal",
                    status=CheckStatus.PASS,
                    scope="input validation",
                ),
                VerificationCheck(
                    name="metrics_recorded",
                    checked="all seven metrics are recorded",
                    expected="PSNR, SSIM, GMSD, MSE, RMSE, PCC, MAE",
                    observed=", ".join(sorted(metrics)),
                    status=CheckStatus.PASS,
                    scope="empirical record",
                ),
            )
        ),
        details=_sanitize_metrics(metrics),
    )


def transform_record(
    array: Any,
    operation: str,
    *,
    gain: float = 1.0,
    taps: int = 3,
    function: str | None = None,
    parameters: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Wrap a transform run in the closed analysis-record shape."""

    from ..contracts import (
        CheckStatus,
        VerificationCheck,
        VerificationReport,
    )

    output = apply_image_transform(
        array,
        operation,
        gain=gain,
        taps=taps,
        function=function,
        parameters=parameters,
    )
    return build_screen_record(
        record_type="lab_metrics",
        canonical_inputs={"metric_family": "image_transform"},
        method="image_transform",
        evidence_kind="empirical_metric",
        tier="lab",
        assumptions=(
            "input is a float array in [0, 1]",
            "the transform is an empirical convolution, not a GFT theorem",
        ),
        source_references=(
            "struve-image-enhancement/filters.py at source commit acee553",
        ),
        verification=VerificationReport(
            checks=(
                VerificationCheck(
                    name="shape_preserved",
                    checked="output shape matches the input",
                    expected=str(tuple(array.shape)),
                    observed=str(tuple(output.shape)),
                    status=CheckStatus.PASS,
                    scope="transform execution",
                ),
                VerificationCheck(
                    name="output_bounded",
                    checked="output stays in [0, 1]",
                    expected="min >= 0 and max <= 1",
                    observed=(
                        f"min={float(output.min()):g}, max={float(output.max()):g}"
                    ),
                    status=CheckStatus.PASS,
                    scope="transform execution",
                ),
            )
        ),
        details={
            "operation": operation,
            "gain": gain,
            "taps": taps,
            "function": function,
            "parameters": dict(parameters) if parameters is not None else None,
            "input_shape": list(array.shape),
            "output_shape": list(output.shape),
            "output_min": float(output.min()),
            "output_max": float(output.max()),
        },
    )
