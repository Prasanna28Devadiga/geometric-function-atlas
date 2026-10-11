"""Closed, packaged replay contract over every written-paper lane."""
import json
import subprocess
import sys
from dataclasses import replace
from importlib import resources

from jsonschema import Draft202012Validator

from geometric_function_atlas import RadiusStatus, list_radii, replay_radius_certificate


def _validator():
    resource = resources.files("geometric_function_atlas").joinpath("schema/radius-replay.schema.json")
    schema = json.loads(resource.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_all_nineteen_written_paper_lanes_have_closed_replay_envelopes():
    validator = _validator()
    rows = [r for r in list_radii() if r.status is RadiusStatus.PAPER_PROVED_EXACT]
    assert len(rows) == 19
    outcomes = {"proven": 0, "symbolic_replay_only": 0, "not_replayable": 0}
    for row in rows:
        result = replay_radius_certificate(row)
        payload = result.to_dict()
        assert not list(validator.iter_errors(payload)), row.direction
        outcomes[result.status] += 1
        assert payload["direction"] == row.direction
        if result.status == "proven":
            assert payload["global_containment_check"] == "bounded_chain_replayed"
            assert payload["certified"] is True
        else:
            assert payload["global_containment_check"] == "not_mechanized"
            assert payload["certified"] is False
    assert outcomes == {"proven": 19, "symbolic_replay_only": 0, "not_replayable": 0}


def test_replay_failures_are_closed_and_never_inherit_containment_check():
    validator = _validator()
    row = next(r for r in list_radii() if r.certificate)
    cases = [
        replay_radius_certificate(row, candidate="1/2"),
        replay_radius_certificate(row, candidate="garbage("),
        replay_radius_certificate(replace(row, value_exact="1/2")),
        replay_radius_certificate(next(r for r in list_radii() if r.status is RadiusStatus.PAPER_PROVED_EXACT and not r.certificate), candidate="1/2"),
    ]
    for result in cases:
        payload = result.to_dict()
        assert not list(validator.iter_errors(payload)), payload
        assert payload["global_containment_check"] == "not_mechanized"
        assert not result.certified
    for key, value in (("certified", True), ("global_containment_check", "bounded_chain_replayed"), ("novelty_claim", True)):
        bad = {**cases[0].to_dict(), key: value}
        assert list(validator.iter_errors(bad)), key
    assert list(validator.iter_errors({**cases[0].to_dict(), "unexpected": True}))


def test_cli_json_is_same_packaged_contract_for_each_lane():
    validator = _validator()
    rows = [r for r in list_radii() if r.status is RadiusStatus.PAPER_PROVED_EXACT]
    assert len(rows) == 19
    for row in rows:
        run = subprocess.run(
            [sys.executable, "-m", "geometric_function_atlas", "verify-radius-certificate", row.source_class, row.target_class, "--json"],
            capture_output=True, text=True, check=False,
        )
        assert run.returncode == 0, (row.direction, run.stderr)
        payload = json.loads(run.stdout)
        assert not list(validator.iter_errors(payload)), row.direction
        assert payload["direction"] == row.direction
