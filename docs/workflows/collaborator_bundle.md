# Share a reproducible result

A result often consists of several files: a JSON record, one or more plots, and
the parameters used to produce them. A bundle manifest lets someone else check
that those files arrived unchanged.

## Run it

The custom-class example already creates a bundle:

```bash
python examples/research_workflows/custom_class.py \
  --alpha 1/4 \
  --order 4 \
  --output /tmp/gfa-bundle
```

## What you will see

Alongside the result and plots, the directory contains
`research_bundle_manifest.json`. It records:

- the script and parameters;
- the package version;
- the primary result file; and
- every included file's size and SHA-256 checksum.

The manifest omits timestamps and absolute paths, so the same calculation in a
different directory produces the same manifest.

## Check a received bundle

```python
from geometric_function_atlas import verify_research_bundle_manifest

manifest = verify_research_bundle_manifest(
    "/tmp/gfa-bundle/research_bundle_manifest.json"
)
print(manifest["workflow"])
print(manifest["primary_record"])
```

Verification detects a missing, renamed, resized, or edited file. It also
rejects paths that escape the bundle directory or pass through a symbolic link.

## What the check means

Bundle verification checks the files, not the mathematics. It does not run the
recorded workflow, and it does not decide whether a theorem in the JSON file is
correct. To reproduce the calculation, inspect the recorded script and
parameters, run them in a trusted checkout, and compare the two bundles.

## Add a manifest to another workflow

After all result files have been written, call:

```python
from geometric_function_atlas import write_research_bundle_manifest

write_research_bundle_manifest(
    output_directory,
    workflow="my_workflow",
    entrypoint="examples/research_workflows/my_workflow.py",
    parameters={"order": 4, "mu": "1/2"},
    primary_record="result.json",
    artifacts=("result.json", "geometry.svg"),
)
```

Use paths relative to the bundle directory. The primary record must be one of
the listed files.