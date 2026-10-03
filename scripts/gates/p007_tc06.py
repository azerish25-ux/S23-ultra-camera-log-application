"""TC-P007-06 uncontrolled threshold-revision gate.

Loosening a threshold without both a review and a recorded version is blocked.
The original failure is retained and the loosened threshold is never an original
pass or an allowed decision. A loosening that was reviewed and versioned is only
a reviewed revision. An unloosened threshold stays failed or unchanged.
Distinct profile sha256 identities are preserved; display names do not merge them.
"""

from __future__ import annotations

CASE_ID = "TC-P007-06"
_DECISIONS = frozenset({"blocked", "reviewed_revision", "failed", "unchanged"})
_KEYS = ("caseId", "threshold", "profiles")
_THRESHOLD_KEYS = ("name", "loosened", "reviewed", "versionRecorded", "originalFailed")


def evaluate(payload: dict) -> dict:
    """Return the TC-P007-06 disposition for a threshold-revision payload."""
    data = _validate(payload)
    threshold = data["threshold"]
    name = threshold["name"]
    loosened = threshold["loosened"]
    reviewed = threshold["reviewed"]
    versioned = threshold["versionRecorded"]
    original_failed = threshold["originalFailed"]
    hashes = _distinct_hashes(data["profiles"])
    profile_reason = _profile_reason(data["profiles"])
    failure = f"original-failure:{name}"

    if loosened and not (reviewed and versioned):
        reasons = [
            f"Threshold {name!r} was loosened without both a review and a recorded version.",
            "The original failure is retained. The loosened threshold is not an original pass.",
            profile_reason,
        ]
        questions = [
            "A reviewed protocol revision with a recorded version and renewed "
            "independent validation is required."
        ]
        return _finish("blocked", reasons, [name], [failure, *hashes], questions)

    if loosened:
        preserved = [failure, *hashes] if original_failed else list(hashes)
        reasons = [
            f"Threshold {name!r} loosening is a reviewed revision with a recorded version.",
            "This is not a claim that the original run passed.",
            profile_reason,
        ]
        return _finish("reviewed_revision", reasons, [], preserved, [])

    if original_failed:
        reasons = [
            f"Threshold {name!r} was not loosened and the original result failed.",
            profile_reason,
        ]
        return _finish("failed", reasons, [], [failure, *hashes], [])

    reasons = [
        f"Threshold {name!r} was not loosened and the original result did not fail.",
        profile_reason,
    ]
    return _finish("unchanged", reasons, [], list(hashes), [])


def _validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    missing = [key for key in _KEYS if key not in payload]
    if missing:
        raise ValueError(f"bad payload: missing {', '.join(missing)}")
    if payload["caseId"] != CASE_ID:
        raise ValueError(f"wrong caseId: {payload['caseId']!r}")
    return {"threshold": _threshold(payload["threshold"]), "profiles": _profiles(payload["profiles"])}


def _threshold(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("threshold must be a dict")
    missing = [key for key in _THRESHOLD_KEYS if key not in value]
    if missing:
        raise ValueError(f"threshold missing {', '.join(missing)}")
    return {
        "name": _text(value["name"], "threshold.name"),
        "loosened": _flag(value["loosened"], "threshold.loosened"),
        "reviewed": _flag(value["reviewed"], "threshold.reviewed"),
        "versionRecorded": _flag(value["versionRecorded"], "threshold.versionRecorded"),
        "originalFailed": _flag(value["originalFailed"], "threshold.originalFailed"),
    }


def _profiles(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        raise ValueError("profiles must be a list")
    profiles: list[dict[str, str]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise ValueError(f"profiles[{index}] must be a dict")
        for key in ("displayName", "sha256"):
            if key not in item:
                raise ValueError(f"profiles[{index}] missing {key}")
        profiles.append(
            {
                "displayName": _text(item["displayName"], f"profiles[{index}].displayName"),
                "sha256": _text(item["sha256"], f"profiles[{index}].sha256"),
            }
        )
    return profiles


def _distinct_hashes(profiles: list[dict[str, str]]) -> list[str]:
    seen: list[str] = []
    for profile in profiles:
        digest = profile["sha256"]
        if digest not in seen:
            seen.append(digest)
    return seen


def _profile_reason(profiles: list[dict[str, str]]) -> str:
    by_name: dict[str, list[str]] = {}
    for profile in profiles:
        hashes = by_name.setdefault(profile["displayName"], [])
        if profile["sha256"] not in hashes:
            hashes.append(profile["sha256"])
    collided = [name for name, hashes in by_name.items() if len(hashes) > 1]
    if collided:
        listed = "; ".join(f"{name} -> {', '.join(by_name[name])}" for name in collided)
        return (
            "profiles with the same display name and different sha256 stay distinct "
            f"versions and are not keyed only by display name: {listed}"
        )
    return "profile identity is the sha256 content hash, not the display name"


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or value == "":
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flag(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _finish(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision == "allowed":
        raise ValueError(f"unexpected decision: {decision}")
    if any(item.startswith("original-pass:") for item in preserved):
        raise ValueError("loosened threshold must not be presented as an original pass")
    lists = {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    for label, items in lists.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{label} must be a list of strings")
    if not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
