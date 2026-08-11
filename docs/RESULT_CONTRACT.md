# Structured result and verification contract

The `v0.2.x` result contract is schema version `1`. It is shared by the
shipped structured results and is the envelope intended for future certificate
replay and snapshot operations. It is deliberately separate from the live
registry website and from any mutable database.

## Success records

`GeneratorSeriesResult.to_dict()` and `FeketeSzegoResult.to_dict()` retain the
legacy `v0.2.x` fields and add the following closed envelope:

- `schema_version`: integer contract version (`1`);
- `result_type`: trusted operation name;
- `canonical_inputs`: exact, direction-preserving problem inputs;
- `exact_expressions`: non-executable display strings and exact output values;
- `exact_expression_dag`: a bounded canonical exact-expression DAG. The DAG,
  not the lossy printer strings, is the authoritative expression identity;
- `method`, `evidence_status`, and `computational_status`: computational method
  and evidence state (`computational_status` is explicit so literature status
  cannot be mistaken for computational evidence);
- `assumptions`: explicit assumptions, not implied claims;
- `source_references`: citations or artifact references used by the result;
- `package_version` and `artifact_versions`: software and input-artifact
  identities;
- `literature_status`: separate from computational evidence;
- `novelty_claim`: always `false` in this package candidate;
- `failure_state`: `null` for a success record; and
- `verification`: a fail-closed `VerificationReport`.

Shipped records also require non-empty operation-specific assumptions, source
references, and artifact identity keys for the source commit and fixture/proof.
`provenance` is derived as `built_in` or `caller_supplied`; it is not an
affirmative literature or novelty state. `evidence_status` is derived from the
verification report and the operation kind rather than accepted as a public
constructor claim: a failed report becomes `unresolved`, while a passing
report becomes `proven_exact_under_declared_assumptions`. Evidence and
literature statuses are closed package-owned values in this release, and the
result-level `__all__` surface intentionally remains the shipped operation
names rather than exporting every contract helper.

The JSON schema is shipped at
`geometric_function_atlas/schema/result.schema.json`. Unknown top-level,
canonical-input, exact-expression, verification-report, and check fields are
rejected by the dependency-free validator `validate_result_payload`.
The validator also requires operation-specific canonical/exact keys and checks
that the retained `v0.1.x` fields agree with those canonical values. A passing
report must have `failure_state: null`; a failed report must name one of the
explicit failure states and use the same value for `computational_status`.

Exact expressions are display data, while the bounded exact-expression DAG is
the authoritative identity. The validator decodes only the closed opcode set,
checks canonical node identity, and recomputes shipped outputs from
that DAG; it never parses or executes a caller formula string. Custom generators
must still be supplied as preconstructed SymPy expressions using the trusted `z`
symbol; formula strings and undeclared symbols remain invalid.

## Verification reports

A `VerificationReport` contains named `VerificationCheck` records. Every check
records:

- what was checked (`checked`);
- expected and observed values without forced floating-point conversion;
- `pass`, `fail`, or `skip` status;
- scope;
- a failure reason when it fails; and
- whether it is required for aggregate success.

A report is successful only when it contains at least one required check and
**all** required checks pass. A required skip is not success. Optional checks
do not promote a failed required check. This prevents a missing leaf, failed
mutation check, or incomplete certificate from being reported as proven.

## Failure states and CLI exit codes

Failure records use the separate closed
`geometric_function_atlas/schema/error.schema.json` contract. The states are:

| State | Meaning | CLI code |
| --- | --- | ---: |
| `invalid_input` | malformed, undeclared, or mathematically invalid input | 2 |
| `unsupported` | operation or artifact kind outside the package scope | 3 |
| `unresolved` | available evidence cannot discharge the requested claim | 4 |
| `resource_limit` | a documented bound prevented symbolic work | 5 |
| `corrupt_artifact` | structure or checksum validation failed | 6 |

CLI commands preserve the existing human-readable argparse errors. With
`--json`, failures are emitted as a versioned JSON error record on stdout with
no traceback and the stable code above.

A standard-output broken pipe (for example `gfa ... | head` when the consumer
closes the pipe early) exits with code 1 after silencing the pipe; no
traceback is emitted. It is an I/O condition, not an operation failure.

The release gate `python scripts/check_clean_install.py <wheel>` creates a
fresh virtual environment outside the checkout, installs the wheel, exercises
the API and trusted registry, mutates a verification record, and checks the
bounded-input rejection path through the installed console module.

## Trusted implementation registry

`get_trusted_implementation()` resolves only the explicit package-owned names
listed by `list_trusted_implementations()`. Records cannot provide Python import
paths, expressions, or code. Future certificate and snapshot readers must use
the same closed-registry rule rather than dynamic imports or `eval`.

## Literature boundary

`literature_status` is not inferred from `evidence_status`. A computationally
exact result can still be `not_assessed`, `known`, `candidate_improvement`,
`no_extracted_claim`, or `unresolved` in the literature. `NO_EXTRACTED_CLAIM`
does not mean novel, and this package never emits an affirmative
`novelty_claim`.
