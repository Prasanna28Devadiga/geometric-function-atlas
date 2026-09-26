# Radius grid scope and canonical counts (review candidate)

The `2026.09.27-paper-review` radius snapshot remains **702 raw public-key rows** (28 source keys × 26 target keys, excluding the 26 self-directions). This is **not the full catalog** of 39 public class keys / 38 distinct generator expressions. Both `janowski_A0_B-1` and `order_0.5` remain valid public identifiers, and the released **0.4.0 immutable snapshot is not rewritten**. The analysis sidecar `src/geometric_function_atlas/data/radius_scope_2026_09_27.json` maps `janowski_A0_B-1 → order_0.5` solely for counts, prefers the `order_0.5` public row when paper-review statuses differ, and discards the two alias-identity diagonal rows. The remaining 50 duplicate rows collapse to 650 canonical off-diagonal questions. Rebuild/check with `python scripts/build_radius_scope.py [--check]`; the sidecar records the exact source-snapshot SHA-256 and rules.

Never source (11 catalog keys): `bean_tanh`, `booth_0.3`, `booth_0.7`, `cardioid_exp`, `cissoid_diocles`, `epicycloid_3`, `epicycloid_6`, `four_leaf`, `nonconvex_sec`, `petal_arcsinh`, `strip_arctan`.

Never target **among the 28 source keys** (2): `nephroid`, `three_leaf`. All 11 never-source keys are also absent as targets; “two never-target” is relative to the source set, not the entire 39-key catalog. The unrestricted 28-key non-self universe has 756 directions; 54 incoming directions to these two keys are missing, not zero radii. The populated 28×26 key rectangle has 702 directions.

| Population | Eligible | Reciprocal unequal / total | Shared non-unit / total (groups) |
| --- | ---: | ---: | ---: |
| Published 0.4.0 snapshot, canonicalized (historical baseline) | 556 | 233 / 239 | 146 / 423 (41) |
| `2026.09.27-paper-review` snapshot, canonicalized (this review) | 557 | 234 / 240 | 148 / 424 (42) |

Eligible means canonical off-diagonal rows whose status is neither `unidentified` nor `audit_required`. Reciprocal counts require both directions eligible and compare stored `value_str`. Shared values group eligible radii strictly below `1−1e−10` by `value_str`. The one newly paper-proved formerly unidentified row changes these counts; **do not quote the 0.4.0 baseline as regenerated results**. These are computational classifications, not new containment proofs.

New canonical status buckets: `audit_required` 11, `closed_form_confirmed` 132, `paper_proved_exact` 19, `touch_proven_exact` 273, `trivial_containment` 133, `unidentified` 82 (sum 650). Excluding trivial and quarantined rows, the contact/status table is:

| Contact | Closed form confirmed | Paper proved | Touch proven exact | Unidentified | Total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Real axis | 76 | 18 | 273 | 6 | 373 |
| Off axis | 56 | 1 | 0 | 76 | 133 |

This table classifies stored `mode` and `status`; it does not recalculate the manuscript's Taylor-coefficient single-sign/mixed-sign diagnostic. Twelve raw audit-required rows remain quarantined; 11 after canonicalization. No failed check has been silently repaired.

**TODO — following release, not this one:** expand to all 38 distinct generator classes, giving **38 × 37 = 1,406** directed non-self questions. This requires new radius calculations and review, not relabeling absent cells. No manuscript edits, merge, deployment, or release follow from this review candidate without owner approval.
