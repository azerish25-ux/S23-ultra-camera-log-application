"""TC-P153-03 Unexplored reversible alternative.

Host reference. One failed route, including one failed P010 route, does not
prove that a broader capture goal such as ten-bit encoding is impossible while
another public route is still untested. Alternatives must be evaluated first.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

TEN_BIT = frozenset({"ten-bit-encoding", "all-ten-bit-encoding"})
ONE_ROUTE = "one-failed-route-does-not-block-broader-goal"
P010_NOT_ALL = "one-failed-p010-route-is-not-all-ten-bit"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "claim",
    "hypotheses",
    "questions",
    "plan",
    "limiter",
    "applyMutant",
    "failed_route",
    "untested_routes",
    "declared_blocked",
    "alternatives_evaluated",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p153_identify_the_actual_blocked_capability.py"
    spec = importlib.util.spec_from_file_location("p153_gate_for_tc03", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()
CASE = dict(_GATE.CASES[2])


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.CASE_COMMON_KEYS))
    failed = _GATE.require_text(payload["failed_route"], "failed_route")
    untested = _GATE.require_str_list(payload["untested_routes"], "untested_routes", allow_empty=True)
    declared = _GATE.require_text(payload["declared_blocked"], "declared_blocked")
    evaluated = _GATE.require_bool(payload["alternatives_evaluated"], "alternatives_evaluated")
    _GATE.require(failed not in untested, "the failed route cannot also be listed as untested")
    unresolved = bool(untested) or not evaluated
    broader = declared != failed
    faults = list(bundle["faults"])
    if broader and unresolved:
        faults.append(ONE_ROUTE)
    if failed == "p010" and declared in TEN_BIT and unresolved:
        faults.append(P010_NOT_ALL)
    extra = [{
        "failed_route": failed,
        "untested_routes": untested,
        "declared_blocked": declared,
        "alternatives_evaluated": evaluated,
        "broaderGoal": broader,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {
            ONE_ROUTE: CASE["expected"],
            P010_NOT_ALL: CASE["negative"],
        },
    )


def example_payload(**overrides):
    payload = _GATE.core_payload(repeat="surface-input")
    payload.update({
        "failed_route": "p010",
        "untested_routes": ["surface-input", "reduced-geometry"],
        "declared_blocked": "p010",
        "alternatives_evaluated": False,
    })
    payload.update(overrides)
    return payload
