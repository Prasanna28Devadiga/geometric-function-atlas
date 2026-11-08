# Compose existing multiplier APIs before adding an operator

For a normalized finite jet, let `F=D_delta^j f` at delta=1 and let
`H=(1-beta)*F+beta*z*F'`. Then `z*H'/H` is a starlike subordination.
This is **not** `(1-beta)*f'+beta*(1+zf''/f')` and does not need a new
coefficient engine. The existing bounded APIs compose:

```python
import sympy as sp
from geometric_function_atlas import (
    euler_differential_coefficients, q_al_oboudi_coefficients,
)
from geometric_function_atlas.schur import member_coefficients

# phi=1+z/2, omega=z*(1/2-z)/(1-z/2), H starlike formally.
H = member_coefficients([sp.Rational(1, 2), sp.S.Zero, sp.S.Zero],
                        [sp.Rational(1, 2), -1], order=3)
F = euler_differential_coefficients(H, second=0, first=1, inverse=True)
f = q_al_oboudi_coefficients(F, q=1, lam=1, degree=2, inverse=True)
assert euler_differential_coefficients(
    q_al_oboudi_coefficients(f, q=1, lam=1, degree=2),
    second=0, first=1,
) == H
```

`q=1` selects ordinary Al-Oboudi multipliers; it does not substitute a Jackson
derivative into an ordinary source equation. Direct generic polynomial
operator iteration and a nonradial rational Schwarz substitution independently
anchor this composition in `tests/test_composed_euler_subordination.py`.
The tests also cover beta=1/2 as **formal algebra only**. A whole-disk
membership argument remains caller-owned. Endpoint beta0/1 and delta1
iterated Alexander integrals admit the familiar genuine starlike/convex
construction; no analogous interior-beta preservation theorem is emitted.

Source application: Lobna Alhadi Alnajjar, *Fekete-Szegö Inequality For Certain
Subclass Of Multivalent Functions Associated with Al-Oboudi Differential
Operator*, JSRAS2026 pp229–234, Definition1.7, Eq2.5–2.8, selected p=b=delta=1
lane. This does not implement the full p-valent or complex-order theorem and
does not endorse the source's literally unsquared Lemma2.2.

An additional definition check matters for DOI10.62225/2583049X.2026.6.3.6336:
its lambda1 endpoint equations use **ordinary** starlike/convex derivatives;
q belongs to the q-exponential generator, not the derivative of f. Supply
its exact B coefficients to existing starlike/convex APIs. Do not call
`q_starlike_member_coefficients` merely because the title says q-derivative.
Finite exact jets, sampled comparisons, and attained witnesses are not a
whole-paper, sharp global upper-bound, or analytic-continuation certificate.
