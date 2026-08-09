# Adversarial public API design for `geometric-function-atlas`

**Status:** design proposal, 2026-08-09. Not a verification gate, not an
authorization to implement, tag, or publish.

**Base commit:** `a82f6b5bf11b9cc8fe6777bc185821191cd71738`
**Package under design:** `0.1.0` in the checkout; RC scope label `0.2.0rc1`.
**Governing scope document:** `docs/RELEASE_SCOPE.md`. Where this design and the
scope document disagree, the scope document wins and this document is wrong.

This document specifies the smallest public interface that makes the package
independently inspectable and claim-safe. It adds **no mathematical
functionality**. Every operation it names is either already implemented at
`0.1.0` or already admitted by `docs/RELEASE_SCOPE.md` §3.

The tone is deliberately hostile. Sections 2, 12, and 16 are written as an
attacker and as an annoyed reviewer, not as an author.

---

## 0. Executive summary

A reviewer must be able to answer six questions from an artifact alone, offline,
without running the package and without trusting the website:

1. What exact mathematical object is this a claim about?
2. What is the exact value, in a form no printer can perturb?
3. What was actually checked, and what was merely assumed?
4. What is the evidence status, and is it distinct from a novelty claim?
5. Which software version, artifact version, and schema version produced it?
6. If it failed, why, and in which of the seven named negative states?

The design achieves this with **one canonical expression encoding**, **one
record envelope**, **one check/report shape**, **one closed failure taxonomy**,
and **a versioning rule that keeps software, artifact, snapshot, and schema
versions independent**. Everything else is deferred.

Three findings drive the design, each verified against the checkout rather than
asserted:

- **F1 — the display string is not the value.** `Generator.formula` and every
  `*_exact` field are `sp.sstr(...)` output. Under SymPy 1.14 the admitted
  `sine → sigmoid` radius prints as `asin((-1 + E)/(1 + E))`, while
  `docs/RELEASE_SCOPE.md` §3.3 writes it as `asin((E - 1)/(E + 1))`. Both name
  the same number. Neither is a stable identity. Any consumer — the website
  included — that compares, hashes, or keys on these strings will report a false
  mismatch on a SymPy upgrade. §4 fixes this.
- **F2 — the evidence status is an unvalidated free-form string with a default.**
  `FeketeSzegoResult.evidence_status: str = "proven_exact_under_declared_assumptions"`
  is a public dataclass field. A caller can construct the record directly with
  any string. Separately, `GeneratorSeriesResult` emits
  `proven_exact_algebraic`, which is **not one of the five statuses defined in
  `docs/PROVENANCE.md`**. The package already emits a status its own policy
  document does not define. §5.3 fixes this.
- **F3 — the radius class namespace does not exist yet.** The eight admitted
  chains in `docs/RELEASE_SCOPE.md` §3.3 reference the class keys `tanh`,
  `order_0.5`, and `order_0.75`. The built-in catalog contains none of them
  (`bell, cosh_sqrt, crescent, exponential, lemniscate, rational_kr, sigmoid,
  sine, starlike`). Implementing radius replay by quietly adding three catalog
  entries would silently expand an artifact pinned at
  `GENERATOR_CATALOG_VERSION = "2026.08.04"`, which §2 of the scope document
  forbids without a separate audit. §5.5 fixes this.

---

## 1. Design axioms

These are non-negotiable invariants. Each later section is only a consequence.

| # | Axiom | Consequence |
| --- | --- | --- |
| A1 | A number without provenance is not a result. | Every public operation returns a record, or a low-level exact value explicitly documented as *not* a claim. |
| A2 | Exact values are DAGs, not strings. | §4. Display strings are lossy views, never identity. |
| A3 | No `eval`, no `sympify` on untrusted text, no executable JSON. | §4.4. A closed opcode whitelist, atoms only, bounded. |
| A4 | Verification fails closed. | §6. An empty, partial, or skipped required check set is a failure, never a vacuous pass. |
| A5 | Negative outcomes are first-class values, not exceptions to be swallowed. | §7. Seven named states, stable codes, stable exit codes. |
| A6 | Software version, artifact version, snapshot version, and schema version are four independent axes. | §8. None may be inferred from another. |
| A7 | The package never reaches the network and never mutates anything outside a caller-named path. | §10. No downloads, no bundled database, no cache directory. |
| A8 | Computational evidence is not literature novelty. | §5.4. `novelty_claim` is `false` in this RC and cannot be set by any public code path. |
| A9 | The website is a display consumer. | §11. Data flows package+snapshot → site. Never site → package. |
| A10 | The smallest surface that satisfies A1–A9 wins. | §16. Anything not required by a reviewer question is cut. |

---

## 2. Adversary model

Who we are defending against, in priority order.

**Adv-1 — the honest reviewer with a different SymPy.** Not malicious; the most
likely source of a false alarm. Installs the wheel on CPython 3.13 with a newer
SymPy, gets a different printed string, and concludes the package is
non-reproducible. Defended by §4 and §9.

**Adv-2 — the optimistic downstream author.** Reads `evidence_status` past the
first underscore, sees `proven`, and writes "proved by the atlas package" in a
manuscript. Or reads `NO_EXTRACTED_CLAIM` as "novel". Defended by §5.3, §5.4,
and by refusing to emit any status string whose prefix reads as a stronger claim
than it is.

**Adv-3 — the untrusted JSON author.** Hands the package a certificate,
manifest, or fixture file. Wants code execution, unbounded memory, unbounded
CPU, or a forged `proven` record. Defended by §4.4, §7, §10.

**Adv-4 — the future maintainer in a hurry.** Adds a field, reuses an exit code,
promotes a `touch_proven_exact` row to sharp because it has a closed form, or
points the package at the live site to "fill in" a missing value. Defended by
§8, §11, and by making the wrong thing hard to express rather than merely
documented as forbidden.

**Adv-5 — the resource attacker.** Supplies a legal-looking but adversarial
input (deeply nested expression, 128-digit rational, order-64 series over a
pathological custom generator). Defended by §10 — with an honest statement of
where the bound does *not* hold.

Explicitly **not** defended against: a hostile maintainer with commit access, a
compromised build pipeline, or a caller who constructs a `Generator` from an
expression that is not actually Ma–Minda admissible. The third is a documented
caller assumption in `docs/PROVENANCE.md` and stays one; §5.3 only ensures the
resulting record cannot *claim* otherwise.

---

## 3. The stable public surface

### 3.1 Python names

Everything listed is exported from `geometric_function_atlas` and covered by the
compatibility rules in §8. Everything not listed is private, including anything
prefixed `_`, every submodule path, and every name in
`docs/RELEASE_SCOPE.md` §3.2's exclusion list (`sharp_radius`, `float_localize`,
`refine_mp`, `identify_radius`, `confirm_candidate`, `_PROVEN_CHAINS`).

**Tier 0 — unchanged Phase 1 names (already stable at `0.1.0`).**

```
Generator            z                    get_generator        list_generators
taylor_coefficients  generator_series     GeneratorSeriesResult
fekete_szego         FeketeSzegoResult    __version__
```

**Tier 1 — evidence and provenance vocabulary (new, small, mostly data).**

```
EvidenceStatus       LiteratureStatus     Assumption           SourceRef
```

**Tier 2 — exact serialization (new; the load-bearing addition).**

```
encode_exact         decode_exact         canonical_json       canonical_digest
```

**Tier 3 — verification (new).**

```
Check                CheckOutcome         VerificationReport   verify
```

**Tier 4 — failures (new; exceptions plus their serializable form).**

```
AtlasError           UnsupportedOperation  InvalidInput        UnresolvedProvenance
VerificationFailed   CorruptArtifact       IncompatibleSchema  ResourceLimitExceeded
Failure
```

**Tier 5 — radius replay (new; admitted by scope §3.2, gated on implementation).**

```
RadiusClass          list_radius_pairs     radius_certificate  RadiusResult
verify_global_max_axis_symbolic
```

