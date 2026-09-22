# Explore your own class

Use this workflow when you have an exact generator $\phi$ and want to see the
class it defines. The example uses the starlike-of-order-$\alpha$ family

$$
\phi_\alpha(z)=\frac{1+(1-2\alpha)z}{1-z},
\qquad 0\leq\alpha<1.
$$

## Run it

From the repository root:

```bash
python examples/research_workflows/custom_class.py \
  --alpha 1/4 \
  --order 4 \
  --output /tmp/gfa-custom-class
```

## What you will see

Open `/tmp/gfa-custom-class`. It contains:

- `custom_class.json`, with the formulas and coefficients;
- `custom_class_phi.svg`, the image of the generator;
- `custom_class_z_times_phi.svg`, the image of $z\phi(z)$;
- `custom_class_f_phi.svg`, the image of the canonical member; and
- `research_bundle_manifest.json`, a file list with checksums.

The three pictures show different functions. In particular, a plot of
$z\phi(z)$ is not a plot of the canonical member.

## Work through the example

At $\alpha=1/4$,

$$
\phi(z)=\frac{1+z/2}{1-z}
      =1+\frac32z+\frac32z^2+\cdots.
$$

The canonical member is defined by

$$
\frac{z f_\phi'(z)}{f_\phi(z)}=\phi(z),
\qquad f_\phi(0)=0,\quad f_\phi'(0)=1.
$$

For this generator the solution is

$$
f_\phi(z)=\frac{z}{(1-z)^{3/2}}
          =z+\frac32z^2+\frac{15}{8}z^3+\frac{35}{16}z^4+\cdots.
$$

The script differentiates this formula and checks the defining identity. It
also computes the Fekete–Szegő bounds at $\mu=0,1/2,1$:

$$
\frac{15}{8},\qquad \frac34,\qquad \frac34.
$$

## Try your own generator

Open `examples/research_workflows/custom_class.py` and edit
`build_generator()`. Return a `Generator` built from an exact SymPy expression
using `gfa.z`. Substitute exact parameter values before running the script; for
example, use `Rational(1, 3)` rather than a decimal approximation.

Give the generator a new key and a source note. The output records both the
formula and a hash, so two different formulas cannot accidentally be treated as
the same class.

## What is checked

The formulas, Taylor coefficients, canonical-member identity, and displayed
coefficient bounds are symbolic calculations. The class-containment checks and
SVGs use sampled points. Treat a sampled picture as a clue to investigate, not
as a proof of containment.

To send the output directory to someone else, continue with
[Share a reproducible result](collaborator_bundle.md).