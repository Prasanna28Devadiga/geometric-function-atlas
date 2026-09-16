# Thirty bounded research recipes

This catalogue is the fixed EX01–EX30 denominator from the reviewer packet. It is not a feature wish list disguised as completed science. Each entry gives a route that works now or an explicit bounded ABSTAIN naming the missing proof/search engine. Exact identities, numerical screens, snapshot lookups, and literature claims remain separate. **No novelty claim** is made by any entry.

## EX01 — Compare sine, exponential, and cardioid generators

**Disposition:** implemented recipe using exact generator series.

**Replay:** call `generator_series(key, order=6)` for `sine`, `exponential`, and `cardioid`, compare `exact_expressions`, then plot `object="phi"` if geometry is needed.

This compares $\phi$ itself, not $z\phi$ or a canonical member. Coefficients stay exact; a sampled plot is explanatory only.

## EX02 — Recover the classical starlike Fekete–Szegő constant

**Disposition:** implemented exact theorem anchor.

**Replay:** run `fekete_szego("starlike", mu="0")` and verify that the exact value is `3`; rerun at `mu="1"` to obtain `1` and inspect the declared Ma–Minda assumptions.

The value is a known theorem specialization, not a new bound.

## EX03 — Vary $\mu$ in Fekete–Szegő

**Disposition:** implemented workflow with exact branch transitions and equality examples.

**Replay:** `python examples/research_workflows/coefficient_comparison.py --generator starlike --output /tmp/gfa-ex03`.

The JSON distinguishes the two extremal Schwarz functions and labels transition non-uniqueness.

## EX04 — Vary starlikeness order $\alpha$

**Disposition:** implemented bounded exact-specialization workflow.

**Replay:** run `custom_class.py` repeatedly with exact rational `--alpha` values such as `0`, `1/4`, and `1/2`; compare the exact JSON records and generator identities.

A finite rational sweep does not prove a statement uniformly over $0\leq\alpha<1$.

## EX05 — Vary Janowski parameters $A,B$

**Disposition:** bounded exact recipe; symbolic parameter regions remain unsupported.

**Replay:** adapt `build_generator()` in `custom_class.py` to the exact specialization $(1+Az)/(1+Bz)$, require exact rational $-1\leq B<A\leq1$, and run a declared finite grid.

Each $(A,B)$ pair is a separate exact object. The recipe does not infer branch formulas over a continuum.

## EX06 — Locate Fekete–Szegő branch changes

**Disposition:** implemented exact derivation.

**Replay:** inspect `transition_mu` and the independent attaining values emitted by `coefficient_comparison.py`; its test checks the displayed extremal against the public theorem result.

The plotted curve samples an exact piecewise formula; the derivation, not the polyline, establishes the transitions.

## EX07 — Compute canonical extremal coefficients

**Disposition:** implemented exact API for built-in and caller-defined generators.

**Replay:** call `class_extremal_coefficients(generator, order=8)` and independently check $zf'_{\phi}/f_{\phi}=\phi$ when a closed form is known.

Algebraic and transcendental catalogue coefficients are kept symbolic rather than forced through `Rational`.

## EX08 — Compare $\phi$, $z\phi$, and $f_\phi$

**Disposition:** implemented workflow with distinct plot semantics.

**Replay:** run `custom_class.py` or call `write_domain_plot(..., object=name)` for each of `phi`, `z*phi`, and `f_phi`.

Metadata records the selected mathematical object and finite-Taylor approximation. The three images are not interchangeable.

## EX09 — Compare pictures across Taylor order

**Disposition:** implemented changed-input recipe.

**Replay:** run `class_geometry.py` at `--order 6` and `--order 12` with the same generator and radius; compare `sampled_truncation_errors_by_degree` and the SVGs.

Those errors are maxima over the declared sampled outer ring, not uniform analytic tail bounds.

## EX10 — Prove a polynomial starlike by a sufficient condition

