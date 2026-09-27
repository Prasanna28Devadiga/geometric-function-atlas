"""Read `gfa ... --json` output for the Experimental Mathematics paper examples."""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys


def gfa_json(path, *command):
    """Load a saved JSON file, or run `gfa <command> --json` when no path is given."""
    if path:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)
    if importlib.util.find_spec("geometric_function_atlas"):
        cli = [sys.executable, "-m", "geometric_function_atlas"]
    elif shutil.which("gfa"):
        cli = ["gfa"]
    else:
        sys.exit("gfa is not installed; see the Getting started page")
    result = subprocess.run([*cli, *command, "--json"], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)
