# Research workflows

Start with a mathematical question, inspect the relevant geometry, compute
examples exactly where possible, and then read the argument explaining the answer.
The plots guide understanding; sampling is never silently promoted to a theorem.

| Question | Worked problem | Read |
|---|---|---|
| What does a function class actually describe? | Distinguish a generator, its canonical member, and the logarithmic derivative; compare sine and classical starlike examples. | [Class geometry](class_geometry.md) |
| Where does a sharp inclusion radius come from? | Sine-to-limaçon contact, then an admissible source where real-axis checking fails. | [Sharp radius](sharp_radius.md) |
| How does a coefficient bound change with a parameter? | Fekete–Szegő bounds and switching extremals for two classes. | [Coefficient comparison](coefficient_comparison.md) |
| How can a plausible conjecture be tested and repaired? | A polynomial family, an exact failure witness, and the correct parameter interval. | [Conjecture repair](conjecture_counterexample.md) |
| What survives an operator transformation? | Alexander's starlike/convex correspondence, with exact coefficient transfer. | [Alexander transform](alexander_transform.md) |

## From worked examples to current research

[Recent-literature case studies](recent_literature.md) use the same tools to:

- reproduce a recent preprint's fifth-coefficient statement, find a canonical
  counterexample, and derive an attaining sharp replacement;
- reduce an all-order logarithmic-coefficient conjecture to convex geometry and
  Schwarz's lemma rather than an expanding numerical search.

These are different kinds of contribution. A classical theorem applied to a
recent conjecture is not automatically a new theorem; a source-version-specific
repair does not establish first-correction priority. Each study states its exact
claim, source version, known-result boundary, and remaining uncertainty.

## Running the examples

The Python scripts are in `examples/research_workflows/` in the source checkout
and source distribution. Use a Python environment with this local package
installed; executable examples are not installed as wheel entry points. Each
page provides its command and a changed-input variation. JSON records exact
expressions and sampling assumptions; SVG files open directly in a browser.

For development, install the test dependencies and run the workflow tests as
specified by the project development instructions. The literature example also
has focused `tests/test_literature_workflow.py` and `tests/test_schur.py` gates.
