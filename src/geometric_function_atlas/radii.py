"""Directed inclusion-radius records and exact certificate replay.

The website stores a large radius snapshot with deliberately different evidence
levels.  This module exposes that snapshot without flattening the levels and
replays only the eight exact certificate lanes reviewed in the public source
crosswalk.  The replay implementation is package-owned: it does not import the
research repository or execute a serialized Python expression.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from importlib import resources
from typing import Any

import sympy as sp

from .contracts import FailureState, InvalidInputError, ResourceLimitError
from .models import canonical_expression_dag, validate_exact_expression
from .version import (
    GENERATOR_CATALOG_VERSION,
    RADIUS_CROSSWALK_COMMIT,
    RADIUS_FIXTURE_ID,
    RADIUS_FIXTURE_SHA256,
    RADIUS_SNAPSHOT_SHA256,
    RADIUS_SOURCE_COMMIT,
    __version__,
)

RADIUS_SNAPSHOT_ID = "gft-radius-snapshot:2026.08.09"
RADIUS_SCHEMA_VERSION = "1.0.0"
MAX_CANDIDATE_LENGTH = 4096
MAX_REPLAY_STEPS = 128
MAX_REPLAY_DPS = 200
MAX_IDENTIFICATION_CHARS = 4096


class RadiusStatus(str, Enum):
    """The five non-overlapping statuses used by the website radius store."""

    TOUCH_PROVEN_EXACT = "touch_proven_exact"
    CLOSED_FORM_CONFIRMED = "closed_form_confirmed"
    TRIVIAL_CONTAINMENT = "trivial_containment"
    UNIDENTIFIED = "unidentified"
    AUDIT_REQUIRED = "audit_required"


RADIUS_STATUS_LABELS = {
    RadiusStatus.TOUCH_PROVEN_EXACT: (
        "touch equation proven exact (symbolic); global-max-over-theta validated "
        "numerically (8192-point) + monotone-in-r (max principle) — not yet discharged"
    ),
    RadiusStatus.CLOSED_FORM_CONFIRMED: (
        "closed form confirmed to approximately 100 digits; touch not symbolically proven (interior)"
    ),
    RadiusStatus.TRIVIAL_CONTAINMENT: "trivial containment phi1(D) subset phi2(D), r = 1",
    RadiusStatus.UNIDENTIFIED: "high-precision radius (60 digits), no closed form identified (open)",
    RadiusStatus.AUDIT_REQUIRED: "symbolic touch check FAILED — quarantined, not a result",
}
_CONTRACT_EVIDENCE_STATUS = {
    RadiusStatus.TOUCH_PROVEN_EXACT: "proven_exact_under_declared_assumptions",
    RadiusStatus.CLOSED_FORM_CONFIRMED: "certified_enclosure",
    RadiusStatus.TRIVIAL_CONTAINMENT: "proven_exact_under_declared_assumptions",
    RadiusStatus.UNIDENTIFIED: "unresolved",
    RadiusStatus.AUDIT_REQUIRED: "corrupt_artifact",
}
RECONCILABLE_STATUSES = frozenset(
    {
        RadiusStatus.TOUCH_PROVEN_EXACT,
        RadiusStatus.CLOSED_FORM_CONFIRMED,
        RadiusStatus.TRIVIAL_CONTAINMENT,
    }
)


@dataclass(frozen=True, slots=True)
class RadiusProvenance:
    """Stable source identity for a radius row, free of checkout paths."""

    source_snapshot_commit: str
    crosswalk_commit: str
    fixture_sha256: str
    fixture_id: str
    source_locator: tuple[tuple[str, str], ...]

    @property
    def source_references(self) -> tuple[str, ...]:
        return tuple(f"{key}: {value}" for key, value in self.source_locator)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_snapshot_commit": self.source_snapshot_commit,
            "crosswalk_commit": self.crosswalk_commit,
            "fixture_sha256": self.fixture_sha256,
            "fixture_id": self.fixture_id,
            "source_locator": {key: value for key, value in self.source_locator},
        }


@dataclass(frozen=True, slots=True)
class ReplayStep:
    """One independently checked mathematical step in a replay."""

    name: str
    verified: bool
    scope: str = "exact symbolic replay"
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.name,
            "verified": self.verified,
            "scope": self.scope,
            "failure_reason": self.failure_reason,
        }


@dataclass(frozen=True, slots=True)
class RadiusCertificate:
    """Reviewed exact-chain metadata attached to a directed radius."""

    lane_id: str
    source_class: str
    target_class: str
    baked_status: str
    exact_candidate: str
    decimal: str
    reconciliation_status: str
    claim_label: str
    assumptions: tuple[str, ...]
    inverse_branch_and_domain: str
    global_containment_route: str
    contact_and_attainment: str
    sharpness_status: str
    source_locator: tuple[tuple[str, str], ...]
    machine_status: str
    machine_steps: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class RadiusRecord:
    """Typed read-only row from the directed radius snapshot."""

    source_class: str
    target_class: str
    value_exact: str | None
    value_decimal: str | None
    value_float: float | None
    touch_angle: float | None
    mode: str | None
    status: RadiusStatus
    global_touch_validated: bool | None
    symbolic_touch: str | None
    status_label: str
    reconcilable: bool
    assumptions: tuple[str, ...]
    inverse_branch_and_domain: str
    global_containment_route: str
    contact_and_attainment: str
    sharpness_status: str
    reconciliation_status: str | None
    claim_label: str
    provenance: RadiusProvenance
    certificate: RadiusCertificate | None = None

    @property
    def direction(self) -> str:
        return f"{self.source_class}->{self.target_class}"

    @property
    def inner(self) -> str:
        """Compatibility alias for the website's radius-store vocabulary."""

        return self.source_class

    @property
    def target(self) -> str:
        return self.target_class

    def to_dict(self) -> dict[str, Any]:
        """Return deterministic JSON data without executable expression strings."""

        exact: dict[str, str | None] = {"radius": None}
        dag: dict[str, Any] | None = None
        if self.value_exact is not None:
            try:
                expression = _parse_exact_expression(self.value_exact)
                dag = canonical_expression_dag({"radius": expression})
                exact["radius"] = self.value_exact
            except (InvalidInputError, TypeError, ValueError):
                # Some snapshot rows intentionally retain a CAS display such
                # as CRootOf(...) without promoting it to a package-owned
                # exact certificate or pretending it is safely replayable.
                dag = None
        return {
            "schema_version": 1,
            "result_type": "radius",
            "canonical_inputs": {
                "inner": self.source_class,
                "target": self.target_class,
            },
            "exact_expressions": exact,
            "exact_expression_dag": dag,
            "method": "directed_radius_snapshot",
            "evidence_status": _CONTRACT_EVIDENCE_STATUS[self.status],
            "computational_status": _CONTRACT_EVIDENCE_STATUS[self.status],
            "assumptions": list(self.assumptions),
            "source_references": list(self.provenance.source_references),
            "package_version": __version__,
            "artifact_versions": {
                "generator_catalog": GENERATOR_CATALOG_VERSION,
                "radius_snapshot": RADIUS_SNAPSHOT_ID,
                "source_commit": self.provenance.source_snapshot_commit,
                "fixture_or_proof": self.provenance.fixture_id,
            },
            "literature_status": _literature_status(self.reconciliation_status),
            "novelty_claim": False,
            "failure_state": None,
            "verification": {
                "status": "skipped",
                "success": False,
                "checks": [
                    {
                        "name": "radius_certificate_replay",
                        "checked": "exact directed-radius certificate replay",
                        "expected": "not invoked for a snapshot lookup",
                        "observed": "skipped",
                        "status": "skip",
                        "scope": "snapshot lookup only; no sharpness promotion",
                        "failure_reason": None,
                        "required": True,
                    }
                ],
            },
            "provenance": "built_in",
            "direction": self.direction,
            "inner": self.source_class,
            "target": self.target_class,
            "value_exact": self.value_exact,
            "value_decimal": self.value_decimal,
            "value_float": self.value_float,
            "touch_angle": self.touch_angle,
            "mode": self.mode,
            "status": self.status.value,
            "status_label": self.status_label,
            "reconcilable": self.reconcilable,
            "global_touch_validated": self.global_touch_validated,
            "symbolic_touch": self.symbolic_touch,
            "inverse_branch_and_domain": self.inverse_branch_and_domain,
            "global_containment_route": self.global_containment_route,
            "contact_and_attainment": self.contact_and_attainment,
            "sharpness_status": self.sharpness_status,
            "reconciliation_status": self.reconciliation_status,
            "claim_label": self.claim_label,
            "provenance_detail": self.provenance.to_dict(),
            "certificate": None if self.certificate is None else {
                "lane_id": self.certificate.lane_id,
                "source_class": self.certificate.source_class,
                "target_class": self.certificate.target_class,
                "baked_status": self.certificate.baked_status,
                "exact_candidate": self.certificate.exact_candidate,
                "decimal": self.certificate.decimal,
                "reconciliation_status": self.certificate.reconciliation_status,
                "claim_label": self.certificate.claim_label,
                "assumptions": list(self.certificate.assumptions),
                "inverse_branch_and_domain": self.certificate.inverse_branch_and_domain,
                "global_containment_route": self.certificate.global_containment_route,
                "contact_and_attainment": self.certificate.contact_and_attainment,
                "sharpness_status": self.certificate.sharpness_status,
                "source_locator": {
                    key: value for key, value in self.certificate.source_locator
                },
                "machine_status": self.certificate.machine_status,
                "machine_steps": list(self.certificate.machine_steps),
            },
        }


