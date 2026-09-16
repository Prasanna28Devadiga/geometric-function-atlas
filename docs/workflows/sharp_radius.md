# Find a sharp radius — and learn when an axis shortcut fails

**Problem.** For every function in a source Ma–Minda class, how far can we dilate it while staying in a target class? Why is that radius sharp? Is checking the real diameter enough?

```sh
python examples/research_workflows/sharp_radius.py --source sine --s 1/2 --output /tmp/gfa-radius-sine
python examples/research_workflows/sharp_radius.py --source sine --s 7/10 --output /tmp/gfa-radius-cap
python examples/research_workflows/sharp_radius.py --source off_axis --s 1/4 --output /tmp/gfa-radius-offaxis
```

The first two runs change the target size. The third changes the source and exposes a different contact mechanism. Output: exact radius/stratum data, generator-containment and inverse-coordinate plots, and a parameter-profile plot. All coordinates are sampled; the reasons for the conclusions are below.

## Definitions that keep the problem straight

Let D be the open unit disk and `S*(phi)` the normalized analytic class defined by `z*f'/f subordinate to phi`. Our target is

`L_s(z)=(1+s*z)^2`, `0<s<=1/sqrt(2)`.

The direction is **S*(phi) -> S*(L_s)**. The sharp radius is the largest R<=1 such that `f_r(z)=f(r*z)/r` belongs to the target class for every source member and every `0<r<=R` (r=1 means f itself). Reversing source and target asks a different question.

The plots compare **generator** images and inverse coordinates, not the member images f(D) shown in the class-geometry workflow.

For an admissible source with principal square root H, target membership becomes

`phi(u) in L_s(D) iff |H(u)-1|<s`.

The branch is essential: `1+s*D` lies in the right half-plane, so the positive-real square root is the correct inverse factor. Squaring without this condition could lose a sign.

The target is admissible: it is normalized, has positive derivative 2s at zero, and real coefficients. Equality of two squared values would give either identical inputs or `z1+z2=-2/s`, impossible for distinct points in D. Furthermore `z*L_s'/(L_s-1)=2(1+sz)/(2+sz)` has positive real part. On the unit circle, the real part of L_s has minimum `(1-s)^2` for s<=1/2 and `1/2-s^2` for s>=1/2. Harmonic positivity is strict in the open disk, including s=1/sqrt(2).

## Solution A: why the sine radius comes from negative-real contact

For `phi(z)=1+sin(z)`,

`H(z)=cos(z/2)+sin(z/2)`.

It squares to phi and has positive real part for |z|<=1, so it is the principal square root. The existing analytic global-maximum lemma is

`max_{|z|<=r}|H(z)-1| = 1-cos(r/2)+sin(r/2)`, `0<=r<=1`,

