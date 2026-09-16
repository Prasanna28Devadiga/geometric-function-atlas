# Reproduce a result and prepare a collaborator bundle

**Problem.** A result directory may contain exact JSON, plots, assumptions, and source references, but how can a collaborator tell which files belong together and whether any byte changed after handoff?

The maintained custom-class workflow is the executable anchor:

```sh
python examples/research_workflows/custom_class.py \
  --alpha 1/4 \
  --order 4 \
  --output /tmp/gfa-collaborator-bundle
```

It writes the primary `custom_class.json` record, distinct SVGs for $\phi$, $z\phi$, and $f_\phi$, and `research_bundle_manifest.json`. The manifest contains:

- the workflow and source-tree entrypoint;
- exact replay parameters;
- the primary result record;
- package version and source-artifact commit;
- a sorted, unique artifact list with byte counts and SHA-256 checksums; and
- no timestamp or absolute path, so identical inputs produce identical manifest bytes in different directories.

## Verify before reading the result

A collaborator can verify the closed bundle with the public API:

```python
from geometric_function_atlas import verify_research_bundle_manifest

manifest = verify_research_bundle_manifest(
    "/tmp/gfa-collaborator-bundle/research_bundle_manifest.json"
)
print(manifest["workflow"], manifest["primary_record"])
```

Verification fails closed if the manifest is malformed, a declared file is missing, its size or checksum changed, paths traverse outside the directory, or a path contains a symlink. The verifier enforces finite file-count and byte limits.

The verifier **does not execute** the recorded entrypoint. Treat `entrypoint` and `parameters` as a replay recipe to inspect before running in a trusted checkout. Re-run the command in a new output directory, verify both manifests, and compare their bytes and declared artifacts.

## Evidence boundary

A valid bundle proves only that the declared artifact bytes match the manifest and that the manifest satisfies the closed bundle schema. It **does not certify** the mathematical claims inside an artifact, establish literature novelty, or turn a numerical screen into a theorem. Those claims retain the evidence statuses, assumptions, source references, and verification records carried by the primary result.

The manifest intentionally excludes itself from its checksum set, because a file cannot contain its own digest. Integrity is anchored by transporting the manifest with the declared artifacts and independently verifying the directory before use.

## Bundle an existing result directory

For a maintained workflow that does not yet emit a manifest, call `write_research_bundle_manifest` only after every declared artifact is complete:

```python
from geometric_function_atlas import write_research_bundle_manifest

write_research_bundle_manifest(
    output_directory,
    workflow="my_exact_workflow",
    entrypoint="examples/research_workflows/my_exact_workflow.py",
    parameters={"order": 4, "mu": "1/2"},
    primary_record="result.json",
    artifacts=("result.json", "geometry.svg"),
)
```

Artifact paths are portable forward-slash paths relative to the bundle directory. The writer rejects absolute paths, traversal, duplicates, symlinks, missing files, its own manifest name, and over-limit bundles. The primary record must be among the declared artifacts.