**Tier 6 — snapshot descriptors (new; descriptor and verifier only, never a loader).**

```
SnapshotDescriptor   read_snapshot_descriptor   verify_snapshot
```

**Tier 7 — schema constants.**

```
RESULT_SCHEMA_VERSION        # int, currently 1
CERTIFICATE_SCHEMA_VERSION   # int, currently 1
EXACT_EXPR_SCHEMA_VERSION    # int, currently 1
SUPPORTED_SCHEMA_VERSIONS    # mapping name -> frozenset[int] this build can *read*
```

That is 34 names, of which 10 already exist. Tiers 5 and 6 are the only ones
that may be deferred past `0.2.0rc1` without weakening the contract; Tiers 0–4
and 7 are the minimum that makes the existing Phase 1 output claim-safe. If the
radius implementation slips, ship Tiers 0–4 and 7 as `0.2.0rc1` and keep Tier 5
for `0.3.0rc1`. Do **not** ship a partial Tier 5.

`verify_global_max_axis_symbolic` is retained verbatim as the compatibility
anchor required by scope §3.2. It is the *only* research-side name that crosses
into the public surface, and it is exported as a thin, documented replay entry
point — not as a re-export of the source module.

### 3.2 CLI surface

```
geometric-function-atlas generators [--json] [--canonical]
geometric-function-atlas coefficients <generator> --order <n> [--json] [--canonical]
geometric-function-atlas fekete-szego <generator> --mu <int|int/int>
                                      [--precision <n>] [--json] [--canonical]
geometric-function-atlas radius <inner> <target> [--json] [--canonical]
geometric-function-atlas verify radius [--pair <inner>:<target>] [--json]
geometric-function-atlas verify phase1 [--json]
geometric-function-atlas verify snapshot --manifest <path> [--assets <dir>] [--json]
geometric-function-atlas schema [--json]
```

Rules:

- `--json` is the human-oriented pretty form: indented, insertion-ordered,
  informative. **It is not the digest input.**
- `--canonical` is the byte-stable form defined in §9: compact separators,
  `sort_keys=True`, `ensure_ascii=True`, single trailing newline, no floats.
  `--canonical` implies `--json`. Two builds with the same versions must emit
  identical bytes.
- `schema` prints the schema names and version ranges this build can read and
  write. It is the machine-readable answer to "will your tooling work with my
  wheel", and it must never require network or data files.
- No `--verbose`, no `--quiet`, no `--config`, no `--output`, no colour flag, no
  `--download`. See §16.

**Encoding defect to fix while here.** `cli._write` currently calls
`json.dumps(..., ensure_ascii=False)` and `print`s the result. Catalog citations
contain non-ASCII characters (`Sokół`, the `–` in `Ma–Minda`). On a console whose
`stdout` encoding is not UTF-8, that `print` raises `UnicodeEncodeError`, which
is not in `cli.main`'s `except (KeyError, TypeError, ValueError)` clause, so the
user gets a traceback and exit `1` from a *successful* computation. Both forms
must therefore write UTF-8 bytes explicitly to `sys.stdout.buffer`, and
`--canonical` must additionally set `ensure_ascii=True`.

---

## 4. Canonical exact expressions (`exact_expr` schema, version 1)

### 4.1 Why the current representation is insufficient

`str(sp.Expr)` is a *printer*. Printers change. §0 F1 shows the two spellings of
one admitted radius already in circulation in this repository. A reviewer
diffing an artifact produced by SymPy 1.12 against one produced by 1.14 must not
see a spurious difference, and a website keying a cache on `value_exact` must
not silently create two entries for one number.

`sp.srepr` is worse for this purpose, not better: `srepr` of the same radius is
`asin(Mul(Add(Integer(-1), E), Pow(Add(Integer(1), E), Integer(-1))))`, and the
only supported way to read it back is `sympify`, which is `eval`. Axiom A3
forbids that. `pickle` is out for the same reason, plus arbitrary code
execution.

### 4.2 The encoding

An exact expression is a JSON object tree. Every node has an `op`. There are
four atoms and a closed set of operators.

**Atoms**

| Node | Meaning | Constraints |
| --- | --- | --- |
| `{"op":"int","value":"<digits>"}` | exact integer | optional leading `-`, no `+`, no leading zeros except `"0"`, ≤ 128 digits |
| `{"op":"rat","num":"<digits>","den":"<digits>"}` | exact rational | lowest terms, `den > 0`, each part ≤ 128 digits, never used when `den == 1` |
| `{"op":"const","name":"e"\|"pi"}` | named exact constant | closed set of two |
| `{"op":"var","name":"z"}` | the generator variable | closed set of one |

**Operators** — `add`, `mul` (n-ary, n ≥ 2), `pow` (binary), `max`, `min`
(n-ary, n ≥ 2), and the unary set `exp`, `log`, `abs`, `sin`, `cos`, `tan`,
`asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`.

There is **no `sqrt` opcode**. `sqrt(2)` is `pow(int 2, rat 1/2)`. There is no
`div`, no `sub`, and no `neg`: they are `pow` with a negative exponent and `mul`
by `int -1`. One normal form per value is the entire point — an alias set is how
canonicalization dies.

**Canonicalization rules**

1. `add`, `mul`, `max`, `min` arguments are sorted by the canonical serialization
   of each argument, byte-wise. This makes the encoding independent of SymPy's
   internal argument order.
2. Integers are `int` nodes; rationals with denominator 1 are `int` nodes.
3. No floating point value may appear anywhere in the tree, at any depth, ever.
4. Object keys are emitted sorted; separators are `(",", ":")`; `ensure_ascii`
   is true.
5. `encode(decode(x)) == x` byte-for-byte for every accepted `x`. This
   idempotence is an acceptance test (§15, AT-05), not a hope.

### 4.3 Worked encodings (verified)

All eight admitted radii encode and round-trip. Verified against SymPy 1.14 on
CPython 3.12.13 with a prototype implementing exactly the rules above:

| Pair | Display (SymPy 1.14) | Canonical form |
| --- | --- | --- |
| `sine → tanh` | `asin(tanh(1))` | `{"args":[{"args":[{"op":"int","value":"1"}],"op":"tanh"}],"op":"asin"}` |
| `starlike → order_0.75` | `1/7` | `{"den":"7","num":"1","op":"rat"}` |
| `exponential → order_0.5` | `log(2)` | `{"args":[{"op":"int","value":"2"}],"op":"log"}` |
| `exponential → lemniscate` | `log(2)/2` | `{"args":[{"args":[{"op":"int","value":"2"}],"op":"log"},{"den":"2","num":"1","op":"rat"}],"op":"mul"}` |
| `crescent → lemniscate` | `sqrt(2)/4` | `{"args":[{"args":[{"op":"int","value":"2"},{"den":"2","num":"1","op":"rat"}],"op":"pow"},{"den":"4","num":"1","op":"rat"}],"op":"mul"}` |
| `order_0.5 → crescent` | `2 - sqrt(2)` | `{"args":[{"args":[{"args":[{"op":"int","value":"2"},{"den":"2","num":"1","op":"rat"}],"op":"pow"},{"op":"int","value":"-1"}],"op":"mul"},{"op":"int","value":"2"}],"op":"add"}` |
| `starlike → lemniscate` | `3 - 2*sqrt(2)` | `{"args":[{"args":[{"args":[{"op":"int","value":"2"},{"den":"2","num":"1","op":"rat"}],"op":"pow"},{"op":"int","value":"-2"}],"op":"mul"},{"op":"int","value":"3"}],"op":"add"}` |
| `sine → sigmoid` | `asin((-1 + E)/(1 + E))` | `{"args":[{"args":[{"args":[{"args":[{"name":"e","op":"const"},{"op":"int","value":"1"}],"op":"add"},{"op":"int","value":"-1"}],"op":"pow"},{"args":[{"name":"e","op":"const"},{"op":"int","value":"-1"}],"op":"add"}],"op":"mul"}],"op":"asin"}` |

