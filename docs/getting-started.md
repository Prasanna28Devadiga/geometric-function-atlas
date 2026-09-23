# Getting started

Install `gfa` and use one Ma–Minda class to answer a concrete coefficient
question.

## Install

```bash
curl --proto '=https' --tlsv1.2 -LsSf https://gft-registry.fly.dev/install.sh | sh
```

The installer supplies the `gfa` command and its own Python.

## Understand the example

The exponential Ma–Minda class is determined by the generator

$$
\phi(z)=e^z.
$$

It consists of normalized functions

$$
f(z)=z+a_2z^2+a_3z^3+\cdots
$$

whose logarithmic derivative satisfies $zf'(z)/f(z)\prec e^z$. The numbers
$a_2,a_3,\ldots$ are coefficients of functions in the class; they are not the
coefficients of the generator $\phi$.

We will ask for the sharp upper bound on
$|a_3-\mu a_2^2|$.

## Compute one bound

Start with $\mu=0$:

```bash
gfa fekete-szego exponential --mu 0
```

The command returns the exact value $3/4$. Thus every function in this class
satisfies $|a_3|\leq 3/4$ under the assumptions reported by the command.

## Change one input

Now set $\mu=1/2$:

```bash
gfa fekete-szego exponential --mu 1/2
```

The exact value changes to $1/2$, so

$$
\left|a_3-\frac12a_2^2\right|\leq\frac12.
$$

The class has not changed. Only the coefficient functional has changed.

## Continue

Choose one of the five [research workflows](workflows/README.md) when you have a
specific class, coefficient problem, radius question, conjecture, or published
claim to investigate.

For an optional command-line overview of several package features, run:

```bash
gfa walkthrough
```