"""TC-P092-01 Unit and parameter substitution.

Host fixture. A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P092-01"
NAME = "Unit and parameter substitution"
INTERVENTION = "Substitute metres for millimetres, diameter for radius, or transmission stop for aperture f-number without conversion."
EXPECTED = "Reject or detect the mismatch through dimensional and independent optical tests."
NEGATIVE = "A plausible-looking blur cannot justify inconsistent physical units."
REPEAT = "Repeat across focal length, focus distance, gate width, and output pixel conversion."
NEGATIVE_TOKEN = "plausible-looking-blur-cannot-justify-inconsistent"
PAYLOAD_KEYS = ("evidenceId", "repeat", "applyNegative", "applyMutant")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["applyNegative"]) is not bool or type(payload["applyMutant"]) is not bool:
        raise ValueError("flags must be bools")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"]:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        decision = "recorded"
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