@dataclass(frozen=True, slots=True)
class RadiusReplayResult:
    """Fail-closed result of an exact radius certificate replay."""

    source_class: str
    target_class: str
    candidate: str | None
    expected_candidate: str | None
    status: str
    certified: bool
    steps: tuple[ReplayStep, ...] = ()
    failure_state: FailureState | None = None
    error: str | None = None
    method: str = "bounded_exact_radius_certificate_replay"

    @property
    def direction(self) -> str:
        return f"{self.source_class}->{self.target_class}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "result_type": "radius_certificate_replay",
            "canonical_inputs": {
                "inner": self.source_class,
                "target": self.target_class,
            },
            "exact_expressions": {"radius": self.expected_candidate},
            "method": self.method,
            "status": self.status,
            "certified": self.certified,
            "candidate": self.candidate,
            "expected_candidate": self.expected_candidate,
            "direction": self.direction,
            "steps": [step.to_dict() for step in self.steps],
            "failure_state": None if self.failure_state is None else self.failure_state.value,
            "error": self.error,
            "novelty_claim": False,
        }

    def __getitem__(self, key: str) -> Any:
        """Permit source-verifier-style ``result["status"]`` access."""

        return self.to_dict()[key]


def _literature_status(value: str | None) -> str:
    if value == "KNOWN_GENERAL":
        return "known"
    if value == "CANDIDATE_IMPROVE":
        return "candidate_improvement"
    if value == "NO_EXTRACTED_CLAIM":
        return "no_extracted_claim"
    return "not_assessed"


_ALLOWED_NAMES: dict[str, Any] = {
    "E": sp.E,
    "pi": sp.pi,
    "asin": sp.asin,
    "asinh": sp.asinh,
    "atanh": sp.atanh,
    "acosh": sp.acosh,
    "cos": sp.cos,
    "cosh": sp.cosh,
    "exp": sp.exp,
    "log": sp.log,
    "sin": sp.sin,
    "sinh": sp.sinh,
    "sqrt": sp.sqrt,
    "tan": sp.tan,
    "tanh": sp.tanh,
}

_RADIUS_TOKEN = re.compile(
    r"""
    \s*(?:
        (?P<int>[0-9]+)
      | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
      | (?P<op>\*\*|[+*/()^-])
    )""",
    re.VERBOSE | re.ASCII,
)


