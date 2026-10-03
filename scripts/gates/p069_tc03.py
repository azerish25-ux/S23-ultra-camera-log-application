"""TC-P069-03 in-flight resource reuse.

Intervention: Delay completion while the resource pool attempts to recycle a
texture or buffer for a newer frame.
Expected: Honor ownership and synchronization so neither stale nor partially
written data reaches accepted output.
Negative: Recycling immediately after command submission must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P069-03"
INTERVENTION = (
    "Delay completion while the resource pool attempts to recycle a texture or buffer for a newer frame."
)
EXPECTED = (
    "Honor ownership and synchronization so neither stale nor partially written data reaches accepted output."
)
NEGATIVE = "Recycling immediately after command submission must fail."
REPEAT = "Repeat during cancellation, context loss, and rapid mode switching."

_KINDS = ("texture", "buffer")
_OUTPUTS = ("none", "fresh", "stale", "partial")
_SITES = ("baseline", "cancellation", "context-loss", "mode-switch")
_PAYLOAD_KEYS = (
    "resourceId",
    "kind",
    "completionDelayed",
    "recycleImmediate",
    "ownershipHeld",
    "synchronized",
    "outputState",
    "site",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "ownership_held"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Keep ownership across a delayed completion, or reject an immediate recycle."""
    resource, kind, delayed, immediate, ownership, synced, output, site = _payload(payload)
    preserved = [
        resource,
        f"kind:{kind}",
        f"delayed:{str(delayed).lower()}",
        f"ownership:{str(ownership).lower()}",
        f"synchronized:{str(synced).lower()}",
        f"output:{output}",
        f"site:{site}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"site {site}"]
    rejected: list[str] = []
    if immediate:
        rejected.append("immediate-recycle")
        reasons.append(NEGATIVE)
        reasons.append(f"{kind} {resource} was not recycled at submission")
    if output in {"stale", "partial"}:
        rejected.append("stale-or-partial-output")
        reasons.append(f"{output} data on {resource} must not reach accepted output")
    if rejected:
        decision = "rejected"
        questions.append(f"{resource} identity was retained after the rejected recycle")
    elif ownership and synced and output in {"none", "fresh"}:
        decision = "ownership_held"
        reasons.append(f"ownership of {resource} was held while completion delayed={str(delayed).lower()}")
    else:
        decision = "withheld"
        reasons.append("ownership or synchronization was incomplete, so output was not accepted")
        questions.append(f"{resource} was not recycled and was not accepted")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    resource = payload["resourceId"]
    if not isinstance(resource, str) or _TOKEN.fullmatch(resource) is None:
        raise ValueError("resourceId must be a token")
    kind = payload["kind"]
    if kind not in _KINDS:
        raise ValueError("kind must be texture or buffer")
    delayed = payload["completionDelayed"]
    immediate = payload["recycleImmediate"]
    ownership = payload["ownershipHeld"]
    synced = payload["synchronized"]
    for name, value in (
        ("completionDelayed", delayed),
        ("recycleImmediate", immediate),
        ("ownershipHeld", ownership),
        ("synchronized", synced),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    output = payload["outputState"]
    if output not in _OUTPUTS:
        raise ValueError("outputState is unsupported")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    return resource, kind, delayed, immediate, ownership, synced, output, site


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P069-03 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