with equality at z=-r. This is a global statement, not an assumption justified by a dense angular scan. Its proof factors `1-cos(z/2)+sin(z/2)` and uses angular derivative inequalities with explicit Taylor remainder bounds; the full argument is in the pinned [sine/limaçon family proof](https://github.com/Prasanna28Devadiga/gft-registry/blob/456432b5f6945ea6db46f420aa12bf0730619cf1/data/proofs/RADIUS_SINE_LIMACON_FAMILY.md), Section 3.

Solving the contact equation gives `sin(r)=2s-s^2`, hence

`R(s)=min(1,asin(2s-s^2))`.

The transition is `s0=1-sqrt(1-sin(1))`. At s>=s0 the entire class is contained; R=1 is the domain cap, not a newly discovered larger radius. Equality s=s0 is a boundary-contact stratum with strict interior inclusion.

The example's rational-input stratum selection uses alternating rational bounds for sin(1), not a rounded comparison. If 32 terms cannot distinguish an input from the transition, it explicitly abstains. The exact boundary s0 is treated in the theorem above, not silently approximated as a rational CLI input.

**From generator geometry to every function.** Write `z*f'/f=phi(omega(z))` with omega Schwarz. Then `|omega(r*z)|<=r|z|<r`; the global bound implies target membership for the dilation. The canonical source member `f_phi=z*exp(integral (phi(t)-1)/t dt)` has omega(z)=z. For any radius larger than the proper threshold, choose a negative-real point strictly between threshold and that radius: this member's dilation violates target membership. That establishes sharpness, separately from the contact equation.

### Snapshot honesty

The public package's immutable `sine -> limacon_0.5` row agrees with `asin(3/4)`, but it retains the older **touch equation** status and no full certificate. The example does not upgrade that snapshot. The later family proof has separate pinned provenance; its existing independent replay was exercised during development. No claim that every radius snapshot row is globally proved follows.

Defining sources: Masih–Kanas, DOI [10.3390/sym12060942](https://doi.org/10.3390/sym12060942), for the target family; Cho et al., DOI [10.1007/s41980-018-0127-5](https://doi.org/10.1007/s41980-018-0127-5), for the sine class. A similarly named fixed target or a radius **into** the sine class is not the same directed parameter theorem. Prior-art completeness remains unresolved; no novelty is claimed.

## Solution B: an admissible off-axis obstruction

Consider the fixed, entire polynomial source

`h(z)=z/4-z^3/32`, `phi(z)=(1+h(z))^2`.

For target s=1/4, every real-diameter check passes, yet full containment fails. This is a counterexample to a **conjectural computational shortcut**, not a refutation of a published theorem.

### Establish admissibility rather than merely drawing the source

Normalize the translated source:

`p(z)=2*(phi(z)-1)=z+z^2/8-z^3/8-z^4/32+z^6/512`.

Its sufficient starlikeness coefficient sum is

`sum_{n>=2} n*|p_n| = 195/256 < 1`.

Here is the criterion, so no opaque checker is needed. Write `p=z*(1+A(z))`. Since `sum |p_n|<1`, p has no zero away from zero. Also

`|z*p'/p-1| <= [sum (n-1)|p_n||z|^(n-1)]/[1-sum |p_n||z|^(n-1)] < 1`,

because `sum n|p_n|<1`. Thus `Re(z*p'/p)>0`, proving p starlike and univalent. Positive scaling gives `phi-1=p/2`, so phi is univalent with image starlike about one.

The normalization is `phi(0)=1`, `phi'(0)=1/2>0`, and coefficients are real. Moreover `|h|<=9/32` on the closed disk gives

`Re phi >= 1-2*(9/32)-(9/32)^2 = 367/1024 >0`.

This lower bound is sufficient, not sharp. All functions here are polynomials, so poles are absent. Since `Re(1+h)>=23/32>0`, the principal square root is exactly `1+h`. These facts establish all source hypotheses used by the containment reduction.

### See exactly what the real axis misses

On the real interval [-1,1], `h'(x)=1/4-3*x^2/32>=5/32>0`, hence

`|h(x)|<=7/32<1/4`.

But for complex z, the triangle bound is attained on the imaginary axis:

`max_{|z|<=r}|h(z)|=r/4+r^3/32`, with equality at z=+/-i*r.

The signs that cancel on the real axis align on the imaginary axis. This is the structural explanation of the failure.

At `u=15i/16`, an interior point of D,

`|h(u)|-1/4 = 1327/131072 >0`.

Therefore `phi(u)` is outside `L_{1/4}(D)` despite the entire real diameter passing the inverse-coordinate test.

### The corrected sharp-radius statement

For this fixed source and arbitrary admissible s, the radius is one when `s>=9/32`; otherwise it is the unique root rho in (0,1) of

`rho^3+8*rho-32*s=0`.

For s=1/4, this becomes `rho^3+8*rho-8=0` (approximately 0.9067953030). Uniqueness follows from derivative `3*rho^2+8>0` and opposite endpoint signs. The Schwarz/dilation argument used above proves class-wide sufficiency. For any r>rho choose `rho<t<r` and evaluate the canonical source member's dilation at z=i*t/r; its logarithmic derivative is phi(i*t), outside the target. This proves sharpness for every larger permitted radius.

At r=rho, the maximum on the **closed** subdisk touches the target boundary, but Schwarz's inequality gives a strictly smaller argument for every z inside D, so the target class still contains the dilation. The supremum on the full open disk need not be attained there.

## What this adds, and what it does not

The sine example explains a nontrivial existing analytic lemma. The changed source supplies a fully explicit obstruction to an axis-only shortcut and a reusable negative fixture. Its rotated-positive-coefficient mechanism is elementary; we do not label it a novel theorem or claim a complete classification of all generators. Its value is that the researcher can see, prove, and test exactly where a tempting inference fails.
