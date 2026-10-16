"""TC-P115-08 Combined temporal effects.

Host fixture. Stabilization, virtual focus, motion integration, and film
finishing are checked together. A passing integral does not replace that
combined regression. The motion integral is the weighted frame sum.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_ID = "TC-P115-08"
NAME = "Combined temporal effects"
INTERVENTION = "Enable stabilization, virtual focus, motion integration, and film finishing on the same difficult clip."
EXPECTED = "Preserve shared geometry and timing without doubled edges, unstable masks, or unexplained cadence changes."
NEGATIVE = "Independent success of each effect cannot replace the combined regression."
REPEAT = "Repeat scene cuts, chunk resumes, and low-confidence motion estimates."
REPEATS = ("scene-cut", "chunk-resume", "low-confidence-motion")
BOOL_KEYS = (
    "stabilization",
    "virtualFocus",
    "motionIntegration",
    "filmFinishing",
    "combinedRun",
    "individualPassesOnly",
    "doubledEdges",
    "unstableMasks",
    "cadenceChanged",
    "cadenceExplained",
    "sharedGeometry",
)
PAYLOAD_KEYS = (
    "evidenceId",
    *BOOL_KEYS,
    "frames",
    "weights",
    "window",
    "oracle",
    "repeat",
)
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
    """Reject separate effect passes. Keep the combined exposure integral."""
    fields = _payload(payload)
    integration = _core().evaluate(
        {
            "caseId": CASE_ID,
            "evidenceId": fields["evidenceId"],
            "claim": NAME,
            "frames": fields["frames"],
            "weights": fields["weights"],
            "window": fields["window"],
            "oracle": fields["oracle"],
            "domain": "linear",
            "applyMutant": False,
        }
    )
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    if fields["individualPassesOnly"] or not fields["combinedRun"]:
        rejected.append("independent-effects-replace-combined-regression")
        reasons.append(NEGATIVE)
    if not (
        fields["stabilization"]
        and fields["virtualFocus"]
        and fields["motionIntegration"]
        and fields["filmFinishing"]
    ):
        rejected.append("missing-combined-effect")
        reasons.append("stabilization, virtual focus, motion integration, and film finishing are all required")
    if fields["doubledEdges"]:
        rejected.append("doubled-edges")
    if fields["unstableMasks"]:
        rejected.append("unstable-masks")
    if not fields["sharedGeometry"]:
        rejected.append("geometry-not-shared")
    if fields["cadenceChanged"] and not fields["cadenceExplained"]:
        rejected.append("unexplained-cadence-change")
    rejected.extend(integration["rejectedClaims"])
    reasons.extend(integration["reasons"])
    decision = "rejected" if rejected else "recorded"
    questions = list(integration["openQuestions"])
    questions.append(REPEAT)
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": integration["preservedResults"],
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or decision not in {"recorded", "rejected"}:
        raise ValueError("result contract drifted")
    if fields["evidenceId"] not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    if fields["weights"] not in result["preservedResults"] or fields["window"] not in result["preservedResults"]:
        raise ValueError("weight list or window was not retained")
    return result


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    fields = {"evidenceId": evidence, "repeat": repeat}
    for key in BOOL_KEYS:
        if type(payload[key]) is not bool:
            raise ValueError(f"{key} must be a bool")
        fields[key] = payload[key]
    for key in ("frames", "weights", "window", "oracle"):
        fields[key] = payload[key]
    return fields