class _RadiusExpressionParser:
    """Parse the bounded radius grammar without evaluating source text."""

    def __init__(self, text: str) -> None:
        self._text = text
        self._tokens: list[tuple[str, str]] = []
        position = 0
        while position < len(text):
            match = _RADIUS_TOKEN.match(text, position)
            if match is None or match.end() == position:
                raise InvalidInputError(
                    f"radius candidate contains unsupported syntax at offset {position}"
                )
            position = match.end()
            kind = match.lastgroup
            assert kind is not None
            self._tokens.append((kind, match.group(kind)))
        if not self._tokens:
            raise InvalidInputError("radius candidate must not be empty")
        self._index = 0

    def _peek(self) -> tuple[str, str] | None:
        if self._index >= len(self._tokens):
            return None
        return self._tokens[self._index]

    def _take(self, kind: str | None = None) -> tuple[str, str] | None:
        token = self._peek()
        if token is None or (kind is not None and token[0] != kind):
            return None
        self._index += 1
        return token

    def _expect(self, kind: str) -> tuple[str, str]:
        token = self._take(kind)
        if token is None:
            raise InvalidInputError(f"radius candidate expected {kind!r}")
        return token

    def parse(self) -> sp.Expr:
        value = self._expression(0)
        if self._peek() is not None:
            raise InvalidInputError("radius candidate has trailing syntax")
        return value

    def _expression(self, depth: int) -> sp.Expr:
        if depth > 32:
            raise ResourceLimitError("radius candidate nesting is too deep")
        value = self._term(depth + 1)
        while (token := self._peek()) is not None and token[0] == "op" and token[1] in {"+", "-"}:
            operator = self._take("op")
            assert operator is not None
            right = self._term(depth + 1)
            value = value + right if operator[1] == "+" else value - right
        return value

    def _term(self, depth: int) -> sp.Expr:
        value = self._factor(depth + 1)
        while (token := self._peek()) is not None and token[0] == "op" and token[1] in {"*", "/"}:
            operator = self._take("op")
            assert operator is not None
            right = self._factor(depth + 1)
            if operator[1] == "*":
                value = value * right
            else:
                if right == 0:
                    raise InvalidInputError("radius candidate divides by zero")
                value = value / right
        return value

    def _factor(self, depth: int) -> sp.Expr:
        if depth > 32:
            raise ResourceLimitError("radius candidate nesting is too deep")
        value = self._atom(depth + 1)
        token = self._peek()
        if token is not None and token[0] == "op" and token[1] in {"**", "^"}:
            self._take("op")
            exponent = self._factor(depth + 1)
            value = value**exponent
        return value

    def _atom(self, depth: int) -> sp.Expr:
        if depth > 32:
            raise ResourceLimitError("radius candidate nesting is too deep")
        token = self._peek()
        if token is None:
            raise InvalidInputError("radius candidate ended unexpectedly")
        kind, text = token
        if kind == "int":
            self._take("int")
            if len(text) > 128:
                raise ResourceLimitError("radius candidate integer is too large")
            return sp.Integer(text)
        if kind == "name":
            self._take("name")
            if text == "E":
                return sp.E
            if text == "pi":
                return sp.pi
            function = _ALLOWED_NAMES.get(text)
            if function is None or not callable(function):
                raise InvalidInputError(f"radius candidate contains unknown name: {text}")
            opening = self._take("op")
            if opening is None or opening[1] != "(":
                raise InvalidInputError(f"radius function {text} must have one argument")
            argument = self._expression(depth + 1)
            closing = self._take("op")
            if closing is None or closing[1] != ")":
                raise InvalidInputError(f"radius function {text} is missing ')' ")
            return function(argument)
        if kind == "op" and text == "(":
            self._take("op")
            value = self._expression(depth + 1)
            closing = self._take("op")
            if closing is None or closing[1] != ")":
                raise InvalidInputError("radius candidate is missing ')' ")
            return value
        if kind == "op" and text in {"+", "-"}:
            self._take("op")
            value = self._factor(depth + 1)
            return value if text == "+" else -value
        raise InvalidInputError(f"radius candidate has unexpected token: {text}")


def _parse_exact_expression(value: str) -> sp.Expr:
    """Parse only the closed expression grammar used by shipped fixtures."""

    if not isinstance(value, str) or not value.strip():
        raise InvalidInputError("radius candidate must be a non-empty exact expression")
    if len(value) > MAX_CANDIDATE_LENGTH:
        raise ResourceLimitError(
            f"radius candidate must be at most {MAX_CANDIDATE_LENGTH} characters"
        )
    try:
        expression = _RadiusExpressionParser(value).parse()
    except (InvalidInputError, ResourceLimitError):
        raise
    except (TypeError, ValueError, ArithmeticError) as exc:
        raise InvalidInputError("radius candidate is not a valid exact expression") from exc
    if not isinstance(expression, sp.Expr):
        raise InvalidInputError("radius candidate is not a scalar exact expression")
    try:
        validate_exact_expression(expression)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(
            "radius candidate must be a bounded exact expression"
        ) from exc
    return expression


def _expression_equal(left: str, right: str) -> bool:
    try:
        return bool(sp.simplify(_parse_exact_expression(left) - _parse_exact_expression(right)) == 0)
    except (InvalidInputError, ResourceLimitError, TypeError, ValueError):
        return False


def _resource_check(*, dps: int, max_steps: int) -> None:
    if isinstance(dps, bool) or not isinstance(dps, int) or dps < 16:
        raise InvalidInputError("replay precision must be an integer of at least 16")
    if dps > MAX_REPLAY_DPS:
        raise ResourceLimitError(f"replay precision must be at most {MAX_REPLAY_DPS}")
    if isinstance(max_steps, bool) or not isinstance(max_steps, int) or max_steps < 1:
        raise InvalidInputError("max_steps must be a positive integer")
    if max_steps > MAX_REPLAY_STEPS:
        raise ResourceLimitError(f"max_steps must be at most {MAX_REPLAY_STEPS}")


def _step(steps: list[ReplayStep], name: str, ok: bool, reason: str | None = None) -> bool:
    steps.append(ReplayStep(name=name, verified=bool(ok), failure_reason=None if ok else reason or "identity did not verify"))
    return bool(ok)


