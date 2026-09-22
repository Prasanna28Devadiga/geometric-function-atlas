# Read the radius map

This page puts every stored class-inclusion radius in one matrix. Use it to find
known pairs, spot gaps, and choose the next problem to work on.

## Run it

```bash
python examples/research_workflows/radius_atlas.py \
  --output /tmp/gfa-radius-atlas
```

## What you will see

Open `/tmp/gfa-radius-atlas/radius_atlas.svg`. The same data are available in
`radius_atlas.json`.

- **Rows are source classes.**
- **Columns are target classes.**
- A cell answers: “How far can every function in this row class be dilated while
  remaining in this column class?”
- Gray cells are pairs for which the package has no stored radius.

Source and target cannot be swapped. The two directions can have different
answers.

## Read one pair

For example:

- `sine→sigmoid` has radius
  $\arcsin((e-1)/(e+1))$ and a local proof certificate;
- `sigmoid→sine` has radius $1$ because the whole source class is contained in
  the target.

Hover over a cell to see its direction, value, status, and whether a local
certificate is available.

## Read the status

| Status | Meaning |
|---|---|
| `touch_proven_exact` | The exact boundary contact and global bound have been proved. |
| `closed_form_confirmed` | A closed form has been matched, but this label does not promise a full local proof check. |
| `trivial_containment` | The full source class is contained in the target, so the radius is $1$. |
| `unidentified` | A numerical radius is stored, but no exact formula has been identified. |
| `audit_required` | The record needs mathematical review before use. |

With 28 classes there are 756 possible non-diagonal directions. The current map
contains 702 records, leaving 54 gaps; eight have a local certificate that the
package can check.

## Use it to choose a problem

Filter `radius_atlas.json` for `audit_required`, `unidentified`, or missing
cells. That gives a concrete list of pairs whose exact value or proof is still
open. Start by fixing the direction, drawing the two generator domains, and
looking for the first boundary contact.