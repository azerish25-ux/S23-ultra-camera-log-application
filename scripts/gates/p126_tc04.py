"""TC-P126-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is not published as accepted, and a late callback cannot reverse
it. Clip rows still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_INDEX = 3
NEGATIVE_TOKEN = "late-callback-reverses-cancellation"
PUBLISHED_TOKEN = "cancelled-job-published-as-accepted"
OWNERSHIP_TOKEN = "cancellation-acknowledged-without-ownership"
STAGES = ("rendering", "verification", "publication", "cleanup")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "cancellationRequested",
    "ownershipControlled",
    "cancellationAcknowledged",
    "publishedAsAccepted",
    "lateCallbackReverses",
    "clips",
    "omitted_ids",
)

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parent / "p126_build_a_trustworthy_clip_library.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
CASE = _CORE.CASES[CASE_INDEX]
CASE_ID = CASE["id"]
NAME = CASE["name"]
INTERVENTION = CASE["intervention"]
EXPECTED = CASE["expected"]
NEGATIVE = CASE["negative"]
REPEAT = CASE["repeat"]
RESULT_KEYS = _CORE.RESULT_KEYS


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flag(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    stage = _text(payload["stage"], "stage")
    if stage not in STAGES:
        raise ValueError("stage is invalid")
    requested = _flag(payload["cancellationRequested"], "cancellationRequested")
    ownership = _flag(payload["ownershipControlled"], "ownershipControlled")
    acknowledged = _flag(payload["cancellationAcknowledged"], "cancellationAcknowledged")
    published = _flag(payload["publishedAsAccepted"], "publishedAsAccepted")
    late = _flag(payload["lateCallbackReverses"], "lateCallbackReverses")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append("stage=" + stage)
    rejected = list(library["rejectedClaims"])
    if requested and published:
        _add(rejected, PUBLISHED_TOKEN)
        reasons.append("cancelled job was published as accepted")
    if late:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if acknowledged and not ownership:
        _add(rejected, OWNERSHIP_TOKEN)
        reasons.append("cancellation acknowledged before ownership was controlled")
    if requested and acknowledged and ownership and not published and not late:
        reasons.append("cancellation-acknowledged-after-ownership")
    preserved = [evidence]
    preserved.extend(library["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
