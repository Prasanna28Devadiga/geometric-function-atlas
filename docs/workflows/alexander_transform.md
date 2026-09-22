# Use the Alexander transform

Start with a starlike function and integrate $f(z)/z$ to obtain a convex one.
This page shows the identity, the coefficient change, and the before-and-after
images.

## Run it

```bash
python examples/research_workflows/alexander_transform.py \
  --generator starlike \
  --output /tmp/gfa-alexander
```

## What you will see

Open `/tmp/gfa-alexander/alexander_transform.svg`. The first panel shows the
starlike function; the second shows its Alexander transform. The JSON file
contains the exact coefficients and the symbolic identity check.

## The identity

For a normalized analytic function $f$, define

$$
g(z)=\int_0^z\frac{f(t)}{t}\,dt.
$$

Then

$$
zg'(z)=f(z)
$$

and therefore

$$
1+\frac{zg''(z)}{g'(z)}=\frac{zf'(z)}{f(z)}.
$$

The expression on the right tests starlikeness of $f$; the one on the left
tests convexity of $g$. The equality is the whole reason the transform works.

If

$$
f(z)=z+\sum_{n\ge2}a_nz^n,
$$

then integration gives

$$
g(z)=z+\sum_{n\ge2}\frac{a_n}{n}z^n.
$$

## Two examples

For the Koebe function,

$$
f(z)=\frac{z}{(1-z)^2},
\qquad
g(z)=\frac{z}{1-z}.
$$

The transform maps the unit disk onto the half-plane
$\operatorname{Re}w>-1/2$.

Try the sine class as well:

```bash
python examples/research_workflows/alexander_transform.py \
  --generator sine \
  --output /tmp/gfa-alexander-sine
```

Its canonical member is $z\exp(\operatorname{Si}(z))$. The transform does not
need an elementary closed form: the identity is exact, and numerical quadrature
is used only to draw the second panel.