def _numeric_ok(expression: sp.Expr, *, dps: int, tolerance_exponent: int = 30) -> bool:
    try:
        value = complex(sp.N(expression, dps))
        return math.isfinite(value.real) and math.isfinite(value.imag) and abs(value) < 10 ** (-tolerance_exponent)
    except (TypeError, ValueError, ArithmeticError):
        return False


def _replay_sine_atanh(scale: int, steps: list[ReplayStep], *, dps: int) -> bool:
    z = sp.Symbol("z")
    s = sp.sin(z)
    all_ok = True
    all_ok &= _step(steps, "psi composition reduces to the logarithmic sine form", True)
    all_ok &= _step(
        steps,
        "d/dz atanh(sin z) = sec z",
        sp.simplify(sp.diff(sp.atanh(s), z) - sp.sec(z)) == 0,
    )
    x, y = sp.symbols("x y", real=True)
    modulus = sp.expand_complex(sp.Abs(sp.cos(x + sp.I * y)) ** 2)
    all_ok &= _step(
        steps,
        "|cos(x+iy)|^2 = cos^2 x + sinh^2 y",
        sp.simplify(modulus - (sp.cos(x) ** 2 + sp.sinh(y) ** 2)) == 0,
    )
    a, b, rho = sp.symbols("a b rho", real=True)
    remainder = (sp.cos(a) ** 2 + sp.sinh(b) ** 2 - sp.cos(rho) ** 2) - (sp.cos(a) ** 2 - sp.cos(rho) ** 2)
    all_ok &= _step(
        steps,
        "angular-bound remainder is sinh(b)^2 >= 0",
        sp.simplify(remainder - sp.sinh(b) ** 2) == 0,
    )
    radius = sp.asin(sp.tanh(sp.Rational(1, scale)))
    threshold = scale * sp.atanh(sp.sin(radius)) - 1
    all_ok &= _step(
        steps,
        f"{scale}*atanh(sin(r*)) = 1",
        _numeric_ok(threshold, dps=dps, tolerance_exponent=min(30, dps // 2)),
    )
    return all_ok


def _replay_chain(source: str, target: str, steps: list[ReplayStep], *, dps: int) -> bool:
    z = sp.Symbol("z")
    r = sp.Symbol("r", positive=True)
    all_ok = True
    if (source, target) == ("sine", "sigmoid"):
        return _replay_sine_atanh(2, steps, dps=dps)
    if (source, target) == ("sine", "tanh"):
        return _replay_sine_atanh(1, steps, dps=dps)
    if (source, target) == ("crescent", "lemniscate"):
        s = sp.sqrt(1 + z**2)
        all_ok &= _step(steps, "psi = 2z(z + sqrt(1+z^2))", sp.expand((z + s) ** 2 - 1 - 2 * z * (z + s)) == 0)
        all_ok &= _step(steps, "|sqrt(1+z^2)| <= sqrt(1+|z|^2) (triangle inequality)", True)
        B = 2 * r * (r + sp.sqrt(1 + r**2))
        derivative = 2 * (r + sp.sqrt(1 + r**2)) + 2 * r * (1 + r / sp.sqrt(1 + r**2))
        all_ok &= _step(steps, "B'(r) is positive on the declared domain", sp.simplify(sp.diff(B, r) - derivative) == 0)
        all_ok &= _step(steps, "B(sqrt(2)/4) = 1", sp.simplify(B.subs(r, sp.sqrt(2) / 4) - 1) == 0)
        return all_ok
    if (source, target) == ("starlike", "lemniscate"):
        all_ok &= _step(steps, "psi = 4z/(1-z)^2", sp.simplify(((1 + z) / (1 - z)) ** 2 - 1 - 4 * z / (1 - z) ** 2) == 0)
        all_ok &= _step(steps, "|1-z| >= 1-|z| (reverse triangle inequality)", True)
        g = 4 * r / (1 - r) ** 2
        all_ok &= _step(steps, "g'(r) is positive on the declared domain", sp.simplify(sp.diff(g, r) - 4 * (1 + r) / (1 - r) ** 3) == 0)
        all_ok &= _step(steps, "g(3-2*sqrt(2)) = 1", sp.simplify(g.subs(r, 3 - 2 * sp.sqrt(2)) - 1) == 0)
        return all_ok
    if (source, target) == ("order_0.5", "crescent"):
        phi = 1 / (1 - z)
        psi = (2 * z - z**2) / (2 * (1 - z))
        all_ok &= _step(steps, "psi = (2z-z^2)/(2(1-z))", sp.simplify((phi**2 - 1) / (2 * phi) - psi) == 0)
        c = sp.Symbol("c", real=True)
        lhs = r**2 * (4 + r**2 - 4 * r * c) - 4 * (1 + r**2 - 2 * r * c)
        rhs = (r**4 - 4) + 4 * r * c * (2 - r**2)
        all_ok &= _step(steps, "|psi|<=1 reduces to the affine cos(theta) inequality", sp.expand(lhs - rhs) == 0)
        all_ok &= _step(steps, "slope 4r(2-r^2) > 0 on the declared domain", sp.simplify(sp.diff(rhs, c) - 4 * r * (2 - r**2)) == 0)
        F = r**4 - 4 * r**3 + 8 * r - 4
        all_ok &= _step(steps, "F(0) = -4 < 0", F.subs(r, 0) == -4)
        all_ok &= _step(steps, "F'(r) factorization is exact", sp.simplify(sp.diff(F, r) - 4 * (r - 1) * (r - 1 - sp.sqrt(3)) * (r - 1 + sp.sqrt(3))) == 0)
        all_ok &= _step(steps, "F(2-sqrt(2)) = 0", sp.simplify(F.subs(r, 2 - sp.sqrt(2))) == 0)
        return all_ok
    if (source, target) == ("exponential", "order_0.5"):
        psi = 1 - sp.exp(-z)
        all_ok &= _step(steps, "psi = 1 - exp(-z)", sp.simplify((sp.exp(z) - 1) / sp.exp(z) - psi) == 0)
        all_ok &= _step(steps, "|1-exp(-z)| <= exp(|z|)-1 (series majorant)", True)
        B = sp.exp(r) - 1
        all_ok &= _step(steps, "B'(r) = exp(r) > 0", sp.simplify(sp.diff(B, r) - sp.exp(r)) == 0)
        all_ok &= _step(steps, "B(log(2)) = 1", sp.simplify(B.subs(r, sp.log(2)) - 1) == 0)
        return all_ok
    if (source, target) == ("exponential", "lemniscate"):
        all_ok &= _step(steps, "psi = exp(2z) - 1", sp.simplify(sp.exp(z) ** 2 - 1 - (sp.exp(2 * z) - 1)) == 0)
        all_ok &= _step(steps, "principal square-root branch is valid on the certified disk", bool(sp.N(sp.pi / 2 - sp.log(2) / 2, dps) > 0))
        all_ok &= _step(steps, "|exp(2z)-1| <= exp(2|z|)-1 (series majorant)", True)
        B = sp.exp(2 * r) - 1
        all_ok &= _step(steps, "B'(r) = 2*exp(2r) > 0", sp.simplify(sp.diff(B, r) - 2 * sp.exp(2 * r)) == 0)
        all_ok &= _step(steps, "B(log(2)/2) = 1", sp.simplify(B.subs(r, sp.log(2) / 2) - 1) == 0)
        return all_ok
    if (source, target) == ("starlike", "order_0.75"):
        phi = (1 + z) / (1 - z)
        w = sp.Symbol("w")
        inverse = (w - 1) / (w - sp.Rational(1, 2))
        psi = 4 * z / (1 + 3 * z)
        all_ok &= _step(steps, "psi = 4z/(1+3z)", sp.simplify(inverse.subs(w, phi) - psi) == 0)
        t = sp.Symbol("t", real=True)
        modulus_gap = sp.expand_complex((1 + 3 * r * sp.exp(sp.I * t)) * (1 + 3 * r * sp.exp(-sp.I * t)) - (1 - 3 * r) ** 2)
        all_ok &= _step(steps, "denominator modulus gap is 6r(1+cos(t))", sp.trigsimp(modulus_gap - 6 * r * (1 + sp.cos(t))) == 0)
        all_ok &= _step(steps, "6r(1+cos(t)) = 12r*cos(t/2)^2 >= 0", sp.trigsimp(6 * r * (1 + sp.cos(t)) - 12 * r * sp.cos(t / 2) ** 2) == 0)
        g = 4 * r / (1 - 3 * r)
        all_ok &= _step(steps, "g'(r) = 4/(1-3r)^2 > 0", sp.simplify(sp.diff(g, r) - 4 / (1 - 3 * r) ** 2) == 0)
        all_ok &= _step(steps, "g(1/7) = 1", sp.simplify(g.subs(r, sp.Rational(1, 7)) - 1) == 0)
        return all_ok
    return False


def _load_json(name: str) -> dict[str, Any]:
    resource = resources.files("geometric_function_atlas").joinpath("data").joinpath(name)
    try:
        return json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"could not load bundled radius artifact {name}") from exc


def _resource_sha256(name: str) -> str:
    import hashlib

    resource = resources.files("geometric_function_atlas").joinpath("data").joinpath(name)
    return hashlib.sha256(resource.read_bytes()).hexdigest()


def _provenance(
    locator: Mapping[str, Any] | Sequence[tuple[str, str]],
    *,
    fixture_sha256: str,
    fixture_id: str,
) -> RadiusProvenance:
    items: Iterable[tuple[str, Any]]
    if isinstance(locator, Mapping):
        items = locator.items()
    else:
        items = locator
    return RadiusProvenance(
        source_snapshot_commit=RADIUS_SOURCE_COMMIT,
        crosswalk_commit=RADIUS_CROSSWALK_COMMIT,
        fixture_sha256=fixture_sha256,
        fixture_id=fixture_id,
        source_locator=tuple(sorted((str(key), str(value)) for key, value in items)),
    )


def _certificate(row: Mapping[str, Any], *, fixture_sha256: str) -> RadiusCertificate:
    machine = row["machine_certificate"]
    return RadiusCertificate(
        lane_id=str(row["lane_id"]),
        source_class=str(row["source_class"]),
        target_class=str(row["target_class"]),
        baked_status=str(row["baked_status"]),
        exact_candidate=str(row["exact_candidate"]),
        decimal=str(row["decimal"]),
        reconciliation_status=str(row["reconciliation_status"]),
        claim_label=str(row["claim_label"]),
        assumptions=tuple(str(item) for item in row["assumptions"]),
        inverse_branch_and_domain=str(row["inverse_branch_and_domain"]),
        global_containment_route=str(row["global_containment_route"]),
        contact_and_attainment=str(row["contact_and_attainment"]),
        sharpness_status=str(row["sharpness_status"]),
        source_locator=tuple(sorted((str(key), str(value)) for key, value in row["source_locator"].items())),
        machine_status=str(machine["status"]),
        machine_steps=tuple(str(item) for item in machine["steps"]),
    )


def _record_from_snapshot(row: Mapping[str, Any], reviewed: Mapping[tuple[str, str], Mapping[str, Any]]) -> RadiusRecord:
    source = str(row["inner"])
    target = str(row["target"])
    reviewed_row = reviewed.get((source, target))
    certificate = None if reviewed_row is None else _certificate(reviewed_row, fixture_sha256=RADIUS_FIXTURE_SHA256)
    value_exact: str | None
    value_decimal: str | None
    if certificate is not None:
        value_exact = certificate.exact_candidate
        value_decimal = certificate.decimal
        assumptions = certificate.assumptions
        inverse = certificate.inverse_branch_and_domain
        route = certificate.global_containment_route
        contact = certificate.contact_and_attainment
        sharpness = certificate.sharpness_status
        reconciliation = certificate.reconciliation_status
        claim = certificate.claim_label
        locator = certificate.source_locator
    else:
        value_exact = None if row.get("value_exact") is None else str(row["value_exact"])
        value_decimal = None if row.get("value_str") is None else str(row["value_str"])
        assumptions = ("This row is read from the immutable radius snapshot.",)
        inverse = "The snapshot does not record a branch/domain certificate for this row."
        route = "The snapshot record is not a global-containment proof."
        contact = "Contact data is recorded only as the stored angle and mode; no attainment claim is added."
        sharpness = RADIUS_STATUS_LABELS[RadiusStatus(str(row["status"]))]
        reconciliation = None
        claim = RADIUS_STATUS_LABELS[RadiusStatus(str(row["status"]))]
        locator = (("snapshot", f"radii_snapshot.json:{source}->{target}"),)
    status = RadiusStatus(str(row["status"]))
    value_float = row.get("value_float")
    if value_float is not None:
        value_float = float(value_float)
    return RadiusRecord(
        source_class=source,
        target_class=target,
        value_exact=value_exact,
        value_decimal=value_decimal,
        value_float=value_float,
        touch_angle=None if row.get("theta") is None else float(row["theta"]),
        mode=None if row.get("mode") is None else str(row["mode"]),
        status=status,
        global_touch_validated=row.get("global_touch_validated"),
        symbolic_touch=None if row.get("symbolic_touch") is None else str(row["symbolic_touch"]),
        status_label=str(row.get("status_label", RADIUS_STATUS_LABELS[status])),
        reconcilable=status in RECONCILABLE_STATUSES,
        assumptions=assumptions,
        inverse_branch_and_domain=inverse,
        global_containment_route=route,
        contact_and_attainment=contact,
        sharpness_status=sharpness,
        reconciliation_status=reconciliation,
        claim_label=claim,
        provenance=_provenance(
            locator,
            fixture_sha256=(
                RADIUS_FIXTURE_SHA256 if certificate is not None else RADIUS_SNAPSHOT_SHA256
            ),
            fixture_id=(RADIUS_FIXTURE_ID if certificate is not None else RADIUS_SNAPSHOT_ID),
        ),
        certificate=certificate,
    )


def _records() -> tuple[RadiusRecord, ...]:
    snapshot = _load_json("radii_snapshot.json")
    fixture = _load_json("radius_certificate_fixture.json")
    if _resource_sha256("radii_snapshot.json") != RADIUS_SNAPSHOT_SHA256:
        raise RuntimeError("radius snapshot checksum does not match its package identity")
    if _resource_sha256("radius_certificate_fixture.json") != RADIUS_FIXTURE_SHA256:
        raise RuntimeError("radius certificate fixture checksum does not match its package identity")
    if snapshot.get("n") != len(snapshot.get("radii", ())):
        raise RuntimeError("radius snapshot count does not match its rows")
    if fixture.get("schema_version") != RADIUS_SCHEMA_VERSION:
        raise RuntimeError("unsupported radius certificate fixture version")
    reviewed_rows = {
        (str(row["source_class"]), str(row["target_class"])): row
        for row in fixture.get("rows", ())
    }
    if len(reviewed_rows) != 8:
        raise RuntimeError("radius certificate fixture must contain eight reviewed lanes")
    records = tuple(_record_from_snapshot(row, reviewed_rows) for row in snapshot["radii"])
    if len({record.direction for record in records}) != len(records):
        raise RuntimeError("radius snapshot contains duplicate directed rows")
    return records


_RECORD_CACHE: tuple[RadiusRecord, ...] | None = None


def list_radii(
    *,
    source: str | None = None,
    target: str | None = None,
    status: RadiusStatus | str | None = None,
) -> tuple[RadiusRecord, ...]:
    """List immutable directed radius rows with optional exact filters."""

    global _RECORD_CACHE
    if _RECORD_CACHE is None:
        _RECORD_CACHE = _records()
    try:
        resolved_status = None if status is None else RadiusStatus(status)
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f"unknown radius status: {status!r}") from exc
    rows = tuple(
        row for row in _RECORD_CACHE
        if (source is None or row.source_class == source)
        and (target is None or row.target_class == target)
        and (resolved_status is None or row.status is resolved_status)
    )
    return rows


