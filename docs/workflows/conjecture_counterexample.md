# Test a conjecture

Consider the family

$$
f_a(z)=z+az^2,
\qquad a\geq0.
$$

For which values of $a$ is $f_a$ starlike in the unit disk? This example starts
with a failed case, finds the exact reason, and then solves the whole family.

## Run it

```bash
python examples/research_workflows/conjecture_counterexample.py \
  --a 1 \
  --output /tmp/gfa-conjecture
```

## What you will see

The result marks $a=1$ as non-starlike and gives the witness $z=-3/4$. At that
point,

$$
\frac{zf_a'(z)}{f_a(z)}=-2,
$$

so its real part is negative. The SVG shows the same logarithmic derivative,
and the JSON records the exact witness.

## Solve the whole family

Away from the removable value at zero,

$$
q_a(z)=\frac{zf_a'(z)}{f_a(z)}
      =\frac{1+2az}{1+az}.
$$

If $0<a\leq1/2$, then

$$
\operatorname{Re}q_a(z)
>\frac{1-2a}{1-a}\geq0
$$

for every $|z|<1$. The endpoint $a=1/2$ is included because the inequality is
strict inside the disk.

If $a>1/2$, the derivative vanishes at $z=-1/(2a)$ inside the disk. Such a
function cannot be univalent, and therefore cannot be starlike.

The corrected statement is

$$
f_a\text{ is starlike exactly when }0\leq a\leq\frac12.
$$

Try the endpoint:

```bash
python examples/research_workflows/conjecture_counterexample.py \
  --a 1/2 \
  --output /tmp/gfa-conjecture-endpoint
```

## A failed sufficient test is not a counterexample

Some coefficient criteria are sufficient but not necessary. If such a test
fails, it has learned nothing about functions outside the criterion. The Koebe
dilation $z/(1-z/4)^2$ is starlike even though the coefficient sum used by one
of the package's simple tests exceeds its threshold.

By contrast, the negative value of $\operatorname{Re}(zf'/f)$ at an interior
point is a direct counterexample. The workflow keeps those two outcomes
separate.