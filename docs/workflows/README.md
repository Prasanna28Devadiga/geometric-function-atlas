# Choose a workflow

Pick the question closest to your own. Each page gives you a command to run, a
worked example, and the mathematics needed to understand the result.

| I want to… | Start here |
|---|---|
| define a generator and study the class it creates | [Explore your own class](custom_class.md) |
| understand the difference between $\phi(\mathbb D)$ and $f(\mathbb D)$ | [See class geometry](class_geometry.md) |
| find the largest disk on which one class lies inside another | [Find a sharp radius](sharp_radius.md) |
| browse all stored source-to-target radii | [Read the radius map](radius_atlas.md) |
| see how a Fekete–Szegő bound changes with $\mu$ | [Compare coefficient bounds](coefficient_comparison.md) |
| test a proposed claim and repair it when it fails | [Test a conjecture](conjecture_counterexample.md) |
| turn a starlike calculation into a convex one | [Use the Alexander transform](alexander_transform.md) |
| send a result directory to a collaborator | [Share a reproducible result](collaborator_bundle.md) |
| reproduce a claim from a recent paper | [Work from a paper](recent_literature.md) |
| browse shorter ideas | [Thirty things to try](catalogue.md) |

## Before you run an example

The workflow scripts live in the source repository. Set up a checkout once:

```bash
git clone https://github.com/Prasanna28Devadiga/geometric-function-atlas.git
cd geometric-function-atlas
uv sync --extra test
```

Run the commands on the following pages from that directory. Each example writes
its results to a directory under `/tmp`, so it will not modify the source tree.

JSON files contain the values used to make the figures. SVG files open directly
in a browser. When a page uses a numerical picture, it also tells you which part
of the argument is exact.