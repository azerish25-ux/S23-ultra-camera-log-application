#!/usr/bin/env python3
"""P073 stock profiles and evidence-level validator.

Stock behaviour is stored apart from virtual format and final appearance.
Each profile keeps family, balance, response model, parameter units, source
references, licence state, and confidence. Measured parameters stay distinct
from reconstructed artistic controls. Display names are not stable identifiers,
and a numerical change requires a new version.

The fixture holds two creative interpretations of one nominal stock. Their
density curves differ and their source data is uncertain. The catalogue must
expose them as versioned interpretations, not as one calibrated material.

The deliberate mutant — treating a marketing name as proof that every
numerical parameter was physically measured — is rejected. This module does
not probe a device, does not qualify a physical S23, and does not execute
TC-P073-01 through TC-P073-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P073"
CASE_ID = "P073"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-stock-profiles-fixture"
METHOD = (
    "Store stock family, balance, response model, parameter units, source references, "
    "licence state, and confidence. Distinguish measured parameters from reconstructed "
    "artistic controls. Keep display names independent of stable profile identifiers and "
    "version every numerical change."
)
FIXTURE = (
    "Two creative interpretations of the same nominal stock with different density curves "
    "and uncertain source data."
)
ORACLE = (
    "The catalogue exposes them as versioned interpretations rather than falsely identical "
    "calibrated materials."
)
MUTANT = "Use a stock marketing name as proof that all numerical parameters are physically measured."
DECLARED_PATH = "catalogued"
MUTANT_PATH = "marketing-as-measured"
PATHS = (DECLARED_PATH, MUTANT_PATH)
HOST_LIMIT = "host fixture does not qualify a physical S23 or film-stock fidelity"
FAMILIES = ("color-negative", "monochrome", "historical")
BALANCES = ("daylight", "tungsten", "unknown")
MODELS = ("density-curve", "generic-synthetic")
UNITS = ("log-density",)
LICENCES = ("unspecified", "attributed", "restricted")
CONFIDENCE = ("low", "medium", "high")
EVIDENCE = ("measured", "reconstructed", "synthetic")
VIRTUAL_FORMATS = ("none", "log", "display")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
VERSION = re.compile(r"^[1-9][0-9]*$")
DENSITY = re.compile(r"^(?:0|[1-9]\d*)(?:\.[0-9]*[1-9])?$")
DISPLAY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .'-]*$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "nominalStock",
    "profiles",
}
PROFILE_KEYS = {
    "profileId",
    "version",
    "displayName",
    "family",
    "balance",
    "responseModel",
    "parameterUnits",
    "sourceReferences",
    "licenceState",
    "confidence",
    "evidenceLevel",
    "densityCurve",
    "artisticControls",
    "measuredParameters",
    "virtualFormat",
    "appearanceId",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "versioned_interpretations"}
_PROFILE_FAULTS = (
    "display-name-collides-with-id",
    "bound-to-virtual-format",
    "bound-to-appearance",
    "nonmonotonic-density",
    "false-measurement",
    "measured-parameters-on-interpretation",
    "artistic-as-measured",
    "high-confidence-without-measurement",
)
_FAULT_TEXT = {
    "display-name-collides-with-id": "display name is not independent of the stable profile identifier",
    "bound-to-virtual-format": "stock behaviour must stay independent of virtual format",
    "bound-to-appearance": "stock behaviour must stay independent of final film appearance",
    "nonmonotonic-density": "density curve reverses or stalls and is not a released monotonic fit",
    "false-measurement": "measured evidence requires high confidence, certain sources, and measured parameters",
    "measured-parameters-on-interpretation": "reconstructed or synthetic interpretations cannot list measured parameters",
    "artistic-as-measured": "reconstructed artistic controls are not measured parameters",
    "high-confidence-without-measurement": "high confidence requires a measured evidence level",
    "unversioned-numerical-change": "a numerical density change kept an existing profile version",
    "duplicate-bytes": "the same profile version was stored twice",
    "falsely-identical-calibrated": "matching curves were presented as one calibrated material",
}


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


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def _tokens(value: object, label: str, allow_empty: bool) -> list[str]:
    require(type(value) is list, label + " must be a list")
    require(allow_empty or bool(value), label + " must be non-empty")
    seen: set[str] = set()
    items: list[str] = []
    for item in value:
        token = _token(item, label)
        require(token not in seen, label + " has a duplicate")
        seen.add(token)
        items.append(token)
    return items


def _density(value: object, label: str) -> list[str]:
    require(type(value) is list, label + " must be a list")
    require(2 <= len(value) <= 8, label + " must contain 2 to 8 samples")
    samples: list[str] = []
    for item in value:
        require(isinstance(item, str) and DENSITY.fullmatch(item) is not None, label + " sample is not canonical")
        samples.append(item)
    return samples


def _display(value: object, label: str) -> str:
    require(isinstance(value, str) and value == value.strip() and DISPLAY.fullmatch(value) is not None, label + " is invalid")
    require(len(value) <= 80, label + " is too long")
    return value


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P073 stock-profile fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "stock catalogue")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P073")
    require(document["mapId"] == MAP_ID, "mapId must be s23-stock-profiles-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "stock catalogue needs the P073 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    nominal = _token(document["nominalStock"], "nominalStock")
    profiles = document["profiles"]
    require(type(profiles) is list and profiles, "profiles must be a non-empty list")
    for index, raw in enumerate(profiles):
        profile = exact_keys(raw, PROFILE_KEYS, f"profile {index}")
        profile_id = _token(profile["profileId"], f"profile {index} profileId")
        require(profile_id.startswith(nominal + "-"), f"profile {index} profileId must extend the nominal stock")
        require(VERSION.fullmatch(profile["version"]) is not None, f"profile {index} version must be canonical")
        _display(profile["displayName"], f"profile {index} displayName")
        _choice(profile["family"], FAMILIES, f"profile {index} family")
        _choice(profile["balance"], BALANCES, f"profile {index} balance")
        _choice(profile["responseModel"], MODELS, f"profile {index} responseModel")
        _choice(profile["parameterUnits"], UNITS, f"profile {index} parameterUnits")
        _tokens(profile["sourceReferences"], f"profile {index} sourceReferences", False)
        _choice(profile["licenceState"], LICENCES, f"profile {index} licenceState")
        _choice(profile["confidence"], CONFIDENCE, f"profile {index} confidence")
        _choice(profile["evidenceLevel"], EVIDENCE, f"profile {index} evidenceLevel")
        _density(profile["densityCurve"], f"profile {index} densityCurve")
        _tokens(profile["artisticControls"], f"profile {index} artisticControls", True)
        _tokens(profile["measuredParameters"], f"profile {index} measuredParameters", True)
        _choice(profile["virtualFormat"], VIRTUAL_FORMATS, f"profile {index} virtualFormat")
        appearance = profile["appearanceId"]
        require(appearance == "none" or (isinstance(appearance, str) and TOKEN.fullmatch(appearance) is not None),
                f"profile {index} appearanceId must be none or a token")


def profile_faults(profile: dict) -> list[str]:
    """Return evidence and identity faults for one profile. Marketing names are not measurements."""
    faults: list[str] = []
    if profile["displayName"] == profile["profileId"]:
        faults.append("display-name-collides-with-id")
    if profile["virtualFormat"] != "none":
        faults.append("bound-to-virtual-format")
    if profile["appearanceId"] != "none":
        faults.append("bound-to-appearance")
    samples = [Decimal(item) for item in profile["densityCurve"]]
    if any(samples[index] >= samples[index + 1] for index in range(len(samples) - 1)):
        faults.append("nonmonotonic-density")
    evidence = profile["evidenceLevel"]
    uncertain = any(item.startswith("uncertain-") for item in profile["sourceReferences"])
    if evidence == "measured":
        if profile["confidence"] != "high" or uncertain or not profile["measuredParameters"]:
            faults.append("false-measurement")
    else:
        if profile["measuredParameters"]:
            faults.append("measured-parameters-on-interpretation")
        if profile["confidence"] == "high":
            faults.append("high-confidence-without-measurement")
    if set(profile["artisticControls"]) & set(profile["measuredParameters"]):
        faults.append("artistic-as-measured")
    return [item for item in _PROFILE_FAULTS if item in faults]


def catalogue_faults(document: dict) -> list[str]:
    """Reject unversioned numerical edits and falsely identical calibrated pairs."""
    faults: list[str] = []
    profiles = document["profiles"]
    first_of: dict[tuple[str, str], dict] = {}
    for profile in profiles:
        key = (profile["profileId"], profile["version"])
        previous = first_of.get(key)
        if previous is None:
            first_of[key] = profile
            continue
        kind = "unversioned-numerical-change" if previous["densityCurve"] != profile["densityCurve"] else "duplicate-bytes"
        faults.append(f"{previous['profileId']}+{profile['profileId']}:{kind}")
    for left in range(len(profiles)):
        for right in range(left + 1, len(profiles)):
            first = profiles[left]
            second = profiles[right]
            if (first["profileId"], first["version"]) == (second["profileId"], second["version"]):
                continue
            same_curve = first["densityCurve"] == second["densityCurve"]
            same_name = first["displayName"] == second["displayName"]
            both_measured = first["evidenceLevel"] == "measured" and second["evidenceLevel"] == "measured"
            if same_curve and same_name and both_measured:
                faults.append(f"{first['profileId']}+{second['profileId']}:falsely-identical-calibrated")
    return faults


def _record(profile: dict) -> str:
    artistic = ",".join(profile["artisticControls"]) if profile["artisticControls"] else "none"
    measured = ",".join(profile["measuredParameters"]) if profile["measuredParameters"] else "none"
    sources = ",".join(profile["sourceReferences"])
    curve = ",".join(profile["densityCurve"])
    return (
        f"profile:{profile['profileId']}:version={profile['version']}:display={profile['displayName']}:"
        f"family={profile['family']}:balance={profile['balance']}:model={profile['responseModel']}:"
        f"units={profile['parameterUnits']}:evidence={profile['evidenceLevel']}:"
        f"confidence={profile['confidence']}:licence={profile['licenceState']}:curve={curve}:"
        f"artistic={artistic}:measured={measured}:sources={sources}:"
        f"virtual={profile['virtualFormat']}:appearance={profile['appearanceId']}"
    )


def _inventory(document: dict) -> list[str]:
    preserved = [f"nominal:{document['nominalStock']}"]
    preserved.extend(_record(profile) for profile in document["profiles"])
    return preserved


def _eligible(group: list[dict]) -> bool:
    if len(group) < 2:
        return False
    curves = {tuple(profile["densityCurve"]) for profile in group}
    keys = {(profile["profileId"], profile["version"]) for profile in group}
    return len(curves) >= 2 and len(keys) >= 2


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P073 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
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


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Expose distinct versioned interpretations, and reject the marketing-name mutant.

    ``path`` ``marketing-as-measured`` is the deliberate mutant. A shared display
    name does not promote numerical parameters to physically measured. Existing
    evidence labels and density curves stay in ``preservedResults``. The decision
    is never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be catalogued or marketing-as-measured")
    reasons = [
        ORACLE,
        "display names stay independent of stable profile identifiers",
        "measured parameters stay distinct from reconstructed artistic controls",
    ]
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "film-stock fidelity is not established by a display name",
    ]
    rejected: list[str] = []
    for profile in document["profiles"]:
        for fault in profile_faults(profile):
            rejected.append(f"{profile['profileId']}:{fault}")
            reasons.append(f"{profile['profileId']} {fault}: {_FAULT_TEXT[fault]}")
    for fault in catalogue_faults(document):
        rejected.append(fault)
        kind = fault.rsplit(":", 1)[-1]
        reasons.append(f"{fault}: {_FAULT_TEXT[kind]}")
    mutant = path == MUTANT_PATH
    if mutant:
        rejected.append("marketing-name-as-measurement")
        reasons.append(MUTANT)
        reasons.append("a stock marketing name is not proof that numerical parameters are physically measured")
        questions.append("marketing name was rejected as measurement proof")
    reasons.append(HOST_LIMIT)
    preserved = _inventory(document)
    if rejected:
        require(mutant or path == DECLARED_PATH, "rejected path drifted")
        return _result("rejected", reasons, rejected, preserved, questions)
    groups: dict[str, list[dict]] = {}
    for profile in document["profiles"]:
        groups.setdefault(profile["displayName"], []).append(profile)
    eligible = [group for group in groups.values() if _eligible(group)]
    if not eligible:
        questions.append("catalogue does not expose two versioned interpretations with different density curves")
        return _result("withheld", reasons, rejected, preserved, questions)
    group = eligible[0]
    reasons.append(
        f"{group[0]['profileId']} version {group[0]['version']} and "
        f"{group[1]['profileId']} version {group[1]['version']} "
        "are distinct versioned interpretations"
    )
    reasons.append("density curves differ and are not one calibrated material")
    reasons.append(f"display name {group[0]['displayName']} is not a stable profile identifier")
    if any(profile["evidenceLevel"] != "measured" for profile in group):
        reasons.append("uncertain source data stays reconstructed or synthetic rather than measured")
    else:
        reasons.append("measured parameters stay attached to profile identifiers, not the display name")
    questions.append("two interpretations remain distinct because density curves and profile identifiers differ")
    return _result("versioned_interpretations", reasons, rejected, preserved, questions)
