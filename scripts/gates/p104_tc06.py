"""TC-P104-06 Stale depth result.

A depth array needs temporal and geometric identity. Blind application is
rejected. Reject or an explicit reproject policy can be recorded.
"""

from __future__ import annotations

import math


CASE_ID = "TC-P104-06"
NAME = "Stale depth result"
INTERVENTION = "Delay inference until its result no longer matches the current source timestamp or crop."
EXPECTED = "Reject or explicitly reproject the result under a validated policy rather than applying it blindly."
NEGATIVE = "A float array without temporal and geometric identity must not be accepted."
REPEAT = "Repeat rapid camera movement, rotation, source switches, and scene cuts."
NEGATIVE_TOKEN = "float-array-without-temporal-and-geometric-identity"
OPEN_QUESTION = "physical S23 measurement was not run"
MOTIONS = ("rapid", "rotation", "source-switch", "scene-cut")
POLICIES = ("reject", "reproject", "apply-blind")
PAYLOAD_KEYS = (
    "evidenceId",
    "motion",
    "sourceTimestamp",
    "depthTimestamp",
    "sourceCrop",
    "depthCrop",
    "hasTemporalIdentity",
    "hasGeometricIdentity",
    "policy",
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
    (
        evidence,
        motion,
        source_ts,
        depth_ts,
        source_crop,
        depth_crop,
        temporal,
        geometric,
        policy,
    ) = _payload(payload)
    stale = source_ts != depth_ts or source_crop != depth_crop
    identity = temporal and geometric
    rejected: list[str] = []
    if policy == "apply-blind" or not identity:
        rejected.append(NEGATIVE_TOKEN)
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if rejected:
        reasons.append(NEGATIVE)
        reasons.append("blind application of an unidentified float array was not accepted")
    else:
        reasons.append(f"{motion} uses {policy}; stale={str(stale).lower()}")
    preserved = [
        evidence,
        f"motion:{motion}",
        f"source-timestamp:{source_ts}",
        f"depth-timestamp:{depth_ts}",
        f"source-crop:{source_crop}",
        f"depth-crop:{depth_crop}",
        f"temporal-identity:{str(temporal).lower()}",
        f"geometric-identity:{str(geometric).lower()}",
        f"stale:{str(stale).lower()}",
        f"policy:{policy}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _timestamp(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or isinstance(value, float) and not math.isfinite(value):
        raise ValueError(label + " must be a finite number")
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(label + " must be an integer timestamp")
    number = int(value)
    if number < 0:
        raise ValueError(label + " must be >= 0")
    return number


def _crop(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(label + " must be a non-empty string")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    motion = payload["motion"]
    if motion not in MOTIONS:
        raise ValueError("motion is unsupported")
    policy = payload["policy"]
    if policy not in POLICIES:
        raise ValueError("policy is unsupported")
    temporal = payload["hasTemporalIdentity"]
    geometric = payload["hasGeometricIdentity"]
    if type(temporal) is not bool or type(geometric) is not bool:
        raise ValueError("identity flags must be bools")
    return (
        evidence,
        motion,
        _timestamp(payload["sourceTimestamp"], "sourceTimestamp"),
        _timestamp(payload["depthTimestamp"], "depthTimestamp"),
        _crop(payload["sourceCrop"], "sourceCrop"),
        _crop(payload["depthCrop"], "depthCrop"),
        temporal,
        geometric,
        policy,
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
