from __future__ import annotations

import ast
import importlib.util
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MKDOCS = ROOT / "mkdocs.yml"
GETTING_STARTED = ROOT / "docs" / "getting-started.md"
PYPROJECT = ROOT / "pyproject.toml"
DOCS_WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
PUBLIC_WORKFLOW_PAGES = (
    "workflows/README.md",
    "workflows/custom_class.md",
    "workflows/coefficient_comparison.md",
    "workflows/sharp_radius.md",
    "workflows/conjecture_counterexample.md",
    "workflows/recent_literature.md",
)
RETIRED_WORKFLOW_PAGES = (
    "workflows/class_geometry.md",
    "workflows/radius_atlas.md",
    "workflows/alexander_transform.md",
    "workflows/collaborator_bundle.md",
    "workflows/catalogue.md",
)
ADVANCED_REFERENCE_PAGES = ("reference/alexander-transform.md",)
REFERENCE_PAGES = {
    "reference/generators-and-coefficients.md": (
        "geometric_function_atlas.catalog",
        "geometric_function_atlas.coefficients",
        "geometric_function_atlas.fekete_szego",
    ),
    "reference/classes.md": ("geometric_function_atlas.classes",),
    "reference/verification.md": ("geometric_function_atlas.verify",),
    "reference/counterexamples.md": ("geometric_function_atlas.counterexamples",),
    "reference/radii.md": ("geometric_function_atlas.radii",),
    "reference/plotting.md": ("geometric_function_atlas.plotting",),
    "reference/snapshots.md": ("geometric_function_atlas.snapshot",),
    "reference/bundles-and-records.md": (
        "geometric_function_atlas.bundle",
        "geometric_function_atlas.records",
        "geometric_function_atlas.contracts",
    ),
    "reference/citations-and-artifacts.md": (
        "geometric_function_atlas.citation",
        "geometric_function_atlas.artifacts",
    ),
}


def test_mkdocs_site_presents_five_curated_research_workflows() -> None:
    assert MKDOCS.is_file(), "mkdocs.yml must define the package documentation site"
    config = MKDOCS.read_text(encoding="utf-8")

    assert "name: material" in config
    assert "navigation.sections" in config
    assert "toc.integrate" in config
    assert "- search" in config
    assert "- mkdocstrings" in config

    for relative_path in PUBLIC_WORKFLOW_PAGES:
        assert (ROOT / "docs" / relative_path).is_file(), relative_path
        assert config.count(relative_path) == 1, relative_path

    for relative_path in RETIRED_WORKFLOW_PAGES:
        assert not (ROOT / "docs" / relative_path).exists(), relative_path
        assert relative_path not in config

    for relative_path in ADVANCED_REFERENCE_PAGES:
        assert (ROOT / "docs" / relative_path).is_file(), relative_path
        assert config.count(relative_path) == 1, relative_path

    nav = config.split("nav:\n", maxsplit=1)[1]
    top_level = [
        line.removeprefix("  - ").removesuffix(":")
        for line in nav.splitlines()
        if line.startswith("  - ")
    ]
    assert top_level == [
        "Getting started",
        "Research workflows",
        "Reference",
        "Developer documentation",
    ]
    assert "Thirty things to try" not in config


def test_getting_started_is_short_with_one_command_per_shell() -> None:
    assert GETTING_STARTED.is_file()
    tutorial = GETTING_STARTED.read_text(encoding="utf-8")

    expected_commands = (
        "curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh",
        "irm https://gft-registry.fly.dev/install.ps1 | iex",
        "gfa fekete-szego exponential --mu 0",
        "gfa fekete-szego exponential --mu 1/2",
        "gfa walkthrough",
    )
    for command in expected_commands:
        assert command in tutorial

    assert tutorial.count("https://gft-registry.fly.dev/install.sh") == 1
    assert tutorial.count("https://gft-registry.fly.dev/install.ps1") == 1
    assert len(tutorial.splitlines()) <= 81
    assert tutorial.count("## ") <= 5
    assert tutorial.count("```bash") <= 4
    assert "f(z)=z+a_2z^2+a_3z^3" in tutorial.replace(" ", "")
    normalized_tutorial = " ".join(tutorial.split())
    assert "coefficients of functions in the class" in normalized_tutorial
    assert "not the coefficients of the generator" in normalized_tutorial
    assert "optional" in tutorial.lower()
    for unwanted in (
        '=== "macOS / Linux"',
        "Review before running",
        "Already have uv?",
        "Optional labs",
        "Upgrade or remove",
        "Invoke-WebRequest",
        "uv tool install",
        "uv tool uninstall",
        "gfa generators",
        "gfa coefficients",
        "gfa verify-counterexample",
        "gfa verify-radius-certificate",
        "gfa plot",
        "from geometric_function_atlas",
        "sine",
        "cardioid",
        "sigmoid",
    ):
        assert unwanted not in tutorial
    assert "replay" not in tutorial.lower()


def test_workflow_guides_lead_with_actions_not_review_vocabulary() -> None:
    primary_pages = PUBLIC_WORKFLOW_PAGES[1:]

    for relative_path in primary_pages:
        guide = (ROOT / "docs" / relative_path).read_text(encoding="utf-8")
        assert "## Run it" in guide, relative_path
        assert "## What you will see" in guide, relative_path

    for relative_path in PUBLIC_WORKFLOW_PAGES:
        guide = (ROOT / "docs" / relative_path).read_text(encoding="utf-8")
        for unwanted in (
            "**Problem.**",
            "**Disposition:**",
            "**Replay:**",
            "bounded ABSTAIN",
            "reviewer denominator",
            "Evidence boundary",
            "Snapshot honesty",
        ):
            assert unwanted not in guide, f"{relative_path}: {unwanted}"
        assert "replay" not in guide.lower(), f"{relative_path}: replay"