**Disposition:** implemented exact sufficient-condition route.

**Replay:** call `verify_function([0.1], property="starlike", max_cost="symbolic")` for $f(z)=z+0.1z^2$ and require `outcome == "proven"`.

For a finite polynomial, the exact C01 coefficient sum is a proof under the documented criterion.

## EX11 — Explain a failed function screen

**Disposition:** implemented counterexample workflow.

**Replay:** run `conjecture_counterexample.py` and inspect the exact parameter interval, candidate witness, interval replay, and repaired claim.

A sampled failure is promoted only when the witness is independently enclosed.

## EX12 — Independently replay a witness

**Disposition:** implemented public verifier recipe.

**Replay:** call `verify_counterexample([1.0], point=(-0.75, 0.0), property="starlike")` for $f(z)=z+z^2$ and require `certified is True`.

The point and coefficient list form a portable witness; the verifier recomputes the interval rather than trusting a stored boolean.

## EX13 — Compare membership across classes

**Disposition:** implemented numerical-screen table recipe.

**Replay:** apply `class_member_screen` to the same finite coefficient list for each named class, record `member`, margin, grid, and witness, and keep `class_containment_screen` as a separate generator-image question.

A pass is sampled evidence only.

## EX14 — Show a sufficient condition can be inconclusive

**Disposition:** implemented negative-control recipe.

**Replay:** call `verify_function(closed_form=z/(1-z)**2, property="starlike", max_cost="symbolic")` and require `outcome == "c01_fails_sufficient_condition"`.

The Koebe function is starlike by the classical theorem, while this coefficient sufficient condition fails. That outcome is **not a counterexample** to starlikeness; it is an ABSTAIN by the selected proof route.

## EX15 — Screen exponential contained in cardioid

**Disposition:** implemented numerical containment-screen recipe.

**Replay:** call `class_containment_screen("exponential", "cardioid")`, retain its sampling parameters and minimum margin, and reverse the arguments as a separate run.

A numerical screen is not a containment theorem; a positive theorem still needs analytic boundary or subordination proof.

## EX16 — Compare $A\to B$ and $B\to A$ radii

**Disposition:** implemented directed snapshot recipe.

**Replay:** use `radius(A, B)` and `radius(B, A)` separately or inspect the two cells in `radius_atlas.json`; direction is never inferred from the reverse row.

The sine/sigmoid anchor visibly has different exact values and statuses in the two directions.

## EX17 — Annotate the sine-to-sigmoid certificate

**Disposition:** implemented certificate-replay recipe.

**Replay:** obtain `radius("sine", "sigmoid")`, run `verify_radius_certificate("sine", "sigmoid")`, and inspect branch, containment, contact, and sharpness checks rather than only the exact string.

The result is locally replayable and source-bound; replay alone does not decide novelty.

## EX18 — Filter radius records needing investigation

**Disposition:** implemented evidence-filter recipe.

**Replay:** call `list_radii(status="audit_required")` and separately `list_radii(status="unidentified")`; preserve source, target, status, and exact/decimal fields in any shortlist.

Do not combine `audit_required` and `unidentified` into one proof status.

## EX19 — Render the radius atlas matrix

**Disposition:** implemented deterministic JSON+SVG workflow.

**Replay:** `python examples/research_workflows/radius_atlas.py --output /tmp/gfa-ex19`.

The export covers all 784 cells over 28 classes, marks 54 missing non-diagonal rows, and reports that only eight stored records have bundled replay certificates.

## EX20 — Estimate a radius for a new pair

**Disposition:** implemented for a declared bounded family, not arbitrary pairs.

**Replay:** run `sharp_radius.py --source off_axis --s 1/4 --output /tmp/gfa-ex20` and inspect the imaginary-axis contact and the real-axis-shortcut counterexample.

The workflow does not claim to solve arbitrary source/target formulas; new pairs require a frozen inverse branch and contact grammar.

