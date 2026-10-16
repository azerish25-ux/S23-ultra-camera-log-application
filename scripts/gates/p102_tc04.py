"""TC-P102-04 Offline asset unavailability.

Host reference. A missing or corrupt local asset must be reported without
waiting on the network. Ordinary capture and the source stay available.
"""

from __future__ import annotations

import hashlib
import re

CASE_ID = "TC-P102-04"
NAME = "Offline asset unavailability"
INTERVENTION = "Disable networking and remove or corrupt a required local model asset."
EXPECTED = "Report the missing capability while preserving ordinary capture and source retention."
NEGATIVE = "An offline camera must not hang waiting for an undisclosed cloud dependency."
REPEAT = "Repeat first installation, asset update, and a previously working offline session."
NEGATIVE_TOKEN = "offline-camera-hang-waiting-undisclosed-cloud"
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "networkingEnabled",
    "waitedForNetwork",
    "missingCapabilityReported",
    "ordinaryCapturePreserved",
    "sourceRetained",
    "assetPresent",
    "assetContent",
    "assetSha256",
    "expectedSha256",
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
    for flag in (
        "networkingEnabled",
        "waitedForNetwork",
        "missingCapabilityReported",
        "ordinaryCapturePreserved",
        "sourceRetained",
        "assetPresent",
    ):
        _require(type(payload[flag]) is bool, flag + " must be a bool")
    expected = payload["expectedSha256"]
    _require(isinstance(expected, str) and DIGEST.fullmatch(expected) is not None,
             "expectedSha256 must be 64 lowercase hex characters")
    if payload["assetPresent"]:
        content = payload["assetContent"]
        declared = payload["assetSha256"]
        _require(isinstance(content, str) and content != "", "assetContent must be a non-empty string")
        actual = hashlib.sha256(content.encode("utf-8")).hexdigest()
        _require(declared == actual, "assetSha256 does not match asset content")
    else:
        _require(payload["assetContent"] is None and payload["assetSha256"] is None,
                 "absent asset must not carry content or a digest")
        actual = None

    missing = not payload["assetPresent"]
    corrupt = payload["assetPresent"] and actual != expected
    rejected: list[str] = []
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, f"repeat {repeat}"]
    if payload["waitedForNetwork"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if (missing or corrupt) and not payload["missingCapabilityReported"]:
        rejected.append("missing-capability-not-reported")
    if not payload["ordinaryCapturePreserved"]:
        rejected.append("ordinary-capture-not-preserved")
    if not payload["sourceRetained"]:
        rejected.append("source-not-retained")
    if (missing or corrupt) and payload["networkingEnabled"] and NEGATIVE_TOKEN not in rejected:
        rejected.append("network-not-disabled")
        reasons.append("offline case left networking enabled")
    if missing or corrupt:
        reasons.append("local asset " + ("missing" if missing else "corrupt"))
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("missing capability reported; capture and source retained")
    preserved_extra = ["asset-missing" if missing else ("asset-corrupt" if corrupt else "asset-present")]
    return _finish(decision, reasons, rejected, evidence, preserved_extra)


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