def test_public_docs_do_not_present_a_brainstorming_catalogue() -> None:
    public_pages = (ROOT / "README.md", ROOT / "docs" / "index.md") + tuple(
        ROOT / "docs" / relative_path for relative_path in PUBLIC_WORKFLOW_PAGES
    )

    for page in public_pages:
        text = page.read_text(encoding="utf-8")
        assert "Thirty things to try" not in text, str(page)
        assert "thirty-example catalogue" not in text, str(page)


def test_workflow_landing_uses_five_mobile_readable_choices() -> None:
    landing = (ROOT / "docs" / "workflows" / "README.md").read_text(
        encoding="utf-8"
    )

    assert "| Research question |" not in landing
    choices = (
        "Understand a new Ma–Minda class",
        "Investigate a coefficient problem",
        "Find and verify an inclusion radius",
        "Test a conjecture",
        "Reproduce and adapt a published result",
    )
    positions = [landing.index(f"[{choice}]") for choice in choices]
    assert positions == sorted(positions)
    for index in range(1, 6):
        assert f"{index}. **[" not in landing


def test_docs_dependencies_and_canonical_url_are_declared() -> None:
    pyproject = PYPROJECT.read_text(encoding="utf-8")

    assert (
        'Documentation = "https://prasanna28devadiga.github.io/'
        'geometric-function-atlas/"'
    ) in pyproject
    assert "docs = [" in pyproject
    assert '"mkdocs==' in pyproject
    assert '"mkdocs-material==' in pyproject
    assert '"mkdocstrings==' in pyproject
    assert '"mkdocstrings-python==' in pyproject

    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "site/" in gitignore


def test_grouped_python_api_reference_is_generated_from_docstrings() -> None:
    config = MKDOCS.read_text(encoding="utf-8")

    for relative_path, modules in REFERENCE_PAGES.items():
        page = ROOT / "docs" / relative_path
        assert page.is_file(), relative_path
        assert config.count(relative_path) == 1, relative_path
        content = page.read_text(encoding="utf-8")
        for module in modules:
            assert f"::: {module}" in content


def test_docs_theme_uses_standard_material_features_and_atlas_branding() -> None:
    config = MKDOCS.read_text(encoding="utf-8")
    assert (ROOT / "docs" / "index.md").is_file()
    assert "content.code.copy" in config
    assert "pymdownx.tabbed" in config
    assert "pymdownx.arithmatex" in config
    assert "assets/stylesheets/extra.css" in config
    assert "assets/javascripts/mathjax.js" in config
    assert "custom_dir:" not in config
    assert "inherited_members: false" in config
    assert "repo_url:" not in config
    assert "social:" in config
    assert "https://github.com/Prasanna28Devadiga/geometric-function-atlas" in config

    css = (ROOT / "docs" / "assets" / "stylesheets" / "extra.css").read_text(
        encoding="utf-8"
    )
    for brand_value in (
        "#faf9f7",
        "#1a1814",
        "#a82e1f",
        "--md-primary-fg-color--dark",
        "IBM Plex",
    ):
        assert brand_value in css


def test_docs_workflow_builds_strictly_and_deploys_with_pages_permissions() -> None:
    assert DOCS_WORKFLOW.is_file()
    workflow = DOCS_WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in workflow
    assert "branches: [main]" in workflow
    assert "uv sync --extra docs --locked" in workflow
    assert "uv run --frozen --extra docs mkdocs build --strict" in workflow
    assert "scripts/check_docs_site.py site" in workflow
    assert "actions/configure-pages@" in workflow
    assert "actions/upload-pages-artifact@" in workflow
    assert "actions/deploy-pages@" in workflow
    assert workflow.count("pages: write") == 1
    assert workflow.count("id-token: write") == 1
    assert "name: github-pages" in workflow


# C0 control characters other than tab, newline and carriage return.  A LaTeX
# command such as "\\frac" that passes through a non-raw Python string turns
# into one of these ("\\f" is a form feed) and MathJax reports an input error.
CONTROL_CHARACTERS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
RECENT_LITERATURE = ROOT / "docs" / "workflows" / "recent_literature.md"


def test_docs_sources_contain_no_control_characters() -> None:
    sources = [ROOT / "README.md", *sorted((ROOT / "docs").rglob("*.md"))]
    offenders = []
    for source in sources:
        # split("\n") rather than splitlines(): splitlines() treats a form
        # feed as a line break and would hide exactly the bug under test.
        for number, line in enumerate(
            source.read_text(encoding="utf-8").split("\n"), start=1
        ):
            if CONTROL_CHARACTERS.search(line):
                offenders.append(f"{source.relative_to(ROOT)}:{number}: {line!r}")
    assert offenders == []


def test_docstrings_rendered_by_mkdocstrings_contain_no_control_characters() -> None:
    offenders = []
    for module in sorted((ROOT / "src").rglob("*.py")):
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and CONTROL_CHARACTERS.search(node.value)
            ):
                offenders.append(f"{module.relative_to(ROOT)}:{node.lineno}")
    assert offenders == []


def test_recent_literature_counterexample_series_is_valid_tex() -> None:
    page = RECENT_LITERATURE.read_text(encoding="utf-8")
    assert r"f_0(z)=z+z^2+\frac34z^3+\frac7{12}z^4+\frac5{12}z^5+\cdots." in page
    assert "\f" not in page


@pytest.mark.skipif(
    importlib.util.find_spec("mkdocs") is None,
    reason="docs extra not installed; the Documentation workflow runs this check",
)
def test_built_site_math_has_no_control_characters(tmp_path: Path) -> None:
    site = tmp_path / "site"
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--strict", "--site-dir", str(site)],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_docs_site.py"), str(site)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
