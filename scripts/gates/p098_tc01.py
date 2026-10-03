"""TC-P098-01 Model identity substitution.

Host fixture. A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P098-01"
NAME = "Model identity substitution"
INTERVENTION = "Replace a model asset with another variant or converted file while retaining a cached result."
EXPECTED = "Invalidate incompatible caches and report the actual model identity before accepting depth output."
NEGATIVE = "A filename match alone must not establish identical weights."
REPEAT = "Repeat with precision changes, runtime versions, and different model variants."
NEGATIVE_TOKEN = "filename-match-alone-establish-identical-weights"
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