Note the last row against `docs/RELEASE_SCOPE.md` §3.3's `asin((E - 1)/(E + 1))`:
the canonical form is identical for both spellings, which is exactly the
property F1 requires.

All nine catalog generator expressions also round-trip under the same opcode
set, so one encoding covers both the coefficient surface and the radius surface.
No second format is needed.

### 4.4 Decoding is the security boundary

`decode_exact` is the only place untrusted structure becomes SymPy. It must:

- reject any `op` not in the whitelist (verified: `{"op":"eval",...}` →
  `InvalidInput: unsupported opcode 'eval'`);
- reject any `var` name not in `{"z"}` (verified: `"__import__"` → rejected);
- reject any integer/rational literal over 128 digits (verified);
- reject rationals not in lowest terms or with non-positive denominator
  (verified: `2/4` and `1/0` both rejected);
- enforce a node budget (4096) and depth budget (64) *during* the walk, not
  after (verified: 200-deep nesting → `ResourceLimitExceeded`);
- never call `sympify`, `eval`, `exec`, `parse_expr`, `pickle.loads`, or
  `getattr(sympy, name)`. The opcode → constructor mapping is a literal dict.

`decode_exact` must not be reachable from any operation that has not already
established the artifact's provenance. Concretely: verify the manifest hash
first, decode second (§7 `corrupt_artifact` precedes `invalid_input`).

### 4.5 Digests

`canonical_digest(record) -> str` returns `"sha256:" + hex` over the UTF-8 bytes
of `canonical_json(record)`. Verified sample digests over the canonical exact
value alone:

```
starlike → order_0.75  (1/7)   sha256:1d31db063674b694446f7544ce4420d139d7d8781945c3605391c7a687bd5770
exponential → order_0.5 log(2) sha256:5759d2a41c06a8a78108e90faf0d7daef67c3b7b9ed71aa836d095260e9ae7c3
sine → sigmoid                 sha256:a279c96145d36a5c2bbc8cb980edaab3d55520326be72bdfdcf9f73f45d92b62
fekete_szego(exponential, 0)   sha256:7f2df945193aa345c02f0a985b23e431bc0938739455196472b0d768c8feedb2
```

Digests are **advisory identifiers, not claims**. A matching digest means two
artifacts encode the same value; it says nothing about whether the value is
correct. Never gate `proven` on a digest match alone.

---

## 5. The record model

### 5.1 Envelope

Every claim-bearing JSON object emitted by the package begins with:

```json
{
  "schema": "gft.result",
  "schema_version": 1,
  "package_version": "0.2.0rc1",
  "artifact_versions": {"generator_catalog": "2026.08.04"},
  "record_kind": "generator_series"
}
```

`schema` and `schema_version` are mandatory and are the first two keys in the
human form. Their absence is the defining property of a `0.1.0` **legacy
record** (scope §2), and consumers must treat an absent `schema_version` as
"legacy, not RC" rather than as "version 1".

### 5.2 Value fields

Any exact quantity appears as a triple, never as a bare string:

```json
"radius": {
  "exact": { ...canonical exact_expr DAG... },
  "display": "log(2)/2",
  "decimal": {"value": "0.34657359027997265471", "precision": 20, "rounding": "sympy.N"}
}
```

- `exact` is authoritative. Comparison, hashing, and equality use it alone.
- `display` is a courtesy for humans and is explicitly **printer- and
  version-dependent**. The field documentation must say so.
- `decimal` is optional, always carries its precision, and is explicitly **not a
  claim**: it is a rounded view of `exact`. It must never be the basis of a
  pass/fail decision.

`FeketeSzegoResult.to_dict` currently calls `self.decimal(precision=...)`, which
can raise `ValueError` for an out-of-range precision — i.e. serialization is
currently a validation site. In the RC, precision is validated at the call
boundary and `to_dict` cannot raise for a well-formed record.

### 5.3 Evidence status

`EvidenceStatus` is a closed enum whose members are exactly the five defined in
`docs/PROVENANCE.md`, plus the source-taxonomy labels that scope §4 requires be
preserved rather than rewritten:

| Member | Meaning | May appear in an aggregate success? |
| --- | --- | --- |
| `PROVEN_EXACT_UNDER_DECLARED_ASSUMPTIONS` | exact theorem/certificate, required checks passed, assumptions recorded | yes |
| `CERTIFIED_ENCLOSURE` | machine-checkable interval containing the sharp value | no |
| `SCREENED` | numerical evidence only | no |
| `DISPROVEN` | certified counterexample to the computational proposition | n/a (a conclusive negative) |
| `UNRESOLVED` | no conclusive computation | no |
| `TOUCH_PROVEN_EXACT` | source taxonomy: touch equation symbolically discharged; **not** a global sharp radius | no |
| `CLOSED_FORM_CONFIRMED` | source taxonomy: high-precision confirmation of a proposed expression | no |

Three hard rules:

1. **`proven_exact_algebraic` is retired.** It is emitted today by
   `GeneratorSeriesResult` and is undefined in `docs/PROVENANCE.md`. Exact
   Taylor coefficients of a preconstructed expression are a decidable algebraic
   computation under a checked normalization, so they map to
   `PROVEN_EXACT_UNDER_DECLARED_ASSUMPTIONS` with the assumption set made
   explicit (§5.4). This is a **breaking output change** and is scheduled in
   §14.
2. **Status is not caller-settable.** `evidence_status` stops being a defaulted
   public dataclass field. Result objects are constructed only by the operations
   that computed them; the field is derived, not supplied. A public constructor
   that accepts `evidence_status="proven..."` is a forgery primitive.
3. **User-supplied generators cannot reach the top status.** Today,
   `fekete_szego(custom_generator, mu=0)` returns a record carrying
   `evidence_status: proven_exact_under_declared_assumptions` and
   `artifact_versions.generator_catalog: "user-supplied"`. The package has
   verified only the algebraic preconditions it can decide; Ma–Minda
   admissibility is a caller assumption. The RC therefore adds a top-level
   `provenance: "builtin_catalog" | "user_supplied"`, and for `user_supplied`
   the status caps at `PROVEN_EXACT_UNDER_DECLARED_ASSUMPTIONS` **only with**
   an explicit `caller_asserted` assumption whose `verified: false` is visible
   in the record. A downstream reader must be able to filter user-supplied
   records with one predicate.

### 5.4 Assumptions, sources, literature

```json
"assumptions": [
  {"id": "phi_normalized", "statement": "phi(0) = 1", "scope": "generator",
   "verified": true,  "method": "exact_symbolic_identity"},
  {"id": "ma_minda_admissible", "statement": "phi is an admissible Ma-Minda generator",
   "scope": "generator", "verified": false, "method": "caller_asserted"}
]
```

The `verified` flag is the field that matters. `0.1.0` emits assumptions as bare
strings, which makes a checked normalization and an unchecked analytic
hypothesis indistinguishable in the JSON. That is the single most misleading
property of the current output.

```json
"sources": [
  {"kind": "theorem", "citation": "W. C. Ma and D. Minda, ...", "url": null},
  {"kind": "proof_artifact", "path": "data/proofs/RADIUS_EXPONENTIAL_LEMNISCATE.md",
   "repository": "gft-registry research artifact",
   "commit": "cf0b2b0a3539ccc7ea9dcae679afd1cd0471b5bd",
   "sha256": "sha256:<artifact digest>"}
]
```

`SourceRef.kind` is a closed set: `theorem`, `proof_artifact`, `fixture`,
`snapshot`, `catalog`. A `proof_artifact` reference with a commit but no digest
is `UNRESOLVED_PROVENANCE`, not a warning — a path alone does not identify
bytes, exactly as scope §1 says of the data-release source commit.

```json
"literature": {"status": "not_reviewed", "novelty_claim": false, "reviewed_by": null}
```

