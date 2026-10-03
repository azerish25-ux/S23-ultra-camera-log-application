#!/usr/bin/env python3
"""P013 codec-route database and interface-specific qualification plan.

Inventory codec names, profiles, levels, sizes, rates, surface support, and
byte-buffer or Image formats. A P010 developer and an EGL surface encoder
have different prerequisites. Failures stay on the candidate that produced
them. Main10 advertising is not P010 Image acceptance.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P013-01 through TC-P013-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE_ID = "P013"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
DATABASE_ID = "s23-codec-route-fixture"
METHOD = (
    "Inventory codec names, profiles, levels, sizes, rates, surface support, "
    "and byte-buffer or Image formats. A P010 developer and an EGL surface "
    "encoder have different prerequisites. Store failures per candidate and "
    "re-query after relevant device software changes."
)
FIXTURE = (
    "A codec advertising Main10 with surface input but no usable P010 Image input."
)
ORACLE = (
    "The surface candidate remains available for testing while the CPU P010 "
    "developer is honestly unavailable."
)
MUTANT = "Use the advertised Main10 profile as the sole P010 acceptance criterion."
MUTANT_CLAIM = "main10-as-sole-p010-criterion"
MAIN10_IMAGE_CLAIM = "main10-implies-p010-image"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
FPS_TEXT = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
INTERFACES = {"surface", "byte_buffer", "image", "encoder", "decoder"}
ROLES = {
    "egl_surface_encoder",
    "cpu_p010_developer",
    "byte_buffer",
    "encoder",
    "decoder",
}
ENV_KEYS = ("buildFingerprint", "codecIdentity", "probeProtocol")
DB_KEYS = {
    "schemaVersion",
    "phase",
    "databaseId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "buildFingerprint",
    "codecIdentity",
    "probeProtocol",
    "candidates",
}
CANDIDATE_KEYS = {
    "candidateId",
    "codecName",
    "profile",
    "level",
    "width",
    "height",
    "minFps",
    "maxFps",
    "interface",
    "inputFormat",
    "tenBit",
    "usable",
    "advertised",
    "failure",
    "role",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"rejected", "requalify", "interface_specific"}
DIFFERENT_PREREQUISITES = (
    "a P010 developer and an EGL surface encoder have different prerequisites"
)


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


def _text(value: object, context: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        context + " must be a non-empty string",
    )
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _fps(value: object, context: str) -> Decimal:
    require(
        isinstance(value, str) and FPS_TEXT.fullmatch(value) is not None,
        context + " must be a decimal string such as 30 or 29.97",
    )
    parsed = Decimal(value)
    require(parsed > 0, context + " must be positive")
    return parsed


def candidate_status(candidate: dict) -> str:
    """Availability is per interface. Profile advertising is not acceptance.

    The mutant would treat profile Main10 as sufficient for every input,
    including an unusable P010 Image route. This function does not do that.
    usable false, or a stored failure, stays unavailable even when the
    profile string is Main10.
    """
    require(isinstance(candidate, dict), "candidate must be an object")
    usable = candidate.get("usable")
    require(type(usable) is bool, "usable must be a bool")
    failure = candidate.get("failure", None)
    require(
        failure is None or (
            isinstance(failure, str) and bool(failure.strip()) and failure == failure.strip()
        ),
        "failure must be a non-empty string or null",
    )
    profile = candidate.get("profile")
    if profile == "Main10" and usable is not True:
        return "unavailable"
    if usable is True and failure is None:
        return "available"
    return "unavailable"


def _candidate(value: object, index: int) -> dict:
    context = f"candidate {index}"
    candidate = exact_keys(value, CANDIDATE_KEYS, context)
    _text(candidate["candidateId"], context + " candidateId")
    _text(candidate["codecName"], context + " codecName")
    _text(candidate["profile"], context + " profile")
    _text(candidate["level"], context + " level")
    for axis in ("width", "height"):
        require(
            type(candidate[axis]) is int and candidate[axis] > 0,
            context + f" {axis} must be a positive int",
        )
    low = _fps(candidate["minFps"], context + " minFps")
    high = _fps(candidate["maxFps"], context + " maxFps")
    require(low <= high, context + " minFps must not exceed maxFps")
    require(candidate["interface"] in INTERFACES, context + " interface is not a known input route")
    _text(candidate["inputFormat"], context + " inputFormat")
    _bool(candidate["tenBit"], context + " tenBit")
    _bool(candidate["usable"], context + " usable")
    _bool(candidate["advertised"], context + " advertised")
    failure = candidate["failure"]
    require(
        failure is None or (
            isinstance(failure, str) and bool(failure.strip()) and failure == failure.strip()
        ),
        context + " failure must be a non-empty string or null",
    )
    require(candidate["role"] in ROLES, context + " role is not a known codec role")
    if candidate["role"] == "egl_surface_encoder":
        require(candidate["interface"] == "surface", context + " EGL surface encoder requires surface")
    if candidate["role"] == "cpu_p010_developer":
        require(candidate["interface"] == "image", context + " CPU P010 developer requires image")
        require(candidate["inputFormat"] == "P010", context + " CPU P010 developer requires P010")
    if candidate["role"] == "byte_buffer":
        require(candidate["interface"] == "byte_buffer", context + " byte_buffer role requires that interface")
    if candidate["usable"] is True and failure is not None:
        raise ValueError(context + " usable candidate cannot also store a failure")
    if candidate["usable"] is False and failure is None:
        raise ValueError(context + " unavailable candidate must store its failure")
    return candidate


def validate_database(document: dict) -> None:
    """Raise ValueError unless document is a P013 codec-route database."""
    exact_keys(document, DB_KEYS, "codec route database")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P013")
    require(document["databaseId"] == DATABASE_ID, "databaseId must be s23-codec-route-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "codec route database needs the P013 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    for key in ENV_KEYS:
        _text(document[key], key)
    candidates = document["candidates"]
    require(isinstance(candidates, list) and candidates, "candidates must be a non-empty list")
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        checked = _candidate(candidate, index)
        require(checked["candidateId"] not in seen, "duplicate candidateId: " + checked["candidateId"])
        seen.add(checked["candidateId"])


def inventory(document: dict) -> list[dict]:
    """Return every candidate. A failure on one route does not drop the others.

    status is available only when that candidate is usable and has no stored
    failure. A Main10 profile does not promote an unusable P010 Image route.
    """
    validate_database(document)
    rows: list[dict] = []
    for candidate in document["candidates"]:
        status = candidate_status(candidate)
        rows.append({
            "candidateId": candidate["candidateId"],
            "codecName": candidate["codecName"],
            "profile": candidate["profile"],
            "level": candidate["level"],
            "width": candidate["width"],
            "height": candidate["height"],
            "minFps": candidate["minFps"],
            "maxFps": candidate["maxFps"],
            "interface": candidate["interface"],
            "inputFormat": candidate["inputFormat"],
            "role": candidate["role"],
            "tenBit": candidate["tenBit"],
            "advertised": candidate["advertised"],
            "status": status,
            "failure": candidate["failure"],
        })
    return rows


def oracle_holds(document: dict) -> bool:
    """True when the packet oracle is present in this database.

    A surface Main10 candidate is available, and a CPU P010 developer on the
    same advertised Main10 profile is unavailable. Implementing the mutant
    (Main10 alone means P010 accepted) makes this false.
    """
    rows = inventory(document)
    surface_ready = any(
        row["status"] == "available"
        and row["interface"] == "surface"
        and row["role"] == "egl_surface_encoder"
        and row["profile"] == "Main10"
        and row["advertised"] is True
        for row in rows
    )
    p010_unavailable = any(
        row["status"] == "unavailable"
        and row["role"] == "cpu_p010_developer"
        and row["interface"] == "image"
        and row["inputFormat"] == "P010"
        and row["profile"] == "Main10"
        and row["advertised"] is True
        and row["failure"]
        for row in rows
    )
    return surface_ready and p010_unavailable


def _environment(value: object) -> dict[str, str]:
    env = exact_keys(value, set(ENV_KEYS), "current environment")
    for key in ENV_KEYS:
        _text(env[key], "current " + key)
    return env


def _stale(document: dict, current: dict[str, str] | None) -> list[str]:
    if current is None:
        return []
    return [key for key in ENV_KEYS if document[key] != current[key]]


def _preserved(rows: list[dict]) -> list[str]:
    preserved: list[str] = []
    for row in rows:
        if row["status"] == "available":
            preserved.append(row["candidateId"])
        else:
            preserved.append("historical:" + row["candidateId"])
        if row["failure"]:
            preserved.append("failure:" + row["candidateId"])
    return preserved


def _available_ids(preserved: list[str]) -> list[str]:
    return [
        item for item in preserved
        if not item.startswith("historical:") and not item.startswith("failure:")
    ]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must not be qualified or allowed")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
    for label, items in (
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        require(
            isinstance(items, list) and all(isinstance(item, str) and item for item in items),
            label + " must be a list of non-empty strings",
        )
    require(bool(preserved), "preservedResults must keep the inventory")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess(
    document: dict,
    sole_main10_as_p010: bool = False,
    current_environment: dict | None = None,
) -> dict:
    """Qualify interfaces independently. Reject the Main10-only P010 mutant.

    sole_main10_as_p010 true is the mutant: advertised Main10 is treated by
    the caller as the sole P010 acceptance criterion. That call is rejected.
    The surface candidate stays in preservedResults. The CPU P010 developer
    is not promoted to available.

    A changed build fingerprint, codec identity, or probe protocol yields
    requalify. The old rows stay historical. Marketing names are not keys.
    """
    require(type(sole_main10_as_p010) is bool, "sole_main10_as_p010 must be a bool")
    current = None if current_environment is None else _environment(current_environment)
    rows = inventory(document)
    preserved = _preserved(rows)
    available = _available_ids(preserved)
    unavailable = [row["candidateId"] for row in rows if row["status"] == "unavailable"]
    surface_ids = [
        row["candidateId"]
        for row in rows
        if row["status"] == "available" and row["interface"] == "surface"
    ]
    p010_unavailable = [
        row["candidateId"]
        for row in rows
        if row["role"] == "cpu_p010_developer" and row["status"] == "unavailable"
    ]
    changed = _stale(document, current)
    questions = ["re-query affected candidates after relevant device software changes"]
    rejected: list[str] = []
    reasons: list[str] = []

    main10_image_gap = any(
        row["profile"] == "Main10"
        and row["advertised"] is True
        and row["interface"] == "image"
        and row["inputFormat"] == "P010"
        and row["status"] == "unavailable"
        for row in rows
    )

    if sole_main10_as_p010:
        decision = "rejected"
        rejected.append(MUTANT_CLAIM)
        reasons.append("advertised Main10 profile is not the sole P010 acceptance criterion")
        reasons.append(DIFFERENT_PREREQUISITES)
        reasons.append("surface input stays available for testing without accepting P010 Image")
        rejected.extend(p010_unavailable)
        if main10_image_gap:
            rejected.append(MAIN10_IMAGE_CLAIM)
        questions.append("CPU P010 developer remains honestly unavailable")
    elif changed:
        decision = "requalify"
        rejected.append("stale-environment")
        rejected.extend(changed)
        reasons.append(
            "device software identity changed (" + ", ".join(changed) + "); requalify affected tuples"
        )
        reasons.append("previous reports stay historical and are not current acceptance")
        reasons.append("cache identity is build, codec, and probe protocol, not a marketing name")
        rejected.extend(unavailable)
    else:
        decision = "interface_specific"
        if surface_ids:
            reasons.append("surface candidate remains available for testing")
        else:
            reasons.append("no surface candidate is available in this inventory")
        if p010_unavailable:
            reasons.append("CPU P010 developer is honestly unavailable")
            questions.append("CPU P010 developer remains honestly unavailable")
        elif any(row["role"] == "cpu_p010_developer" and row["status"] == "available" for row in rows):
            reasons.append("CPU P010 developer availability was recorded on its own interface")
        else:
            reasons.append("no CPU P010 developer candidate was inventoried")
        reasons.append(DIFFERENT_PREREQUISITES)
        reasons.append("failures are stored per candidate")
        rejected.extend(unavailable)
        if main10_image_gap:
            rejected.append(MAIN10_IMAGE_CLAIM)

    for row in rows:
        if row["role"] == "cpu_p010_developer" and row["status"] != "available":
            require(
                row["candidateId"] not in available,
                "unavailable CPU P010 developer must not be presented as available",
            )
    require(not sole_main10_as_p010 or decision == "rejected", "mutant must be rejected")
    if surface_ids:
        for surface_id in surface_ids:
            require(surface_id in preserved, "surface candidate dropped from the inventory")
    return _result(decision, reasons, rejected, preserved, questions)