## EX21 — Compose radii through an intermediate class

**Disposition:** bounded ABSTAIN pending a theorem-level composition contract.

**Replay:** compare the two directed input records manually and record their assumptions; do not multiply them as a sharp radius.

Dilation can suggest a product lower bound under compatible normalizations, but the package does not yet encode the direction, hypotheses, provenance propagation, or sharpness-loss semantics. It therefore does not return a composed radius.

## EX22 — Construct members from Schwarz functions

**Disposition:** bounded exact internal workflow, with public promotion deferred.

**Replay:** use the maintained `member_coefficients` anchors in `tests/test_schur.py` and the source-bound literature workflow; fixed real rational Schur parameters reconstruct exact finite Taylor jets.

The current helper does not accept general complex Schur parameters and is not advertised as a complete public member parametrization.

## EX23 — Optimize $H_2(2)$

**Disposition:** bounded ABSTAIN for global optimization; exact point evaluation exists.

**Replay:** `functional_value("hankel2_2", coefficients)` evaluates $|a_2a_4-a_3^2|$ exactly at a supplied jet, but do not label a parameter sample maximum as sharp.

The package does not implement the required complex-Schur search denominator or exact global upper-bound certificate.

## EX24 — Compare inverse and logarithmic coefficients

**Disposition:** implemented fixed-jet comparison; class-wide optimization remains unsupported.

**Replay:** evaluate `functional_value("inv_a3", coefficients)` and `functional_value("log_gamma2", coefficients)` on the same exact member coefficients in the maintained Schur tests.

This compares two exact functionals at specified members; it does not maximize either over a class.

## EX25 — Investigate $H_3(1)$

**Disposition:** bounded ABSTAIN for a missing higher-order engine.

**Replay:** verify that unsupported key `hankel3_1` fails closed, then retain the proposed functional and coefficient order in the negative ledger.

The current bounded grammar stops below the necessary order and does not provide complex-Schur search, checkpoints, or a global upper-bound certificate.

## EX26 — Disprove a custom coefficient inequality

**Disposition:** bounded ABSTAIN for arbitrary functionals; one maintained polynomial-family repair exists.

**Replay:** use `conjecture_counterexample.py` for its declared coefficient family and certified witness, but reject arbitrary expression strings.

The package does not parse caller-supplied functional code or search an undeclared parameter space. A general route depends on the same safe grammar and certificate engine as EX23/EX25.

## EX27 — Locate special-function loss of starlikeness

**Disposition:** bounded ABSTAIN for a missing parameter-family boundary engine.

**Replay:** use `verify_function` only at explicitly supplied specializations and record screens or certified point violations; do not infer the first loss parameter from a finite grid.

The package does not provide rigorous continuation over a family parameter, singularity tracking, or a certified boundary root with branch exclusions.

## EX28 — Test an integral transform

**Disposition:** implemented exact Alexander-transform workflow.

**Replay:** run `alexander_transform.py` for `starlike` and `sine`; verify the coefficient transfer and the exact identity connecting starlike and convex forms.

Plots remain sampled explanations of an exact operator identity.

## EX29 — Reproduce a published table

**Disposition:** implemented source-version-specific coefficient audit.

**Replay:** run `literature_coefficient_audit.py`, compare the emitted exact coefficients with the cited equation/table locator, and retain the source version in the record.

A discrepancy is tied to the inspected version; correction priority and novelty require separate source reconciliation.

## EX30 — Bundle an experiment for a collaborator

**Disposition:** implemented deterministic checksum-manifest workflow.

**Replay:** run `custom_class.py`, then call `verify_research_bundle_manifest` on its `research_bundle_manifest.json`; rerun in a fresh directory and compare manifest bytes.

Bundle verification checks file identity and closed schema only. It does not execute the entrypoint, certify the mathematics inside the files, or establish novelty.
