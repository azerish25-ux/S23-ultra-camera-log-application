"""TC-P122-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after ownership is controlled.
A cancelled job is not published as accepted. A late callback that reverses
cancellation is rejected. The frozen recipe version is left unchanged.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
NEGATIVE_TOKEN = "late-callback-reverses-cancellation"
PUBLISHED_TOKEN = "cancelled-job-published-as-accepted"
OWNERSHIP_TOKEN = "cancellation-acknowledged-without-ownership"
STAGES = {"rendering", "verification", "publication", "cleanup"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "cancelled",
    "ownershipControlled",
    "acknowledged",
    "publishedAsAccepted",
    "lateCallbackReversesCancellation",
    "versions",
    "mutatedInPlace",
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
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parent / "p122_create_non_destructive_recipe_versions.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def valid_versions():
    return _CORE.sample_versions()


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    stage = _text(payload["stage"], "stage")
    if stage not in STAGES:
        raise ValueError("stage must be rendering, verification, publication, or cleanup")
    cancelled = _bool(payload["cancelled"], "cancelled")
    ownership = _bool(payload["ownershipControlled"], "ownershipControlled")
    acknowledged = _bool(payload["acknowledged"], "acknowledged")
    published = _bool(payload["publishedAsAccepted"], "publishedAsAccepted")
    late = _bool(payload["lateCallbackReversesCancellation"], "lateCallbackReversesCancellation")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", f"stage={stage}"]
    reasons.extend(chain["reasons"])
    if late:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if cancelled and published and PUBLISHED_TOKEN not in rejected:
        rejected.append(PUBLISHED_TOKEN)
        reasons.append("cancelled job was published as accepted")
    if cancelled and acknowledged and not ownership and OWNERSHIP_TOKEN not in rejected:
        rejected.append(OWNERSHIP_TOKEN)
        reasons.append("cancellation was acknowledged before ownership was controlled")
    if cancelled and ownership and acknowledged and not published and not late:
        reasons.append("cancellation acknowledged after ownership was controlled")
    preserved = [evidence, f"stage={stage}", f"cancelled={cancelled}", f"ownershipControlled={ownership}"]
    preserved.extend(chain["preservedResults"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
