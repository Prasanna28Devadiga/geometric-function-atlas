# Getting started

Install the `gfa` command, run a short tour, and try the main calculations.

## Install

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh
```

The installer sets up `gfa` and its own Python. You do not need to prepare a
Python environment first.

## Take the tour

```bash
gfa walkthrough
```

This introduces the notation and runs three examples: a generator expansion, a
coefficient bound, and a radius check.

## Browse the built-in classes

A Ma–Minda class is described by a generator $\phi$. List the generators that
ship with the package:

```bash
gfa generators
```

The output includes short names that can be used in later commands:

```text
exponential: exp(z)
sine: sin(z) + 1
cardioid: 2*z**2/3 + 4*z/3 + 1
lemniscate: sqrt(z + 1)
sigmoid: 2/(1 + exp(-z))
```

## Expand a generator

For the sine class,

$$
\phi(z)=1+\sin z
       =1+z-\frac{z^3}{6}+\frac{z^5}{120}+\cdots.
$$

Ask for the first five coefficients:

```bash
gfa coefficients sine --order 5 --json
```

The result contains

```json
{
  "coefficients": ["1", "0", "-1/6", "0", "1/120"]
}
```

The strings are exact symbolic values, so `-1/6` has not been rounded to a
decimal.

## Compute a Fekete–Szegő bound

For the exponential class, compute the bound for
$|a_3-\mu a_2^2|$ at $\mu=0$:

```bash
gfa fekete-szego exponential --mu 0 --json
```

The exact answer is $3/4$:

```json
{
  "value_exact": "3/4",
  "value_decimal": "0.7500000000000000"
}
```

Parameters can be fractions. For example, replace `--mu 0` with `--mu 1/2`.

## Disprove starlikeness at one point

Take

$$
f(z)=z+z^2.
$$

The following command checks the point $z=-3/4$:

```bash
gfa verify-counterexample --coefficients 1 --point=-0.75,0 --property starlike
```

It returns:

```text
CERTIFIED COUNTEREXAMPLE
Criterion: starlikeness
Witness: z = -0.75 + 0i
Certified value: [-2, -2]
Counterexample condition: value <= 0
```

Starlikeness requires $\operatorname{Re}(zf'(z)/f(z))>0$ throughout the disk.
The value $-2$ at an interior point is therefore a proof that this particular
function is not starlike.

## Check a sharp radius

The package contains a proved inclusion radius from the sine class to the
sigmoid class. Check its calculation:

```bash
gfa verify-radius-certificate sine sigmoid
```

The radius is

$$
\arcsin\!\left(\frac{e-1}{e+1}\right).
$$

The command checks the identities used in the proof and reports each step. The
[full argument](https://gft-registry.fly.dev/proofs/radius-sine-sigmoid) is on
the live Atlas.

## Draw a domain

```bash
gfa plot domain exponential --output exponential-domain.svg
```

Open `exponential-domain.svg` in a browser. The picture comes from a finite
Taylor expansion, so use it to explore the geometry rather than as a proof of
the full image domain.

## Use Python

The same calculations are available as Python functions:

```python
from geometric_function_atlas import fekete_szego, generator_series

series = generator_series("sine", order=5)
print(series.to_dict()["coefficients"])

bound = fekete_szego("exponential", mu="1/2")
print(bound.to_dict()["value_exact"])
```

## Choose what to do next

Go to [Choose a workflow](workflows/README.md) for worked examples on class
geometry, sharp radii, coefficient bounds, conjectures, and recent papers.