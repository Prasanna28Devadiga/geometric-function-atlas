# Evidence and provenance policy

## Claim boundary

A returned number is not enough. Structured result objects and CLI records identify:

1. the canonical mathematical problem;
2. exact inputs and formulas;
3. the algorithm or theorem used;
4. declared assumptions;
5. evidence status;
6. source references;
7. package and artifact versions;
8. whether any literature-novelty claim is being made.

The versioned schema and fail-closed check semantics are specified in
`docs/RESULT_CONTRACT.md`; the shipped JSON schemas are under
`src/geometric_function_atlas/schema/`.

Low-level exact helpers may return bare SymPy expressions or tuples for use in
other symbolic programs. Their structured counterparts (`generator_series`,
the theorem result objects, and CLI JSON) carry the full record above.

## Evidence statuses

The package will use explicit, non-overlapping statuses:

- `screened`: numerical evidence only;
- `certified_enclosure`: a machine-checkable interval containing the sharp value;
- `proven_exact_under_declared_assumptions`: exact theorem or certificate with stated assumptions;
- `disproven`: certified counterexample or contradiction to the computational proposition;
- `unresolved`: no conclusive computation.

Literature reconciliation is a separate taxonomy. A computationally proven result may be known, a candidate improvement, absent from the indexed corpus, or still under human review. “No indexed match” is never emitted as “novel.”

## Built-in and custom generators

Built-in formulas and citations are versioned package data. Exact coefficient
operations also accept custom generators as preconstructed SymPy expressions.
String expressions are rejected because SymPy's general string parser is
eval-based; undeclared free symbols are rejected as well. For a custom generator,
the package checks only the algebraic preconditions documented by the operation;
it does not silently certify all analytic Ma–Minda admissibility hypotheses.
Structured records mark this input as `provenance: "caller_supplied"` and retain
the caller-supplied source/fixture identity explicitly; they never relabel it as
the built-in catalog.

CLI rational parameters use a bounded signed-integer or `integer/integer`
grammar. Exponent notation is intentionally unsupported, and rational
components are capped before symbolic arithmetic begins.

## Directed-radius snapshot and certificate replay

The package ships two immutable data artifacts:

- `radii_snapshot.json`, a 702-row directed snapshot from source commit
  `cf0b2b0a3539ccc7ea9dcae679afd1cd0471b5bd`; and
- `radius_certificate_fixture.json`, the eight-row reviewed source crosswalk
  from `73515129716c70d4287e2e228d15633e6ccb45f2`.

The SHA-256 values are recorded in `geometric_function_atlas.version` and are
checked before the catalog is loaded. Provenance locators use stable artifact
names and row/lane identifiers rather than checkout paths. A radius is always
identified as `source->target`; lookup never silently swaps that direction.

Radius status is evidence taxonomy, not a claim that every stored number has a
proof. The five statuses are `touch_proven_exact`, `closed_form_confirmed`,
`trivial_containment`, `unidentified`, and `audit_required`. The first two
describe different strengths of radius evidence; `trivial_containment` is a
separate route; `unidentified` is an open closed-form question; and
`audit_required` is quarantined. The typed record retains branch/domain
assumptions, the global-containment route, contact/attainment wording, and
reconciliation status without collapsing them into one boolean.

Only the eight reviewed certificate lanes are replayable. Replay uses a
package-owned, bounded SymPy implementation of the recorded inverse,
positive-majorant, boundary-contact, and monotonicity identities. It does not
import the research repository and never evaluates a candidate as Python code.
Malformed expressions, wrong direction, missing evidence, source/hash
mismatch, and resource exhaustion fail closed; only all required replay steps
passing yields `certified: true`. A candidate that parses but differs from the
reviewed exact expression is reported as `candidate_mismatch`, not as a new
radius.

## Migration from the research artifact

The original registry repository is treated as a research artifact and source of candidate algorithms/data. Code is not copied wholesale. Each migrated operation receives:

- a minimal public interface;
- independent anchor tests;
- explicit path and data injection;
- no Flask, deployment, OCR, or private-review dependency;
- a provenance note naming the originating artifact and the audit performed;
- clean wheel/sdist installation verification.

## Registry snapshots

Registry data is not package code and is never bundled into the wheel. A snapshot
manifest is the identity boundary: it records the dataset version, decompressed
SQLite byte count and SHA-256, required application tables, and row populations.
There is no canonical snapshot URL bundled with this software. When a user
acquires a snapshot from an independently published source, the manifest may
preserve that HTTPS `source_url`; the database URL and manifest URL remain
caller-supplied inputs rather than an implied package release asset.
Compressed assets additionally carry their own byte count and SHA-256. Installation
verifies the compressed asset, enforces compressed/decompressed resource limits,
opens the result with SQLite read-only and immutable flags, and checks both
`PRAGMA quick_check` and `PRAGMA integrity_check` before atomically installing it.

A successful database hash does not make a live mutable database equivalent to the
snapshot: row populations and required tables are checked as well. Snapshot facts,
paper claims, evidence records, and application associations remain observations
from the selected dataset. They do not by themselves establish a theorem,
application effectiveness, or literature novelty.

Certificate replay has a separate evidence boundary: lookup confirms the
requested versioned record exists; replay checks the stored candidate is attained
and is consistent with the declared upper bound; only a source record
with an explicit sharpness proof receives
`proven_exact_under_declared_assumptions`. A non-sharp record can therefore
report a certified upper-bound enclosure without being labelled sharp.

## Optional application labs

The Cryptography Lab exposes the website's finite S-box diagnostics. The LAT is
the signed Walsh spectrum divided by two, with input-mask rows and output-mask
columns; it is a diagnostic table and not a security proof. The package offers
both a finite generated benchmark set and an immutable 435-row website metric
snapshot; snapshot rows are reported metrics, not S-box values, and
paper-reported columns are not recomputed S-boxes.

The Image Lab accepts finite 2D or RGB arrays and applies the named coefficient
derived kernels with the website's one-reflection boundary index. Color SSIM
matches the website's clipped 7x7-window luminance calculation; it is not a
per-channel score. Image metrics and transforms are empirical statistics and
convolutions, not analytic image-domain or conformal-warp results.
