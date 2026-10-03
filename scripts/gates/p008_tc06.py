"""TC-P008-06. Uncontrolled threshold revision.

Loosening a failing acceptance threshold without review and a recorded version
keeps the original failure. A reviewed, versioned revision is still not phase
completion. P008 never treats a local build as completion: the remote commit is
preserved and a pending physical-device gate stays open.
"""

from __future__ import annotations

from typing import Any

CASE_ID = "TC-P008-06"
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: Any) -> dict[str, Any]:
    """Judge a threshold revision. Never returns allowed or complete."""
    threshold, remote_commit, local_build = _parse(payload)
    name = threshold["name"]
    loosened = threshold["loosened"]
    reviewed = threshold["reviewed"]
    version_recorded = threshold["versionRecorded"]
    original_failed = threshold["originalFailed"]
    failure = f"original-failure:{name}"
    questions = ["physical-device gate pending"]
    reasons = [
        "Physical-device gate is pending, so the phase is not complete.",
        f"Remote commit {remote_commit} is preserved.",
    ]
    if local_build:
        reasons.append("Local build success does not erase the original failure or mark the phase complete.")
    else:
        reasons.append("Local build status is not a substitute for the threshold record.")

    if loosened and not (reviewed and version_recorded):
        reasons.append(
            f"Threshold {name} was loosened without both a review and a recorded version; "
            "the original failure stands and a retrospective pass is rejected."
        )
        questions.append(f"reviewed protocol revision required for {name}")
        return _result(
            "blocked",
            reasons,
            [name, "original-pass"],
            [failure, remote_commit],
            questions,
        )

    if loosened and reviewed and version_recorded:
        reasons.append(
            f"Threshold {name} has a reviewed versioned revision; "
            "that is a protocol revision, not phase completion, and not an original pass."
        )
        questions.append(f"renewed independent validation required for {name}")
        preserved = [remote_commit]
        rejected = ["original-pass", "phase-complete"]
        if original_failed:
            preserved = [failure, remote_commit]
            reasons.append(f"Original failure of {name} remains recorded alongside the reviewed revision.")
        return _result("reviewed_revision", reasons, rejected, preserved, questions)

    if original_failed:
        reasons.append(f"Threshold {name} failed and was not revised; the original failure stands.")
        return _result(
            "failed",
            reasons,
            [name],
            [failure, remote_commit],
            questions,
        )

    reasons.append(f"Threshold {name} is unchanged and did not originally fail; the phase is still not complete.")
    return _result("unchanged", reasons, [], [remote_commit], questions)


def _parse(payload: Any) -> tuple[dict[str, Any], str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    for key in ("threshold", "remoteCommit", "localBuildSucceeded"):
        if key not in payload:
            raise ValueError(f"payload missing {key}")
    raw = payload["threshold"]
    if not isinstance(raw, dict):
        raise ValueError("threshold must be an object")
    for key in ("name", "loosened", "reviewed", "versionRecorded", "originalFailed"):
        if key not in raw:
            raise ValueError(f"threshold missing {key}")
    name = raw["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError("threshold.name must be a non-empty string")
    flags = {}
    for key in ("loosened", "reviewed", "versionRecorded", "originalFailed"):
        if type(raw[key]) is not bool:
            raise ValueError(f"threshold.{key} must be a boolean")
        flags[key] = raw[key]
    remote_commit = payload["remoteCommit"]
    if not isinstance(remote_commit, str) or not remote_commit.strip():
        raise ValueError("remoteCommit must be a non-empty string")
    local_build = payload["localBuildSucceeded"]
    if type(local_build) is not bool:
        raise ValueError("localBuildSucceeded must be a boolean")
    threshold = {"name": name.strip(), **flags}
    return threshold, remote_commit, local_build


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    if decision in {"allowed", "complete"}:
        raise ValueError("P008 must not mark the phase allowed or complete")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    body = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(body) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return body
