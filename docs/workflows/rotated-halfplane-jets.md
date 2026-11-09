# Using the convex jet solver outside convex function classes

`convex_member_coefficients(B, gammas, order=n)` solves the normalized equation
`1+z*f''/f'=phi(omega)`. Its name describes the differential equation, not an
unconditional geometric assertion. Neither positive real part nor a Ma–Minda
admissibility theorem is imposed by this low-level tuple operation.

For example, set `C=gamma*exp(-I*theta)*cos(theta)` and
`phi(z)=1-C*z/(1-z)`. Supply **every** coefficient `B1..Bn=-C` of this whole
rational generator, not a declaration that later coefficients vanish. The
existing solver handles exact negative and exact complex coefficients with
real Schur parameters; this does not add arbitrary complex Schur support.
An analytic nonzero derivative can be separately constructed by

    f'(z)=exp(integral_0^z -C*omega(t)/(t*(1-omega(t))) dt).

The removable origin singularity, Schwarz disk range and primitive on the disk
justify this whole-function construction. Convexity or global univalence does
not follow from the tuple. For `omega=z`, the whole function is
`[1-(1-z)^(C+1)]/(C+1)` using the disk's analytic logarithm of `1-z`.

`tests/test_rotated_halfplane_composition.py` checks the equation independently
by multiplying rational denominators after direct differentiation, using both
an odd Schwarz function and an explicitly nonradial rational Schwarz function.
A changed sign is rejected. The source application is arXiv:2603.16388v1,
class definition p2, Eq1.2 p3 and analytic Theorems2.1–2.2 pp6–9. These tests
are algebraic regression anchors, not endorsement of the harmonic sections or
a whole-paper certificate. No runtime API or released artifact changes.
