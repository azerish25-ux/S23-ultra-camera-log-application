"""TC-P102-05 Delegate failure and fallback.

Host reference. A failed delegate may use an explicitly qualified fallback or
disable optional depth. An untested backend or an upload is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P102-05"
NAME = "Delegate failure and fallback"
INTERVENTION = "Fail runtime or delegate initialization while a preview or development job is active."
EXPECTED = "Use only an explicitly qualified fallback or disable optional depth processing with a clear reason."
NEGATIVE = "Silently changing to an untested backend or uploading frames must fail."
REPEAT = "Repeat CPU, GPU, and available accelerator configurations as applicable."
NEGATIVE_TOKEN = "silently-changing-untested-backend-uploading-frames"
FALLBACKS = {"qualified", "disabled", "untested-backend", "upload", "none"}
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "delegateInitialized",
    "fallback",
    "reason",
    "framesUploaded",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def evaluate(payload: dict) -> dict:
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["delegateInitialized"]) is bool, "delegateInitialized must be a bool")
    _require(type(payload["framesUploaded"]) is bool, "framesUploaded must be a bool")
    fallback = payload["fallback"]
    reason = payload["reason"]
    _require(fallback in FALLBACKS, "fallback is not a known policy")
    _require(isinstance(reason, str), "reason must be a string")

    rejected: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, f"repeat {repeat}", "fallback " + fallback]
    if payload["framesUploaded"] or fallback in {"untested-backend", "upload"}:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        if payload["framesUploaded"]:
            reasons.append("frames were uploaded")
    elif fallback in {"qualified", "disabled"}:
        if not reason.strip():
            rejected.append("fallback-without-clear-reason")
            reasons.append("fallback has no clear reason")
    elif fallback == "none" and not payload["delegateInitialized"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("delegate failed without a qualified fallback or a disable reason")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("optional depth stayed on an explicit policy")
    return _finish(decision, reasons, rejected, evidence, ["fallback:" + fallback])


def _finish(decision: str, reasons: list[str], rejected: list[str], evidence: str, extra: list[str]) -> dict:
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, *extra],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
