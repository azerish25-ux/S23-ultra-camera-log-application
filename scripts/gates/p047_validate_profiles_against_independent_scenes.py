#!/usr/bin/env python3
"""P047 independent profile acceptance on a host fixture.

Held-out skin, foliage, fabric, neutral, colored-light, and high-contrast
scenes are scored on color, exposure, noise, highlight, and neutral gates.
Artistic preference is inventoried and is not a calibration error term.

The deliberate mutant — treating a preferred cinematic appearance as proof of
camera colorimetric accuracy — is rejected. This module does not probe a
device, does not qualify a physical S23, and does not execute TC-P047-01
through TC-P047-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P047"
CASE_ID = "P047"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-independent-profile-acceptance-fixture"
METHOD = (
    "Use skin, foliage, fabrics, neutral steps, colored lights, and high-contrast "
    "scenes not used for fitting. Capture repeat conditions and assess color, "
    "exposure, noise, and highlight behaviour separately. Keep artistic preference "
    "scores out of calibration error calculations."
)
FIXTURE = (
    "A profile that makes one skin sample attractive while moving neutral greys "
    "and saturated fabric beyond the declared tolerance."
)
ORACLE = "The neutral and color gates fail independently of subjective preference."
MUTANT = "Use a preferred cinematic appearance as proof of camera colorimetric accuracy."
LIMITATION = (
    "Host acceptance is not a phone default, not colorimetric accuracy, and not "
    "physical S23 qualification. Neutral and color failures stay independent of "
    "artistic preference."
)
SCENE_CLASSES = (
    "skin",
    "foliage",
    "fabrics",
    "neutral",
    "colored-light",
    "high-contrast",
)
APPEARANCES = ("preferred-cinematic", "neutral", "unspecified")
DELTA_FIELDS = (
    "colorDelta",
    "exposureDelta",
    "noiseDelta",
    "highlightDelta",
    "neutralDelta",
)
SEPARATE_GATES = (
    ("colorDelta", "color-gate"),
    ("exposureDelta", "exposure-gate"),
    ("noiseDelta", "noise-gate"),
    ("highlightDelta", "highlight-gate"),
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
IDENT = re.compile(r"[a-z0-9-]{1,64}")
REPEAT = re.compile(r"[A-Za-z0-9._-]{1,32}")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "limitation",
    "tolerance",
    "profile",
    "training",
    "scenes",
}
TOLERANCE_KEYS = set(DELTA_FIELDS)
PROFILE_KEYS = {"id", "appearance", "preferenceScore"}
TRAINING_KEYS = {"error", "patchIds"}
SCENE_KEYS = {
    "id",
    "sceneClass",
    "repeatId",
    "usedForFitting",
    "colorDelta",
    "exposureDelta",
    "noiseDelta",
    "highlightDelta",
    "neutralDelta",
    "preferenceScore",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld"}
_FORBIDDEN = {"qualified", "allowed", "colorimetric"}
MUTANT_CLAIM = "preferred-cinematic-as-colorimetric-accuracy"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, label: str, pattern: re.Pattern[str]) -> str:
    require(
        isinstance(value, str) and pattern.fullmatch(value) is not None,
        label + " is not canonical",
    )
    return value


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    return value


def _unit_interval(value: object, label: str) -> str:
    text = _decimal(value, label)
    number = Decimal(text)
    require(Decimal("0") <= number <= Decimal("1"), label + " must be from 0 through 1")
    return text


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN, "P047 decision is not a qualification")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _scene(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, SCENE_KEYS, f"scene {index}")
    ident = _text(item["id"], f"scene {index} id", IDENT)
    require(ident not in seen, "duplicate scene id: " + ident)
    seen.add(ident)
    require(item["sceneClass"] in SCENE_CLASSES, f"scene {index} sceneClass is unsupported")
    _text(item["repeatId"], f"scene {index} repeatId", REPEAT)
    require(type(item["usedForFitting"]) is bool, f"scene {index} usedForFitting must be a bool")
    for field in ("colorDelta", "exposureDelta", "noiseDelta", "highlightDelta"):
        _decimal(item[field], f"scene {index} {field}")
    neutral = item["neutralDelta"]
    if item["sceneClass"] == "neutral":
        _decimal(neutral, f"scene {index} neutralDelta")
    else:
        require(neutral is None, f"scene {index} neutralDelta must be null off the neutral class")
    _unit_interval(item["preferenceScore"], f"scene {index} preferenceScore")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P047 acceptance schema."""
    exact_keys(document, DOCUMENT_KEYS, "profile acceptance document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P047")
    require(document["mapId"] == MAP_ID, "mapId must be s23-independent-profile-acceptance-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "profile acceptance document needs the P047 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["limitation"] == LIMITATION, "limitation text drifted")
    tolerance = exact_keys(document["tolerance"], TOLERANCE_KEYS, "tolerance")
    for field in DELTA_FIELDS:
        _decimal(tolerance[field], "tolerance " + field)
        require(Decimal(tolerance[field]) > 0, "tolerance " + field + " must be positive")
    profile = exact_keys(document["profile"], PROFILE_KEYS, "profile")
    _text(profile["id"], "profile id", IDENT)
    require(profile["appearance"] in APPEARANCES, "profile appearance is unsupported")
    _unit_interval(profile["preferenceScore"], "profile preferenceScore")
    training = exact_keys(document["training"], TRAINING_KEYS, "training")
    _decimal(training["error"], "training error")
    patches = training["patchIds"]
    require(type(patches) is list and patches, "training patchIds must be a non-empty list")
    require(len(patches) == len(set(patches)), "training patchIds must be unique")
    for index, patch in enumerate(patches):
        _text(patch, f"training patch {index}", IDENT)
    scenes = document["scenes"]
    require(type(scenes) is list and scenes, "scenes must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(scenes):
        _scene(item, index, seen)
    overlap = seen & set(patches)
    require(not overlap, "training patches overlap held-out scenes: " + ", ".join(sorted(overlap)))
    present = {item["sceneClass"] for item in scenes}
    missing = [name for name in SCENE_CLASSES if name not in present]
    require(not missing, "held-out classes missing: " + ", ".join(missing))
    repeats = {item["repeatId"] for item in scenes}
    require(len(repeats) >= 2, "repeat conditions require at least two repeat ids")
    repeated = False
    for name in SCENE_CLASSES:
        ids = {item["repeatId"] for item in scenes if item["sceneClass"] == name}
        if len(ids) >= 2:
            repeated = True
    require(repeated, "at least one scene class must repeat under distinct repeat ids")


def calibration_error_terms(document: dict) -> list[str]:
    """Return calibration terms. Preference scores are never included."""
    validate_document(document)
    terms = ["training:" + document["training"]["error"]]
    for scene in document["scenes"]:
        for field in DELTA_FIELDS:
            value = scene[field]
            if value is not None:
                terms.append(f"{scene['id']}:{field}:{value}")
    return terms


def gate_failures(document: dict) -> list[str]:
    """Independent gate failures. Subjective preference is not consulted."""
    validate_document(document)
    tolerance = document["tolerance"]
    failed: list[str] = []
    for scene in document["scenes"]:
        if scene["usedForFitting"]:
            failed.append("used-for-fitting:" + scene["id"])
        for field, gate in SEPARATE_GATES:
            if Decimal(scene[field]) > Decimal(tolerance[field]):
                failed.append(f"{gate}:{scene['id']}")
        if scene["sceneClass"] == "neutral" and Decimal(scene["neutralDelta"]) > Decimal(
            tolerance["neutralDelta"]
        ):
            failed.append("neutral-gate:" + scene["id"])
    return failed


def _preserved(document: dict) -> list[str]:
    profile = document["profile"]
    preserved = [
        "profile:" + profile["id"],
        f"preference:{profile['id']}:{profile['preferenceScore']}:not-calibration-error",
        "appearance:" + profile["appearance"] + ":not-colorimetric-proof",
        "training-error:" + document["training"]["error"],
    ]
    for patch in document["training"]["patchIds"]:
        preserved.append("training-patch:" + patch)
    for scene in document["scenes"]:
        preserved.append(
            f"scene:{scene['id']}:{scene['sceneClass']}:repeat:{scene['repeatId']}"
        )
        for field in DELTA_FIELDS:
            value = scene[field]
            preserved.append(f"delta:{scene['id']}:{field}:{'na' if value is None else value}")
        preserved.append(
            f"scene-preference:{scene['id']}:{scene['preferenceScore']}:excluded"
        )
    return preserved


def _questions() -> list[str]:
    return [
        "physical S23 profile acceptance unverified",
        "artistic preference is excluded from calibration error",
        "color, exposure, noise, and highlight gates stay separate",
        LIMITATION,
    ]


def _failure_reasons(failed: list[str]) -> list[str]:
    reasons = [
        ORACLE,
        "artistic preference was excluded from calibration error",
        "profile is not the phone default",
    ]
    for gate, label in (
        ("neutral-gate:", "neutral gate failed"),
        ("color-gate:", "color gate failed"),
        ("exposure-gate:", "exposure gate failed"),
        ("noise-gate:", "noise gate failed"),
        ("highlight-gate:", "highlight gate failed"),
        ("used-for-fitting:", "a fitting scene is not an independent validation scene"),
    ):
        if any(item.startswith(gate) for item in failed):
            reasons.append(label)
    return reasons


def assess(document: dict) -> dict:
    """Fail independent gates without promoting preference to accuracy.

    The fixture decision is ``rejected``. A document inside every tolerance is
    ``withheld``: a host pass is not a phone default. The decision is never
    ``qualified``, ``allowed``, or ``colorimetric``.
    """
    failed = gate_failures(document)
    preserved = _preserved(document)
    questions = _questions()
    if failed:
        return _result("rejected", _failure_reasons(failed), failed, preserved, questions)
    return _result(
        "withheld",
        [
            ORACLE,
            "independent scenes stayed inside declared tolerances",
            "artistic preference was excluded from calibration error",
            "a host pass does not install this profile as the phone default",
            "preferred cinematic appearance is not colorimetric accuracy",
        ],
        [],
        preserved,
        questions,
    )


def apply_preferred_appearance_as_accuracy(document: dict) -> dict:
    """Reject the mutant that treats cinematic preference as colorimetric proof.

    Gate failures already found by ``assess`` stay in ``rejectedClaims``. The
    preference inventory is kept and is still marked as not a calibration error.
    """
    failed = gate_failures(document)
    claims = list(failed)
    claims.append(MUTANT_CLAIM)
    return _result(
        "rejected",
        [
            MUTANT,
            ORACLE,
            "preferred cinematic appearance is not camera colorimetric accuracy",
            "neutral and color gates were not overridden by subjective preference",
        ],
        claims,
        _preserved(document),
        _questions(),
    )
