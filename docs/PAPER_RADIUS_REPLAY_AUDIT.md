# Paper-radius replay audit (v0.5.0 snapshot unchanged)

**Update:** all eleven lanes below now replay as `proven` (`certified: true`,
`bounded_chain_replayed`), following the paper proofs step by step. Identities,
branch normalisation, thresholds, domain margins and contacts are checked;
Lemma 4.1, Lemma 4.2 and Lemma 3.1 are recorded as cited steps (as the eight
fixture lanes record their majorant premises). The Theorem 4.8 lanes re-run
`analysis/thm48_interval_check.py` (resultant, cusp, exact endpoint, radius
enclosure, 2,000 bulk boxes and 50 endpoint boxes at `iv.dps=30`); the Jordan
domain step is cited. The text below records the earlier deferral.

Input: handoff §4; paper `atlas_em_rewrite.tex`, Theorems 4.4–4.8 and Lemmas 4.1–4.2 (local submission is **read-only**). The 702-row v0.5.0 radius snapshot and historical eight-lane fixture are intentionally unchanged. Nineteen rows retain their written-paper-theorem labels. A successful symbolic replay checks finite identities against the *unaltered* snapshot row and its stored decimal; it does not alter the row's status, value, certificate, artifact identity or literature verdict. The decimal comparison guards identity, **not** containment.

## Completed analytic lanes

- `crescent -> exponential` (paper Thm 4.4(a)): `sin(1)`. For |u|<1, on branches fixed at 0, `log(u+sqrt(1+u²))=asinh(u)`. The binomial series for its derivative has alternating even coefficients `(-1)^n binomial(2n,n)/4^n`; integration gives odd coefficients of absolute value `binomial(2n,n)/(4^n(2n+1))`. The absolute-coefficient sum is `asin(r)`. At `u=ir` all terms align, giving `asinh(ir)=i asin(r)`. At `r=sin(1)<1`, `asin(r)=1` and `u+sqrt(1+u²)=cos(1)+i sin(1)=exp(i)` at contact. The principal log is analytic on this disk: `u+sqrt(1+u²)=exp(asinh(u))`, and `|Im asinh(u)|<=asin(r)<=1<pi`, so its log branch does not cross the cut.
- `exponential -> crescent` (paper Thm 4.4(b)): `asinh(1)=log(1+sqrt(2))`. The crescent inverse `(w²-1)/(2w)` at `w=exp(u)` is `sinh(u)`. Its odd coefficients are positive, so `|sinh(u)|<=sinh(r)` with equality at `u=r`; `sinh(asinh(1))=1`. The right-hand branch is fixed because `Re cosh(u)>0` for `|Im u|<=r<pi/2`. At contact `exp(r)=1+sqrt(2)` is the crescent tip.

Both use the standard Ma–Minda Schwarz witness and dilation for sharpness (paper's sharpness lemma). Replay checks symbolic identities, candidate and historical decimal, while binomial positivity, branch inequality, maximum principle and extremal arguments are **written analytic deductions**, not mechanically checked global proofs. Accordingly `method=paper_symbolic_radius_replay`, `status=symbolic_replay_only`, `global_containment_check=not_mechanized`, and `certified=false` distinguish these from the eight historical certificate lanes. The snapshot's written-proof evidence is separate from computational replay.

## Deferred (9 of 11; no new replay claim)

| Direction | Paper route | What a sound local replay still needs |
|---|---|---|
| sine -> rational_kr | Thm 4.8(a), interval | Reproduce the elimination polynomial, certified outward-rounded interval bounds on 2,000 angular boxes through `pi-1/20`, and a positive second-derivative bound on the endpoint interval. No floating grid or paper-stated lower bound alone is a certificate. |
| sigmoid -> rational_kr | Thm 4.8(b), interval | Same with 2,000 angular boxes through `pi-1/100` and endpoint second-derivative bound; independently verify polynomial/branch orientation. |
| cosh_sqrt -> lemniscate | Thm 4.5(a), positive series | Replay entire nonnegative Taylor-series majorant for `sinh²(sqrt(u))`, inverse branch, and equality at the positive radius. |
| exponential -> sine | Thm 4.5(b), positive composition | Establish principal `asin` branch and positive-series composition on the full certified disk; check threshold and contact. |
| rational_kr -> sine | Thm 4.5(c), positive composition | Check rational generator normalization and pole exclusion, positive series and exact quadratic root/branch. |
| bell -> sine | Thm 4.5(d), positive composition | Check Bell formula and both nested positive-series compositions, branch/radius and contact. |
| exponential -> bell | Thm 4.5(e), alternating log | Bound `log(1+u)` by `-log(1-r)` via absolute coefficients; check Bell inverse and negative-axis contact. |
| sine -> exponential | Thm 4.6(b), sine-ray lemma | Replay `log(1+sin(u))` ray bound (the paper's half-angle proof), branch and negative-axis equality. |
| sine -> bell | Thm 4.6(c), nested sine-ray | Replay preceding sine-ray inequality and nested `log(1+v)` absolute-series bound with strict interior branch condition. |

These seven analytic routes are plausible from the written paper, **not yet package-replayable**, and stay `unsupported`. In particular, the two interval rows have no executable directed-rounding witness in this branch. Do not label any deferred row `certified` by numerical agreement, nor move its historical evidence status until a separately reviewed versioned data snapshot is prepared. The existing snapshot's `crescent -> exponential` value is `paper_proved_exact` under a written theorem, but its computational status remains `unresolved`.

## Handoff §7(B): 12 quarantined touch checks (separate diagnostic)

A red-first regression (`tests/test_quarantined_radius_touch.py`) checks **all 12** `audit_required` rows with exact rational target inverses and catalog generators. It yields `touch_equation_only` for every row, while replay remains `not_replayable`. Ten target `janowski_A0.75_B-0.25`; two are `cardioid -> janowski_A1_B0` and `cardioid -> order_0.75`. The inverse of the first target is `4(w-1)/(3+w)` (pole at -3, not on the target's real image); the other inverses are `w-1` and `(w-1)/(w-1/2)` (the latter pole lies left of the target half-plane). The exact contacts give inverse `+1` in eleven cases and `-1` for cardioid -> order_0.75. The exact candidate equations simplify to zero for every case, including both strongly-starlike sources; this rules out a branch mismatch **at these real contacts only**, not off the real axis.

The legacy research checker `gft/radius.py:533–558` tests `|psi|²-1` numerically to `1e-70` *before* exact simplification. Its `_janowski(0.75,-0.25)`, `_janowski(1.0,0.0)`, and `_ord(0.75)` (lines 81–86, 123–132) insert binary floats into symbolic expressions. Reproducing those formulas at three contacts gives nonzero residuals of roughly `-4.44e-16`, `-1.11e-16`, and `-5.92e-16`, respectively; eighty-digit evaluation cannot restore precision lost to binary constants. **Likely cause of the 12 `FAILED` labels: checker precision bug, not evidence that a radius theorem fails.** The package-side diagnostic does not edit registry code or snapshot data. Whole-disk inclusion and sharpness still need independent global arguments before any `audit_required` row can be promoted. Fixing the research checker and regenerating/versioning its dataset belongs to the separate data/status workstream.

Handoff §7(C) grid expansion is an owner decision; §7(D)–(F) are another package workstream and intentionally untouched here.
