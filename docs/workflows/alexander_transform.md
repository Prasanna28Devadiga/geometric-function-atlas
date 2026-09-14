# Transfer a starlike problem to a convex one

**Problem.** How can a transformation turn a solved starlike problem into a convex one? What changes in the coefficients and image geometry?

```sh
python examples/research_workflows/alexander_transform.py --generator starlike --output /tmp/gfa-alexander-classical
python examples/research_workflows/alexander_transform.py --generator sine --output /tmp/gfa-alexander-sine
```

The two solutions use the same operator, not separately memorized formulas. Change `--radius` to investigate the images farther toward the boundary. The output preserves exact coefficient transformations, the identity residuals, numerical curve data, and a plot.

## The identity does the mathematical work

Let f be normalized analytic and define the Alexander transform

`g(z)=integral_0^z f(t)/t dt`.

The quotient f(t)/t extends analytically at zero, and the disk is simply connected, so the integral is path independent and `g(0)=0, g'(0)=1`. Differentiation gives

`z*g'(z)=f(z)` and `1+z*g''(z)/g'(z)=z*f'(z)/f(z)`.

The quotients are understood by continuation at zero. Elsewhere the identity requires nonvanishing of f/z, equivalently g'. For the canonical members in this workflow, f/z is an exponential and has no zeros.

Consequently the starlikeness condition for f becomes the convexity condition for g. More generally, the two expressions are identical in the defining subordinations for `S*(phi)` and `C(phi)`. This is a classical Alexander relation, not a new operator theorem.

If `f(z)=z+sum_{n>=2} a_n*z^n`, termwise integration gives

`g(z)=z+sum_{n>=2} (a_n/n)*z^n`.

The script uses the package's exact canonical-member recurrence, divides the nth coefficient by n, and checks both analytic identities symbolically.

## Two explicit solutions

For the Koebe function `f=z/(1-z)^2`, integration gives `g=z/(1-z)`. On the full disk g maps onto the half-plane Re(w)>-1/2; its finite-radius circular images help explain the convexity geometrically.

For the sine-associated canonical member `f=z*exp(Si(z))`, the transform is

`g(z)=integral_0^z exp(Si(t)) dt`.

A simple elementary closed form is not required to use the operator. The exact derivative identity gives the class relation; numerical straight-path quadrature supplies the plot. The first transformed coefficients are `a2/2=1/2`, `a3/3=1/6`, and `a4/4=1/36`.

## What the computation does not establish

The plot samples full analytic functions, with numerical quadrature for the sine transform. A one-point comparison at two working precisions is a consistency check, not a global error estimate. Exact coefficient transformations do not imply that an arbitrary finite Taylor polynomial remains convex.

The before/after panels use equal real and imaginary units within each plane; read the printed ranges before comparing apparent image sizes. Sources and assumptions are part of the problem, not hidden consequences of the plot. The mathematical transfer is justified by the displayed identity and the standard analytic characterizations, not by visual convexity.
