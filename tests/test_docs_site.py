from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MKDOCS = ROOT / "mkdocs.yml"
GETTING_STARTED = ROOT / "docs" / "getting-started.md"
PYPROJECT = ROOT / "pyproject.toml"
DOCS_WORKFLOW = ROOT / ".github" / "workflows" / "docs.yml"
WORKFLOW_PAGES = (
    "workflows/README.md",
    "workflows/custom_class.md",
    "workflows/class_geometry.md",
    "workflows/sharp_radius.md",
    "workflows/radius_atlas.md",
    "workflows/coefficient_comparison.md",
    "workflows/conjecture_counterexample.md",
    "workflows/alexander_transform.md",
    "workflows/collaborator_bundle.md",
    "workflows/recent_literature.md",
    "workflows/catalogue.md",
)
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


def test_mkdocs_site_declares_every_research_workflow_once() -> None:
    assert MKDOCS.is_file(), "mkdocs.yml must define the package documentation site"
    config = MKDOCS.read_text(encoding="utf-8")

    assert "name: material" in config
    assert "navigation.sections" in config
    assert "toc.integrate" in config
    assert "- search" in config
    assert "- mkdocstrings" in config

    for relative_path in WORKFLOW_PAGES:
        assert (ROOT / "docs" / relative_path).is_file(), relative_path
        assert config.count(relative_path) == 1, relative_path


def test_getting_started_is_a_short_tutorial_with_one_install_path() -> None:
    assert GETTING_STARTED.is_file()
    tutorial = GETTING_STARTED.read_text(encoding="utf-8")

    expected_commands = (
        "curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh",
        "gfa walkthrough",
        "gfa generators",
        "gfa coefficients sine --order 5 --json",
        "gfa fekete-szego exponential --mu 0 --json",
        "gfa verify-counterexample --coefficients 1 --point=-0.75,0 --property starlike",
        "gfa verify-radius-certificate sine sigmoid",
        "gfa plot domain exponential --output exponential-domain.svg",
    )
    for command in expected_commands:
        assert command in tutorial

    assert tutorial.count("https://gft-registry.fly.dev/install.sh") == 1
    assert len(tutorial.splitlines()) < 220
    for unwanted in (
        '=== "macOS / Linux"',
        '=== "Windows PowerShell"',
        "Review before running",
        "Already have uv?",
        "Optional labs",
        "Upgrade or remove",
        "Invoke-WebRequest",
        "uv tool install",
        "uv tool uninstall",
    ):
        assert unwanted not in tutorial
    assert "replay" not in tutorial.lower()


def test_workflow_guides_lead_with_actions_not_review_vocabulary() -> None:
    primary_pages = WORKFLOW_PAGES[1:-1]

    for relative_path in primary_pages:
        guide = (ROOT / "docs" / relative_path).read_text(encoding="utf-8")
        assert "## Run it" in guide, relative_path
        assert "## What you will see" in guide, relative_path

    for relative_path in WORKFLOW_PAGES:
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
    assert "actions/configure-pages@" in workflow
    assert "actions/upload-pages-artifact@" in workflow
    assert "actions/deploy-pages@" in workflow
    assert workflow.count("pages: write") == 1
    assert workflow.count("id-token: write") == 1
    assert "name: github-pages" in workflow
