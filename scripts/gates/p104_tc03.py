"""TC-P104-03 Conversion accuracy regression.

Loading is not numerical qualification. Errors outside the declared tolerances
stay experimental. A within-tolerance host result is recorded, never qualified.
"""

from __future__ import annotations

import math
from decimal import Decimal


CASE_ID = "TC-P104-03"
NAME = "Conversion accuracy regression"
INTERVENTION = "Compare exported or quantized model results against the approved host baseline on withheld scenes."
EXPECTED = "Meet declared depth and boundary tolerances or remain experimental despite successful loading."
NEGATIVE = "A model that merely runs is not numerically qualified."
REPEAT = "Repeat hair, glass, low light, thin objects, and saturated illumination."
NEGATIVE_TOKEN = "model-that-merely-runs-is-not-numerically-qualified"
OPEN_QUESTION = "physical S23 measurement was not run"
SCENES = ("hair", "glass", "low-light", "thin-objects", "saturated")
STATUSES = ("experimental", "within-tolerance")
PAYLOAD_KEYS = (
    "evidenceId",
    "scene",
    "loads",
    "depthError",
    "boundaryError",
    "depthTolerance",
    "boundaryTolerance",
    "status",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    evidence, scene, loads, depth, boundary, depth_tol, boundary_tol, status = _payload(payload)
    within = depth <= depth_tol and boundary <= boundary_tol
    rejected: list[str] = []
    if not loads:
        rejected.append("model-did-not-load")
    if not within and status != "experimental":
        rejected.append(NEGATIVE_TOKEN)
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if NEGATIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
        reasons.append("successful loading was not treated as numerical qualification")
    elif not within:
        reasons.append(f"{scene} remains experimental; depth {canonical(depth)} boundary {canonical(boundary)}")
    else:
        reasons.append(
            f"{scene} meets depth tolerance {canonical(depth_tol)} and boundary tolerance {canonical(boundary_tol)}"
        )
        reasons.append("within-tolerance host arithmetic is recorded and is not qualified")
    preserved = [
        evidence,
        f"scene:{scene}",
        f"loads:{str(loads).lower()}",
        f"depth-error:{canonical(depth)}",
        f"boundary-error:{canonical(boundary)}",
        f"depth-tolerance:{canonical(depth_tol)}",
        f"boundary-tolerance:{canonical(boundary_tol)}",
        f"within-tolerance:{str(within).lower()}",
        f"status:{status}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def canonical(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _number(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(label + " must be finite")
    number = Decimal(value) if isinstance(value, int) else Decimal(str(value))
    if number < 0:
        raise ValueError(label + " must be >= 0")
    return number


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    scene = payload["scene"]
    if scene not in SCENES:
        raise ValueError("scene is unsupported")
    loads = payload["loads"]
    if type(loads) is not bool:
        raise ValueError("loads must be a bool")
    status = payload["status"]
    if status not in STATUSES:
        raise ValueError("status is unsupported")
    return (
        evidence,
        scene,
        loads,
        _number(payload["depthError"], "depthError"),
        _number(payload["boundaryError"], "boundaryError"),
        _number(payload["depthTolerance"], "depthTolerance"),
        _number(payload["boundaryTolerance"], "boundaryTolerance"),
        status,
    )


def _finish(decision: str, reasons: list[str], rejected: list[str], preserved: list[str], evidence: str) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
