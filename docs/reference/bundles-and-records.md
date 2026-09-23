# Bundles, records, and result contracts

Create and verify deterministic collaborator manifests, build screen records, and
interpret the shared result/failure taxonomy.

## Research bundle manifests

A generated result directory can include `research_bundle_manifest.json`, which
records the script, parameters, package version, primary result, and file
checksums. Use `verify_research_bundle_manifest()` to check a received bundle.

This checks the files, not the mathematics. It detects changed or missing files
but does not run the recorded workflow or decide whether a theorem is correct.

::: geometric_function_atlas.bundle
    options:
      members_order: source
      show_root_heading: true
      show_source: false

::: geometric_function_atlas.records
    options:
      members_order: source
      show_root_heading: true
      show_source: false

::: geometric_function_atlas.contracts
    options:
      members_order: source
      show_root_heading: true
      show_source: false
