"""Image lab: deterministic metrics and transforms on generated arrays."""

from __future__ import annotations

import subprocess
import sys
from typing import Any

import pytest

np = pytest.importorskip("numpy")

from geometric_function_atlas.lab import (
    apply_image_transform,
    image_metrics,
    image_metrics_record,
    sample_image,
    special_function_coefficients,
    transform_record,
)
from geometric_function_atlas.records import validate_screen_record


def test_identical_images_have_identity_metrics() -> None:
    image = sample_image(seed=1, size=16)
    metrics = image_metrics(image, image)
    assert metrics["PSNR"] == float("inf")
    assert metrics["SSIM"] == pytest.approx(1.0)
    assert metrics["GMSD"] == pytest.approx(0.0, abs=1e-9)
    assert metrics["MSE"] == pytest.approx(0.0)
    assert metrics["RMSE"] == pytest.approx(0.0)
    assert metrics["PCC"] == pytest.approx(1.0)
    assert metrics["MAE"] == pytest.approx(0.0)


def test_perturbed_image_has_finite_deteriorating_metrics() -> None:
    image = sample_image(seed=1, size=16)
    noise = sample_image(seed=9, size=16)
    noisy = np.clip(0.6 * image + 0.4 * noise, 0.0, 1.0)
    metrics = image_metrics(image, noisy)
    assert np.isfinite(metrics["PSNR"])
    assert 0.0 < metrics["PSNR"] < 100.0
    assert metrics["SSIM"] < 1.0
    assert metrics["MSE"] > 0.0
    assert metrics["PCC"] < 1.0


def test_shape_mismatch_is_rejected() -> None:
    with pytest.raises(ValueError, match="same shape"):
        image_metrics(np.zeros((4, 4)), np.zeros((8, 8)))


@pytest.mark.parametrize(
    "shape",
    [
        (4,),
        (4, 4, 1),
        (4, 4, 2),
        (4, 4, 4),
        (0, 4),
        (4, 0),
        (0, 4, 3),
        (4, 0, 3),
    ],
)
def test_image_metrics_rejects_non_2d_or_rgb_inputs(shape: tuple[int, ...]) -> None:
    image = np.zeros(shape)

    with pytest.raises(ValueError, match="2D or RGB"):
        image_metrics(image, image)


@pytest.mark.parametrize(
    "shape",
    [(4,), (4, 4, 1), (4, 4, 2), (4, 4, 4), (0, 4), (4, 0), (0, 4, 3)],
)
def test_image_transform_rejects_non_2d_or_rgb_inputs(shape: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="2D or RGB"):
        apply_image_transform(np.zeros(shape), "smooth")


def test_valid_rgb_transform_remains_supported() -> None:
    image = np.full((4, 4, 3), 0.5)

    output = apply_image_transform(image, "smooth")

    assert output.shape == image.shape
    assert np.allclose(output, image)


def test_image_lab_cli_rejects_non_rgb_input_without_traceback(tmp_path) -> None:
    reference = tmp_path / "reference.npy"
    test = tmp_path / "test.npy"
    np.save(reference, np.zeros((4, 4, 4)))
    np.save(test, np.zeros((4, 4, 4)))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "geometric_function_atlas",
            "image-lab",
            "metrics",
            "--ref",
            str(reference),
            "--test",
            str(test),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 2
    assert "reference must be a non-empty 2D or RGB array" in completed.stderr
    assert "Traceback" not in completed.stderr
    assert completed.stdout == ""


def test_smooth_transform_preserves_shape_and_bounds() -> None:
    image = sample_image(seed=2, size=16)
    output = apply_image_transform(image, "smooth")
    assert output.shape == image.shape
    assert output.min() >= 0.0
    assert output.max() <= 1.0


@pytest.mark.parametrize("taps", [3, 5, 7])
def test_smooth_transform_accepts_every_documented_tap_size(taps: int) -> None:
    image = np.full((8, 8), 0.5)

    output = apply_image_transform(image, "smooth", taps=taps)

    assert output.shape == image.shape
    assert np.allclose(output, image)


@pytest.mark.parametrize("taps", [3, 5, 7])
def test_edge_transform_accepts_every_documented_tap_size(taps: int) -> None:
    image = np.full((8, 8), 0.5)

    output = apply_image_transform(image, "edge", taps=taps)

    assert output.shape == image.shape
    assert np.allclose(output, 0.0, atol=1e-12)


def test_smooth_of_constant_array_is_the_same_array() -> None:
    constant = np.full((8, 8), 0.5)
    output = apply_image_transform(constant, "smooth")
    assert np.allclose(output, constant)


