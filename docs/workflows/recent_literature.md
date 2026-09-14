# Use recent literature to find—and repair—a coefficient problem

This connects [canonical-member geometry](class_geometry.md),
[coefficient comparison](coefficient_comparison.md), and
[conjecture repair](conjecture_counterexample.md) to concrete recent sources.
The aim is a mathematical explanation, not a large number of computations.

Two different outcomes matter here: a conjecture that follows from a classical
geometric mechanism, and a false stated bound that can be replaced sharply.
No claim of first discovery or first correction is made.

## 1. Repair a fifth-coefficient bound

**Source problem.** Kumar and Giri define
`S*_nc={f in A: zf'/f subordinate to phi}`, where
`phi(z)=(1+z)/cos(z)` and `A` consists of analytic functions in the open unit
disk D with `f(0)=0`, `f'(0)=1`. Their preprint's Theorem 12 states
`|a5|<=1/3`; its displayed canonical expansion in Equation (6) has
`a5=35/96`.[2]

### Reproduce the discrepancy

From an installed checkout/source distribution:

```sh
python examples/research_workflows/literature_coefficient_audit.py --output /tmp/gfa-literature
python examples/research_workflows/literature_coefficient_audit.py --dilation 3/4 --output /tmp/gfa-literature-dilated
```

The script uses the package's exact generator expansion and Schur-member
reconstruction, not the paper's coefficient table as ground truth. The first run
returns `a5=5/12`, excess `1/12`, and `FALSIFIED` for the literal `1/3` bound.
The second member has `a5=135/1024`; it does not itself violate that bound.
A nonviolating example is **not** evidence that the universal bound is true.

The SVG plots the exact family formula `a5(d)=5*d^4/12`, sampled for display,
against both bounds. JSON contains the rational coordinates and comparisons.
Violation occurs precisely when `d>(4/5)^(1/4)`; equality is not violation.

### Why this is a genuine analytic witness

Define the full function, not just a polynomial,

`f0(z)=z*exp(integral_0^z ((1+t)/cos(t)-1)/t dt)`.

The integrand is analytic in D after removing its singularity at zero. The
cosine denominator has no zero there. Thus `f0` is normalized, has no zero except
zero, and `zf0'/f0=phi`. The Schwarz function `omega(z)=z` establishes membership.
The dilations are `f_d(z)=f0(d*z)/d` for `0<d<=1`, with `f_0(z)=z` by continuation.
Their logarithmic derivatives are `phi(d*z)`, so all belong to the same class.

One can also check starlikeness without relying on the source's geometric claims.
For `z=x+iy` in D, the sign of `Re phi(z)` is the sign of
`1+x-y*tan(x)*tanh(y)`, since `cos(x)*cosh(y)>0`.
For `x<=0`, the subtracted term is nonpositive and `1+x>0`.
For `x>=0`, `tan(x)<=2x` and `0<=y*tanh(y)<=y^2<1`, so the expression is at least
`1+x-2xy^2>=1-x>0`. The tangent estimate follows from
`sin(x)<=x` and `cos(x)>=1-x^2/2>1/2`. Therefore `Re(zf0'/f0)>0`:
the witness is starlike and univalent. Its truncated polynomial need not be.

Directly expanding the definition gives

`phi=1+z+z^2/2+z^3/2+5z^4/24+...`,

`f0=z+z^2+3z^3/4+7z^4/12+5z^5/12+...`.

This disproves the stated `1/3` upper bound. It also shows why copying a printed
canonical expansion into an anchor test can preserve an error rather than detect it.

### Solve the repaired problem: the sharp bound is 5/12

Write `omega=(p-1)/(p+1)` with `p(z)=1+sum p_k*z^k`, `Re p>0`.
The paper's Equation (8), which does agree with direct expansion, gives[2]

`192*a5 = -p1^4+4*p1^2*p2+4*p1*p3+24*p4`

`        = 4*p1^2*(p2-p1^2/4)+4*(p1*p3+6*p4)`.

Set `t=|p1|`, so `0<=t<=2`. The crucial dependence is

`|p2-p1^2/2| <= 2-t^2/2`,

hence `|p2-p1^2/4|<=2-t^2/4`. To see the first inequality, write
`omega=c1*z+c2*z^2+...`; then `p1=2c1`, `p2=2(c2+c1^2)` and apply the
Schwarz coefficient estimate `|c2|<=1-|c1|^2`.
Together with `|p3|,|p4|<=2`, this yields

`192*|a5| <= 4*t^2*(2-t^2/4)+4*(2*t+12)`

`          = M(t) = 48+8*t+8*t^2-t^4`.

But `M'(t)=8+4*t*(4-t^2)>=8` on `[0,2]`. Consequently

**`|a5| <= M(2)/192 = 5/12`.**

For `p=(1+z)/(1-z)`, every `p_k=2`, and the canonical member above attains
`a5=5/12`. This proves the corrected bound is **sharp**, not merely an upper
bound compatible with the counterexample. The proof works for complex coefficients;
no assumption that the extremizing parameters are real was used in the upper bound.

