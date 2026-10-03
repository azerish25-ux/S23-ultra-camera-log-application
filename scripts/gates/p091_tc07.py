"""TC-P091-07 Lens-character provenance.

Host fixture. A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P091-07"
NAME = "Lens-character provenance"
INTERVENTION = "Load a creative lens profile beside a measured profile with similar display names."
EXPECTED = "Preserve distinct evidence labels and parameter identities without implying equal physical calibration."
NEGATIVE = "Plausible aberration values must not be called measured without references."
REPEAT = "Repeat vignetting, cat-eye bokeh, breathing, and chromatic effects."
NEGATIVE_TOKEN = "plausible-aberration-values-called-measured-without"
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