def test_function_transform_uses_website_reflect_boundary_semantics() -> None:
    image = np.arange(4, dtype=float).reshape(2, 2) / 3.0
    output = apply_image_transform(image, "smooth", taps=7, function="sine")

    from geometric_function_atlas.lab.image import _function_kernel

    def website_reflect(index: int, length: int) -> int:
        if index < 0:
            index = -index - 1
        if index >= length:
            index = 2 * length - index - 1
        return max(0, min(length - 1, index))

    kernel = _function_kernel("sine", "smooth", 7, 1.0, None)
    side = kernel.shape[0]
    center = side // 2
    expected = np.zeros_like(image)
    for row in range(side):
        for column in range(side):
            for y in range(image.shape[0]):
                for x in range(image.shape[1]):
                    yy = website_reflect(y + row - center, image.shape[0])
                    xx = website_reflect(x + column - center, image.shape[1])
                    expected[y, x] += kernel[row, column] * image[yy, xx]
    expected = np.clip(expected, 0.0, 1.0)
    assert np.allclose(output, expected)


def test_color_ssim_uses_website_luma_and_clipped_windows() -> None:
    reference = np.arange(8 * 8 * 3, dtype=float).reshape(8, 8, 3) / 191.0
    test = np.roll(reference, 1, axis=1)

    def website_ssim(x: Any, y: Any) -> float:
        luma_x = 0.299 * x[..., 0] + 0.587 * x[..., 1] + 0.114 * x[..., 2]
        luma_y = 0.299 * y[..., 0] + 0.587 * y[..., 1] + 0.114 * y[..., 2]
        c1, c2, radius = 0.01**2, 0.03**2, 3
        values = []
        for row in range(x.shape[0]):
            for column in range(x.shape[1]):
                y0, y1 = max(0, row - radius), min(x.shape[0] - 1, row + radius)
                x0, x1 = max(0, column - radius), min(x.shape[1] - 1, column + radius)
                xx = luma_x[y0 : y1 + 1, x0 : x1 + 1]
                yy = luma_y[y0 : y1 + 1, x0 : x1 + 1]
                mux, muy = float(xx.mean()), float(yy.mean())
                varx = float((xx * xx).mean()) - mux * mux
                vary = float((yy * yy).mean()) - muy * muy
                cov = float((xx * yy).mean()) - mux * muy
                values.append(
                    ((2 * mux * muy + c1) * (2 * cov + c2))
                    / ((mux * mux + muy * muy + c1) * (varx + vary + c2))
                )
        return float(np.mean(values))

    expected = website_ssim(reference, test)
    assert image_metrics(reference, test)["SSIM"] == pytest.approx(expected, abs=1e-12)


def test_edge_of_constant_array_is_zero() -> None:
    constant = np.full((8, 8), 0.5)
    output = apply_image_transform(constant, "edge")
    assert np.allclose(output, 0.0, atol=1e-12)


def test_sharpen_changes_a_ramp_and_stays_bounded() -> None:
    ramp = np.linspace(0.0, 1.0, 16)[:, None] * np.ones((1, 16))
    output = apply_image_transform(ramp, "sharpen", gain=0.5)
    assert output.shape == ramp.shape
    assert output.min() >= 0.0 and output.max() <= 1.0


def test_unknown_operation_is_rejected() -> None:
    with pytest.raises(ValueError, match="operation"):
        apply_image_transform(np.zeros((4, 4)), "warp")


def test_invalid_taps_are_rejected() -> None:
    with pytest.raises(ValueError, match="taps"):
        apply_image_transform(np.zeros((4, 4)), "smooth", taps=9)


def test_special_function_coefficients_match_the_website_sine_anchor() -> None:
    coefficients = special_function_coefficients("sine", terms=4)

    assert coefficients == pytest.approx((1.0, 1.0, 0.0, -1.0 / 6.0))


def test_function_derived_smoothing_accepts_five_taps_and_preserves_constants() -> None:
    constant = np.full((8, 8), 0.5)

    output = apply_image_transform(
        constant,
        "smooth",
        taps=5,
        function="sine",
    )

    assert np.allclose(output, constant)


def test_transform_record_preserves_function_kernel_inputs() -> None:
    record = transform_record(
        np.full((4, 4), 0.5),
        "smooth",
        taps=5,
        function="sine",
    )

    assert record["details"]["function"] == "sine"
    assert record["details"]["taps"] == 5


def test_sample_image_is_deterministic() -> None:
    assert np.array_equal(sample_image(seed=7, size=16), sample_image(seed=7, size=16))
    assert not np.array_equal(sample_image(seed=7, size=16), sample_image(seed=8, size=16))


def test_metrics_record_is_closed() -> None:
    image = sample_image(seed=3, size=16)
    record = image_metrics_record(image_metrics(image, image))
    assert record["record_type"] == "lab_metrics"
    assert record["evidence_kind"] == "empirical_metric"
    assert record["details"]["PSNR"] is None  # inf is not JSON-serializable
    validate_screen_record(record)


def test_transform_record_is_closed() -> None:
    image = sample_image(seed=4, size=16)
    record = transform_record(image, "smooth")
    assert record["evidence_kind"] == "empirical_metric"
    validate_screen_record(record)
