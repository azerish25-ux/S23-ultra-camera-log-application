"""TC-P103-01 Model identity substitution.

Host fixture. A filename match is not a weight identity. A negative control
must not come back as qualified or allowed.
"""

from __future__ import annotations

CASE_ID = "TC-P103-01"
NAME = "Model identity substitution"
INTERVENTION = "Replace a model asset with another variant or converted file while retaining a cached result."
EXPECTED = "Invalidate incompatible caches and report the actual model identity before accepting depth output."
NEGATIVE = "A filename match alone must not establish identical weights."
REPEAT = "Repeat with precision changes, runtime versions, and different model variants."
NEGATIVE_TOKEN = "filename-match-alone-establish-identical-weights"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "filename",
    "cachedModelId",
    "actualModelId",
    "reportedModelId",
    "cachedWeightsDigest",
    "actualWeightsDigest",
    "cacheRetained",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    if type(payload["applyNegative"]) is not bool or type(payload["applyMutant"]) is not bool:
        raise ValueError("flags must be bools")
    if type(payload["cacheRetained"]) is not bool:
        raise ValueError("cacheRetained must be a bool")
    filename = _text(payload["filename"], "filename")
    cached_model = _text(payload["cachedModelId"], "cachedModelId")
    actual_model = _text(payload["actualModelId"], "actualModelId")
    reported_model = _text(payload["reportedModelId"], "reportedModelId")
    cached_digest = _text(payload["cachedWeightsDigest"], "cachedWeightsDigest")
    actual_digest = _text(payload["actualWeightsDigest"], "actualWeightsDigest")
    weights_differ = cached_digest != actual_digest
    identity_differs = cached_model != actual_model
    filename_only = weights_differ and (
        reported_model == filename or cached_model == filename
    ) and reported_model != actual_model
    cache_kept = payload["cacheRetained"] and (weights_differ or identity_differs)
    identity_hidden = reported_model != actual_model
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"filename={filename}; cached={cached_model}; actual={actual_model}; reported={reported_model}",
        f"weightsDiffer={weights_differ}; cacheRetained={payload['cacheRetained']}",
    ]
    rejected: list[str] = []
    if payload["applyMutant"] or payload["applyNegative"] or filename_only:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if cache_kept and NEGATIVE_TOKEN not in rejected:
        rejected.append("incompatible-cache-retained")
        reasons.append("incompatible cache was retained")
    if identity_hidden and NEGATIVE_TOKEN not in rejected and "incompatible-cache-retained" not in rejected:
        rejected.append("actual-model-identity-not-reported")
        reasons.append("actual model identity was not reported")
    if not rejected and (weights_differ or identity_differs) and payload["cacheRetained"]:
        rejected.append("incompatible-cache-retained")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("actual model identity reported; incompatible cache not retained")
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