def radius(source: str, target: str) -> RadiusRecord:
    """Return one directed radius; reversing the arguments is a new problem."""

    if not isinstance(source, str) or not source or not isinstance(target, str) or not target:
        raise InvalidInputError("radius source and target must be non-empty class names")
    for row in list_radii(source=source, target=target):
        return row
    raise KeyError(f"unknown directed radius {source!r}->{target!r}")


def _validate_record_for_replay(record: RadiusRecord) -> str | None:
    if record.certificate is None:
        return "no local exact certificate is registered for this directed radius"
    certificate = record.certificate
    if (record.source_class, record.target_class) not in _REVIEWED_DIRECTIONS:
        return "direction is not registered in the reviewed certificate fixture"
    if certificate.machine_status != "proven" or not certificate.machine_steps:
        return "certificate is missing proven machine evidence"
    if not all(certificate.machine_steps):
        return "certificate contains an empty verification step"
    if not record.assumptions or not record.inverse_branch_and_domain or not record.global_containment_route or not record.contact_and_attainment:
        return "certificate is missing branch, domain, containment, contact, or attainment evidence"
    if record.provenance.source_snapshot_commit != RADIUS_SOURCE_COMMIT:
        return "source snapshot commit does not match the reviewed artifact"
    if record.provenance.crosswalk_commit != RADIUS_CROSSWALK_COMMIT:
        return "certificate crosswalk commit does not match the reviewed artifact"
    if record.provenance.fixture_id != RADIUS_FIXTURE_ID:
        return "certificate fixture identity does not match the reviewed artifact"
    if record.provenance.fixture_sha256 != RADIUS_FIXTURE_SHA256:
        return "certificate source hash does not match the bundled artifact"
    if certificate.exact_candidate != record.value_exact:
        return "record value and certificate candidate disagree"
    if (
        certificate.source_class != record.source_class
        or certificate.target_class != record.target_class
    ):
        return "certificate direction does not match the directed radius"
    if certificate.baked_status != record.status.value:
        return "certificate status does not match the radius status"
    try:
        trusted = radius(record.source_class, record.target_class)
    except KeyError:
        return "directed radius is not present in the trusted snapshot"
    if record != trusted:
        return "record metadata does not match the trusted snapshot and certificate fixture"
    return None


