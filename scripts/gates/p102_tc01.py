"""TC-P102-01 Model identity substitution.

Host reference. Filename equality is not a weight identity. The actual SHA-256
of the weight material is the identity that must be reported.
"""

from __future__ import annotations

import hashlib
import re

CASE_ID = "TC-P102-01"
NAME = "Model identity substitution"
INTERVENTION = "Replace a model asset with another variant or converted file while retaining a cached result."
EXPECTED = "Invalidate incompatible caches and report the actual model identity before accepting depth output."
NEGATIVE = "A filename match alone must not establish identical weights."
REPEAT = "Repeat with precision changes, runtime versions, and different model variants."
NEGATIVE_TOKEN = "filename-match-alone-establish-identical-weights"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "filename",
    "cachedFilename",
    "cachedWeightSha256",
    "weightMaterial",
    "actualWeightSha256",
    "reportedIdentity",
    "cacheInvalidated",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DIGEST = re.compile(r"^[0-9a-f]{64}$")


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
    filename = payload["filename"]
    cached_name = payload["cachedFilename"]
    material = payload["weightMaterial"]
    _require(isinstance(filename, str) and filename.strip(), "filename must be a non-empty string")
    _require(isinstance(cached_name, str) and cached_name.strip(), "cachedFilename must be a non-empty string")
    _require(isinstance(material, str) and material != "", "weightMaterial must be a non-empty string")
    cached_hash = payload["cachedWeightSha256"]
    declared_actual = payload["actualWeightSha256"]
    _require(isinstance(cached_hash, str) and DIGEST.fullmatch(cached_hash) is not None,
             "cachedWeightSha256 must be 64 lowercase hex characters")
    actual = hashlib.sha256(material.encode("utf-8")).hexdigest()
    _require(declared_actual == actual, "actualWeightSha256 does not match weight material")
    reported = payload["reportedIdentity"]
    _require(isinstance(reported, str) and reported.strip(), "reportedIdentity must be a non-empty string")
    _require(type(payload["cacheInvalidated"]) is bool, "cacheInvalidated must be a bool")

    incompatible = cached_hash != actual
    filename_alone = reported in {filename, cached_name} and reported != actual
    rejected: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, f"repeat {repeat}"]
    if filename_alone or (incompatible and not payload["cacheInvalidated"]) or reported != actual:
        decision = "rejected"
        if filename_alone or (filename == cached_name and incompatible):
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append("filename match does not establish identical weights")
        else:
            rejected.append("model-identity-not-reported")
            reasons.append("actual weight sha256 was not the reported identity")
        if incompatible and not payload["cacheInvalidated"]:
            reasons.append("incompatible cache was retained")
    else:
        decision = "recorded"
        if incompatible:
            reasons.append("incompatible cache invalidated")
        else:
            reasons.append("weight sha256 matches the cached identity")
        reasons.append("reported weight identity " + actual)
    return _finish(decision, reasons, rejected, evidence, [actual])


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
