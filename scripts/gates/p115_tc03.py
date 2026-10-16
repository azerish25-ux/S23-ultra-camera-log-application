"""TC-P115-03 Temporal integration energy.

Host fixture. Integrate known synthetic motion in the linear domain and compare
it with an independent oracle. Display-encoded averages and unnormalized
weights are rejected. Negative weights and out-of-window frames are not dropped.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P115-03"
NAME = "Temporal integration energy"
INTERVENTION = "Integrate known synthetic motion over an explicitly defined exposure window."
EXPECTED = "Match independent linear-domain energy and trail extent within the numerical tolerance."
NEGATIVE = "Averaging display-encoded frames or unnormalized temporal weights must fail."
REPEAT = "Repeat constant velocity, acceleration, and partial exposure at clip boundaries."
REPEATS = ("constant-velocity", "acceleration", "partial-exposure-boundary")
PAYLOAD_KEYS = ("evidenceId", "frames", "weights", "window", "oracle", "domain", "repeat")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_CORE = None


def _core():
    global _CORE
    if _CORE is None:
        path = Path(__file__).resolve().parent / "p115_build_a_temporal_integration_reference.py"
        spec = importlib.util.spec_from_file_location("p115_build_a_temporal_integration_reference", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _CORE = module
    return _CORE


def evaluate(payload: dict) -> dict:
    """Integrate the stack. The sample keeps every weight; bad exposures are rejected."""
    evidence, frames, weights, window, oracle, domain, repeat = _payload(payload)
    integration = _core().evaluate(
        {
            "caseId": CASE_ID,
            "evidenceId": evidence,
            "claim": NAME,
            "frames": frames,
            "weights": weights,
            "window": window,
            "oracle": oracle,
            "domain": domain,
            "applyMutant": False,
        }
    )
    rejected = list(integration["rejectedClaims"])
    reasons = [EXPECTED, INTERVENTION, f"repeat {repeat}", *integration["reasons"]]
    if "display-encoded-average" in rejected or "unnormalized-temporal-weights" in rejected:
        reasons.append(NEGATIVE)
    questions = list(integration["openQuestions"])
    questions.append(REPEAT)
    result = {
        "caseId": CASE_ID,
        "decision": integration["decision"],
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": integration["preservedResults"],
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or result["decision"] not in {"recorded", "rejected"}:
        raise ValueError("result contract drifted")
    if evidence not in result["preservedResults"] or weights not in result["preservedResults"]:
        raise ValueError("weight list was not retained")
    if window not in result["preservedResults"]:
        raise ValueError("window was not retained")
    return result


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    return (
        evidence,
        payload["frames"],
        payload["weights"],
        payload["window"],
        payload["oracle"],
        payload["domain"],
        repeat,
    )
