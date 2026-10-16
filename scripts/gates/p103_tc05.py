"""TC-P103-05 Delegate failure and fallback.

Host fixture. A silent backend change or frame upload is rejected.
"""

from __future__ import annotations

CASE_ID = "TC-P103-05"
NAME = "Delegate failure and fallback"
INTERVENTION = "Fail runtime or delegate initialization while a preview or development job is active."
EXPECTED = "Use only an explicitly qualified fallback or disable optional depth processing with a clear reason."
NEGATIVE = "Silently changing to an untested backend or uploading frames must fail."
REPEAT = "Repeat CPU, GPU, and available accelerator configurations as applicable."
NEGATIVE_TOKEN = "silently-changing-untested-backend-uploading-frames"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "delegateFailed",
    "fallbackName",
    "fallbackExplicitlyQualified",
    "depthDisabled",
    "disableReason",
    "silentBackendChange",
    "uploadedFrames",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    for name in (
        "applyNegative",
        "applyMutant",
        "delegateFailed",
        "fallbackExplicitlyQualified",
        "depthDisabled",
        "silentBackendChange",
        "uploadedFrames",
    ):
        _bool(payload[name], name)
    fallback = payload["fallbackName"]
    if fallback is not None:
        _text(fallback, "fallbackName")
    reason = payload["disableReason"]
    if not isinstance(reason, str):
        raise ValueError("disableReason must be a string")
    explicit_fallback = (
        isinstance(fallback, str)
        and bool(fallback.strip())
        and payload["fallbackExplicitlyQualified"] is True
    )
    disabled_clearly = payload["depthDisabled"] is True and bool(reason.strip())
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"delegateFailed={payload['delegateFailed']}; fallback={fallback}",
        f"fallbackExplicitlyQualified={payload['fallbackExplicitlyQualified']}",
        f"depthDisabled={payload['depthDisabled']}; silentBackendChange={payload['silentBackendChange']}",
        f"uploadedFrames={payload['uploadedFrames']}",
    ]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"] or payload["silentBackendChange"] or payload["uploadedFrames"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["delegateFailed"] and not explicit_fallback and not disabled_clearly:
        rejected.append("untested-fallback-or-missing-disable-reason")
        reasons.append("delegate failure had neither an explicitly qualified fallback nor a clear disable reason")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if payload["delegateFailed"] and explicit_fallback:
            reasons.append("explicitly qualified fallback retained; frames were not uploaded")
        elif payload["delegateFailed"] and disabled_clearly:
            reasons.append("optional depth disabled with a clear reason; frames were not uploaded")
        else:
            reasons.append("delegate initialized; no silent backend change")
        reasons.append("narrower software result retained; physical behavior stays open")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
