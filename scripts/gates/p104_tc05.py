"""TC-P104-05 Delegate failure and fallback.

An untested backend or an upload of frames is rejected. Optional depth is
disabled only with an explicit reason, or an explicit fallback is used.
"""

from __future__ import annotations


CASE_ID = "TC-P104-05"
NAME = "Delegate failure and fallback"
INTERVENTION = "Fail runtime or delegate initialization while a preview or development job is active."
EXPECTED = "Use only an explicitly qualified fallback or disable optional depth processing with a clear reason."
NEGATIVE = "Silently changing to an untested backend or uploading frames must fail."
REPEAT = "Repeat CPU, GPU, and available accelerator configurations as applicable."
NEGATIVE_TOKEN = "silent-untested-backend-or-frame-upload"
OPEN_QUESTION = "physical S23 measurement was not run"
CONFIGS = ("cpu", "gpu", "accelerator")
FALLBACKS = ("none", "explicit", "untested")
PAYLOAD_KEYS = (
    "evidenceId",
    "config",
    "delegateFailed",
    "fallback",
    "uploadFrames",
    "depthDisabledReason",
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
    evidence, config, failed, fallback, upload, reason = _payload(payload)
    rejected: list[str] = []
    if upload or fallback == "untested":
        rejected.append(NEGATIVE_TOKEN)
    if failed and fallback == "none" and not reason:
        rejected.append("missing-disable-reason")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if NEGATIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    elif failed and fallback == "none":
        reasons.append(f"{config} depth disabled: {reason}")
    elif failed and fallback == "explicit":
        reasons.append(f"{config} uses an explicit fallback and does not upload frames")
    else:
        reasons.append(f"{config} delegate remained available")
    preserved = [
        evidence,
        f"config:{config}",
        f"delegate-failed:{str(failed).lower()}",
        f"fallback:{fallback}",
        f"upload-frames:{str(upload).lower()}",
        "depth-disabled-reason:" + (reason if reason else "none"),
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    config = payload["config"]
    if config not in CONFIGS:
        raise ValueError("config is unsupported")
    fallback = payload["fallback"]
    if fallback not in FALLBACKS:
        raise ValueError("fallback is unsupported")
    reason = payload["depthDisabledReason"]
    if not isinstance(reason, str) or reason != reason.strip():
        raise ValueError("depthDisabledReason must be a string")
    return (
        evidence,
        config,
        _bool(payload["delegateFailed"], "delegateFailed"),
        fallback,
        _bool(payload["uploadFrames"], "uploadFrames"),
        reason,
    )


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(label + " must be a bool")
    return value


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
