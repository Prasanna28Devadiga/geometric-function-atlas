# Reproduce and adapt a published result

These two examples begin with a recent coefficient claim and ask a practical
question: can the package reproduce it from the class definition? One claim
fails on the canonical member; the other follows from a classical geometric
argument.

## Run it

```bash
python examples/research_workflows/literature_coefficient_audit.py \
  --output /tmp/gfa-literature
```

## What you will see

The JSON file compares the paper's stated value with coefficients derived from
the defining subordination. The SVG shows a one-parameter family and marks
where it crosses the proposed bound.

## Case 1: repair a fifth-coefficient bound

Kumar and Giri study the class

$$
\frac{zf'(z)}{f(z)}\prec\frac{1+z}{\cos z}.
$$

Theorem 12 of arXiv:2412.04819v1 states $|a_5|\leq1/3$.[2] Start with the
canonical member

$$
f_0(z)=z\exp\!\left(
  \int_0^z\frac{(1+t)/\cos t-1}{t}\,dt
\right).
$$

By construction,

$$
\frac{zf_0'(z)}{f_0(z)}=\frac{1+z}{\cos z},
$$

so $f_0$ belongs to the class. Expanding directly gives

$$
f_0(z)=z+z^2+\frac34z^3+\frac7{12}z^4+\frac5{12}z^5+\cdots.
$$

Thus $a_5=5/12>1/3$. The proposed bound is false.

### Find the correct bound

Write

$$
p(z)=1+\sum_{k\ge1}p_kz^k,
\qquad \operatorname{Re}p(z)>0.
$$

The coefficient identity used in the paper is

$$
192a_5=-p_1^4+4p_1^2p_2+4p_1p_3+24p_4.
$$

Set $t=|p_1|$. The Carathéodory bounds and the coupled estimate

$$
\left|p_2-\frac{p_1^2}{2}\right|
\leq2-\frac{t^2}{2}
$$

give

$$
192|a_5|
\leq48+8t+8t^2-t^4.
$$

The right-hand side increases on $0\leq t\leq2$, so

$$
|a_5|\leq\frac5{12}.
$$

The canonical member attains equality. The corrected bound is therefore sharp.

## Case 2: solve an all-order conjecture geometrically

Majumder, Sarkar and Ahamed consider

$$
\frac{zf'(z)}{f(z)}\prec e^z
$$

and conjecture

$$
|\gamma_n|\leq\frac1{2n}
$$

for every $n\geq1$, where
$\log(f(z)/z)=2\sum_{n\ge1}\gamma_nz^n$.[1]

The key fact is that $e^z$ is convex and univalent on the unit disk. If
$q(z)=1+\sum b_kz^k\prec e^z$, the classical coefficient theorem for a convex
dominant gives $|b_n|\leq1$. Since

$$
q(z)=\frac{zf'(z)}{f(z)}
    =1+2\sum_{n\ge1}n\gamma_nz^n,
$$

we immediately obtain

$$
|\gamma_n|\leq\frac1{2n}.
$$

Equality is reached by functions satisfying
$zf_n'(z)/f_n(z)=e^{z^n}$. The all-order result comes from convexity, so there is
no need to optimize each coefficient separately.

## What to take away

For a claim from the literature, begin with the defining equation rather than a
printed coefficient table. Test the canonical member first. If a claim fails,
look for the geometric constraint that controls the corrected extremal problem.
Before publishing a correction, check later paper versions, journal versions,
and errata.

## Sources

[1] https://arxiv.org/abs/2511.03218v1

[2] https://arxiv.org/abs/2412.04819v1

[3] https://matwbn.icm.edu.pl/ksiazki/apm/apm57/apm5727.pdf