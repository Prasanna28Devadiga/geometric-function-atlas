# From a class definition to geometry

**Problem.** A Ma–Minda class is specified by `z*f'(z)/f(z) subordinate to phi(z)`. What does the generator constrain, and what does a member of the class look like?

Run the two solved examples, or change `--radius` and `--order`:

```sh
python examples/research_workflows/class_geometry.py --generator starlike --output /tmp/gfa-starlike-geometry
python examples/research_workflows/class_geometry.py --generator sine --radius 0.7 --order 12 --output /tmp/gfa-sine-geometry
```

The output pairs an SVG with its complete sampled curve coordinates and exact definitions in JSON. It uses the installed public package, not the website.

## Three objects, not interchangeable pictures

1. **phi(D_r):** the comparison domain for the logarithmic derivative.
2. **f_phi(D_r):** the actual image of the canonical normalized member.
3. **z*f_phi'/f_phi:** for this member, exactly equal to phi, so the first and third panels agree.

Solve the differential identity rather than guess the member:

`f_phi(z)=z*exp(integral_0^z (phi(t)-1)/t dt)`.

The integrand is analytic at zero by removal of the singularity. Thus `f(0)=0` and `f'(0)=1`; the exponential also shows that f has no zeros away from zero. The package's exact coefficient recurrence gives a separate finite expansion of this member. It does not claim that every finite truncation lies in the class.

For `phi=(1+z)/(1-z)`, integration gives the Koebe function `z/(1-z)^2`. For `phi=1+sin(z)`, it gives `z*exp(Si(z))`, where `Si(z)=integral_0^z sin(t)/t dt` is the entire sine integral. The script differentiates these literal formulas symbolically and requires a zero residual against the generator from the public catalog.

## What the orange comparison teaches

Blue curves sample the full analytic functions on four circles inside the open disk. Orange compares the outer-ring image of a finite Taylor polynomial with the blue full-function image. Real and imaginary axes use equal units within each panel; different panels may have different ranges.

The JSON compares approximation errors for polynomial degrees `order+1` and `2*order+1` on 128 outer-ring points. These are **sampled errors**, not rigorous sup-norm or tail bounds. Near the Koebe pole at z=1, convergence is much slower than for the entire sine member: increasing the radius can make a low-order polynomial picture very misleading.

This is a useful way to decide whether a proposed visualization is informative. It is not a proof of univalence, class membership, or complete image containment. The analytic class statements rely on the stated generator hypotheses and defining differential relation.

## A compatibility warning

The existing `gfa plot domain <generator>` operation documents a different construction: the truncation of `z*phi(z)`. This workflow intentionally does not change that public command. It explicitly constructs `f_phi`; never relabel a z*phi plot as the canonical member's image.

**Attribution and scope:** classical Ma–Minda construction, using the public generator catalog and `class_extremal_coefficients`. The figures are new explanatory artifacts, not new theorems. The sine generator's source is Cho et al., *Radius problems associated with the sine function*, DOI 10.1007/s41980-018-0127-5; the present differential identity is derived explicitly above.
