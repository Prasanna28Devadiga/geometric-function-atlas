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


def test_getting_started_preserves_commands_and_evidence_boundaries() -> None:
    assert GETTING_STARTED.is_file()
    tutorial = GETTING_STARTED.read_text(encoding="utf-8")

    expected_commands = (
        "curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh",
        "curl -LsSf https://gft-registry.fly.dev/install.sh -o gfa-install.sh",
        "uv tool install --managed-python --python 3.12 geometric-function-atlas",
        "gfa walkthrough",
        "gfa generators",
        "gfa coefficients sine --order 5 --json",
        "gfa fekete-szego exponential --mu 0 --json",
        "gfa verify-counterexample --coefficients 1 --point=-0.75,0 --property starlike",
        "gfa verify-radius-certificate sine sigmoid",
        "gfa plot domain exponential --output exponential-domain.svg",
        "uv tool install --managed-python --python 3.12 'geometric-function-atlas[lab]'",
        "uv tool uninstall geometric-function-atlas",
    )
    for command in expected_commands:
        assert command in tutorial

    assert "A numerical screen is not a proof" in tutorial
    assert "certificate replay does not establish novelty" in tutorial.lower()
    assert "visualization, not a proof" in tutorial
    assert "integrity does not certify the mathematics" in tutorial.lower()


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
