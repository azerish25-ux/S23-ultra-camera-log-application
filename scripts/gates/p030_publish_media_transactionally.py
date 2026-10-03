#!/usr/bin/env python3
"""P030 transactional media publication.

Write into private staging, inspect the output, then copy or move using the
storage provider's actual semantics. Commit publication before removing
redundant staging. Temporary duplication is budgeted. A failed report export
leaves the media intact and discoverable.

The deliberate mutant — deleting private staging before the public copy is
durably accepted — is rejected. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P030-01 through TC-P030-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P030"
CASE_ID = "P030"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-publish-media-fixture"
METHOD = (
    "Write into private staging, inspect output, copy or move according to the actual "
    "storage provider semantics, commit publication, and only then remove redundant staging. "
    "Budget temporary duplication. Failed report export must leave media intact and discoverable."
)
FIXTURE = (
    "A full gallery destination after private recording succeeds, followed by a report "
    "serialization exception."
)
ORACLE = (
    "The source remains in recovery storage, no empty gallery success is shown, and the "
    "error identifies the failed publication step."
)
MUTANT = "Delete private staging before the public copy is durably accepted."

STEP_ORDER = (
    "private_staging",
    "inspect",
    "copy_or_move",
    "commit",
    "report_export",
    "redundant_staging_cleanup",
)
CHAIN = (
    "private_staging",
    "inspect",
    "copy_or_move",
    "commit",
    "redundant_staging_cleanup",
)
OUTCOMES = ("succeeded", "failed", "not_reached")
SEMANTICS = ("copy", "move")
SPACES = ("available", "full")
GRANTS = ("present", "revoked")
DECISIONS = (
    "rejected",
    "withheld",
    "recovery_retained",
    "media_retained",
    "publication_recorded",
)
HEX40 = re.compile(r"^[0-9a-f]{40}$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "recording",
    "destination",
    "provider",
    "steps",
    "staging",
    "gallery",
    "error",
    "inventory",
}
RECORDING_KEYS = {"privateRecordingSucceeded", "sourceId", "bytes", "nonempty"}
DESTINATION_KEYS = {"kind", "space", "grant"}
PROVIDER_KEYS = {"semantics", "publicCopyDurablyAccepted"}
STEP_KEYS = {"name", "outcome", "reason"}
STAGING_KEYS = {"present", "location", "deletedBeforeDurableAccept"}
GALLERY_KEYS = {"emptySuccessShown", "entries"}
ERROR_KEYS = {"step", "code"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_HOST_LIMIT = "host fixture does not qualify a physical S23"


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


def _text(value: object, label: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            label + " must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _strings(value: object, label: str) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    require(all(isinstance(item, str) and item and item == item.strip() for item in value),
            label + " must be non-empty strings")
    require(len(value) == len(set(value)), label + " must be unique")
    return list(value)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in DECISIONS and decision not in _FORBIDDEN,
            "P030 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
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


def _step(value: object, index: int) -> dict:
    item = exact_keys(value, STEP_KEYS, f"step {index}")
    name = _text(item["name"], f"step {index} name")
    require(name == STEP_ORDER[index], f"step {index} must be {STEP_ORDER[index]}")
    outcome = item["outcome"]
    require(outcome in OUTCOMES, f"step {index} outcome is unknown")
    reason = item["reason"]
    if outcome == "failed":
        _text(reason, f"step {index} reason")
    else:
        require(reason is None, f"step {index} reason must be null unless the step failed")
    return item


def _chain_stops(steps: list[dict]) -> None:
    by_name = {item["name"]: item for item in steps}
    stopped = False
    for name in CHAIN:
        outcome = by_name[name]["outcome"]
        if stopped:
            require(outcome == "not_reached", name + " must not run after the chain stops")
        elif outcome != "succeeded":
            stopped = True


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P030 publication fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "publication document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P030")
    require(document["mapId"] == MAP_ID, "mapId must be s23-publish-media-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "publication document needs the P030 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    recording = exact_keys(document["recording"], RECORDING_KEYS, "recording")
    _bool(recording["privateRecordingSucceeded"], "privateRecordingSucceeded")
    source_id = _text(recording["sourceId"], "sourceId")
    require(type(recording["bytes"]) is int and recording["bytes"] >= 0,
            "bytes must be a non-negative int")
    nonempty = _bool(recording["nonempty"], "nonempty")
    require(nonempty is (recording["bytes"] > 0), "nonempty must agree with bytes")

    destination = exact_keys(document["destination"], DESTINATION_KEYS, "destination")
    require(destination["kind"] == "gallery", "destination kind must be gallery")
    require(destination["space"] in SPACES, "destination space must be available or full")
    require(destination["grant"] in GRANTS, "destination grant must be present or revoked")

    provider = exact_keys(document["provider"], PROVIDER_KEYS, "provider")
    require(provider["semantics"] in SEMANTICS, "provider semantics must be copy or move")
    durable = _bool(provider["publicCopyDurablyAccepted"], "publicCopyDurablyAccepted")

    raw_steps = document["steps"]
    require(isinstance(raw_steps, list) and len(raw_steps) == len(STEP_ORDER),
            "steps must list the publication transaction in order")
    steps = [_step(item, index) for index, item in enumerate(raw_steps)]
    _chain_stops(steps)
    by_name = {item["name"]: item for item in steps}

    if destination["space"] == "full":
        require(not durable, "a full destination cannot durably accept a public copy")
        copy_step = by_name["copy_or_move"]
        require(copy_step["outcome"] == "failed" and copy_step["reason"] == "destination-full",
                "a full destination fails copy_or_move as destination-full")
    if destination["grant"] == "revoked":
        require(not durable, "a revoked grant cannot durably accept a public copy")
        commit = by_name["commit"]
        require(commit["outcome"] != "succeeded", "a revoked grant cannot commit publication")
        if commit["outcome"] == "failed":
            require(commit["reason"] == "grant-revoked", "revoked grant failure must be grant-revoked")
    if durable:
        require(by_name["copy_or_move"]["outcome"] == "succeeded",
                "durable accept requires a succeeded copy or move")

    staging = exact_keys(document["staging"], STAGING_KEYS, "staging")
    present = _bool(staging["present"], "staging present")
    location = staging["location"]
    require(location in {"recovery", "absent"}, "staging location must be recovery or absent")
    require(present is (location == "recovery"), "staging present must agree with location")
    early = _bool(staging["deletedBeforeDurableAccept"], "deletedBeforeDurableAccept")
    if early:
        require(not durable, "early deletion cannot accompany durable accept")
        require(not present and location == "absent", "early deletion removes private staging")

    cleanup = by_name["redundant_staging_cleanup"]
    if cleanup["outcome"] == "succeeded":
        require(durable, "cleanup cannot succeed before durable accept")
        require(by_name["commit"]["outcome"] == "succeeded", "cleanup cannot precede commit")
        require(not early, "cleanup after commit is not an early delete")
        require(not present, "redundant staging is absent after cleanup")

    gallery = exact_keys(document["gallery"], GALLERY_KEYS, "gallery")
    _bool(gallery["emptySuccessShown"], "emptySuccessShown")
    _strings(gallery["entries"], "gallery entries")

    error = document["error"]
    if error is not None:
        err = exact_keys(error, ERROR_KEYS, "error")
        require(err["step"] in STEP_ORDER, "error step must be a publication step")
        _text(err["code"], "error code")

    inventory = _strings(document["inventory"], "inventory")
    require(f"source:{source_id}" in inventory, "inventory must keep the source id")
    require(f"bytes:{recording['bytes']}" in inventory, "inventory must keep the byte count")


def _by_name(document: dict) -> dict[str, dict]:
    return {item["name"]: item for item in document["steps"]}


def mutant_deletes_before_accept(document: dict) -> bool:
    """Return whether the forbidden mutant would delete private staging.

    The mutant deletes as soon as private recording has succeeded and the
    public copy is not durably accepted. It ignores copy-versus-move semantics.
    Callers that publish must not follow this function.
    """
    validate_fixture(document)
    return (
        document["recording"]["privateRecordingSucceeded"] is True
        and document["provider"]["publicCopyDurablyAccepted"] is not True
    )


def honest_retains_staging(document: dict) -> bool:
    """Keep recovery staging until the public copy is durably accepted.

    This is the opposite of the mutant. A full gallery and a report failure
    both leave the private source in recovery.
    """
    validate_fixture(document)
    if document["provider"]["publicCopyDurablyAccepted"] is True:
        return document["staging"]["deletedBeforeDurableAccept"] is False
    return (
        document["staging"]["deletedBeforeDurableAccept"] is False
        and document["staging"]["present"] is True
        and document["staging"]["location"] == "recovery"
    )


def provider_action(document: dict) -> str:
    """Return copy or move. Never delete.

    Deleting private staging before durable accept is the mutant and is not a
    storage-provider action.
    """
    validate_fixture(document)
    action = document["provider"]["semantics"]
    require(action in SEMANTICS, "provider action must be copy or move")
    require(action != "delete", "delete is not a provider action")
    return action


def trace_publication(document: dict) -> dict[str, Any]:
    """Describe the honest transaction without removing staging early."""
    validate_fixture(document)
    by_name = _by_name(document)
    durable = document["provider"]["publicCopyDurablyAccepted"] is True
    commit_ok = by_name["commit"]["outcome"] == "succeeded"
    early = document["staging"]["deletedBeforeDurableAccept"] is True
    error = document["error"]
    return {
        "steps": [item["name"] for item in document["steps"]],
        "cleanupPermitted": durable and commit_ok and not early,
        "temporaryDuplication": True,
        "stagingRetained": honest_retains_staging(document) if not durable else (
            document["staging"]["present"] is True
        ),
        "failedStep": None if error is None else error["step"],
        "semantics": provider_action(document),
        "failedSteps": [item["name"] for item in document["steps"] if item["outcome"] == "failed"],
    }


def _append(preserved: list[str], token: str) -> None:
    if token not in preserved:
        preserved.append(token)


def assess_publication(document: dict) -> dict:
    """Judge one publication transaction.

    decision is recovery_retained when private media stays in recovery, the
    gallery shows no empty success, and the error names a step that failed.
    decision is rejected when staging was deleted before durable accept, when
    an empty gallery success is shown, or when the error does not name the
    failed step. decision is never qualified or allowed. The inventory is kept
    either way. The mutant is not applied.
    """
    validate_fixture(document)
    by_name = _by_name(document)
    recording = document["recording"]
    destination = document["destination"]
    provider = document["provider"]
    staging = document["staging"]
    gallery = document["gallery"]
    error = document["error"]
    durable = provider["publicCopyDurablyAccepted"] is True
    early = staging["deletedBeforeDurableAccept"] is True or (
        not durable and staging["present"] is not True
    )
    failed = [item for item in document["steps"] if item["outcome"] == "failed"]
    if not failed:
        error_ok = error is None
    else:
        error_ok = error is not None and any(
            item["name"] == error["step"] and item["reason"] == error["code"] for item in failed
        )
    report_failed = by_name["report_export"]["outcome"] == "failed"
    discoverable = staging["present"] is True or bool(gallery["entries"])
    empty_success = gallery["emptySuccessShown"] is True or (
        not durable and bool(gallery["entries"])
    )
    commit_ok = by_name["commit"]["outcome"] == "succeeded"
    cleanup_ok = by_name["redundant_staging_cleanup"]["outcome"] == "succeeded"
    recording_ok = (
        recording["privateRecordingSucceeded"] is True
        and recording["nonempty"] is True
        and recording["bytes"] > 0
    )

    rejected: list[str] = []
    if early:
        rejected.append("staging-deleted-before-durable-accept")
    if empty_success:
        rejected.append("empty-gallery-success")
    if not error_ok:
        rejected.append("unidentified-publication-step")
    if report_failed and not discoverable and not early:
        rejected.append("media-not-discoverable")

    if rejected:
        decision = "rejected"
    elif not recording_ok:
        decision = "withheld"
    elif (
        not durable
        and staging["present"] is True
        and staging["location"] == "recovery"
        and not empty_success
    ):
        decision = "recovery_retained"
    elif durable and report_failed and discoverable and not empty_success:
        decision = "media_retained"
    elif (
        durable
        and not failed
        and error is None
        and commit_ok
        and cleanup_ok
        and bool(gallery["entries"])
        and not empty_success
    ):
        decision = "publication_recorded"
    else:
        decision = "withheld"

    reasons = [ORACLE]
    if "staging-deleted-before-durable-accept" in rejected:
        reasons.append(MUTANT)
        reasons.append("private staging was deleted before the public copy was durably accepted")
    if "empty-gallery-success" in rejected:
        reasons.append("an empty gallery success was claimed")
    if "unidentified-publication-step" in rejected:
        reasons.append("the error does not identify the failed publication step")
    if "media-not-discoverable" in rejected:
        reasons.append("failed report export must leave media intact and discoverable")
    for item in failed:
        reasons.append(item["name"] + " failed: " + item["reason"])
    if decision == "recovery_retained":
        reasons.extend((
            "the source remains in recovery storage",
            "no empty gallery success is shown",
            "temporary duplication is budgeted",
            "redundant staging was not removed",
        ))
    elif decision == "media_retained":
        reasons.append("failed report export left media intact and discoverable")
        reasons.append("no empty gallery success is shown")
        reasons.append("temporary duplication is budgeted")
        if cleanup_ok:
            reasons.append("redundant staging was removed only after durable accept")
        else:
            reasons.append("redundant staging was not removed")
    elif decision == "publication_recorded":
        reasons.extend((
            "publication committed only after durable accept",
            "redundant staging was removed only after commit",
            "temporary duplication was budgeted",
            "publication_recorded is a host-fixture label, not physical S23 qualification",
        ))
    elif decision == "withheld":
        reasons.append("publication is withheld")
    if decision == "rejected":
        reasons.append("the inventory is preserved")
    if error is not None and error_ok:
        reasons.append(
            "failed publication step " + error["step"] + " identified as " + error["code"]
        )

    questions = [_HOST_LIMIT]
    if not durable:
        questions.append("public copy is not durably accepted")
    if destination["space"] == "full":
        questions.append("destination space is full")
    if destination["grant"] == "revoked":
        questions.append("publication grant was revoked")
    if report_failed and decision != "rejected":
        questions.append("report export failed; media remains discoverable")
    if decision == "publication_recorded":
        questions.append("publication_recorded is not physical qualification")
    if decision == "withheld":
        questions.append("publication remains withheld on this host fixture")

    preserved = list(document["inventory"])
    _append(preserved, "staging:present" if staging["present"] else "staging:absent")
    _append(preserved, "location:" + staging["location"])
    _append(preserved, "semantics:" + provider["semantics"])
    _append(preserved, "durable-accept:" + ("true" if durable else "false"))
    if error is not None:
        _append(preserved, "failed-step:" + error["step"])
        _append(preserved, "error:" + error["code"])
    _append(preserved, "duplication-budget:temporary")
    for entry in gallery["entries"]:
        _append(preserved, "gallery-entry:" + entry)

    require(not (decision == "publication_recorded" and early),
            "publication_recorded cannot follow an early staging delete")
    require(provider_action(document) != "delete", "assess must not delete staging")
    require("source:" + recording["sourceId"] in preserved, "source inventory was wiped")
    return _result(decision, reasons, rejected, preserved, questions)
