# Website → package parity

The package is the local reproduction layer for the Geometric Function Atlas website.
Each scientific webpage action should have one short `gfa` command and a
Python function backed by the same implementation. A separate GUI is out of scope.

| Website capability | Local package interface | State |
|---|---|---|
| Browse/search function families | `gfa generators`, `gfa classes` | **available** |
| Inspect facts, instances, evidence, and verification runs | `gfa verify`, `gfa class-check` | **available** |
| Re-check a supplied counterexample witness | `gfa verify-counterexample` | **available** |
| Verify a function from a closed form or coefficients | `gfa verify` | **available** |
| Search for a violation and certify it | `gfa find-counterexample` | **available** |
| Reproduce generator Taylor coefficients | `gfa coefficients` | **available** |
| Reproduce Fekete–Szegő values and bounds | `gfa fekete-szego` | **available** |
| Query other coefficient bounds and expansions | `gfa coefficient-bound`, `gfa expansion` | planned |
| Reproduce function-domain and coefficient plots | `gfa plot` | **available** |
| Query or recompute directed inclusion radii | `gfa radius` | planned |
| Re-run a stored proof or certificate | `gfa verify-certificate` | planned |
| Compare classes and hierarchy | `gfa compare` | **available** |
| Inspect class application tags | `gfa applications` | planned |
| Inspect papers and reconciliation records | `gfa papers`, `gfa reconciliation` | planned |
| Reproduce Image Lab transformations | `gfa image-lab` | **available** (lab extra) |
| Reproduce Cryptography Lab metrics | `gfa crypto-lab` | **available** (lab extra) |
| Report registry snapshot statistics | `gfa stats` | planned |

## Completion rule

A row is complete only when:

1. the command is simple enough to copy from the webpage;
2. the Python API performs the same scientific operation;
3. a parity test compares it with a frozen website/API result;
4. the output clearly distinguishes a proof, a certified enclosure, a numerical
   screen, and an unresolved result.

The registry database remains a separately versioned snapshot. Snapshot selection,
provenance, and integrity checks may be handled internally; ordinary users should not
need to understand those details to run a command.

## Website panel

Each implemented scientific item should display a small **Run locally** panel,
not a custom launcher or desktop application:

```text
Install once   [macOS/Linux] [Windows]
Reproduce      gfa <task-oriented command>
```

The install buttons copy the commands in `docs/INSTALL.md`. The reproduce button
copies the exact command for that page item. Human-readable output is the default;
`--json` is an optional advanced action.
