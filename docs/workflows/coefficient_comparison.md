# Investigate a coefficient problem

For

$$
f(z)=z+a_2z^2+a_3z^3+\cdots,
$$

the Fekete–Szegő problem asks for the largest possible value of
$|a_3-\mu a_2^2|$. This workflow shows how the answer changes as the real
parameter $\mu$ moves.

## Run it

```bash
python examples/research_workflows/coefficient_comparison.py \
  --generator starlike \
  --output /tmp/gfa-coefficients
```

## What you will see

Open `/tmp/gfa-coefficients/coefficient_comparison.svg`. The graph has a flat
middle section and two sloping sides. The JSON file gives the exact transition
points and an equality example for each part.

For the classical starlike class, the answer is

$$
\max\{1,|3-4\mu|\}.
$$

The graph changes at $\mu=1/2$ and $\mu=1$.

## Why the graph has corners

Write

$$
\phi(z)=1+B_1z+B_2z^2+\cdots
$$

and

$$
\frac{zf'(z)}{f(z)}=\phi(\omega(z)),
\qquad \omega(z)=c_1z+c_2z^2+\cdots.
$$

Comparing coefficients gives

$$
a_3-\mu a_2^2
=\frac{B_1}{2}\left(c_2+Qc_1^2\right),
\qquad
Q=\frac{B_2}{B_1}+(1-2\mu)B_1.
$$

The Schwarz coefficient inequality yields

$$
|a_3-\mu a_2^2|
\leq \frac{B_1}{2}\max\{1,|Q|\}.
$$

Two functions compete for equality: $\omega(z)=z$ supplies the sloping pieces,
while $\omega(z)=z^2$ supplies the flat piece. A corner appears when the winner
changes.

## Try the sine class

```bash
python examples/research_workflows/coefficient_comparison.py \
  --generator sine \
  --output /tmp/gfa-sine-coefficients
```

Here $B_1=1$ and $B_2=0$, so the bound is

$$
\frac12\max\{1,|1-2\mu|\},
$$

with transitions at $\mu=0$ and $\mu=1$.

The formulas above prove the bounds for every real $\mu$. The SVG simply makes
the piecewise formula easier to see.

Source: W. C. Ma and D. Minda, *A unified treatment of some special classes of
univalent functions*, Proceedings of the Conference on Complex Analysis,
Tianjin 1992, International Press (1994), 157–169.