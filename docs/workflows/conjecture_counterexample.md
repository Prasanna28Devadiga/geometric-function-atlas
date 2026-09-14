# Test a conjecture, explain the failure, and repair it

**Problem.** For which real `a>=0` is `f_a(z)=z+a*z^2` starlike on the open unit disk?

```sh
python examples/research_workflows/conjecture_counterexample.py --a 1 --output /tmp/gfa-fail
python examples/research_workflows/conjecture_counterexample.py --a 1/2 --output /tmp/gfa-endpoint
python examples/research_workflows/conjecture_counterexample.py --a 2/5 --output /tmp/gfa-interior
```

The worked interface accepts `0<=a<=10` as exact rational input; the mathematical statement below covers every real nonnegative a. The output is a classification, an exact witness when appropriate, the correction to the conjecture, and a plot of the relevant logarithmic derivative.

## Solve the whole family, not just the sampled examples

Away from the removable zero at the origin,

`q_a(z)=z*f_a'(z)/f_a(z)=(1+2*a*z)/(1+a*z)=2-1/(1+a*z)`.

For `0<a<=1/2`, the denominator never vanishes in the disk. Since `|1+a*z|>=1-a*|z|`,

`Re q_a(z) >= 2-1/(1-a*|z|) > 2-1/(1-a) = (1-2a)/(1-a) >= 0`.

At a=0, q is identically one. Thus f_a is starlike for `0<=a<=1/2` by the usual analytic characterization. In particular, a=1/2 is included: its boundary infimum is zero, but its real part is strictly positive everywhere inside D.

For a>1/2, the derivative vanishes at `z=-1/(2a)` inside D. A univalent analytic function has nonzero derivative, so every such f_a fails univalence and hence starlikeness. There is also a direct negative-real logarithmic-derivative witness: choose

`t=min((a+1/2)/2,3/4)`, `z=-t/a`.

Then `1/2<t<min(a,1)`, so z is strictly inside D and

`q_a(z)=(1-2t)/(1-t)<0`.

This proves the corrected claim **f_a is starlike if and only if 0<=a<=1/2**. It is an elementary family classification, not an AI-discovered theorem claim.

## Inspect a concrete failure

At a=1 and z=-3/4, the exact value is -2. Both coefficient and point are exactly binary-representable, so the script also replays this witness through the public interval checker. For other rational inputs, it does not silently round the original object: it either verifies that the float inputs are exactly identical, or retains the symbolic rational witness and says why the float-based public replay was not used.

The image plot alone is not the refutation. The exact pointwise violation is. The plotted radius is chosen to include the witness while avoiding the logarithmic derivative's pole; it is disclosed in JSON. For a>1, f_a additionally has a nonzero root inside D at -1/a. At a=1 that root is on the boundary, not inside.

## A failed test is not necessarily a failed conjecture

A sufficient starlikeness coefficient condition is `sum_{n>=2} n*|a_n|<=1`. Consider the normalized Koebe dilation

`F(z)=z/(1-z/4)^2`.

Its logarithmic derivative `(1+z/4)/(1-z/4)` has positive real part throughout D, so F is starlike. But `a_n=n*(1/4)^(n-1)` gives

`sum_{n>=2} n*|a_n| = (1+1/4)/(1-1/4)^3-1 = 53/27 > 1`.

The sufficient coefficient test is therefore inconclusive, **not a disproof**. This control is deliberately about the same property (starlikeness); it avoids confusing failure of a convexity criterion with failure of starlikeness.

All plotted curves are sampled. The interval classification and witness above rest on exact analysis. No new literature-novelty claim is made; the reusable contribution of the workflow is the explicit conjecture-to-witness-to-correction method and its failure semantics.
