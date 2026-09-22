# Find a sharp radius

Suppose every function in one Ma–Minda class is dilated by
$f_r(z)=f(rz)/r$. How large can $r$ be before the dilated function leaves a
target class? That largest value is the inclusion radius.

This page starts with a case where the first contact occurs on the negative real
axis, then shows why that shortcut does not work in general.

## Run it

```bash
python examples/research_workflows/sharp_radius.py \
  --source sine \
  --s 1/2 \
  --output /tmp/gfa-sharp-radius
```

## What you will see

The directory contains a JSON result and three SVG figures. Together they show
the source generator, the target generator, the point where their boundaries
first meet, and how the radius changes with the target parameter $s$.

The target family is

$$
L_s(z)=(1+sz)^2.
$$

Rows and formulas always mean the direction

$$
\mathcal S^*(\phi)\longrightarrow\mathcal S^*(L_s).
$$

Reversing the arrow is a different question.

## The sine calculation

For $\phi(z)=1+\sin z$, take the principal square root

$$
H(z)=\sqrt{\phi(z)}=\cos(z/2)+\sin(z/2).
$$

Membership in the target is equivalent to $|H(z)-1|<s$. For $|z|\le r$,
the maximum occurs at $z=-r$ and equals

$$
1-\cos(r/2)+\sin(r/2).
$$

Setting this equal to $s$ gives

$$
R(s)=\min\{1,\arcsin(2s-s^2)\}.
$$

At $s=1/2$ the answer is therefore

$$
R=\arcsin(3/4).
$$

The Schwarz lemma carries this generator inclusion to every member of the
source class. The canonical member reaches the same boundary, so a larger
radius cannot work. This proves sharpness.

The detailed maximum argument is in the
[sine/limaçon proof](https://github.com/Prasanna28Devadiga/gft-registry/blob/456432b5f6945ea6db46f420aa12bf0730619cf1/data/proofs/RADIUS_SINE_LIMACON_FAMILY.md).

## Why checking only the real axis can fail

Run the second example:

```bash
python examples/research_workflows/sharp_radius.py \
  --source off_axis \
  --s 1/4 \
  --output /tmp/gfa-off-axis-radius
```

Here

$$
h(z)=\frac z4-\frac{z^3}{32},
\qquad \phi(z)=(1+h(z))^2.
$$

Every point on the real diameter satisfies $|h(x)|<1/4$, but on a circle
$|z|=r$ the maximum is

$$
\max |h(z)|=\frac r4+\frac{r^3}{32},
$$

attained at $z=\pm ir$. The signs cancel on the real axis and reinforce on the
imaginary axis. For $s=1/4$, the sharp radius is the unique root in $(0,1)$ of

$$
r^3+8r-8=0,
$$

approximately $0.9067953030$.

The lesson is simple: real-axis contact is a theorem to prove for a particular
generator, not a general rule for radius problems.

Sources: Masih–Kanas, DOI
[10.3390/sym12060942](https://doi.org/10.3390/sym12060942), for the target
family; Cho et al., DOI
[10.1007/s41980-018-0127-5](https://doi.org/10.1007/s41980-018-0127-5), for the
sine class.