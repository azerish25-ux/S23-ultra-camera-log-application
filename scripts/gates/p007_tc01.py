"""TC-P007-01 provenance and unsupported-certainty gate.

Profile identity is the sha256 content hash. Matching display names do not
merge distinct versions. Unknown or denied redistribution rights exclude an
image from the public bundle. An unsupported physical claim cannot be reported
as established or allowed; the narrower software result stays preserved.
"""

from __future__ import annotations

CASE_ID = "TC-P007-01"
_RIGHTS = frozenset({"unknown", "permitted", "denied"})
_NON_PHYSICAL = frozenset({"emulator", "simulated", "unavailable_probe"})
_KEYS = (
    "caseId",
    "profiles",
    "image",
    "unsupportedPhysicalClaim",
    "claimText",
    "softwareResult",
    "openQuestion",
    "evidenceKind",
)


def evaluate(payload: dict) -> dict:
    """Return the TC-P007-01 disposition for a provenance payload."""
    data = _validate(payload)
    preserved: list[str] = []
    rejected: list[str] = []
    questions: list[str] = []
    reasons: list[str] = []

    seen: list[str] = []
    by_name: dict[str, list[str]] = {}
    for profile in data["profiles"]:
        digest = profile["sha256"]
        name = profile["displayName"]
        if digest not in seen:
            seen.append(digest)
            preserved.append(digest)
        hashes = by_name.setdefault(name, [])
        if digest not in hashes:
            hashes.append(digest)

    collided = [name for name, hashes in by_name.items() if len(hashes) > 1]
    if collided:
        listed = "; ".join(
            f"{name} -> {', '.join(by_name[name])}" for name in collided
        )
        reasons.append(
            "profiles with the same display name and different sha256 stay distinct "
            f"versions and are not keyed only by display name: {listed}"
        )
    else:
        reasons.append(
            "profile identity is the sha256 content hash, not the display name"
        )

    image_id = data["image"]["id"]
    rights = data["image"]["rights"]
    if rights == "permitted":
        preserved.append(image_id)
        reasons.append(
            f"image {image_id} redistribution is permitted and may enter the public bundle"
        )
    else:
        rejected.append(image_id)
        reasons.append(
            f"image {image_id} excluded from the public bundle: redistribution {rights}"
        )

    kind = data["evidenceKind"]
    if kind in _NON_PHYSICAL:
        reasons.append(
            f"evidence kind {kind} does not establish physical behavior"
        )

    if data["unsupportedPhysicalClaim"]:
        rejected.append(data["claimText"])
        preserved.append(data["softwareResult"])
        questions.append(data["openQuestion"])
        reasons.append(
            "unsupported physical claim rejected; narrower software result preserved; "
            "open research question retained; physical behavior is not established"
        )
        decision = "software_only"
    elif rights == "permitted":
        reasons.append(
            "distinct profile versions accepted with permitted redistribution"
        )
        decision = "accepted"
    else:
        reasons.append(
            "public bundle excludes the image until redistribution is permitted"
        )
        decision = "excluded"

    if decision in {"established", "allowed"}:
        raise ValueError("decision must not be established or allowed")
    if kind in _NON_PHYSICAL and decision == "established":
        raise ValueError("non-physical evidence must not be established")

    return _finish(decision, reasons, rejected, preserved, questions)


def _validate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    missing = [key for key in _KEYS if key not in payload]
    if missing:
        raise ValueError(f"bad payload: missing {', '.join(missing)}")
    if payload["caseId"] != CASE_ID:
        raise ValueError(f"wrong caseId: {payload['caseId']!r}")
    image = payload["image"]
    if not isinstance(image, dict):
        raise ValueError("image must be a dict")
    for key in ("id", "rights"):
        if key not in image:
            raise ValueError(f"bad payload: image missing {key}")
    rights = image["rights"]
    if rights not in _RIGHTS:
        raise ValueError(f"bad image rights: {rights!r}")
    return {
        "profiles": _profiles(payload["profiles"]),
        "image": {"id": _text(image["id"], "image.id"), "rights": rights},
        "unsupportedPhysicalClaim": _flag(
            payload["unsupportedPhysicalClaim"], "unsupportedPhysicalClaim"
        ),
        "claimText": _text(payload["claimText"], "claimText"),
        "softwareResult": _text(payload["softwareResult"], "softwareResult"),
        "openQuestion": _text(payload["openQuestion"], "openQuestion"),
        "evidenceKind": _text(payload["evidenceKind"], "evidenceKind"),
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
    lists = {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    for label, items in lists.items():
        if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
            raise ValueError(f"{label} must be a list of strings")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