`LiteratureStatus` is a closed enum: `NOT_REVIEWED`, `KNOWN_GENERAL`,
`KNOWN_SPECIFIC`, `CANDIDATE_IMPROVEMENT`, `CONTRADICTION`, `NO_EXTRACTED_CLAIM`.
In this RC every emitted record carries `NOT_REVIEWED`. `novelty_claim` is a
literal `false` with **no public code path that can set it true** — not a
parameter, not a flag, not an environment variable. `NO_EXTRACTED_CLAIM` never
implies novelty, and the enum deliberately has no `NOVEL` member for a human to
reach for.

### 5.5 Problem identity, and the radius class namespace

Directed identity is serialized with named roles, never as a positional array:

```json
"problem": {
  "kind": "inclusion_radius",
  "inner":  {"class": "sine",          "params": {}},
  "target": {"class": "starlike_order", "params": {"alpha": {"den":"2","num":"1","op":"rat"}}},
  "label":  "sine -> order_0.5"
}
```

`["sine","sigmoid"]` is forbidden: a reader cannot tell it from `["sigmoid","sine"]`
reversed, and the eight chains are directional.

This resolves F3. `order_0.5` and `order_0.75` are **display labels carried
forward from the source taxonomy**, not identities. Keying a mathematical class
on a decimal string is a defect: it invites float parsing, makes `order_0.5` and
`order_0.50` distinct keys for one class, and hides the exact parameter. The
canonical identity carries the parameter as an `exact_expr` rational.

Consequently the RC introduces a **radius class registry** that is a separate,
separately versioned artifact from the generator catalog:

```json
"artifact_versions": {"generator_catalog": "2026.08.04", "radius_classes": "2026.08.09"}
```

Each `RadiusClass` either links to a catalog generator (`generator_key: "sine"`)
or declares its own expression and citation (`generator_key: null`). Adding
`tanh`, `starlike_order`, and any other class required by the eight chains must
**not** mutate `GENERATOR_CATALOG_VERSION`, which scope §2 pins at `2026.08.04`
pending a separate audit.

---

## 6. Verification: checks, reports, fail-closed aggregation

### 6.1 Check

```json
{
  "id": "global_max_on_axis",
  "description": "Symbolic global maximum of the boundary functional is attained on the real axis",
  "required": true,
  "outcome": "pass",
  "scope": "0 < r <= asin(tanh(1))",
  "expected": {"exact": {...}, "display": "0"},
  "observed": {"exact": {...}, "display": "0"},
  "method": "sympy.simplify difference to zero",
  "reason": null,
  "duration_ms": 412
}
```

- `outcome` ∈ `pass | fail | skip`. There is no `warn` and no `xfail`.
- `expected` and `observed` are mandatory for `pass` and `fail`. A check that
  cannot state both is not a check; it is a comment.
- `scope` states where the check holds. A symbolic identity verified only on a
  subinterval must say so; a check with an unstated scope is treated as
  `unknown` and cannot be `required`.
- `reason` is mandatory and non-empty for `fail` and `skip`, and must be `null`
  for `pass`.

### 6.2 Report and the fail-closed rule

```json
{
  "schema": "gft.verification_report", "schema_version": 1,
  "target": {"kind": "inclusion_radius", "inner": {...}, "target": {...}},
  "required_check_ids": ["candidate_exact", "boundary_touch", "global_max_on_axis", "attainment_witness"],
  "checks": [ ... ],
  "counts": {"pass": 4, "fail": 0, "skip": 0, "total": 4},
  "aggregate": "pass",
  "evidence_status": "proven_exact_under_declared_assumptions",
  "reason": null
}
```

`aggregate == "pass"` **only if every one of the following holds**:

1. `required_check_ids` is declared, non-empty, and comes from the registered
   chain definition — not from the checks that happened to run;
2. every id in `required_check_ids` appears exactly once in `checks`;
3. every required check has `outcome == "pass"`;
4. no check has `outcome == "fail"`, required or not;
5. no required check has `outcome == "skip"` — a skipped required check is a
   failure, with the skip reason as the failure reason;
6. every `SourceRef` resolved and every declared assumption is either
   `verified: true` or explicitly listed as a declared assumption of the
   registered chain;
7. the artifact's recorded source commit matches the chain's pinned commit.

Otherwise `aggregate` is `"fail"` and `reason` names the first violated rule.
There is no third aggregate value; a report whose checks all skipped is `fail`,
not `inconclusive`.

**The vacuous-truth trap.** `all([])` is `True` in Python, and `all(c.passed for
c in self.checks)` over an empty or filtered list is the single most likely way
this contract silently becomes worthless. Rules 1, 2, and 5 exist specifically
to make an empty or partial check set impossible to mistake for success, and
AT-11 in §15 tests exactly that.

Aggregation across targets uses the same rule: `verify radius` over all eight
pairs passes only if all eight reports pass and all eight registered pairs were
attempted. A missing pair is a failure, not a smaller run.

### 6.3 What verification does not do

It does not establish sharpness beyond the registered chain, does not upgrade
`TOUCH_PROVEN_EXACT` to a sharp radius, does not consult literature, and does
not decide novelty. A passing report is a statement about *executed checks under
declared assumptions*, and its human summary line must say that, in those words.

---

## 7. Negative states

Seven states, one code each, in a closed set. Each has exactly one Python
exception type and one CLI exit code.

| Code | Exception | Exit | When | Not to be confused with |
| --- | --- | --- | --- | --- |
| `unsupported_operation` | `UnsupportedOperation` | 4 | Name is known to the project but not admitted in this release (a 9th radius pair, a Hankel functional, `sharp_radius`). | `invalid_input` — the caller did nothing wrong. |
| `invalid_input` | `InvalidInput` | 3 | Malformed or out-of-grammar input: unknown generator key, `mu="1e1000"`, non-normalized generator, unknown opcode, undeclared symbol. | usage error (exit 2) — the *command line* was well-formed. |
| `unresolved_provenance` | `UnresolvedProvenance` | 5 | A required `SourceRef` cannot be resolved to bytes: missing proof artifact, digest absent, source commit mismatch. | `corrupt_artifact` — nothing is corrupt; something is missing or unpinned. |
| `verification_failed` | `VerificationFailed` | 6 | A required check failed or the §6.2 aggregate rule was violated. | `invalid_input` — the input was fine and the answer is "no". |
| `corrupt_artifact` | `CorruptArtifact` | 7 | Bytes exist but do not match: SHA-256 mismatch, truncated archive, `PRAGMA integrity_check` not `ok`, JSON that will not parse. | `incompatible_schema` — the bytes are damaged, not merely newer. |
| `incompatible_schema` | `IncompatibleSchema` | 8 | Well-formed artifact whose `schema_version` or snapshot manifest version is outside `SUPPORTED_SCHEMA_VERSIONS`, or which carries unknown claim-bearing keys (§8.3). | `corrupt_artifact`. |
| `resource_limit` | `ResourceLimitExceeded` | 9 | A declared bound was hit: order > 64, precision > 1000, rational > 128 digits, expression ops > 10 000, DAG nodes > 4096, depth > 64. | `invalid_input` — the request was legal but too large. |

