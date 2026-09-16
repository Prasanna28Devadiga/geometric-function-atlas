# Investigate an exact class of your own

**Problem.** Given an exact analytic generator that is not in the built-in catalogue, how can we inspect its admissibility, compute sharp low-order data, construct its canonical member, compare its class with a known class, and export auditable plots without pretending that numerical screens are proofs?

The maintained template uses the starlike-of-order-$\alpha$ family

$$
\phi_\alpha(z)=\frac{1+(1-2\alpha)z}{1-z},\qquad 0\leq\alpha<1,
$$

specialized at an exact rational value. Run the anchor case:

```sh
python examples/research_workflows/custom_class.py \
  --alpha 1/4 \
  --order 4 \
  --output /tmp/gfa-custom-class
```

The output directory contains `custom_class.json`, three SVGs for $\phi$, $z\phi$, and the canonical extremal $f_\phi$, and a deterministic `research_bundle_manifest.json` covering those four research artifacts. These are deliberately distinct mathematical objects. See [Reproduce a result and prepare a collaborator bundle](collaborator_bundle.md) for independent checksum verification and its evidence boundary.

## Exact construction

For $\alpha=1/4$,

$$
\phi(z)=\frac{1+z/2}{1-z}
      =1+\frac32z+\frac32z^2+\cdots.
$$

The exact canonical member solving

$$
\frac{z f_\phi'(z)}{f_\phi(z)}=\phi(z),
\qquad f_\phi(0)=0,\quad f_\phi'(0)=1,
$$

is

$$
f_\phi(z)=\frac{z}{(1-z)^{3/2}}.
$$

The script verifies the logarithmic-derivative identity symbolically. Its first coefficients are

$$
a_2=\frac32,
\qquad a_3=\frac{15}{8},
\qquad a_4=\frac{35}{16}.
$$

For $\mu=0,1/2,1$, the exact Ma–Minda Fekete–Szegő bounds emitted by the script are respectively

$$
\frac{15}{8},\qquad \frac34,\qquad \frac34.
$$

These values are theorem applications under the stated admissibility hypotheses, not newly claimed inequalities.

## Identity and provenance

A caller-defined generator cannot borrow the identity of a built-in class merely by reusing its key. Every result record uses

```text
user:<caller-key>:<full SHA-256 of the exact SymPy formula>
```

as its canonical identity and also records the full formula and caller citation. Built-in classes retain their historical keys. Names and citations do not change the mathematical identity; changing the exact formula does.

## What is exact and what is screened

- The generator formula, Taylor coefficients, canonical-member coefficients, logarithmic-derivative residual, and Fekete–Szegő values use exact SymPy arithmetic.
- Admissibility is mixed evidence: normalization and $\phi'(0)>0$ are exact checks, while positive-real-part, symmetry, and starlikeness-with-respect-to-$1$ are finite numerical screens.
- The finite polynomial membership operation screens only the displayed Taylor truncation on a declared grid. It does not prove that the full canonical member belongs to the class. The exact logarithmic-derivative identity supplies the analytic relation for the displayed full member.
- Containment is a sampled winding-number screen, not a theorem.
- SVGs are finite Taylor visualizations, not proofs of full image geometry.

## Modify the workflow safely

Edit `build_generator()` to return another exact `Generator`. The constructor requires a pre-built SymPy expression using only `gfa.z`; it does not parse arbitrary expression strings, and unresolved free parameters are rejected. Specialize parameters exactly before running numerical screens. Give the object a meaningful key and a source/caller citation.

If a screen fails, preserve the report and witness as a bounded negative or inconclusive result. Do not relabel a sampled pass as a proof. For symbolic parameter regions, arbitrary coefficient-functional optimization, or a theorem asserting containment, use a separate certified workflow rather than widening this template silently.
