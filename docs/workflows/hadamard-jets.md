# Normalized Hadamard jets (bounded API)

`hadamard_coefficients(left, right)` returns `(a2*b2, ..., a9*b9)` for equally
long, nonempty exact normalized jets. Both functions have implicit coefficients
`a0=b0=0`, `a1=b1=1`; at most eight tail coefficients are accepted. Missing
coefficients are unknown, never padded by zero. Inexact, nonfinite or string
coefficients are refused using the existing package exact-jet validator.

```python
from geometric_function_atlas import hadamard_coefficients
assert hadamard_coefficients([2, 3, 4], [2, 3, 4]) == (4, 9, 16)
```

This is coefficientwise convolution, **not** ordinary multiplication of `f/z`
and `g/z`. It proves no disk analyticity, class membership, unknown tail,
convolution-duality statement, global starlikeness, sharp radius or upper bound.
No new CLI command or result-envelope certification route is introduced.

Source application: B. Bhowmik and S. Biswas, arXiv:2606.20861v1, p2 definition
of Hadamard product; Theorem1 pp3-4 concerns the universal family
`S * St(alpha)`, `0 <= alpha < 1`, and is a lower bound, not a claim that its
new bound is sharp. Directed Ma-Minda generator inclusion is a different
problem. The finite transform is the smallest missing reusable operation; it
intentionally does not purport to implement the duality theorem.

Independent whole-function anchors: for `k=z/(1-z)^2`,
`k*k=z*(1+z)/(1-z)^3`; for `g_t=z/(1-t*z)`,
`k*g_t=k(t*z)/t`. Tests compare finite jets against these independently known
whole functions and against a coefficient-symbol control. Global membership
of these named whole functions follows from their defining rational formulas,
not from their jets. The general Lemmas1-5 and continuum quantifiers remain
outside this helper's scope.
