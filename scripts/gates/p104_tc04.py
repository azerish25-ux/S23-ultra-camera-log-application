"""TC-P104-04 Offline asset unavailability.

A missing or corrupt local asset must be reported. Ordinary capture and source
retention stay. Waiting on an undisclosed cloud dependency is rejected.
"""

from __future__ import annotations


CASE_ID = "TC-P104-04"
NAME = "Offline asset unavailability"
INTERVENTION = "Disable networking and remove or corrupt a required local model asset."
EXPECTED = "Report the missing capability while preserving ordinary capture and source retention."
NEGATIVE = "An offline camera must not hang waiting for an undisclosed cloud dependency."
REPEAT = "Repeat first installation, asset update, and a previously working offline session."
NEGATIVE_TOKEN = "offline-camera-hangs-for-undisclosed-cloud-dependency"
OPEN_QUESTION = "physical S23 measurement was not run"
SESSIONS = ("first-install", "asset-update", "previously-working")
ASSETS = ("missing", "corrupt", "present")
PAYLOAD_KEYS = (
    "evidenceId",
    "session",
    "networkingEnabled",
    "assetState",
    "hangForCloud",
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


def evaluate(payload: dict) -> dict:
    evidence, session, networking, asset, hang, capture, source, reported = _payload(payload)
    unavailable = asset in {"missing", "corrupt"}
    rejected: list[str] = []
    if hang:
        rejected.append(NEGATIVE_TOKEN)
    if unavailable and not reported:
        rejected.append("missing-capability-not-reported")
    if not capture or not source:
        rejected.append("capture-or-source-not-retained")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if NEGATIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if "capture-or-source-not-retained" not in rejected:
        reasons.append("ordinary capture and source retention preserved")
    if unavailable and reported:
        reasons.append(f"{session} reports missing capability for {asset} asset")
    preserved = [
        evidence,
        f"session:{session}",
        f"networking-enabled:{str(networking).lower()}",
        f"asset-state:{asset}",
        f"hang-for-cloud:{str(hang).lower()}",
        f"capture-preserved:{str(capture).lower()}",
        f"source-retained:{str(source).lower()}",
        f"missing-capability-reported:{str(reported).lower()}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    session = payload["session"]
    if session not in SESSIONS:
        raise ValueError("session is unsupported")
    asset = payload["assetState"]
    if asset not in ASSETS:
        raise ValueError("assetState is unsupported")
    return (
        evidence,
        session,
        _bool(payload["networkingEnabled"], "networkingEnabled"),
        asset,
        _bool(payload["hangForCloud"], "hangForCloud"),
        _bool(payload["capturePreserved"], "capturePreserved"),
        _bool(payload["sourceRetained"], "sourceRetained"),
        _bool(payload["missingCapabilityReported"], "missingCapabilityReported"),
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
