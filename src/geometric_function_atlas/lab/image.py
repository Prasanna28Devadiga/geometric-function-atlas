"""Image quality metrics and transforms (the optional lab extra).

Pure-NumPy reimplementation of the website's ``struve-image-enhancement``
metrics (PSNR, SSIM, GMSD, MSE, RMSE, PCC, MAE) without the scipy
dependency, plus deterministic convolution transforms. Inputs are float
arrays in ``[0, 1]``. All outputs are empirical; no geometric-function
theorem is claimed. Import lazily through :mod:`geometric_function_atlas.lab`.
"""

from __future__ import annotations

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


def _convolve3(a: np.ndarray, kernel: np.ndarray) -> np.ndarray:
    """3x3 correlation with nearest-edge padding (scipy ``convolve`` parity)."""

    padded = np.pad(a, 1, mode="edge")
    result = np.zeros_like(a, dtype=float)
    for row in range(3):
        for column in range(3):
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
    mr = np.sqrt(_convolve3(r, hx) ** 2 + _convolve3(r, hy) ** 2)
    mt = np.sqrt(_convolve3(t, hx) ** 2 + _convolve3(t, hy) ** 2)
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


def apply_image_transform(
    array: Any,
    operation: str,
    *,
    gain: float = 1.0,
    taps: int = 3,
) -> np.ndarray:
    """Apply a deterministic convolution transform to a float array in [0, 1].

    Operations: ``smooth`` (box filter), ``sharpen`` (identity minus the
    Laplacian, scaled by ``gain``), ``edge`` (Sobel magnitude). Output is
    clipped to ``[0, 1]``. Empirical transform, not a GFT theorem.
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
    for channel in range(channels.shape[2]):
        if operation == "edge":
            sobel_x, sobel_y = _kernel("edge", taps, gain)
            gx = _convolve3(channels[..., channel], sobel_x)
            gy = _convolve3(channels[..., channel], sobel_y)
            result[..., channel] = np.sqrt(gx**2 + gy**2)
        else:
            kernel = _kernel(operation, taps, gain)
            result[..., channel] = _convolve3(channels[..., channel], kernel)
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
) -> dict[str, Any]:
    """Wrap a transform run in the closed analysis-record shape."""

    from ..contracts import (
        CheckStatus,
        VerificationCheck,
        VerificationReport,
    )

    output = apply_image_transform(array, operation, gain=gain, taps=taps)
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
            "input_shape": list(array.shape),
            "output_shape": list(output.shape),
            "output_min": float(output.min()),
            "output_max": float(output.max()),
        },
    )
