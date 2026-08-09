# `geometric-function-atlas` v0.2.0rc1 release scope

**Scope decision:** verification gate, 2026-08-09

This document is the acceptance boundary for the `v0.2.0rc1` candidate. It is a
scope and provenance record, not a declaration that the candidate is published,
paper-ready, novel, sharp, or complete. The current checkout remains the
`0.1.0` Phase 1 package at `e504452`; the radius implementation and the shared
verification contracts must pass their own tests and independent review before a
version bump or release is authorized.

The candidate is deliberately small:

1. the already reviewable Phase 1 exact generator and Ma--Minda
   Fekete--Szego operations; and
2. a narrow exact-radius certificate-replay slice containing only the eight
   reviewed global-discharge chains listed below.

The source research repository remains source material. Its broad API, mutable
registry database, discovery sweeps, proof corpus, web application, and private
review state are not package dependencies.

## 1. Immutable audit anchors

| Artifact | Exact identity | Use in this scope |
| --- | --- | --- |
| Public package under audit | `e504452eb399bf9818fbf79fff078f4104ab94ae` (`refactor: rename package to geometric-function-atlas`) | Current package surface and distribution baseline. |
| Phase 1 package base | `473bf6a1cc63648b0b6b999ea7428cbc6b455611` (`[verified] Build standalone Phase 1 package`) | Package commit named by the existing data snapshot manifest. |
| Reviewed research campaign | `cf0b2b0a3539ccc7ea9dcae679afd1cd0471b5bd` (`fix(fs2): correct mu-zero expansion count`) | Exact source for the reviewed radius campaign and its corrected result-campaign handoff. |
| Data-release source commit | `acee553e03f9ca2bdcb55977e18ff7d9deb57e40` | Exact repository commit recorded by the existing snapshot manifest. It does not identify the ignored database bytes by itself. |
| Existing data release | [`registry-2026.08.05`](https://github.com/Prasanna28Devadiga/geometric-function-atlas/releases/tag/registry-2026.08.05) | Provenance anchor only; the database is not bundled into this software RC. |

The package's existing migration fixture is intentionally older and narrower:
`tests/fixtures/fekete_szego_research_artifact.json` records source commit
`acee553`, operation `gft.fs_sharp_constant(..., verify_grid=False)`, audit date
`2026-08-04`, nine generator keys, six `mu` values, and 54 cases. The RC must
preserve that provenance rather than silently relabelling the fixture as the
`cf0b2b0` radius campaign.

### Existing data-release verification

The `registry-2026.08.05` release is independent of the software version. Its
manifest reports `manifest_schema_version: 1`, package commit
`473bf6a1cc63648b0b6b999ea7428cbc6b455611`, source database SHA-256
`5dfd7060c232bcfeb61b4118d667b59127cb5142a91eee9d030c633789de5634`, and
`database_git_tracked: false` with a dirty source worktree. It reports a
24,961,024-byte SQLite file, 25 application tables, 10,120 total rows,
`PRAGMA quick_check: ok`, `PRAGMA integrity_check: ok`, SQLite library 3.53.1,
and `PRAGMA user_version: 0`.

The release assets and verified hashes are:

| Asset | Bytes | SHA-256 |
| --- | ---: | --- |
| `gft-registry-2026.08.05.sqlite.zst` | 2,254,015 | `4fea49b741e57964f411cebfa388881a64d81f3aefd2a08d3940c296dc2acef6` |
| `registry-manifest.json` | 2,792 | `0a42493e1d0812cb0cff96112c7279bbfac3adefe2a536efbb0373153555fdec` |
| `registry-schema.sql` | 15,166 | `5298e3885a922d2207e3d0e5aa54b5569854674ce2297ffd0ad3b5ff77359f47` |
| decompressed `gft-registry-2026.08.05.sqlite` | 24,961,024 | `e20ab91171cbe7515fbb8ad116311e98cf09054407140fbb93746d1c6608f82e` |

A fresh download was decompressed and checked read-only during this audit:
all four listed hashes matched, zstd decompression succeeded, and both SQLite
integrity pragmas returned `ok`. The raw SQLite audit saw 27 entries in
`sqlite_master`; the two additional entries are SQLite internal tables, while
the release manifest's application/schema table count remains 25.

## 2. Version and schema matrix

| Contract | Version in the audited inputs | RC rule |
| --- | --- | --- |
| Software version in checkout | `0.1.0` | Do not call the checkout `0.2.0rc1` until the implementation, distribution gate, and independent review are complete. |
| RC software target | `0.2.0rc1` | Scope label only; this audit does not bump `src/geometric_function_atlas/version.py` or `CITATION.cff`. |
| Built-in generator catalog | `2026.08.04` (`GENERATOR_CATALOG_VERSION`) | Preserve as the Phase 1 artifact version unless a catalog change is separately audited. |
| RC structured-result schema | `1` | Every structured Phase 1 and radius record must carry an explicit schema version. The current 0.1.0 records have no explicit schema key and are legacy records, not RC records. |
| RC radius-certificate schema | `1` | Version the exact source/target identity, exact value, proof steps, assumptions, evidence state, and source references. Do not serialize an unreviewed discovery row as a certificate. |
| Registry snapshot manifest | `1` | The existing `registry-2026.08.05` manifest remains an external data-release contract. |
| Registry SQLite schema | `PRAGMA user_version: 0` | Treat the released `registry-schema.sql` and its checksums as the schema identity; do not infer a new schema version from the software RC. |

Supported Python policy is inherited from `pyproject.toml` and CI: runtime
requirement `>=3.10`, with CI coverage for CPython 3.10, 3.11, 3.12, and 3.13.
The audited distribution baseline was run on CPython 3.12.13. No claim is made
for versions or implementations outside that declared/CI-tested range.

## 3. Public operation inventory

### 3.1 Phase 1 names admitted by the current package

The stable Phase 1 Python names are exactly the names already exported by
`geometric_function_atlas.__all__`:

- `Generator` and `z` for trusted, preconstructed SymPy generator definitions;
- `get_generator` and `list_generators` for the built-in catalog;
- `taylor_coefficients` and `generator_series`, including the structured
  `GeneratorSeriesResult` record;
- `fekete_szego`, including the structured `FeketeSzegoResult` record; and
- `__version__`.

The console entry point is `geometric-function-atlas`, with only these Phase 1
subcommands:

- `generators [--json]`;
- `coefficients <generator> --order <n> [--json]`; and
- `fekete-szego <generator> --mu <integer-or-integer/integer> [--precision <n>] [--json]`.

Custom generators continue to require trusted, preconstructed SymPy expressions
in `z`. Formula strings, undeclared symbols, non-normalized generators, invalid
rational syntax, and over-limit resource requests remain rejection paths.

### 3.2 Radius names and operation boundary

The radius implementation must keep the source operation name
`verify_global_max_axis_symbolic` as the compatibility anchor for exact global
certificate replay. A structured `RadiusResult`-compatible record may carry its
output, but the RC must not expose the source module wholesale. The admitted
radius surface is therefore:

1. canonical directed problem identity `(inner, target)`;
2. exact candidate/radius representation;
3. replay of the registered global-discharge chain, including its proof steps,
   declared elementary assumptions, attainment/sharpness witness, source
   references, and evidence state; and
4. deterministic structured/JSON output for that replay.

`sharp_radius`, `float_localize`, `refine_mp`, `identify_radius`,
`confirm_candidate`, and generic numerical discovery helpers are not stable RC
names. They remain research/discovery internals even when useful to regenerate a
candidate. `verify_touch_symbolic` alone is also not a sharp-radius certificate:
a touch equation without a discharged global maximum and an attainment witness
must remain a weaker evidence state.

### 3.3 The eight admitted exact-radius chains

The following directed pairs are the complete radius certificate inventory for
this RC. Values are exact expressions, not floating-point claims.

| Inner class | Target class | Exact radius | Reviewed discharge / artifact |
| --- | --- | --- | --- |
| `sine` | `sigmoid` | `asin((E - 1)/(E + 1))` | Parameterized artanh-sine chain; keystone proof in `data/proofs/RADIUS_SINE_SIGMOID.md`. |
| `sine` | `tanh` | `asin(tanh(1))` | Scale-1 artanh-sine chain; `data/proofs/RADIUS_SINE_TANH.md`. |
| `crescent` | `lemniscate` | `sqrt(2)/4` | Positive-coefficient triangle majorant; `data/proofs/RADIUS_CRESCENT_LEMNISCATE.md`. |
| `starlike` | `lemniscate` | `3 - 2*sqrt(2)` | Reverse-triangle rational majorant; `data/proofs/RADIUS_STARLIKE_LEMNISCATE.md`. |
| `order_0.5` | `crescent` | `2 - sqrt(2)` | Cosine-linear boundary reduction; `data/proofs/RADIUS_ORDER_HALF_CRESCENT.md`. |
| `exponential` | `order_0.5` | `log(2)` | Exponential majorant; `data/proofs/RADIUS_EXPONENTIAL_ORDER_HALF.md`. |
| `exponential` | `lemniscate` | `log(2)/2` | Principal-branch and exponential majorant checks; `data/proofs/RADIUS_EXPONENTIAL_LEMNISCATE.md`. |
| `starlike` | `order_0.75` | `1/7` | Rational majorant and negative-axis attainment; `data/proofs/RADIUS_STARLIKE_ORDER_THREE_QUARTERS.md`. |

For this table, `proven` means the executable chain establishes the exact
containment/global maximum and the normalized Ma--Minda extremal/dilation gives
attainment. It does not mean new, novel, or publication-ready. The source
baked atlas retains its lower-level labels such as `touch_proven_exact` and
`closed_form_confirmed`; those labels must not be silently rewritten as sharp
theorems merely because a candidate has a closed form.

The package must not ship the 702-row discovery atlas as if it were this
certificate inventory. The source snapshot's counts are useful audit evidence:
702 rows total, with 323 `touch_proven_exact`, 140 `closed_form_confirmed`, 142
`trivial_containment`, 85 `unidentified`, and 12 `audit_required`. These are
separate discovery/taxonomy outcomes, not eight RC theorems.

## 4. Trust and evidence contract

Every structured result must preserve, at minimum:

- canonical exact inputs and directed problem identity;
- exact expressions and normalized display values;
- method/algorithm and the individual checks performed;
- declared assumptions and their scope;
- source repository/commit and proof or fixture references;
- package version, artifact version, and schema version;
- computational evidence status; and
- literature status as a separate field, with `novelty_claim: false` in this RC.

The following distinctions are mandatory:

- `proven_exact_under_declared_assumptions` is reserved for an exact theorem or
  certificate whose required checks pass and whose assumptions are recorded;
- `touch_proven_exact` means only that the touch equation was symbolically
  discharged under the source taxonomy; it is not automatically a global sharp
  radius;
- `closed_form_confirmed` means numerical/high-precision confirmation of a
  proposed expression, not a global proof;
- `numeric_certified`/enclosure states remain numerical evidence;
- `unidentified`, `audit_required`, `unsupported`, `unresolved`, invalid-input,
  resource-limit, and corrupt-artifact outcomes are first-class negative or
  abstention results, not successful records; and
- `NO_EXTRACTED_CLAIM`, `CANDIDATE_IMPROVE`, and similar literature outcomes do
  not become `novel` automatically. External literature closure and human
  sign-off are outside the package.

The result contract must fail closed: an aggregate `proven`/success state is
possible only when every required check passes. A missing leaf, stale source
commit, failed symbolic check, missing attainment witness, malformed exact
input, or missing provenance must prevent promotion.

## 5. Reviewer-to-artifact crosswalk

| Review question | Evidence to inspect | RC treatment |
| --- | --- | --- |
| Can a user reproduce the Phase 1 exact operations? | `src/geometric_function_atlas/`, `tests/test_*.py`, `tests/fixtures/fekete_szego_research_artifact.json`, CLI JSON, wheel/sdist smoke tests | In scope. Keep exact arithmetic, bounded input grammar, and clean-install behavior. |
| Are the radius headline rows more than numerical recognition? | `cf0b2b0`, `docs/RADIUS_PORTFOLIO_EXPANSION.md`, `docs/RADIUS_PORTFOLIO_EXPANSION_II.md`, eight `data/proofs/RADIUS_*.md` artifacts, and `tests/test_radius_proof.py` | In scope only through registered replay with global discharge and attainment. A generic touch or numerical candidate is not enough. |
| Is the source database reproducible? | `registry-2026.08.05`, its manifest/schema/checksums, source commit `acee553`, database SHA-256, and SQLite integrity results | Provenance anchor only. The DB is a separately versioned data release, not a wheel payload or RC API. |
| Does the paper's discovery/proof pipeline preserve failures? | `docs/RESULT_CAMPAIGN_HANDOFF.md`, `docs/KISHAN_RESULT_CAMPAIGN_NOTES.md`, radius status taxonomy, and deferred rows in `RADIUS_PORTFOLIO_EXPANSION_II.md` | Preserve negative results and abstentions. Do not promote candidates, open cells, or audit-required rows. |
| Are 39-class coefficient claims reviewable here? | The source campaign's `a3`, `a2a3`, FS2, inverse, logarithmic, and Toeplitz artifacts | Out of scope for this RC. No 39-class coefficient claim, count, or implication is part of the public candidate. |
| Is `T_{3,1}=H_3(1)` safe to publish from this boundary? | Source Toeplitz/Hankel frontier material and the explicit RC acceptance review | Explicitly excluded. The RC must not expose or imply the false `T_{3,1}=H_3(1)` identity. |
| Were heavy computations independently completed? | `docs/H31_RESULT_GATE.md`, `data/sos/BATCH_HANDOFF.md`, and the source campaign's deferred H3 notes | No. H3, Julia, SOS, dense SDP, and uncontrolled sweeps are excluded. |
| Does a literature screen establish novelty? | `data/radii/radius_novelty_audit.jsonl` and the source's partial-corpus reconciliation | No. Literature reconciliation is separate, partial, and human-gated; `novelty_claim` remains false. |
| Is the package ready for publication? | `docs/RELEASING.md`, distribution gate, fresh-wheel/sdist tests, and independent staged-diff review | This document does not grant publication readiness. No PyPI, Zenodo, GitHub release publication, deployment, or author contact is authorized. |

## 6. Explicit exclusions and abstentions

The following are outside `v0.2.0rc1`, even if source files contain related
experiments or names:

- the false or unreviewed `T_{3,1}=H_3(1)` identity and all `T_{3,1}`/H3
  claims;
- H3, Julia, SOS, dense SDP, high-memory solves, and broad/uncontrolled
  parameter or class sweeps;
- the source's 39-class coefficient families, including `a3`, `a2a3`, FS2,
  inverse/logarithmic, and Toeplitz coverage claims;
- candidate constants, numerical enclosures, flat/open cells, and
  `audit_required` rows presented as exact or sharp results;
- automatic novelty, contradiction, known/novel editorial decisions, or any
  assertion that `NO_EXTRACTED_CLAIM` means novel;
- OCR, paper harvesting, OpenAlex/arXiv search, metadata cleanup, PDF storage,
  review-ledger mutation, usefulness/expert sign-off, and manuscript/submission
  packaging;
- the mutable registry database, database download/install machinery, live-site
  routes, site baking, deployment, and website-only behavior;
- arbitrary formula parsing/evaluation, Python execution from JSON, caller
  `eval`, and unbounded symbolic/numerical resource requests; and
- PyPI/Zenodo/GitHub release publication, deployment, author contact, or
  credential/token output.

The existing data release may be used to identify a future snapshot contract,
but it is not a silent dependency of the RC and does not make the RC a registry
release.

## 7. Radius implementation handoff

The radius implementer should begin from the exact `cf0b2b0` source commit and
its radius artifacts, not from a broad current worktree or from the 702-row
atlas. The first implementation slice should:

1. reproduce the eight directed pairs and exact values in §3.3;
2. keep `inner` and `target` direction explicit in every identity and record;
3. register only the eight reviewed global-discharge chains;
4. emit the RC result/certificate schema from §2 and the evidence contract in
   §4, including source commit, proof artifact, assumptions, checks, and
   `novelty_claim: false`;
5. add positive anchors, at least one candidate/touch-only negative anchor, an
   invalid-candidate mutation, and a missing/failed-check mutation;
6. preserve the source taxonomy rather than relabelling all discovery rows; and
7. verify the installed wheel from outside the checkout before requesting the
   independent staged-diff review.

Private source helpers such as `_PROVEN_CHAINS`, discovery/localization routines,
PSLQ/`mp.identify` heuristics, and proof-campaign scripts are implementation
machinery, not public API. A future expansion needs a separate scope decision,
source commit, artifact/schema version, and review crosswalk.

## 8. Baseline verification recorded for this audit

The audited `e504452` checkout was exercised with the following real commands.
The current package version is still `0.1.0`.

```text
uv run --with pytest --with ruff --with mypy --with build --with twine python -m pytest -q
82 passed in 4.02s

uv run --with pytest --with ruff --with mypy --with build --with twine python -m ruff check src tests scripts
All checks passed!

uv run --with pytest --with ruff --with mypy --with build --with twine python -m mypy src --ignore-missing-imports
Success: no issues found in 8 source files

uv run --with pytest --with ruff --with mypy --with build --with twine python -W error -m pytest -q
82 passed in 2.94s

uv run --with pytest --with ruff --with mypy --with build --with twine python -m build
Successfully built geometric_function_atlas-0.1.0.tar.gz and geometric_function_atlas-0.1.0-py3-none-any.whl

uv run --with pytest --with ruff --with mypy --with build --with twine python -m twine check dist/*
Checking ...whl: PASSED
Checking ...tar.gz: PASSED

uv run --with pytest --with ruff --with mypy --with build --with twine python scripts/check_distribution.py dist
distribution contents: PASS (geometric_function_atlas-0.1.0-py3-none-any.whl, geometric_function_atlas-0.1.0.tar.gz)
```

A fresh wheel environment, outside the checkout, passed API, module/console
entry-point, JSON, and scientific-notation rejection smoke tests. A fresh sdist
environment, also outside the checkout, passed the `generator_series` API smoke
test. The first sdist invocation used a relative `dist/...` path after changing
to `/tmp` and failed before installation; rerunning with the absolute archive
path passed. This was a harness path error, not a package result.

This baseline verifies the current Phase 1 distribution only. It does not verify
the unimplemented RC radius surface, the future result schema, a paper-level
reproduction, novelty, or publication readiness.

## 9. Verification gate for the RC

Before any RC tag or publication action, require all of the following:

- the implementation diff is reviewed against this document and the exact
  `e504452`/`cf0b2b0` anchors;
- Phase 1 compatibility and the eight radius positive/negative/mutation tests
  pass with warnings treated as errors;
- the closed result/certificate schemas are versioned and archive contents are
  checked;
- wheel and sdist installs work from a neutral directory, including rejection
  and resource-limit paths;
- no database, cache, secret, audit log, private review state, H3/SOS artifact,
  or broad corpus leaks into the distribution;
- the source research worktree is unchanged by package work;
- a reviewer inspects the repository-qualified final staged diff and archive
  contents; and
- publication, deployment, author contact, and credentials remain separately
  authorized actions.

Until those gates pass, the correct status is `RC scope approved; implementation
and independent verification pending`, not `SAFE TO PUBLISH`.
