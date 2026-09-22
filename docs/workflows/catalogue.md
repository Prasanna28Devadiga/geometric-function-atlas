# Thirty things to try

Choose an idea, follow the starting point, and open the linked workflow when you
want the full derivation.

## Ready to try

**Ready** means the current package can run the stated calculation. The entry
also says whether the result is exact or based on sampled points.

## Not yet supported

**Not yet supported** means the package has no complete search or proof method
for that question. There is no hidden command for it yet.

## All thirty ideas

**EX01 — Compare three generators**

`generator_series(key, order=6)` for `sine`, `exponential`, and `cardioid`. **Ready.** The coefficients are exact.

**EX02 — Recover a classical constant**

Run `fekete_szego("starlike", mu="0")`. **Ready.** The answer is $3$.

**EX03 — Vary $\mu$ in the Fekete–Szegő problem**

Start with [Compare coefficient bounds](coefficient_comparison.md). **Ready.** The transition points and equality examples are exact.

**EX04 — Vary the starlikeness order $\alpha$**

Run [Explore your own class](custom_class.md) with `--alpha 0`, `1/4`, and `1/2`. **Ready** for exact chosen values.

**EX05 — Vary Janowski parameters $A,B$**

Adapt `build_generator()` to $(1+Az)/(1+Bz)$. **Ready** for chosen rational pairs, not a symbolic parameter region.

**EX06 — Locate Fekete–Szegő branch changes**

Read `transition_mu` from the coefficient workflow. **Ready.** The derivation explains the corners.

**EX07 — Compute canonical-member coefficients**

Call `class_extremal_coefficients(generator, order=8)`. **Ready.** Coefficients remain symbolic.

**EX08 — Compare $\phi$, $z\phi$, and $f_\phi$**

Run [Explore your own class](custom_class.md). **Ready.** The three plots represent different functions.

**EX09 — Compare two Taylor orders**

Run [See class geometry](class_geometry.md) with `--order 6` and `12`. **Ready.** The reported errors are sampled.

**EX10 — Prove a polynomial starlike**

Call `verify_function([0.1], property="starlike", max_cost="symbolic")`. **Ready** for the stated sufficient criterion.

**EX11 — Explain why a candidate function fails**

Run [Test a conjecture](conjecture_counterexample.md). **Ready.** It returns an exact witness when one is found.

**EX12 — Recheck a fixed counterexample**

Call `verify_counterexample([1.0], point=(-0.75, 0.0), property="starlike")`. **Ready.** Interval arithmetic checks the witness.

**EX13 — Compare one polynomial with several classes**

Call `class_member_screen(...)`. **Ready** as a numerical screen.

**EX14 — See why a sufficient test can be inconclusive**

Test the Koebe dilation with `verify_function`. **Ready.** Failing this test does not disprove starlikeness.

**EX15 — Compare exponential and cardioid domains**

Call `class_containment_screen("exponential", "cardioid")`. **Ready** as a screen; sampled points cannot prove containment.

**EX16 — Compare $A\to B$ and $B\to A$**

Call `radius(A, B)` and `radius(B, A)`. **Ready.** The source and target cannot be swapped.

**EX17 — Recheck the sine-to-sigmoid radius**

Call `verify_radius_certificate("sine", "sigmoid")`. **Ready.** It checks all stored proof steps.

**EX18 — List radius records that need work**

Call `list_radii(status="audit_required")`. **Ready.** Keep `audit_required` and `unidentified` separate.

**EX19 — Draw the complete radius map**

Run [Read the radius map](radius_atlas.md). **Ready.** It shows 702 rows; eight have a local certificate.

**EX20 — Solve an off-axis radius example**

Run [Find a sharp radius](sharp_radius.md) with `--source off_axis`. **Ready** for this family.

**EX21 — Compose radii through an intermediate class**

Compare the two input records by hand. **Not yet supported.** A product of two radii need not be sharp.

**EX22 — Construct members from Schwarz parameters**

See `tests/test_schur.py`. **Ready** for fixed real rational parameters; there is no general complex interface.

**EX23 — Maximize $H_2(2)$ over a class**

`functional_value("hankel2_2", coefficients)` evaluates one member. **Not yet supported.** The package cannot prove a global maximum.

**EX24 — Compare inverse and logarithmic coefficients**

Evaluate `inv_a3` and `log_gamma2` on the same coefficients. **Ready** for a chosen member, not a class-wide maximum.

**EX25 — Investigate $H_3(1)$**

Record the functional and required coefficient order. **Not yet supported.** The higher-order search engine is missing.

**EX26 — Test an arbitrary coefficient inequality**

Use the maintained polynomial example as a model. **Not yet supported.** Caller-supplied functional formulas are not accepted.

**EX27 — Find where a family loses starlikeness**

Test explicitly chosen parameter values. **Not yet supported.** The package cannot certify the first loss parameter over a continuum.

**EX28 — Apply the Alexander transform**

Run [Use the Alexander transform](alexander_transform.md). **Ready.** The coefficient transfer and differential identity are exact.

**EX29 — Check a coefficient table from a paper**

Run [Work from a paper](recent_literature.md). **Ready** for the cited source and version.

**EX30 — Send an experiment to a collaborator**

Run [Share a reproducible result](collaborator_bundle.md). **Ready.** Checksums detect changed files.