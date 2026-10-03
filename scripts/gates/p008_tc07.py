"""TC-P008-07 concurrent collaborator change.

Preserve collaborator work and the remote commit. A local build must not
invent phase completion or erase a concurrent change.
"""

from __future__ import annotations

CASE_ID = "TC-P008-07"

_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_PAYLOAD_KEYS = (
    "collaborator",
    "integratedRevision",
    "remoteCommit",
    "localBuildSucceeded",
)

_COLLABORATOR_KEYS = (
    "present",
    "preserved",
    "overlapping",
    "remoteHeadChanged",
    "content",
)


def evaluate(payload: object) -> dict:
    """Judge a concurrent collaborator handoff.

    Returns exactly caseId, decision, reasons, rejectedClaims,
    preservedResults, and openQuestions. Raises ValueError if payload is
    invalid. reasons is non-empty because this case never decides "allowed".
    """
    data = _payload(payload)
    collaborator = data["collaborator"]
    present = collaborator["present"]
    preserved_flag = collaborator["preserved"]
    overlapping = collaborator["overlapping"]
    remote_head_changed = collaborator["remoteHeadChanged"]
    content = collaborator["content"]
    integrated_revision = data["integratedRevision"]
    remote_commit = data["remoteCommit"]
    local_build_succeeded = data["localBuildSucceeded"]

    if present and not preserved_flag:
        decision = "blocked"
        reasons = [
            "collaborator modification was not preserved",
            "resetting collaborator work for a clean demonstration is rejected",
        ]
        if overlapping:
            reasons.append(
                "overlapping assumptions cannot be re-evaluated after a reset"
            )
        if remote_head_changed:
            reasons.append(
                "remote head changed before push and must still be preserved"
            )
        if local_build_succeeded:
            reasons.append(
                "local build success does not flip a blocked handoff to complete or allowed"
            )
        else:
            reasons.append("local build failure does not change the blocked decision")
        rejected = ["clean-demonstration-reset"]
        preserved = {"content": content, "remoteCommit": remote_commit}
        open_questions: list[str] = []
    elif present and preserved_flag:
        decision = "integrated"
        reasons = ["collaborator modification is preserved"]
        if overlapping:
            reasons.append("overlapping assumptions were re-evaluated")
        if remote_head_changed:
            reasons.append(
                "remote head changed before push and is preserved in the integrated state"
            )
        if not overlapping and not remote_head_changed:
            reasons.append(
                "integrated revision reports the preserved collaborator state"
            )
        if local_build_succeeded:
            reasons.append("local build success does not establish phase completion")
        else:
            reasons.append(
                "local build has not succeeded and is not treated as completion"
            )
        rejected = []
        preserved = {
            "content": content,
            "integratedRevision": integrated_revision,
            "remoteCommit": remote_commit,
        }
        open_questions = []
    else:
        decision = "unchanged"
        reasons = [
            "no concurrent collaborator modification is present",
            "remote commit is preserved",
        ]
        if remote_head_changed:
            reasons.append("remote head changed before push and is preserved")
        if local_build_succeeded:
            reasons.append("local build success does not invent completion")
        else:
            reasons.append(
                "absence of a collaborator change leaves the handoff unchanged"
            )
        rejected = []
        preserved = {"remoteCommit": remote_commit}
        open_questions = []

    return _result(decision, reasons, rejected, preserved, open_questions)


def _payload(payload: object) -> dict:
    if type(payload) is not dict:
        raise ValueError("payload must be a dict")
    missing = [key for key in _PAYLOAD_KEYS if key not in payload]
    extra = [key for key in payload if key not in _PAYLOAD_KEYS]
    if missing or extra:
        raise ValueError(
            "payload keys are invalid:"
            f" missing={missing or '[]'} extra={extra or '[]'}"
        )
    collaborator = payload["collaborator"]
    if type(collaborator) is not dict:
        raise ValueError("collaborator must be a dict")
    c_missing = [key for key in _COLLABORATOR_KEYS if key not in collaborator]
    c_extra = [key for key in collaborator if key not in _COLLABORATOR_KEYS]
    if c_missing or c_extra:
        raise ValueError(
            "collaborator keys are invalid:"
            f" missing={c_missing or '[]'} extra={c_extra or '[]'}"
        )
    for flag in ("present", "preserved", "overlapping", "remoteHeadChanged"):
        if type(collaborator[flag]) is not bool:
            raise ValueError(f"collaborator.{flag} must be a bool")
    revision = payload["integratedRevision"]
    if type(revision) is not str or revision.strip() == "":
        raise ValueError("integratedRevision must be a non-empty string")
    commit = payload["remoteCommit"]
    if type(commit) is not str or commit.strip() == "":
        raise ValueError("remoteCommit must be a non-empty string")
    if type(payload["localBuildSucceeded"]) is not bool:
        raise ValueError("localBuildSucceeded must be a bool")
    return payload


def _result(decision, reasons, rejected, preserved, open_questions) -> dict:
    if decision in ("complete", "allowed"):
        raise ValueError("completion must not be invented")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": dict(preserved),
        "openQuestions": list(open_questions),
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("result keys are invalid")
    return result
