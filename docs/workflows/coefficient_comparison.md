# Compare sharp coefficient bounds and locate extremal changes

**Problem.** For normalized functions `f(z)=z+a2*z^2+a3*z^3+...` in a selected Ma–Minda class, determine the sharp bound for `|a3-mu*a2^2|` as real `mu` varies. What makes the graph change slope?

This workflow solves the problem for the classical starlike and sine-associated classes using a known general theorem. It does not claim a new coefficient inequality.

## Run it and change the problem

From a source checkout with the package installed:

```sh
python examples/research_workflows/coefficient_comparison.py --generator starlike --output /tmp/gfa-starlike-fs
python examples/research_workflows/coefficient_comparison.py --generator sine --output /tmp/gfa-sine-fs
```

Each run writes `coefficient_comparison.json` and `coefficient_comparison.svg`. The JSON preserves exact rational parameter values and equality examples. The plot samples the formula; it is not the proof. The starlike transition parameters are `1/2, 1`; changing the class to sine gives `0, 1`. Read the derivation below to understand why.

The script restricts its class choices to these two worked examples. It calls the public `fekete_szego` function, not private registry code, and works without the website or a registry database. In your own calculation, use that public function with another documented generator; analytic admissibility must still be justified.

## Why the answer is piecewise

Write the admissible generator as

`phi(z)=1+B1*z+B2*z^2+...`, with `B1>0` and real `B2`.

Subordination means `z*f'(z)/f(z)=phi(omega(z))`, where `omega(z)=c1*z+c2*z^2+...` is a Schwarz function. Comparing coefficients gives

- `a2=B1*c1`;
- `2*a3=B1*c2+(B2+B1^2)*c1^2`.

Consequently

`a3-mu*a2^2 = B1/2 * [c2 + Q*c1^2]`,

where `Q=B2/B1+(1-2*mu)*B1`. The Schwarz coefficient inequality `|c2|<=1-|c1|^2` implies

`|c2+Q*c1^2| <= 1+(|Q|-1)*|c1|^2 <= max(1,|Q|)`.

Thus the bound is `B1/2*max(1,|Q|)`. The maximum of two different contributions explains the corners in its graph.

**Equality is visible, not merely asserted by the bound routine.** For `omega(z)=z`, the expression attains `|B1^2+B2-2*mu*B1^2|/2`. For `omega(z)=z^2`, it attains `B1/2`. The script independently computes these two coefficient examples and checks that the appropriate one equals every tabulated bound. At a transition both examples attain; this is not a classification of all equality cases.

For each such Schwarz function the normalized analytic solution is

`f(z)=z*exp(integral_0^z (phi(omega(t))-1)/t dt)`.

The integrand has a removable singularity at zero. This constructs genuine class members under the stated admissibility assumptions, rather than assuming that a finite polynomial with the same first coefficients is itself in the class.

## The two solutions

For the classical starlike class, `phi(z)=(1+z)/(1-z)`, so `B1=B2=2`. The answer is `max(1,|3-4*mu|)`, flat between `1/2` and `1`.

For the sine class, `phi(z)=1+sin(z)`, so `B1=1, B2=0`. The answer is `max(1,|1-2*mu|)/2`, flat between `0` and `1`.

A candidate universal starlike bound of `2` is false at `mu=0`: the Koebe function `z/(1-z)^2` has `a3=3`. This simple negative anchor prevents confusing a convenient numerical bound with the correct sharp one.

## What is assumed, and what is established?

The generator is analytic and univalent on the unit disk, normalized at one, with positive real part, real-axis symmetry, and an image starlike about one in the Ma–Minda setting. The package's coefficient checks do not prove all these analytic hypotheses for arbitrary supplied generators.

The displayed derivation applies to the real-parameter continuum. The rational table is a reproducible selection of examples, not a proof by enumeration. Numerical SVG coordinates are for presentation only.

**Attribution:** W. C. Ma and D. Minda, *A unified treatment of some special classes of univalent functions*, Proceedings of the Conference on Complex Analysis, Tianjin 1992, International Press (1994), 157–169; see the package's theorem provenance. A formula-critical primary-source locator is still pending independent source review. This pending locator does not turn a known theorem into a novelty claim; the elementary reduction used here is stated above for inspection.
