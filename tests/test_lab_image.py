"""Image lab: deterministic metrics and transforms on generated arrays."""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")

from geometric_function_atlas.lab import (
    apply_image_transform,
    image_metrics,
    image_metrics_record,
    sample_image,
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


def test_smooth_transform_preserves_shape_and_bounds() -> None:
    image = sample_image(seed=2, size=16)
    output = apply_image_transform(image, "smooth")
    assert output.shape == image.shape
    assert output.min() >= 0.0
    assert output.max() <= 1.0


def test_smooth_of_constant_array_is_the_same_array() -> None:
    constant = np.full((8, 8), 0.5)
    output = apply_image_transform(constant, "smooth")
    assert np.allclose(output, constant)


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
