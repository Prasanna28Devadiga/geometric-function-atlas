# Choose a research question

The Atlas focuses on five recurring parts of a geometric-function-theory
investigation. Choose the question that matches the decision you need to make.

**[Understand a new Ma–Minda class](custom_class.md)**

Connect a generator $\phi$ to its canonical member $f_\phi$, exact
coefficients, and the different domains that can be plotted.

**[Investigate a coefficient problem](coefficient_comparison.md)**

Derive a sharp Fekete–Szegő bound, locate parameter transitions, and identify
equality cases.

**[Find and verify an inclusion radius](sharp_radius.md)**

Fix the source-to-target direction, find the first boundary contact, and prove
that the resulting radius is sharp.

**[Test a conjecture](conjecture_counterexample.md)**

Separate an exact counterexample from an inconclusive test and repair a false
statement.

**[Reproduce and adapt a published result](recent_literature.md)**

Recompute a claim from its defining equation, check an extremal member, and
determine what survives.

These are not examples of every command in the package. They are complete
mathematical investigations that show when a computation is useful and what
must still be proved.

## Before you run an example

The workflow scripts live in the source repository. Set up a checkout once:

```bash
git clone https://github.com/Prasanna28Devadiga/geometric-function-atlas.git
cd geometric-function-atlas
uv sync --extra test
```

Run the command on the selected workflow page from that directory. Each example
writes its results to a directory under `/tmp`, so it will not modify the source
tree.

JSON files contain the values used to make the figures. SVG files open directly
in a browser. When a page uses a numerical picture, it also tells you which part
of the argument is exact.