"""TC-P103-04 Offline asset unavailability.

Host fixture. An offline camera must not hang on an undisclosed cloud dependency.
"""

from __future__ import annotations

CASE_ID = "TC-P103-04"
NAME = "Offline asset unavailability"
INTERVENTION = "Disable networking and remove or corrupt a required local model asset."
EXPECTED = "Report the missing capability while preserving ordinary capture and source retention."
NEGATIVE = "An offline camera must not hang waiting for an undisclosed cloud dependency."
REPEAT = "Repeat first installation, asset update, and a previously working offline session."
NEGATIVE_TOKEN = "offline-camera-hang-waiting-undisclosed-cloud"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "applyNegative",
    "applyMutant",
    "networkEnabled",
    "assetPresent",
    "assetCorrupt",
    "hungWaitingForCloud",
    "capturePreserved",
    "sourceRetained",
    "missingCapabilityReported",
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
    flags = (
        "applyNegative",
        "applyMutant",
        "networkEnabled",
        "assetPresent",
        "assetCorrupt",
        "hungWaitingForCloud",
        "capturePreserved",
        "sourceRetained",
        "missingCapabilityReported",
    )
    values = {name: _bool(payload[name], name) for name in flags}
    missing_asset = (not values["assetPresent"]) or values["assetCorrupt"]
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        f"networkEnabled={values['networkEnabled']}; assetPresent={values['assetPresent']}",
        f"assetCorrupt={values['assetCorrupt']}; hungWaitingForCloud={values['hungWaitingForCloud']}",
        f"capturePreserved={values['capturePreserved']}; sourceRetained={values['sourceRetained']}",
    ]
    rejected: list[str] = []
    if values["applyMutant"] or values["applyNegative"] or values["hungWaitingForCloud"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if not values["capturePreserved"] or not values["sourceRetained"]:
        rejected.append("ordinary-capture-or-source-not-preserved")
        reasons.append("ordinary capture or source retention was dropped")
    if missing_asset and not values["missingCapabilityReported"]:
        rejected.append("missing-capability-not-reported")
        reasons.append("missing local model capability was not reported")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        if missing_asset:
            reasons.append("missing capability reported; capture and source retained; no cloud wait")
        else:
            reasons.append("local asset available offline; capture and source retained")
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
