"""Paper proofs and axis recognition remain distinct from replay certificates."""
import json
from collections import Counter
from importlib import resources

import sympy as sp

from geometric_function_atlas import list_radii, radius, replay_radius_certificate
from geometric_function_atlas.radii import recognize_axis_radius

PAPER = {
    'sine->sigmoid': '4.3', 'sine->rational_kr': '4.8(a)',
    'cosh_sqrt->lemniscate': '4.5(a)', 'exponential->sine': '4.5(b)',
    'exponential->bell': '4.5(e)', 'rational_kr->sine': '4.5(c)',
    'bell->sine': '4.5(d)', 'sine->exponential': '4.6(b)',
    'sigmoid->rational_kr': '4.8(b)', 'sine->bell': '4.6(c)',
    'crescent->lemniscate': '4.7(a)', 'sine->tanh': '4.6(a)',
    'starlike->lemniscate': '4.5(h)', 'order_0.5->crescent': '4.7(b)',
    'exponential->lemniscate': '4.5(f)', 'exponential->order_0.5': '4.5(g)',
    'starlike->order_0.75': '4.5(i)', 'crescent->exponential': '4.4(a)',
    'exponential->crescent': '4.4(b)',
}
MISSED = {'nephroid->bell', 'parabolic->rational_kr', 'three_leaf->bell',
          'three_leaf->sigmoid', 'three_leaf->sine', 'three_leaf->tanh'}


def test_paper_theorems_are_marked_without_inventing_machine_replays():
    proved = {r.direction: r for r in list_radii() if r.paper_theorem}
    assert set(proved) == set(PAPER)
    for direction, theorem in PAPER.items():
        row = proved[direction]
        assert row.paper_theorem == f'Theorem {theorem}'
        assert row.to_dict()['evidence_status'] == 'proven_exact_under_declared_assumptions'
        assert row.to_dict()['paper_proof_status'] == 'written_proof'
        assert row.value_exact
        assert row.to_dict()['verification']['success'] is False
    assert len([r for r in proved.values() if r.certificate is not None]) == 8
    assert replay_radius_certificate(radius('crescent', 'exponential')).certified is False
    assert radius('crescent', 'exponential').to_dict()['computational_status'] == 'unresolved'
    assert radius('crescent', 'exponential').value_exact == 'sin(1)'
    assert abs(float(sp.N(sp.sin(1), 18)) - radius('crescent', 'exponential').value_float) < 1e-14


def test_all_written_theorem_values_agree_with_stored_decimals():
    from geometric_function_atlas.radii import _parse_exact_expression
    for direction in PAPER:
        row = radius(*direction.split('->'))
        assert abs(float(sp.N(_parse_exact_expression(row.value_exact), 35)) - row.value_float) < 1e-12


def test_six_axis_equations_are_recognized_not_promoted_to_global_proofs():
    for direction in MISSED:
        source, target = direction.split('->')
        row = radius(source, target)
        assert row.axis_equation
        assert row.paper_theorem is None
        assert row.to_dict()['evidence_status'] == 'unresolved'
        assert abs(recognize_axis_radius(source, target) - row.value_float) < 1e-6


def test_axis_route_agrees_with_every_stored_axis_record():
    rows = [r for r in list_radii() if r.mode in ('axis', 'axis_bisect') and r.status.value not in ('audit_required', 'trivial_containment')]
    assert len(rows) == 409
    mismatches = [(r.direction, recognize_axis_radius(r.source_class, r.target_class), r.value_float)
                  for r in rows if abs(recognize_axis_radius(r.source_class, r.target_class) - r.value_float) >= 1e-6]
    assert mismatches == []


def test_snapshot_is_new_version_and_counts_are_consistent():
    from geometric_function_atlas.radii import RADIUS_SNAPSHOT_ID
    assert RADIUS_SNAPSHOT_ID != 'gft-radius-snapshot:2026.08.09'
    blob = resources.files('geometric_function_atlas').joinpath('data/radii_snapshot.json').read_text()
    snapshot = json.loads(blob)
    assert snapshot['n'] == len(snapshot['radii']) == 702
    assert snapshot['counts'] == dict(Counter(row['status'] for row in snapshot['radii']))