Reserved: `0` success, `1` internal error (an unhandled exception; always a bug,
never a normal outcome), `2` usage error (argparse's, unchanged). Codes 10–63
are reserved for future states. **A code's meaning is never reused or
renumbered** — that is a major-version change under §8.

All seven inherit from `AtlasError`, so `except AtlasError` catches every
expected failure and nothing else. `KeyError`, `TypeError`, and bare `ValueError`
stop being part of the contract: `get_generator("missing")` currently raises
`KeyError`, which forces callers to catch a builtin and stringifies with quotes
in messages. `InvalidInput` subclasses `LookupError` and `ValueError` for one
release to keep existing `except (KeyError, ValueError)` callers working (§14).

`Failure` is the serializable form, emitted instead of a result whenever
`--json` is in effect so that machine consumers get structured output on the
failure path too:

```json
{
  "schema": "gft.failure", "schema_version": 1,
  "code": "verification_failed",
  "message": "required check 'attainment_witness' did not run",
  "operation": "verify radius --pair sine:sigmoid",
  "detail": {"required_check_ids": ["..."], "missing": ["attainment_witness"]},
  "package_version": "0.2.0rc1"
}
```

`message` is human text and may change in a patch release. `code` and `detail`
keys are contract. Failure output goes to **stdout** when `--json` is set (so it
can be piped) and to stderr otherwise; the exit code is authoritative either
way.

**Current-state note.** At `0.1.0`, `cli.main` funnels `KeyError`, `TypeError`,
and `ValueError` into `parser.error(...)`, so "unknown generator", "order too
large", and "you forgot `--mu`" all exit `2` and are indistinguishable to a
script. `tests/test_cli.py` pins that behaviour. §14 schedules the change.

---

## 8. Versioning and compatibility

### 8.1 Four independent axes

| Axis | Where it lives | Format | Changed by |
| --- | --- | --- | --- |
| Software version | `version.py`, `CITATION.cff`, `pyproject` dynamic | SemVer, `0.2.0rc1` | a code release |
| Artifact versions | `GENERATOR_CATALOG_VERSION`, `RADIUS_CLASSES_VERSION` | `YYYY.MM.DD` | an audited data change |
| Schema versions | `RESULT_SCHEMA_VERSION`, `CERTIFICATE_SCHEMA_VERSION`, `EXACT_EXPR_SCHEMA_VERSION` | monotone `int` | a record-shape change |
| Snapshot version | the registry release manifest | `registry-YYYY.MM.DD` + `manifest_schema_version` | a data release |

**No axis may be derived from another.** In particular: the software version
must never be parsed to decide snapshot compatibility, `PRAGMA user_version: 0`
must never be reinterpreted as a software version (scope §2), and installing a
newer wheel must never change which snapshot a user's pipeline reads. A record
states all four; a consumer that needs one must read that field.

### 8.2 SemVer rules for the software

Pre-1.0, the **minor** acts as the major: `0.2.x → 0.3.0` may break. Say so in
the README rather than pretending `0.x` is stable.

*Major (or, pre-1.0, minor) — breaking:*

- removing/renaming a Tier 0–7 name, a CLI subcommand, or a flag;
- changing the meaning of an exit code, or the `code` of a failure state;
- narrowing accepted input so a previously-valid call now fails;
- changing the default emitted `schema_version` of any record;
- removing a schema version from `SUPPORTED_SCHEMA_VERSIONS`;
- changing an `evidence_status` value for a fixed input;
- changing the *exact* value emitted for a fixed input — including when the old
  value was wrong. A mathematical correction is a breaking change **and** an
  erratum note, never a patch.

*Minor — additive:*

- new public name, new subcommand, new optional flag with an unchanged default;
- new **non-claim-bearing** optional field in a record (see §8.3);
- reading a new schema version that this build did not previously accept.

*Patch:*

- bug fixes with no change to any emitted field for any previously-succeeding
  input; message text; docs; performance; widening a `display` string is **not**
  patch-safe if any consumer could key on it — which is why §4 exists.

A change to `display` strings caused by a SymPy upgrade is not a package version
change at all, which is precisely why `exact` must be the identity. The `sympy`
dependency is therefore pinned as `sympy>=1.12` with a documented statement that
`display` and `decimal` may vary across SymPy versions while `exact` may not,
and AT-06 pins the canonical forms across the CI matrix.

### 8.3 Schema compatibility: strict by default

Each schema declares a read range. A build's `SUPPORTED_SCHEMA_VERSIONS` maps
name → the set of versions it can read; it writes exactly one version per
schema.

- Reading `schema_version` **below** the supported minimum: `IncompatibleSchema`.
  Do not "upgrade" old records silently — an upgrade is a claim about what the
  old record meant.
- Reading `schema_version` **above** the maximum: `IncompatibleSchema`. Never
  best-effort-parse a newer claim record.
- Reading an unknown **claim-bearing** key at any level: `IncompatibleSchema`.
  This is the deliberate opposite of the usual "ignore unknown fields" rule, and
  the reason is Adv-4: if version 2 adds `"retracted": true`, a lenient version-1
  reader would silently present a retracted result as valid. Fail closed.
- Unknown keys under the reserved `"ext"` object are ignored. `"ext"` may hold
  only non-claim-bearing data (timings, tool metadata, display hints), and a
  verifier must produce identical outcomes with `"ext"` removed. AT-12 tests
  that.

Additive record changes therefore cost a schema-version bump. That is the
intended price.

---

## 9. Determinism

`canonical_json(obj)` is the one serializer that carries guarantees:

1. `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
   allow_nan=False)`, encoded UTF-8, exactly one trailing `\n`.
2. No `float` may appear in `obj`; the encoder raises `InvalidInput` if one
   does. `allow_nan=False` is belt-and-braces.
3. Lists whose order is not semantic — `checks`, `assumptions`, `sources` — are
   emitted in a documented deterministic order: `checks` by `required_check_ids`
   order then id, `assumptions` and `sources` by id/kind then canonical bytes.
   Lists whose order *is* semantic, notably `coefficients`, keep their
   mathematical order and are never sorted.
4. No timestamps, no host names, no absolute paths, no PIDs, no random
   iteration order, no locale-dependent formatting anywhere in a canonical
   record. A wall-clock `duration_ms` (§6.1) is non-deterministic by nature and
   therefore lives under `"ext"`, not in the canonical record.
5. Same package version + same artifact versions + same input ⇒ identical
   canonical bytes on every supported CPython and SymPy in the CI matrix.
   AT-06 asserts this against stored golden bytes.

The human `--json` form has no byte guarantee and must not be hashed. Say that
in `--help`.

---

## 10. Hostile input and resource bounds

Existing bounds are kept and made discoverable rather than being scattered
constants: `MAX_TAYLOR_ORDER = 64`, `MAX_DECIMAL_PRECISION = 1000`,
`MAX_RATIONAL_CHARACTERS = 128`, 128-digit rational components,
`MAX_EXPRESSION_OPERATIONS = 10 000`. Added: `MAX_EXACT_NODES = 4096`,
`MAX_EXACT_DEPTH = 64`, `MAX_ARTIFACT_BYTES` for any file the package reads.

Rules:

- Every bound has a named public constant, a specific `resource_limit` message
  naming the bound and the observed value, and a test.
- Bounds are checked **before** the expensive operation, and during the walk for
  recursive structures.
- The rational grammar stays a regex over a bounded string, and decimal /
  exponent notation stays rejected, so no untrusted short string can construct a
  huge integer.
- The package opens only caller-named paths. It never downloads, never writes
  outside a caller-named output path, never creates a cache directory, never
  reads environment variables for data locations, and never executes a
  subprocess.
- Artifact reading order is: size check → hash check → parse → schema check →
  decode. Never decode first.

**Honest limitation.** These bounds cap *input size*, not *work*. A custom
`Generator` can satisfy `count_ops <= 10 000` and still make
`sp.series(..., order=64)` or `sp.simplify` run for an unbounded time — nested
transcendentals are the obvious construction. The package will not embed a
watchdog thread or a signal-based timeout: both are unreliable, platform-specific,
and cannot interrupt SymPy's C-level work.

The design's answer is a documented split rather than a false guarantee:

- **Built-in catalog generators**: bounded work, measured in CI, warned about if
  a case exceeds a budget.
- **Caller-supplied generators**: the caller owns the resource risk. Documented
  in the docstring, the README, and `docs/PROVENANCE.md`, in one sentence:
  *the package bounds the size of your expression, not the time SymPy takes to
  analyse it; run untrusted generators under your own timeout and memory limit.*

Claiming otherwise would be the kind of overpromise this document exists to
prevent.

---

## 11. The website is a display consumer

Data flows in exactly one direction:

```
released wheel/sdist  ─┐
                       ├─→  site build  ─→  static pages
released snapshot     ─┘
```

Binding rules:

1. The package has **no** knowledge of the site: no URL constant, no HTTP
   client, no `requests`/`httpx`/`urllib` call, no site-shaped JSON, no route
   names. `scripts/check_distribution.py` should grow an assertion that no
   networking module is imported by the package.
2. Every displayed value on the site must be traceable to a released artifact,
   and the page must show `package_version`, the relevant `artifact_versions`,
   `schema_version`, and the snapshot id used (already required by
   `docs/ROADMAP.md` Phase 6).
3. The site may not compute, round, re-derive, or "clean up" a value. If it
   needs a decimal, it renders the record's `decimal` field with its stated
   precision, or it renders `display`.
4. The site may not display an evidence status or literature status the record
   does not carry, and may not aggregate several records into a stronger claim.
   In particular it must not render the eight radius certificates alongside the
   702-row discovery atlas in a way that implies one status for both.
5. If the site needs something the artifacts do not contain, the fix is a new
   released artifact — never a site-side database read. A site that can answer a
   question the package cannot has become the source of truth, which is the
   failure mode this rule exists to prevent.
6. Reproduction instructions on any page must be executable with only the
   published wheel and the published snapshot.

---

## 12. Concrete examples

### 12.1 Python — Phase 1, unchanged call, richer record

```python
from geometric_function_atlas import (
    EvidenceStatus, canonical_digest, canonical_json, fekete_szego,
)

result = fekete_szego("exponential", mu=0)

# Exact value is a SymPy expression; equality is symbolic, never string-based.
assert result.value == sympy.Rational(3, 4)
assert result.evidence_status is EvidenceStatus.PROVEN_EXACT_UNDER_DECLARED_ASSUMPTIONS
assert result.literature.novelty_claim is False
assert result.provenance == "builtin_catalog"

record = result.to_dict()
assert record["schema"] == "gft.result" and record["schema_version"] == 1
assert canonical_digest(record).startswith("sha256:")
open("fs.json", "wb").write(canonical_json(record))
```

### 12.2 Python — exact serialization round trip, no `eval`

```python
from geometric_function_atlas import decode_exact, encode_exact, InvalidInput

node = encode_exact(result.value)
assert node == {"den": "4", "num": "3", "op": "rat"}
assert decode_exact(node) == result.value
assert encode_exact(decode_exact(node)) == node          # idempotent

try:
    decode_exact({"op": "eval", "args": [{"op": "int", "value": "1"}]})
except InvalidInput as exc:
    assert exc.code == "invalid_input"                    # never executed
```

### 12.3 Python — radius replay and fail-closed verification

```python
from geometric_function_atlas import (
    VerificationFailed, list_radius_pairs, radius_certificate, verify,
)

assert len(list_radius_pairs()) == 8                      # exactly the admitted chains

cert = radius_certificate(inner="exponential", target="lemniscate")
assert str(cert.radius) == "log(2)/2"
assert cert.evidence_status is EvidenceStatus.PROVEN_EXACT_UNDER_DECLARED_ASSUMPTIONS

report = verify(cert)
assert report.aggregate == "pass"
assert set(report.required_check_ids) <= {c.id for c in report.checks}
assert all(c.reason for c in report.checks if c.outcome in {"fail", "skip"})
```

```python
from geometric_function_atlas import UnsupportedOperation

# A pair that exists in the 702-row discovery atlas but is not an admitted chain.
try:
    radius_certificate(inner="bell", target="sigmoid")
except UnsupportedOperation as exc:
    assert exc.code == "unsupported_operation"            # not a silent None, not a guess
```

### 12.4 Python — the negative path is typed

```python
from geometric_function_atlas import AtlasError, InvalidInput, ResourceLimitExceeded

for call, expected in [
    (lambda: fekete_szego("missing", mu=0),          InvalidInput),
    (lambda: fekete_szego("sine", mu="1e1000"),      InvalidInput),
    (lambda: taylor_coefficients("sine", order=65),  ResourceLimitExceeded),
]:
    try:
        call()
    except AtlasError as exc:
        assert isinstance(exc, expected) and exc.code and exc.exit_code
```

### 12.5 JSON — a Fekete–Szegő record (human form)

```json
{
  "schema": "gft.result",
  "schema_version": 1,
  "record_kind": "fekete_szego",
  "package_version": "0.2.0rc1",
  "artifact_versions": {"generator_catalog": "2026.08.04"},
  "provenance": "builtin_catalog",
  "problem": {
    "kind": "fekete_szego",
    "generator": {"class": "exponential", "params": {}},
    "mu": {"op": "int", "value": "0"},
    "functional": "|a3 - mu*a2^2|"
  },
  "inputs": {
    "generator_formula": "exp(z)",
    "B1": {"exact": {"op": "int", "value": "1"}, "display": "1"},
    "B2": {"exact": {"den": "2", "num": "1", "op": "rat"}, "display": "1/2"}
  },
  "value": {
    "exact": {"den": "4", "num": "3", "op": "rat"},
    "display": "3/4",
    "decimal": {"value": "0.7500000000000000", "precision": 16, "rounding": "sympy.N"}
  },
  "method": "ma_minda_fekete_szego_closed_form",
  "evidence_status": "proven_exact_under_declared_assumptions",
  "assumptions": [
    {"id": "phi_normalized",     "statement": "phi(0) = 1", "scope": "generator",
     "verified": true,  "method": "exact_symbolic_identity"},
    {"id": "b1_positive_real",   "statement": "B1 is positive and real", "scope": "generator",
     "verified": true,  "method": "sympy_assumption_query"},
    {"id": "b2_real",            "statement": "B2 is real", "scope": "generator",
     "verified": true,  "method": "sympy_assumption_query"},
    {"id": "ma_minda_admissible","statement": "phi is an admissible Ma-Minda generator",
     "scope": "generator", "verified": false, "method": "declared"}
  ],
  "sources": [
    {"kind": "theorem", "citation": "W. C. Ma and D. Minda, A unified treatment of some special classes of univalent functions, Proc. Conf. Complex Analysis, Tianjin 1992, International Press (1994), 157-169.", "url": null},
    {"kind": "catalog", "citation": "Mendiratta, Nagpal & Ravichandran (2015)", "url": null}
  ],
  "literature": {"status": "not_reviewed", "novelty_claim": false, "reviewed_by": null}
}
```

### 12.6 JSON — a radius verification report that fails closed

```json
{
  "schema": "gft.verification_report",
  "schema_version": 1,
  "package_version": "0.2.0rc1",
  "artifact_versions": {"generator_catalog": "2026.08.04", "radius_classes": "2026.08.09"},
  "target": {
    "kind": "inclusion_radius",
    "inner":  {"class": "sine",     "params": {}},
    "target": {"class": "sigmoid",  "params": {}},
    "label":  "sine -> sigmoid"
  },
  "required_check_ids": ["candidate_exact", "boundary_touch", "global_max_on_axis", "attainment_witness"],
  "checks": [
    {"id": "candidate_exact", "description": "Replayed candidate equals the registered exact radius",
     "required": true, "outcome": "pass", "scope": "exact identity",
     "expected": {"display": "asin((-1 + E)/(1 + E))"},
     "observed": {"display": "asin((-1 + E)/(1 + E))"},
     "method": "canonical exact_expr equality", "reason": null},
    {"id": "boundary_touch", "description": "Boundary functional touches the target boundary at r",
     "required": true, "outcome": "pass", "scope": "|z| = r",
     "expected": {"display": "0"}, "observed": {"display": "0"},
     "method": "sympy.simplify difference to zero", "reason": null},
    {"id": "global_max_on_axis", "description": "Global maximum attained on the real axis",
     "required": true, "outcome": "pass", "scope": "0 < r <= asin((-1 + E)/(1 + E))",
     "expected": {"display": "0"}, "observed": {"display": "0"},
     "method": "verify_global_max_axis_symbolic", "reason": null},
    {"id": "attainment_witness", "description": "Normalized Ma-Minda extremal attains the bound",
     "required": true, "outcome": "skip", "scope": "witness construction",
     "expected": null, "observed": null, "method": "extremal_dilation",
     "reason": "witness artifact data/proofs/RADIUS_SINE_SIGMOID.md digest not recorded"}
  ],
  "counts": {"pass": 3, "fail": 0, "skip": 1, "total": 4},
  "aggregate": "fail",
  "evidence_status": "unresolved",
  "reason": "required check 'attainment_witness' was skipped; a skipped required check is a failure"
}
```

Three passing symbolic checks and a missing witness give `fail` and `unresolved`
— not `touch_proven_exact` promoted to sharp, and not a 75 % score.

### 12.7 CLI

```bash
$ geometric-function-atlas radius exponential lemniscate --canonical
{"artifact_versions":{...},"evidence_status":"proven_exact_under_declared_assumptions",...}
$ echo $?
0

$ geometric-function-atlas verify radius --pair sine:sigmoid --json
{ ...report above... }
$ echo $?
6

$ geometric-function-atlas radius bell sigmoid --json
{"schema":"gft.failure","schema_version":1,"code":"unsupported_operation",
 "message":"pair bell -> sigmoid is not one of the 8 admitted radius chains", ...}
$ echo $?
4

$ geometric-function-atlas coefficients sine --order 65
error: order must be at most 64 (resource_limit)
$ echo $?
9
```

---

## 13. What this design deliberately does not contain

Restating `docs/RELEASE_SCOPE.md` §6 as API constraints, because an exclusion
that is not expressible in the type system tends to reappear:

- **No `T_{3,1} = H_3(1)` correspondence.** The false identity is excluded, and
  so is any API shape that could imply it: there is no Toeplitz functional, no
  Hankel functional, no `H3`, and no generic "functional" enum member that a
  future contributor could point at both.
- **No 39-class sharp claims.** `list_generators()` returns nine entries and the
  radius registry eight pairs. There is no "all classes" iterator, no class
  count in any record, and no coverage percentage anywhere.
- **No novelty automation.** `LiteratureStatus` has no `NOVEL` member and
  `novelty_claim` has no setter.
- **No mutable database bundling.** No SQLite file in the wheel or sdist, no
  download helper, no ORM, no connection pool. `verify_snapshot` takes paths the
  caller already has and returns a `VerificationReport`.
- **No OCR, harvesting, deployment, or web UI.** No PDF handling, no OpenAlex or
  arXiv client, no Flask, no templates, no static assets, no CI deploy step in
  the package.
- **No `eval` path.** No `sympify` on user text, no `parse_expr`, no `pickle`,
  no `getattr`-by-name dispatch, no plugin entry points.

Each of these should be an executable assertion where it can be:
`check_distribution.py` already asserts no `.db`/`.sqlite`/`.env` in the
archives; extend it to assert no networking import, no `sympify`/`eval`/`exec`
token in the shipped package, and no `NOVEL`/`novelty_claim: true` literal.

---

## 14. Migration from the Phase 1 API

Guiding rule: **no exact mathematical value emitted by `0.1.0` may change.** All
54 fixture cases in `tests/fixtures/fekete_szego_research_artifact.json` must
produce identical `value_exact` strings throughout. Only the envelope, the
statuses, and the failure taxonomy move.

### Step 1 — additive, no behaviour change (patch-shaped)

- Add `encode_exact`, `decode_exact`, `canonical_json`, `canonical_digest`,
  `EvidenceStatus`, `LiteratureStatus`, `Assumption`, `SourceRef`, `Check`,
  `CheckOutcome`, `VerificationReport`, the `AtlasError` hierarchy, and `Failure`.
  Nothing consumes them yet.
- Add the `schema` CLI subcommand.
- Add `RESULT_SCHEMA_VERSION = 1` and friends.
- Tests: §15 AT-01…AT-06, AT-12.

### Step 2 — record envelope (breaking for exact-dict consumers; minor pre-1.0)

- `to_dict()` gains `schema`, `schema_version`, `record_kind`, `provenance`, and
  the structured `value`/`assumptions`/`sources`/`literature` shapes.
- `GeneratorSeriesResult.evidence_status` changes from `proven_exact_algebraic`
  to `proven_exact_under_declared_assumptions` with an explicit assumption list.
  This is F2 and it is a **breaking output change**; it is named in the release
  notes as an erratum, since the old value was undefined in
  `docs/PROVENANCE.md`.
- `evidence_status` becomes a derived, non-constructible `EvidenceStatus`.
  Records keep emitting the same lowercase strings in JSON, so JSON consumers
  see no change here.
- User-supplied generators start emitting `provenance: "user_supplied"` and the
  unverified `ma_minda_admissible` assumption.
- Update `tests/test_cli.py`, `test_coefficients.py`, `test_fekete_szego.py`
  expectations; keep `test_migration_crosscheck.py` assertions byte-identical —
  if that file needs editing, the migration is wrong.

### Step 3 — failure taxonomy and exit codes (breaking; minor pre-1.0)

- Raise `AtlasError` subclasses from the library. For one release only,
  `InvalidInput` also subclasses `LookupError` and `ValueError` so existing
  `except KeyError` / `except ValueError` callers keep working; the dual
  inheritance is documented as removed in the following minor.
- CLI maps `AtlasError.exit_code` to the §7 table. Exit `2` is reserved for
  argparse usage errors only.
- `tests/test_cli.py` currently asserts `returncode == 2` for an unknown
  generator and for over-limit order/precision; those become `3` and `9`. This
  is the most visible break and belongs in the release notes.
- Add `Failure` JSON emission on the failure path under `--json`.

### Step 4 — radius replay (additive; Tier 5)

- Introduce the radius class registry with its own `RADIUS_CLASSES_VERSION`,
  resolving F3 without touching `GENERATOR_CATALOG_VERSION`.
- Register exactly the eight chains from scope §3.3, each pinned to `cf0b2b0`
  and its proof artifact digest.
- Implement `radius_certificate`, `list_radius_pairs`,
  `verify_global_max_axis_symbolic`, and `verify`.
- Anchors required by scope §7.5: eight positives, at least one touch-only
  negative, one invalid-candidate mutation, one missing-check mutation.

### Step 5 — snapshot descriptors (additive; Tier 6, optional for the RC)

- `read_snapshot_descriptor(path)` parses a manifest; `verify_snapshot(...)`
  hashes assets the caller already has and returns a report. No download, ever.

### Step 6 — release hygiene

- Bump `version.py` and `CITATION.cff` together (they currently disagree with
  the RC label by design — the checkout is `0.1.0`).
- Extend `scripts/check_distribution.py` per §13.
- Run the existing `docs/RELEASING.md` gate unchanged; it is adequate.

**Not in the migration:** removing `taylor_coefficients`' bare-tuple return
(`docs/PROVENANCE.md` explicitly allows low-level helpers to return bare
values), renaming anything in Tier 0, or changing the `--mu` grammar. One
deprecation is proposed and deferred: `fekete_szego(mu=<float>)` currently
routes a float through `sp.Rational(str(value))`, so `mu=0.1` silently becomes
exactly `1/10` — an inexact input type on an exact path. Warn in `0.2`, remove
in `0.3`.

---

## 15. Minimal acceptance-test matrix

Twenty tests. Each is one property, each fails loudly, none requires network or
the database. Run with `-W error` per `docs/RELEASING.md`.

| ID | Area | Input | Expected | Exit |
| --- | --- | --- | --- | --- |
| AT-01 | exact encode | each of the 9 catalog generator expressions | `decode(encode(e))` equals `e` symbolically | — |
| AT-02 | exact encode | each of the 8 admitted radii | canonical bytes equal the stored golden bytes in §4.3 | — |
| AT-03 | exact decode | `{"op":"eval",...}`, `{"op":"var","name":"__import__"}`, `{"op":"rat","num":"2","den":"4"}`, `{"op":"rat","num":"1","den":"0"}` | `InvalidInput`; no `sympify`/`eval` reached | 3 |
| AT-04 | exact decode | 200-deep nesting; 4097-node tree; 200-digit integer | `ResourceLimitExceeded` naming the bound | 9 |
| AT-05 | exact encode | every AT-01/AT-02 value | `encode(decode(x)) == x` byte-for-byte | — |
| AT-06 | determinism | every Phase 1 + radius record | canonical bytes identical across CPython 3.10–3.13 and the SymPy floor/ceiling in CI | — |
| AT-07 | value stability | all 54 fixture cases | `value_exact` strings identical to `0.1.0` | 0 |
| AT-08 | envelope | every emitted record | `schema`, `schema_version`, `package_version`, `artifact_versions`, `literature.novelty_claim == false` present | — |
| AT-09 | status closure | every emitted `evidence_status` | member of the §5.3 enum; `proven_exact_algebraic` never emitted | — |
| AT-10 | claim safety | `fekete_szego(custom_generator, mu=0)` | `provenance == "user_supplied"` and an `ma_minda_admissible` assumption with `verified: false` | 0 |
| AT-11 | fail closed | report with empty `checks`; report missing one required id; report with a skipped required check | `aggregate == "fail"` in all three; `reason` non-empty | 6 |
| AT-12 | schema strict | record with an unknown top-level key; record with unknown key under `"ext"` | `IncompatibleSchema` for the first; identical verdict for the second | 8 / 0 |
| AT-13 | schema range | record with `schema_version: 0` and `schema_version: 99` | `IncompatibleSchema` both ways; no best-effort parse | 8 |
| AT-14 | radius positive | all 8 admitted pairs | exact radius matches scope §3.3; `aggregate == "pass"`; all required checks ran | 0 |
| AT-15 | radius negative | a touch-only chain | status stays `touch_proven_exact`; never `proven_exact_under_declared_assumptions` | 6 |
| AT-16 | radius mutation | perturbed candidate; deleted required check; wrong source commit | `verification_failed` / `unresolved_provenance`, never a pass | 6 / 5 |
| AT-17 | unsupported | `radius_certificate("bell", "sigmoid")`; a `sharp_radius` import | `UnsupportedOperation`; `ImportError` | 4 |
| AT-18 | exit codes | one CLI invocation per §7 row plus a usage error | each exit code exactly as tabulated; `--json` emits a `gft.failure` on stdout | 0–9 |
| AT-19 | distribution | built wheel and sdist | no `.db`/`.sqlite`/`.env`; no networking import; no `eval`/`exec`/`sympify` token in shipped package; `py.typed` present | 0 |
| AT-20 | encoding | `generators --json` and `--canonical` piped to a non-UTF-8 consumer | no `UnicodeEncodeError`; `--canonical` output is pure ASCII | 0 |

AT-07, AT-11, AT-14, and AT-19 are the four that must never be marked
`xfail`. If any of them is inconvenient, the design is wrong, not the test.

---

## 16. Overdesign to avoid

This is a small research package. Every item below is a plausible next step that
should be refused, with the reason it is refused.

| Tempting | Refuse because |
| --- | --- |
| A plugin/entry-point registry for generators or chains | It is a code-execution surface for an untrusted package, and the admitted inventory is nine generators and eight chains — a literal tuple is better. |
| A general certificate "engine" with pluggable check backends | There are four required checks. An abstract base class per check is more code than the checks. |
| A DSL or grammar for expressions | §4's opcode set is a DSL with 22 opcodes and no parser. That is the correct amount of DSL. |
| An interval-arithmetic / enclosure framework | `CERTIFIED_ENCLOSURE` is a status this RC never emits. Build it when Phase 3 needs it, not before. |
| JSON Schema files plus generated validators | Four record shapes. Hand-written validators are shorter, give better errors, and cannot drift from the code. Publish JSON Schema as *documentation* if reviewers ask, generated from the code. |
| A config file, config object, or `GFT_*` environment variables | Configuration is a hidden input to a reproducibility claim. Every knob must be an explicit argument. |
| A logging framework, log levels, structured logging | The record *is* the log. `--json` covers machine consumers. |
| Caching, memoization, or a results database | A cache is a stale-value generator and an integrity surface. SymPy is fast enough for order ≤ 64. |
| Resumable/checkpointed verification | Nothing in this RC takes long enough. Phase 3 may need it; it can have it then. |
| `async`, threading, multiprocessing, progress bars | Eight chains. |
| An HTTP client for snapshots ("just a convenience downloader") | Axiom A7. The moment the package can fetch, the site can become the source of truth. |
| A distinct exception class per error message | Seven states, seven classes. Message text is data, not type. |
| `__eq__` / `__hash__` on results delegating to the digest | Two records with equal digests are equal *as serializations*. Silently making them equal *as results* invites a digest match to be read as a correctness proof. Keep digest comparison explicit. |
| Rich/colour terminal output, tables, TUI | `--json` plus plain lines. |
| A `--strict` flag pair for every fail-closed rule | Fail-closed is the only mode. A `--lenient` flag is a request to be misled. |
| Bundling the 702-row discovery atlas "for context" | Scope §3.3. Shipping it next to eight certificates is how a discovery row becomes a theorem in a reader's mind. |
| Backporting compatibility shims for the `0.1.0` dict shape | Pre-1.0. One clean break, documented, beats a permanent dual-format reader. |
| A `metrics`/telemetry hook | No. |

Rough size target: the additions above are roughly 900–1300 lines of
implementation and 700–1000 lines of tests. If the implementation exceeds
~2000 lines, something in this table was built anyway.

---

## 17. Open decisions for the maintainer

Five things this design cannot decide alone. Each is small, and each changes the
implementation if answered the other way.

1. **Does `0.2.0rc1` ship Tier 5 (radius)?** If the eight chains are not ready,
   shipping Tiers 0–4 + 7 as the RC is still a meaningful improvement, and this
   design is written to allow it. Recommendation: split.
2. **The `RADIUS_CLASSES_VERSION` date and the exact `starlike_order` parameter
   spelling.** F3 requires a decision; `2026.08.09` and `alpha` as an exact
   rational are placeholders.
3. **Retiring `proven_exact_algebraic`** is an erratum on published output.
   Confirm this is acceptable rather than defining the status in
   `docs/PROVENANCE.md` instead. Recommendation: retire it; a status the policy
   document does not define is worse than a breaking change.
4. **Deprecating float `mu`.** Recommendation: warn in `0.2`, remove in `0.3`.
5. **Whether `verify snapshot` belongs in the RC at all**, given that the
   registry snapshot is an external data-release contract (scope §1). It can be
   a separate tool. Recommendation: defer.

---

## 18. Relationship to the governing documents

- `docs/RELEASE_SCOPE.md` — this design implements §3 (public inventory), §4
  (trust and evidence contract), and §2 (version and schema matrix). It adds no
  operation outside §3 and touches no exclusion in §6.
- `docs/PROVENANCE.md` — §5.3 makes the five evidence statuses a closed enum and
  removes the one undefined status the package currently emits. Its statement
  that low-level helpers may return bare SymPy values is preserved.
- `docs/ROADMAP.md` — the type names here (`Generator`, `RadiusProblem`,
  `EvidenceState`, `Certificate`, `LiteratureVerdict`) are the same model the
  roadmap converges on, spelled `Generator`, the `problem` envelope,
  `EvidenceStatus`, `RadiusResult`, and `LiteratureStatus`. Phases 3–5 fit as
  additive record kinds and schema-version bumps.
- `docs/RELEASING.md` — unchanged. The gate is adequate; §13 only adds
  assertions to `scripts/check_distribution.py`.

This document authorizes nothing. It does not bump a version, implement a
chain, tag a release, or move the RC past
`RC scope approved; implementation and independent verification pending`.