**What changed mathematically?** Keeping the coupled `p1,p2` constraint gives a
valid monotone majorant and an attaining member. The useful output is the short
repair argument, not a black-box optimization verdict.

**Source boundary.** The statements audited are those of arXiv:2412.04819v1,
Theorem 12 and Equation (8), p. 6, and Equation (6), p. 3.[2]
The checked arXiv history lists v1 only; a separate journal correction or an
independent earlier derivation has not been ruled out. Do not extrapolate this
finding to all other bounds in that paper.

## 2. Replace an all-order search by convex geometry

**Source problem.** Majumder, Sarkar and Ahamed establish
`|gamma_n|<=1/(2n)` for `n=1,2,3,4` in `S*_e`, then state the same sharp inequality
for all positive integers as Conjecture 3.1. Here `zf'/f subordinate to exp(z)`
and `log(f/z)=2*sum gamma_n*z^n`, with the analytic logarithm normalized at zero.[1]

Rather than optimize a fifth coefficient, examine the generator.

### The coefficient-extraction argument

Let `phi` be convex univalent in D, `phi(0)=1`, `phi'(0)=B1>0`, and
`q=1+sum b_k*z^k` subordinate to `phi`. Fix any integer `n>=1` and average
`q(zeta^j*z)` over the nth roots of unity. The average lies in the **open convex**
domain `phi(D)` and equals

`A_n(z)=1+sum_{k>=1} b_{kn}*z^(kn)=Q_n(z^n)`.

The series `Q_n(w)=1+sum b_{kn}*w^k` is analytic in D by Cauchy's coefficient
estimates on smaller disks. Since `z -> z^n` maps D onto D, `Q_n(D)` lies in
`phi(D)`; no boundary-limit argument is needed. Thus `phi^{-1} composed with Q_n`
is an analytic disk self-map fixing zero. Schwarz's lemma gives `|b_n|<=B1`.
This is the classical convex-subordination coefficient mechanism; Ma and Minda's
1992 paper already uses Rogosinski's result in precisely this coefficient-bound
form for a convex dominant.[4]

Now `q=zf'/f=1+2*sum n*gamma_n*z^n`, so

**`|gamma_n|<=B1/(2n)` for every `n>=1`.**

For `phi(z)=exp(z)`, `Re(1+z*phi''/phi')=Re(1+z)>0`, proving convex
univalence; `B1=1`. This supplies the conjectured all-order inequality.
The inverse branch used above exists because `exp` is univalent on D, and is
chosen to send `1` to `0`.

Sharpness is explicit:

`f_n(z)=z*exp(sum_{k>=1} z^(nk)/(n*k*k!))`,

for which `zf_n'/f_n=exp(z^n)` and `gamma_n=1/(2n)`.
These functions are normalized and starlike because `Re exp(z^n)>0` in D.

**Changed input.** Replace `exp(z)` by `exp(a*z)`, `0<a<=1` real. Convexity still
holds, the sharp bound becomes `a/(2n)`, and the extremal replaces the series
summand by `a^k*z^(nk)/(n*k*k!)`. The test suite checks finite equality anchors
at `n=1,...,5` and `a=1,1/2`; the proof above, not those tests, covers all n.

**Research payoff and novelty.** Convexity reduces every coefficient question
to one first-derivative bound. This answers the literal conjectural statement,
but is a classical-theorem consequence, not a new general coefficient theorem.
First-resolution priority for the particular preprint is not asserted.

## Publication assessment

The fifth-coefficient result is a candidate for a short correction or technical
note: it identifies a false stated bound, supplies an analytic counterexample,
and solves the replacement extremal problem sharply. This is a correction of an
invalid bound, not an improvement over a valid previously sharp bound. Before
claiming first-correction priority or submitting a note, check the journal
version and any errata, reconcile earlier treatments of this exact class, and
obtain a collaborator's mathematical review.

The exponential result is a useful resolution of the literal conjecture through
classical convex subordination, not a new general theorem. Both cases support a
research-software paper by demonstrating mathematical diagnosis and explanation;
the number of workflows is not a count of novel mathematical contributions.

## Reproduction and limitations

Run `python -m pytest tests/test_literature_workflow.py tests/test_schur.py -q`
from the development checkout. The source audit uses public coefficient machinery;
its analytic admissibility and sharp upper bound are proved above.

The fifth-order anchor exposed a reconstruction defect: the old Schur helper
accepted five parameters but emitted at most four coefficients, and member
reconstruction also zero-padded rational tails for shorter parameter lists.
The local fix uses bounded reverse Schur recursion with a zero terminal Schur
remainder, expanded to the requested order. A zero Schur remainder is **not**
a zero Taylor tail. Tests compare with independently constructed rational
functions and the monomial `omega=z^5`. Existing baked certificate data are not
silently regenerated or upgraded by this example.

## Sources

[1] https://arxiv.org/abs/2511.03218v1
[2] https://arxiv.org/abs/2412.04819v1
[4] https://matwbn.icm.edu.pl/ksiazki/apm/apm57/apm5727.pdf
