#!/usr/bin/env python3
"""P041 calibrated profile contract.

A profile is an accountable measurement record: source identity, matrix
direction, white point, exposure scale, crop, CFA, illuminant, black model,
defect policy, and fit provenance. Measured, manufacturer-derived provisional,
and synthetic profiles stay separate. The complete numerical payload is hashed.
Nonfinite values are rejected. The author assertion is retained separately and
never becomes certified status.

The deliberate mutant — promote any imported profile whose author string says
measured to certified status — is rejected. This module does not probe a
device, does not qualify a physical S23, and does not execute TC-P041-01
through TC-P041-08.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any


PHASE = "P041"
CASE_ID = "P041"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-calibrated-profile-fixture"
METHOD = (
    "Specify source identity, matrix direction, white point, exposure scale, crop, "
    "CFA assumptions, illuminant, black model, defect policy, and fit provenance. "
    "Separate measured, manufacturer-derived provisional, and synthetic profiles. "
    "Hash the complete numerical payload and reject nonfinite values."
)
FIXTURE = (
    "A profile labelled measured but lacking measurement references, plus a synthetic "
    "profile offered for physical footage."
)
ORACLE = (
    "The importer retains the author assertion separately and refuses synthetic "
    "evidence as physical calibration."
)
MUTANT = "Promote any imported profile with a measured string to certified status."
HOST_LIMIT = "this host record does not qualify a physical S23"

CATEGORIES = ("measured", "manufacturer-provisional", "synthetic")
OFFERED = ("physical", "synthetic-fixture", "research")
DIRECTIONS = ("camera-rgb-to-xyz-d50", "xyz-d50-to-camera-rgb")
WHITE_POINTS = ("D50", "D65")
ILLUMINANTS = ("D50", "D65", "A", "D55", "D75")
CFAS = ("RGGB", "GRBG", "GBRG", "BGGR")
DEFECT_POLICIES = ("retain-signed", "clamp-zero")
NONFINITE = ("NaN", "nan", "Infinity", "infinity", "inf", "-Infinity", "-infinity", "-inf")

HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
CROP = re.compile(r"^[1-9][0-9]*x[1-9][0-9]*\+(?:0|[1-9][0-9]*)\+(?:0|[1-9][0-9]*)$")
FINITE = re.compile(r"^(?:0|-?0\.[0-9]*[1-9]|-?[1-9][0-9]*(?:\.[0-9]*[1-9])?)$")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "profiles",
}
PROFILE_KEYS = {
    "id",
    "authorAssertion",
    "category",
    "offeredFor",
    "sourceIdentity",
    "matrixDirection",
    "matrix",
    "whitePoint",
    "exposureScale",
    "crop",
    "cfa",
    "illuminant",
    "blackModel",
    "defectPolicy",
    "fitProvenance",
    "payloadHash",
}
SOURCE_KEYS = {"handset", "firmware", "route", "logicalCamera"}
BLACK_KEYS = {"offset", "rowBias", "columnBias"}
FIT_KEYS = {"fitId", "measurementReferences"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "provisional", "measurement_record"}
_FORBIDDEN = {"qualified", "allowed", "certified"}


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


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _finite_or_token(value: object, label: str) -> str:
    require(isinstance(value, str), label + " must be a string")
    if value in NONFINITE or FINITE.fullmatch(value) is not None:
        return value
    raise ValueError(label + " must be a canonical finite decimal or a nonfinite token")


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def numerical_payload(profile: dict) -> dict[str, Any]:
    """Canonical numerical payload. Strings are hashed, not binary floats."""
    black = profile["blackModel"]
    return {
        "blackModel": {
            "columnBias": black["columnBias"],
            "offset": black["offset"],
            "rowBias": black["rowBias"],
        },
        "crop": profile["crop"],
        "exposureScale": profile["exposureScale"],
        "matrix": profile["matrix"],
        "matrixDirection": profile["matrixDirection"],
        "whitePoint": profile["whitePoint"],
    }


def payload_digest(profile: dict) -> str:
    """SHA-256 of the canonical JSON numerical payload."""
    blob = json.dumps(numerical_payload(profile), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def profile_token(profile: dict) -> str:
    """Stable inventory token. The author assertion is not rewritten."""
    source = profile["sourceIdentity"]
    return (
        f"{profile['id']}|assertion={profile['authorAssertion']}"
        f"|category={profile['category']}|offered={profile['offeredFor']}"
        f"|source={source['handset']}/{source['firmware']}/{source['route']}/{source['logicalCamera']}"
        f"|hash={profile['payloadHash']}"
    )


def _nonfinite_fields(profile: dict) -> list[str]:
    found: list[str] = []
    scale = profile["exposureScale"]
    if scale in NONFINITE:
        found.append("exposureScale")
    for row_index, row in enumerate(profile["matrix"]):
        for col_index, cell in enumerate(row):
            if cell in NONFINITE:
                found.append(f"matrix[{row_index}][{col_index}]")
    black = profile["blackModel"]
    for key in ("offset", "rowBias", "columnBias"):
        if black[key] in NONFINITE:
            found.append("blackModel." + key)
    return found


def _matrix(value: object, label: str) -> list[list[str]]:
    require(isinstance(value, list) and len(value) == 3, label + " must be 3 rows")
    rows: list[list[str]] = []
    for row_index, row in enumerate(value):
        require(isinstance(row, list) and len(row) == 3, f"{label} row {row_index} must have 3 cells")
        rows.append([_finite_or_token(cell, f"{label}[{row_index}][{col}]") for col, cell in enumerate(row)])
    return rows


def _profile(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, PROFILE_KEYS, f"profiles[{index}]")
    ident = _token(item["id"], f"profiles[{index}] id")
    require(ident not in seen, "duplicate profile id " + ident)
    seen.add(ident)
    _token(item["authorAssertion"], f"profiles[{index}] authorAssertion")
    require(item["category"] in CATEGORIES, f"profiles[{index}] category is not measured, provisional, or synthetic")
    require(item["offeredFor"] in OFFERED, f"profiles[{index}] offeredFor is unknown")
    source = exact_keys(item["sourceIdentity"], SOURCE_KEYS, f"profiles[{index}] sourceIdentity")
    for key in ("handset", "firmware", "route", "logicalCamera"):
        _token(source[key], f"profiles[{index}] sourceIdentity.{key}")
    require(item["matrixDirection"] in DIRECTIONS, f"profiles[{index}] matrixDirection is unknown")
    _matrix(item["matrix"], f"profiles[{index}] matrix")
    require(item["whitePoint"] in WHITE_POINTS, f"profiles[{index}] whitePoint is unknown")
    _finite_or_token(item["exposureScale"], f"profiles[{index}] exposureScale")
    require(isinstance(item["crop"], str) and CROP.fullmatch(item["crop"]) is not None,
            f"profiles[{index}] crop must look like 4000x3000+0+0")
    require(item["cfa"] in CFAS, f"profiles[{index}] cfa is unknown")
    require(item["illuminant"] in ILLUMINANTS, f"profiles[{index}] illuminant is unknown")
    black = exact_keys(item["blackModel"], BLACK_KEYS, f"profiles[{index}] blackModel")
    for key in ("offset", "rowBias", "columnBias"):
        _finite_or_token(black[key], f"profiles[{index}] blackModel.{key}")
    require(item["defectPolicy"] in DEFECT_POLICIES, f"profiles[{index}] defectPolicy is unknown")
    fit = exact_keys(item["fitProvenance"], FIT_KEYS, f"profiles[{index}] fitProvenance")
    _token(fit["fitId"], f"profiles[{index}] fitId")
    refs = fit["measurementReferences"]
    require(isinstance(refs, list), f"profiles[{index}] measurementReferences must be a list")
    require(len(refs) <= 16, f"profiles[{index}] measurementReferences exceed the harness bound")
    require(all(isinstance(ref, str) and TOKEN.fullmatch(ref) is not None for ref in refs),
            f"profiles[{index}] measurementReferences must be tokens")
    require(len(refs) == len(set(refs)), f"profiles[{index}] measurementReferences must be unique")
    require(isinstance(item["payloadHash"], str) and HEX64.fullmatch(item["payloadHash"]) is not None,
            f"profiles[{index}] payloadHash must be 64 lowercase hex characters")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P041 profile-contract shape."""
    exact_keys(document, DOCUMENT_KEYS, "profile document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P041")
    require(document["mapId"] == MAP_ID, "mapId must be s23-calibrated-profile-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "profile document needs the P041 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    profiles = document["profiles"]
    require(isinstance(profiles, list) and 1 <= len(profiles) <= 8, "profiles must be a list of 1 to 8")
    seen: set[str] = set()
    for index, profile in enumerate(profiles):
        _profile(profile, index, seen)


def _classify(profile: dict) -> tuple[str, list[str], list[str], list[str]]:
    ident = profile["id"]
    category = profile["category"]
    assertion = profile["authorAssertion"]
    offered = profile["offeredFor"]
    refs = profile["fitProvenance"]["measurementReferences"]
    claims: list[str] = []
    reasons: list[str] = []
    questions: list[str] = []
    if assertion != category and not (category == "manufacturer-provisional" and assertion == "provisional"):
        questions.append(f"{ident} author assertion {assertion} is not importer status")
    if profile["defectPolicy"] == "clamp-zero":
        claims.append(f"clamped-defect-policy:{ident}")
        reasons.append(f"{ident} defect policy clamps residuals before they are recorded")
        return "rejected-defect-policy", claims, reasons, questions
    if category == "synthetic":
        claims.append(f"synthetic-not-physical:{ident}")
        reasons.append(f"{ident} synthetic evidence is refused as physical calibration")
        if offered == "physical":
            claims.append(f"synthetic-as-physical:{ident}")
            reasons.append(f"{ident} synthetic profile was offered for physical footage")
            return "rejected-synthetic-physical", claims, reasons, questions
        return "synthetic_retained", claims, reasons, questions
    if category == "manufacturer-provisional":
        reasons.append(f"{ident} manufacturer-derived profile stays provisional")
        questions.append(f"{ident} provisional is not a measured profile")
        if assertion == "measured":
            claims.append(f"measured-assertion-on-provisional:{ident}")
            reasons.append(f"{ident} author assertion measured does not upgrade a provisional profile")
        return "provisional", claims, reasons, questions
    if not refs:
        claims.append(f"unreferenced-measured-label:{ident}")
        reasons.append(f"{ident} is labelled measured but lacks measurement references")
        questions.append(f"{ident} retained for exploratory research")
        return "rejected-unreferenced", claims, reasons, questions
    reasons.append(f"{ident} measurement references stay bound to the numerical payload")
    questions.append(f"{ident} measurement record is not certified status")
    return "measurement_record", claims, reasons, questions


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P041 must not decide qualified, allowed, or certified")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": _dedupe(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _decision_for(statuses: list[str], claims: list[str], promote: bool) -> str:
    if promote:
        return "rejected"
    hard = {
        "rejected-nonfinite",
        "rejected-hash",
        "rejected-defect-policy",
        "rejected-unreferenced",
        "rejected-synthetic-physical",
    }
    if any(status in hard for status in statuses):
        return "rejected"
    if any(claim.startswith("synthetic-as-physical:") for claim in claims):
        return "rejected"
    if statuses and all(status == "measurement_record" for status in statuses):
        return "measurement_record"
    if statuses and all(status == "provisional" for status in statuses):
        return "provisional"
    return "withheld"


def assess(document: dict, promote_measured_string: bool = False) -> dict:
    """Import profiles without promoting a measured string to certified status.

    promote_measured_string True is the mutant. It is rejected even when an
    author assertion is the string measured. Author assertions stay in
    preservedResults and are not the importer status. Synthetic profiles are
    refused as physical calibration.
    """
    validate_document(document)
    require(type(promote_measured_string) is bool, "promote_measured_string must be a bool")
    preserved: list[str] = []
    rejected: list[str] = []
    questions = [
        "author assertion is retained separately from importer status",
        "host fixture is not physical S23 qualification",
    ]
    reasons = [ORACLE, "measured, provisional, and synthetic profiles stay separate"]
    statuses: list[str] = []
    for profile in document["profiles"]:
        ident = profile["id"]
        preserved.append(profile_token(profile))
        preserved.append(f"assertion:{ident}:{profile['authorAssertion']}")
        digest = payload_digest(profile)
        preserved.append(f"computed-hash:{ident}:{digest}")
        nonfinite = _nonfinite_fields(profile)
        status: str | None = None
        if nonfinite:
            rejected.append(f"nonfinite:{ident}:{','.join(nonfinite)}")
            reasons.append(f"{ident} numerical payload is not finite")
            status = "rejected-nonfinite"
        else:
            if digest != profile["payloadHash"]:
                rejected.append(f"payload-hash-mismatch:{ident}")
                reasons.append(f"{ident} payload hash does not match the numerical payload")
                status = "rejected-hash"
            class_status, claims, extra_reasons, extra_questions = _classify(profile)
            if status is None:
                status = class_status
            rejected.extend(claims)
            reasons.extend(extra_reasons)
            questions.extend(extra_questions)
        statuses.append(status)
        preserved.append(f"importer-status:{ident}:{status}")
        if profile["authorAssertion"] == "measured":
            reasons.append(f"{ident} author assertion measured was not promoted")
    decision = _decision_for(statuses, rejected, promote_measured_string)
    if promote_measured_string:
        rejected.insert(0, "measured-string-to-certified")
        reasons.append(MUTANT)
        reasons.append("a measured string is not certified status")
        questions.append("measured-string promotion was rejected")
    if decision == "measurement_record":
        reasons.append("the importer recorded references and did not certify the profile")
        questions.append("measurement record is not certified status")
    if decision == "provisional":
        reasons.append("manufacturer-derived profiles were not treated as measured")
    if decision == "withheld":
        reasons.append("synthetic or mixed evidence was withheld from physical calibration")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
