from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from geometric_function_atlas.lab import apply_image_transform, image_metrics

np = pytest.importorskip("numpy")


ROOT = Path(__file__).resolve().parents[1]
WEBSITE_LAB = Path(
    os.environ.get(
        "GFT_WEBSITE_LAB",
        str(ROOT.parent / "gft-registry" / "static-site" / "lab.js"),
    )
)


def _node_json(body: str) -> Any:
    script = (
        "global.window = {};\n"
        "const api = require(" + json.dumps(str(WEBSITE_LAB)) + ");\n"
        + body
    )
    completed = subprocess.run(
        ["node", "-e", script],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def _require_website_lab() -> None:
    if shutil.which("node") is None or not WEBSITE_LAB.is_file():
        pytest.skip("direct website lab probe requires Node and static-site/lab.js")


def test_package_function_transform_matches_website_lab_on_small_boundary_input() -> None:
    _require_website_lab()
    image = np.arange(4, dtype=float).reshape(2, 2) / 3.0
    package_output = apply_image_transform(
        image, "smooth", taps=7, function="sine"
    )

    values = json.dumps(image.ravel().tolist())
    website_output = np.asarray(
        _node_json(
            f"""
const image = new api.Img(2, 2);
const values = {values};
image.r = new Float32Array(values);
image.g = new Float32Array(values);
image.b = new Float32Array(values);
const kernel = api.buildKernel(api.FUNCTIONS.sine.coeff({{}}), 1, 7, "smooth");
console.log(JSON.stringify(Array.from(api.applyKernel(image, kernel).r)));
"""
        ),
        dtype=float,
    ).reshape(2, 2)

    assert np.allclose(package_output, website_output, atol=1e-7)


def test_package_ssim_matches_website_luma_window_probe() -> None:
    _require_website_lab()
    reference = np.arange(8 * 8 * 3, dtype=float).reshape(8, 8, 3) / 191.0
    test = np.roll(reference, 1, axis=1)
    package_ssim = image_metrics(reference, test)["SSIM"]

    def channel_values(channel: int, array: Any) -> str:
        return json.dumps(array[..., channel].ravel().tolist())

    website_ssim = float(
        _node_json(
            f"""
const a = new api.Img(8, 8);
const b = new api.Img(8, 8);
a.r = new Float32Array({channel_values(0, reference)});
a.g = new Float32Array({channel_values(1, reference)});
a.b = new Float32Array({channel_values(2, reference)});
b.r = new Float32Array({channel_values(0, test)});
b.g = new Float32Array({channel_values(1, test)});
b.b = new Float32Array({channel_values(2, test)});
console.log(JSON.stringify(api.ssim(a, b, 8, 8)));
"""
        )
    )

    assert package_ssim == pytest.approx(website_ssim, abs=1e-6)


@pytest.mark.parametrize("height,width", [(5, 3), (7, 5)])
def test_package_gmsd_matches_website_on_odd_dimensions(height: int, width: int) -> None:
    _require_website_lab()
    rng = np.random.default_rng(20260811 + height + width)
    reference = rng.random((height, width, 3))
    test = rng.random((height, width, 3))
    package_gmsd = image_metrics(reference, test)["GMSD"]

    def channel_values(channel: int, array: Any) -> str:
        return json.dumps(array[..., channel].ravel().tolist())

    website_gmsd = float(
        _node_json(
            f"""
const a = new api.Img({width}, {height});
const b = new api.Img({width}, {height});
a.r = new Float32Array({channel_values(0, reference)});
a.g = new Float32Array({channel_values(1, reference)});
a.b = new Float32Array({channel_values(2, reference)});
b.r = new Float32Array({channel_values(0, test)});
b.g = new Float32Array({channel_values(1, test)});
b.b = new Float32Array({channel_values(2, test)});
console.log(JSON.stringify(api.gmsd(a, b, {width}, {height})));
"""
        )
    )

    assert package_gmsd == pytest.approx(website_gmsd, abs=1e-6)
