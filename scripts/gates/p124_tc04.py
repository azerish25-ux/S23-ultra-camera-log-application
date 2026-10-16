"""TC-P124-04 Cancellation at acceptance boundary.

Host fixture. Cancellation is acknowledged only after workers release output
ownership. A cancelled job is not published as accepted, and a late callback
cannot reverse that cancellation.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-04"
NAME = "Cancellation at acceptance boundary"
INTERVENTION = "Cancel during rendering, verification, publication, or final cleanup."
EXPECTED = "Acknowledge cancellation only after ownership is controlled and never publish a cancelled job as accepted."
NEGATIVE = "A late worker callback that reverses cancellation must fail."
REPEAT = "Repeat with process restart and an already retained partial output."
EARLY_ACK = "cancellation-acknowledged-before-ownership-release"
PUBLISHED = "cancelled-job-published-accepted"
LATE_CALLBACK = "late-callback-reverses-cancellation"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "stage",
    "cancellationRequested",
    "workerOwnsOutput",
    "cancellationAcknowledged",
    "publishedState",
    "lateCallbackReversesCancellation",
    "partialRetained",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
STAGES = ("rendering", "verification", "publication", "cleanup")

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    stage = payload["stage"]
    if stage not in STAGES:
        raise ValueError("stage must be rendering, verification, publication, or cleanup")
    requested = _bool(payload["cancellationRequested"], "cancellationRequested")
    owns = _bool(payload["workerOwnsOutput"], "workerOwnsOutput")
    acknowledged = _bool(payload["cancellationAcknowledged"], "cancellationAcknowledged")
    published = payload["publishedState"]
    if published not in {"none", "accepted", "withheld"}:
        raise ValueError("publishedState must be none, accepted, or withheld")
    late = _bool(payload["lateCallbackReversesCancellation"], "lateCallbackReversesCancellation")
    retained = _bool(payload["partialRetained"], "partialRetained")

    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, "stage=" + stage]
    rejected: list[str] = []
    if requested and acknowledged and owns:
        rejected.append(EARLY_ACK)
        reasons.append("cancellation was acknowledged while a worker still owns the output")
    if requested and published == "accepted":
        rejected.append(PUBLISHED)
        reasons.append("a cancelled job was published as accepted")
    if late:
        rejected.append(LATE_CALLBACK)
        reasons.append(NEGATIVE)
    if requested and not owns and acknowledged and not late and published != "accepted":
        reasons.append("cancellation acknowledged after ownership was released")
    if requested and owns and not acknowledged:
        reasons.append("cancellation is pending until the worker releases ownership")
    if retained:
        reasons.append("partial output remains retained")
    else:
        reasons.append("no partial output was retained")
    if not requested and not late and published != "accepted":
        reasons.append("job was not cancelled")
    decision = "rejected" if rejected else "recorded"
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence, "stage=" + stage, "partialRetained=" + str(retained).lower()],
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
