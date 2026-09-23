# Alexander transform

The Alexander transform is a useful identity connecting starlike and convex
functions. It is kept here as an advanced example rather than presented as a
separate research workflow.

## The identity

For a normalized analytic function $f$, define

$$
g(z)=\int_0^z\frac{f(t)}{t}\,dt.
$$

Then $zg'(z)=f(z)$ and

$$
1+\frac{zg''(z)}{g'(z)}=\frac{zf'(z)}{f(z)}.
$$

The right-hand side tests starlikeness of $f$; the left-hand side tests
convexity of $g$. If

$$
f(z)=z+\sum_{n\ge2}a_nz^n,
$$

then

$$
g(z)=z+\sum_{n\ge2}\frac{a_n}{n}z^n.
$$

## Worked example

From a source checkout, run:

```bash
python examples/research_workflows/alexander_transform.py \
  --generator starlike \
  --output /tmp/gfa-alexander
```

The output contains the exact transformed coefficients, a symbolic check of the
identity, and a sampled before-and-after plot. For the Koebe function
$f(z)=z/(1-z)^2$, the transform is $g(z)=z/(1-z)$.
