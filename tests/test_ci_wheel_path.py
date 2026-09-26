from pathlib import Path


def test_ci_installs_the_builds_versioned_wheel_not_the_old_release():
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows/ci.yml').read_text()
    assert 'dist/geometric_function_atlas-0.4.0-py3-none-any.whl' not in workflow
    assert 'dist/geometric_function_atlas-*.whl' in workflow
