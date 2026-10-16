"""TC-P127-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is never published as accepted. A late callback that reverses
the cancellation is rejected. Bundle manifest rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
NEGATIVE_TOKEN = "late-callback-reversed-cancellation"
PUBLISH_TOKEN = "cancelled-job-published-as-accepted"
OWNERSHIP_TOKEN = "cancellation-acknowledged-before-ownership"
STAGES = frozenset({"rendering", "verification", "publication", "cleanup"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "labels",
    "manifest",
    "export_allowed",
    "grade_applied",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
    "stage",
    "cancelRequested",
    "ownershipControlled",
    "cancellationAcknowledged",
    "publishedAsAccepted",
    "lateCallbackReversesCancel",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage must be rendering, verification, publication, or cleanup")
    flags = (
        "cancelRequested",
        "ownershipControlled",
        "cancellationAcknowledged",
        "publishedAsAccepted",
        "lateCallbackReversesCancel",
    )
    if any(type(payload[name]) is not bool for name in flags):
        raise ValueError("cancellation flags must be bools")
    bundle = _CORE.judge_bundle(payload)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, "stage=" + stage]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    if payload["lateCallbackReversesCancel"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if payload["cancelRequested"] and payload["publishedAsAccepted"]:
        rejected.append(PUBLISH_TOKEN)
        reasons.append("cancelled job was published as accepted")
    if payload["cancelRequested"] and payload["cancellationAcknowledged"] and not payload["ownershipControlled"]:
        rejected.append(OWNERSHIP_TOKEN)
        reasons.append("cancellation was acknowledged before ownership was controlled")
    if (
        payload["cancelRequested"]
        and payload["ownershipControlled"]
        and payload["cancellationAcknowledged"]
        and not payload["publishedAsAccepted"]
        and not payload["lateCallbackReversesCancel"]
    ):
        reasons.append("cancellation acknowledged after ownership; job was not accepted")
    elif not payload["cancelRequested"] and not payload["publishedAsAccepted"] and not payload["lateCallbackReversesCancel"]:
        reasons.append("job was not cancelled")
    preserved = [evidence, "stage=" + stage]
    preserved.extend(bundle["preservedResults"])
    result = _CORE.seal(
        CASE_ID,
        evidence,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return result