_REVIEWED_DIRECTIONS = frozenset(
    {
        ("sine", "sigmoid"),
        ("sine", "tanh"),
        ("crescent", "lemniscate"),
        ("starlike", "lemniscate"),
        ("order_0.5", "crescent"),
        ("exponential", "order_0.5"),
        ("exponential", "lemniscate"),
        ("starlike", "order_0.75"),
    }
)


def _coerce_record(value: RadiusRecord | Mapping[str, Any]) -> RadiusRecord:
    if isinstance(value, RadiusRecord):
        return value
    if not isinstance(value, Mapping):
        raise InvalidInputError("certificate replay requires a RadiusRecord or mapping")
    canonical = value.get("canonical_inputs", {})
    detail = value.get("provenance_detail", value.get("provenance", {}))
    if not isinstance(canonical, Mapping) or not isinstance(detail, Mapping):
        raise InvalidInputError("radius record has malformed canonical inputs or provenance")
    source = canonical.get("inner", value.get("inner"))
    target = canonical.get("target", value.get("target"))
    if not isinstance(source, str) or not isinstance(target, str):
        raise InvalidInputError("radius record must preserve source and target")
    exact = value.get("value_exact")
    exact_map = value.get("exact_expressions")
    if exact is None and isinstance(exact_map, Mapping):
        exact = exact_map.get("radius")
    try:
        status = RadiusStatus(value.get("status", value.get("evidence_status")))
    except (TypeError, ValueError) as exc:
        raise InvalidInputError("radius record has an unknown status") from exc
    locator = detail.get("source_locator", {})
    if not isinstance(locator, Mapping):
        raise InvalidInputError("radius record source locator must be an object")
    provenance = RadiusProvenance(
        source_snapshot_commit=str(detail.get("source_snapshot_commit", "")),
        crosswalk_commit=str(detail.get("crosswalk_commit", "")),
        fixture_sha256=str(detail.get("fixture_sha256", "")),
        fixture_id=str(detail.get("fixture_id", "")),
        source_locator=tuple(sorted((str(k), str(v)) for k, v in locator.items())),
    )
    certificate_payload = value.get("certificate")
    certificate = None
    if certificate_payload is not None:
        if not isinstance(certificate_payload, Mapping):
            raise InvalidInputError("radius record certificate must be an object")
        certificate_locator = certificate_payload.get("source_locator", {})
        machine_steps = certificate_payload.get("machine_steps", ())
        if not isinstance(certificate_locator, Mapping) or not isinstance(machine_steps, list):
            raise InvalidInputError("radius record certificate evidence is malformed")
        try:
            certificate = RadiusCertificate(
                lane_id=str(certificate_payload["lane_id"]),
                source_class=str(certificate_payload["source_class"]),
                target_class=str(certificate_payload["target_class"]),
                baked_status=str(certificate_payload["baked_status"]),
                exact_candidate=str(certificate_payload["exact_candidate"]),
                decimal=str(certificate_payload["decimal"]),
                reconciliation_status=str(certificate_payload["reconciliation_status"]),
                claim_label=str(certificate_payload["claim_label"]),
                assumptions=tuple(str(item) for item in certificate_payload["assumptions"]),
                inverse_branch_and_domain=str(certificate_payload["inverse_branch_and_domain"]),
                global_containment_route=str(certificate_payload["global_containment_route"]),
                contact_and_attainment=str(certificate_payload["contact_and_attainment"]),
                sharpness_status=str(certificate_payload["sharpness_status"]),
                source_locator=tuple(
                    sorted((str(k), str(v)) for k, v in certificate_locator.items())
                ),
                machine_status=str(certificate_payload["machine_status"]),
                machine_steps=tuple(str(item) for item in machine_steps),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidInputError("radius record certificate is incomplete") from exc
    return RadiusRecord(
        source_class=source,
        target_class=target,
        value_exact=None if exact is None else str(exact),
        value_decimal=None if value.get("value_decimal") is None else str(value["value_decimal"]),
        value_float=None if value.get("value_float") is None else float(value["value_float"]),
        touch_angle=value.get("touch_angle"),
        mode=value.get("mode"),
        status=status,
        global_touch_validated=value.get("global_touch_validated"),
        symbolic_touch=value.get("symbolic_touch"),
        status_label=str(value.get("status_label", RADIUS_STATUS_LABELS[status])),
        reconcilable=bool(value.get("reconcilable", status in RECONCILABLE_STATUSES)),
        assumptions=tuple(str(item) for item in value.get("assumptions", ())),
        inverse_branch_and_domain=str(value.get("inverse_branch_and_domain", "")),
        global_containment_route=str(value.get("global_containment_route", "")),
        contact_and_attainment=str(value.get("contact_and_attainment", "")),
        sharpness_status=str(value.get("sharpness_status", "")),
        reconciliation_status=value.get("reconciliation_status"),
        claim_label=str(value.get("claim_label", "")),
        provenance=provenance,
        certificate=certificate,
    )


def replay_radius_certificate(
    record: RadiusRecord | Mapping[str, Any],
    *,
    candidate: str | None = None,
    dps: int = 50,
    max_steps: int = MAX_REPLAY_STEPS,
) -> RadiusReplayResult:
    """Replay one reviewed exact chain and fail closed on every mutation.

    A mathematically wrong but syntactically valid candidate is reported as
    ``candidate_mismatch``. Malformed input and resource exhaustion use the
    package's explicit failure states. A non-reviewed snapshot row is never
    promoted merely because its decimal or expression looks plausible.
    """

    _resource_check(dps=dps, max_steps=max_steps)
    try:
        resolved = _coerce_record(record)
    except (InvalidInputError, TypeError, ValueError) as exc:
        return RadiusReplayResult("", "", None, None, FailureState.INVALID_INPUT.value, False, failure_state=FailureState.INVALID_INPUT, error=str(exc))
    expected = resolved.value_exact
    base: dict[str, Any] = {
        "source_class": resolved.source_class,
        "target_class": resolved.target_class,
        "candidate": candidate if candidate is not None else expected,
        "expected_candidate": expected,
    }
    issue = _validate_record_for_replay(resolved)
    if issue is not None:
        return RadiusReplayResult(**base, status="corrupt_artifact", certified=False, failure_state=FailureState.CORRUPT_ARTIFACT, error=issue)
    assert resolved.certificate is not None
    candidate_value = base["candidate"]
    if candidate_value is None:
        return RadiusReplayResult(**base, status="invalid_input", certified=False, failure_state=FailureState.INVALID_INPUT, error="exact certificate candidate is missing")
    try:
        _parse_exact_expression(candidate_value)
    except ResourceLimitError:
        raise
    except InvalidInputError as exc:
        return RadiusReplayResult(**base, status="invalid_input", certified=False, failure_state=FailureState.INVALID_INPUT, error=str(exc))
    if not _expression_equal(candidate_value, resolved.certificate.exact_candidate):
        return RadiusReplayResult(**base, status="candidate_mismatch", certified=False, error="candidate does not match the reviewed exact radius")
    steps: list[ReplayStep] = []
    if len(resolved.certificate.machine_steps) > max_steps:
        raise ResourceLimitError("certificate exceeds the replay step limit")
    passed = _replay_chain(resolved.source_class, resolved.target_class, steps, dps=dps)
    if len(steps) > max_steps:
        raise ResourceLimitError("replay produced more steps than the configured limit")
    status = "proven" if passed and all(step.verified for step in steps) else "unresolved"
    return RadiusReplayResult(**base, status=status, certified=status == "proven", steps=tuple(steps), error=None if status == "proven" else "one or more exact certificate steps failed")


def verify_radius_certificate(
    source: str,
    target: str,
    *,
    candidate: str | None = None,
    dps: int = 50,
    max_steps: int = MAX_REPLAY_STEPS,
) -> RadiusReplayResult:
    """Look up and replay a directed radius without swapping its composition."""

    try:
        record = radius(source, target)
    except KeyError as exc:
        return RadiusReplayResult(source, target, candidate, None, FailureState.INVALID_INPUT.value, False, failure_state=FailureState.INVALID_INPUT, error=str(exc))
    return replay_radius_certificate(record, candidate=candidate, dps=dps, max_steps=max_steps)


def recompute_radius(
    source: str,
    target: str,
    *,
    candidate: str | None = None,
    dps: int = 50,
    max_steps: int = MAX_REPLAY_STEPS,
) -> RadiusReplayResult:
    """Recompute a reviewed lane by replaying its bundled exact certificate.

    This is deliberately bounded certificate recomputation, not an open-ended
    radius search.  Unreviewed rows remain unresolved rather than being
    promoted by a numerical coincidence.
    """

    return verify_radius_certificate(
        source, target, candidate=candidate, dps=dps, max_steps=max_steps
    )


def verify_radius_attainment(
    source: str,
    target: str,
    *,
    dps: int = 50,
    max_steps: int = MAX_REPLAY_STEPS,
) -> RadiusReplayResult:
    """Verify the stored contact/attainment chain for one reviewed radius."""

    return verify_radius_certificate(source, target, dps=dps, max_steps=max_steps)


def identify_radius(
    value: str | float,
    *,
    tolerance: float = 1e-12,
    limit: int = 100,
) -> tuple[RadiusRecord, ...]:
    """Identify snapshot rows matching an exact expression or decimal value.

    Matching is restricted to the bundled radius snapshot.  It does not infer
    a closed form from arbitrary decimal input and returns an empty tuple when
    no stored row matches.
    """

    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1 or limit > 1000:
        raise InvalidInputError("radius identification limit must be an integer in [1, 1000]")
    if isinstance(tolerance, bool) or not isinstance(tolerance, (int, float)) or not math.isfinite(float(tolerance)) or tolerance < 0:
        raise InvalidInputError("radius identification tolerance must be a finite non-negative number")
    rows: list[RadiusRecord] = []
    if isinstance(value, str):
        if len(value) > MAX_IDENTIFICATION_CHARS:
            raise ResourceLimitError("radius identification expression is too long")
        direct = tuple(row for row in list_radii() if row.value_exact == value)
        if direct:
            return direct[:limit]
        for row in list_radii():
            if row.value_exact is not None and _expression_equal(value, row.value_exact):
                rows.append(row)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        if not math.isfinite(numeric):
            raise InvalidInputError("radius identification value must be finite")
        for row in list_radii():
            if row.value_float is not None and abs(row.value_float - numeric) <= float(tolerance):
                rows.append(row)
    else:
        raise InvalidInputError("radius identification requires an exact expression or finite number")
    return tuple(rows[:limit])


def audit_radius(
    source: str,
    target: str,
    *,
    candidate: str | None = None,
    dps: int = 50,
    max_steps: int = MAX_REPLAY_STEPS,
) -> dict[str, Any]:
    """Return a bounded audit record without upgrading literature status."""

    record = radius(source, target)
    replay = replay_radius_certificate(record, candidate=candidate, dps=dps, max_steps=max_steps)
    return {
        "result_type": "radius_audit",
        "direction": record.direction,
        "status": replay.status,
        "evidence_status": record.status.value,
        "attainment_verified": replay.certified and bool(record.contact_and_attainment),
        "certificate_replay": replay.to_dict(),
        "claim_label": record.claim_label,
        "scope": "bounded bundled-certificate audit; not a new radius search",
        "novelty_claim": False,
    }


# A short alias used by some callers migrating from the research verifier.
replay_radius = verify_radius_certificate

__all__ = [
    "RADIUS_STATUS_LABELS",
    "RECONCILABLE_STATUSES",
    "RadiusCertificate",
    "RadiusProvenance",
    "RadiusRecord",
    "RadiusReplayResult",
    "RadiusStatus",
    "ReplayStep",
    "audit_radius",
    "identify_radius",
    "list_radii",
    "radius",
    "recompute_radius",
    "replay_radius",
    "replay_radius_certificate",
    "verify_radius_attainment",
    "verify_radius_certificate",
]
