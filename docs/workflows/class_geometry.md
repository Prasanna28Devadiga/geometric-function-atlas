# See class geometry

A Ma–Minda class is defined through the logarithmic derivative
$zf'(z)/f(z)$, not directly through the image $f(\mathbb D)$. This example puts
the relevant pictures side by side.

## Run it

```bash
python examples/research_workflows/class_geometry.py \
  --generator starlike \
  --output /tmp/gfa-class-geometry
```

## What you will see

Open `/tmp/gfa-class-geometry/class_geometry.svg`. It has three panels:

1. **$\phi(\mathbb D_r)$** — the domain that constrains $zf'/f$;
2. **$f_\phi(\mathbb D_r)$** — the image of the canonical function itself;
3. **$zf_\phi'/f_\phi$** — equal to $\phi$ for this canonical function.

The first and third panels agree because of an identity. The middle panel is a
different geometric object.

## Where the canonical member comes from

Solve

$$
\frac{zf_\phi'(z)}{f_\phi(z)}=\phi(z)
$$

with $f_\phi(0)=0$ and $f_\phi'(0)=1$. The solution is

$$
f_\phi(z)
=z\exp\!\left(\int_0^z\frac{\phi(t)-1}{t}\,dt\right).
$$

For the classical starlike generator
$\phi(z)=(1+z)/(1-z)$, this gives the Koebe function

$$
f_\phi(z)=\frac{z}{(1-z)^2}.
$$

For $\phi(z)=1+\sin z$, it gives

$$
f_\phi(z)=z\exp(\operatorname{Si}(z)).
$$

Try the sine example:

```bash
python examples/research_workflows/class_geometry.py \
  --generator sine \
  --radius 0.7 \
  --order 12 \
  --output /tmp/gfa-sine-geometry
```

## Read the orange curve

The blue curve uses the full analytic formula. The orange curve uses a finite
Taylor polynomial. Near the Koebe pole at $z=1$, a low-order polynomial can be
far from the full function; the JSON file reports the sampled difference at two
Taylor orders.

Those error numbers are measured on the displayed sample points. The defining
identity above—not the picture—is what places the canonical member in the
class.