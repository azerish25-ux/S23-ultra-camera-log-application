#!/usr/bin/env python3
"""P031 cold-start recovery for interrupted recordings.

Journal path identity, take metadata, selected tracks, and terminal status.
On cold start, nonempty remnants are inspected. An unfinished MP4 is not
assumed playable. Export and retry are explicit. The sole retained copy is
not deleted without confirmation.

The deliberate mutant — delete every file lacking a completed journal flag —
is rejected. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P031-01 through TC-P031-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P031"
CASE_ID = "P031"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-interrupted-recording-fixture"
METHOD = (
    "Journal path identity, take metadata, selected tracks, and terminal status. "
    "On cold start, inspect nonempty remnants without assuming an unfinished MP4 "
    "is playable. Offer explicit export and retry, and require confirmation before "
    "deleting the sole retained copy."
)
FIXTURE = (
    "Process termination during muxer finalization with both a nonempty partial "
    "file and an incomplete journal record."
)
ORACLE = (
    "The recovery library exposes the artefact as unverified and does not discard "
    "it merely because normal validation cannot complete."
)
MUTANT = "Delete every file lacking a completed journal flag."
MUTANT_POLICY = "delete_lacking_completed_journal"
RETAIN_POLICY = "retain"

TRANSITIONS = (
    "before_first_sample",
    "active_muxing",
    "muxer_finalization",
    "after_publication",
)
TERMINAL = ("incomplete", "completed", "published")
TRACKS = ("video", "audio")
KINDS = ("partial_mp4", "audio_partial", "sidecar")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]*")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "journal",
    "artefacts",
    "offers",
    "deleteConfirmation",
}
JOURNAL_KEYS = {
    "pathIdentity",
    "takeId",
    "selectedTracks",
    "terminalStatus",
    "completedJournalFlag",
    "transition",
}
ARTEFACT_KEYS = {
    "path",
    "kind",
    "bytes",
    "nonempty",
    "playable",
    "validationComplete",
    "soleRetainedCopy",
}
OFFER_KEYS = {"export", "retry"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"unverified", "rejected", "withheld", "journal_complete", "delete_authorized"}


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
    require(TOKEN.fullmatch(value) is not None, label + " must be a path or token")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P031 must not decide qualified or allowed")
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


def artefact_token(item: dict) -> str:
    """Inventory token. Bytes and playable are recorded, not upgraded."""
    nonempty = "true" if item["nonempty"] else "false"
    playable = "true" if item["playable"] else "false"
    return f"{item['path']}:bytes={item['bytes']}:nonempty={nonempty}:playable={playable}"


def _journal(value: object) -> dict:
    item = exact_keys(value, JOURNAL_KEYS, "journal")
    _text(item["pathIdentity"], "journal pathIdentity")
    _text(item["takeId"], "journal takeId")
    tracks = item["selectedTracks"]
    require(isinstance(tracks, list) and tracks, "selectedTracks must be a non-empty list")
    require(len(tracks) == len(set(tracks)), "selectedTracks must be unique")
    require(all(track in TRACKS for track in tracks), "selectedTracks must be video and/or audio")
    status = item["terminalStatus"]
    require(status in TERMINAL, "terminalStatus must be incomplete, completed, or published")
    flag = _bool(item["completedJournalFlag"], "completedJournalFlag")
    transition = item["transition"]
    require(transition in TRANSITIONS, "transition must be a known journal transition")
    if transition == "after_publication":
        require(status == "published" and flag, "publication requires a completed journal")
    else:
        require(status == "incomplete" and not flag,
                "an unfinished transition keeps an incomplete journal")
    if status == "completed":
        require(flag, "completed status requires the journal flag")
    if status == "incomplete":
        require(not flag, "incomplete status must not set the journal flag")
    return item


def _artefact(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, ARTEFACT_KEYS, f"artefact {index}")
    path = _text(item["path"], f"artefact {index} path")
    require(path not in seen, "duplicate artefact path: " + path)
    seen.add(path)
    require(item["kind"] in KINDS, f"artefact {index} kind is not in the fixture vocabulary")
    require(type(item["bytes"]) is int and item["bytes"] >= 0,
            f"artefact {index} bytes must be a non-negative int")
    nonempty = _bool(item["nonempty"], f"artefact {index} nonempty")
    require(nonempty is (item["bytes"] > 0), f"artefact {index} nonempty must agree with bytes")
    _bool(item["playable"], f"artefact {index} playable")
    _bool(item["validationComplete"], f"artefact {index} validationComplete")
    _bool(item["soleRetainedCopy"], f"artefact {index} soleRetainedCopy")
    return item


def _offers(value: object) -> dict:
    item = exact_keys(value, OFFER_KEYS, "offers")
    _bool(item["export"], "offers export")
    _bool(item["retry"], "offers retry")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P031 recovery fixture."""
    exact_keys(document, DOCUMENT_KEYS, "recovery document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P031")
    require(document["mapId"] == MAP_ID, "mapId must be s23-interrupted-recording-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "recovery document needs the P031 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _journal(document["journal"])
    artefacts = document["artefacts"]
    require(isinstance(artefacts, list), "artefacts must be a list")
    seen: set[str] = set()
    parsed = [_artefact(item, index, seen) for index, item in enumerate(artefacts)]
    soles = [item["path"] for item in parsed if item["soleRetainedCopy"]]
    require(len(soles) <= 1, "at most one artefact may be the sole retained copy")
    _offers(document["offers"])
    _bool(document["deleteConfirmation"], "deleteConfirmation")


def _inventory(document: dict) -> list[str]:
    journal = document["journal"]
    preserved = [
        f"journal:{journal['pathIdentity']}",
        f"take:{journal['takeId']}",
        *[f"track:{track}" for track in journal["selectedTracks"]],
        f"status:{journal['terminalStatus']}",
        f"transition:{journal['transition']}",
        f"completedFlag:{'true' if journal['completedJournalFlag'] else 'false'}",
    ]
    preserved.extend(artefact_token(item) for item in document["artefacts"])
    if document["offers"]["export"]:
        preserved.append("offer:export")
    if document["offers"]["retry"]:
        preserved.append("offer:retry")
    return preserved


def retained_paths(document: dict) -> list[str]:
    """Nonempty remnant paths. An incomplete journal does not empty this list."""
    validate_document(document)
    return [item["path"] for item in document["artefacts"] if item["nonempty"]]


def _unfinished_playable(item: dict, journal: dict) -> bool:
    if not item["playable"]:
        return False
    if not item["validationComplete"] or not journal["completedJournalFlag"]:
        return True
    return item["kind"] == "partial_mp4" and journal["transition"] != "after_publication"


def assess(document: dict) -> dict:
    """Expose a cold-start remnant as unverified and keep it.

    Nonempty files stay in preservedResults when the journal flag is absent
    and when validation cannot complete. Unfinished MP4 playability is not
    assumed. Export and retry are recorded only when explicitly offered.
    deleteConfirmation on the document does not discard the sole copy.
    """
    validate_document(document)
    journal = document["journal"]
    preserved = _inventory(document)
    nonempty = [item for item in document["artefacts"] if item["nonempty"]]
    offers_ready = document["offers"]["export"] and document["offers"]["retry"]
    rejected: list[str] = []
    questions: list[str] = []
    reasons = [ORACLE]

    lied = [item for item in nonempty if _unfinished_playable(item, journal)]
    if lied:
        rejected.append("playable-unfinished-mp4")
    if not offers_ready:
        rejected.append("missing-explicit-export-or-retry")

    blocked = (not journal["completedJournalFlag"]) or any(
        not item["validationComplete"] for item in nonempty
    )
    if not nonempty:
        decision = "withheld"
        questions.append("no nonempty remnant")
        reasons.append("cold start found no nonempty media to retain")
    elif lied:
        decision = "rejected"
        questions.append("unfinished output is not verified")
        reasons.append("an unfinished MP4 is not playable")
        reasons.append("the artefact is retained")
    elif blocked:
        decision = "unverified"
        questions.append("normal validation cannot complete")
        questions.append("unfinished output is not verified")
        reasons.append("unfinished MP4 is not assumed playable")
        reasons.append("nonempty remnant retained despite incomplete journal")
        reasons.append("the artefact is not discarded merely because validation cannot complete")
    else:
        decision = "journal_complete"
        questions.append("host journal status is not physical S23 qualification")
        reasons.append("a completed journal is not physical S23 qualification")

    if offers_ready and nonempty:
        reasons.append("explicit export and retry are offered")
    elif not offers_ready:
        reasons.append("export and retry must be explicit")
        if decision == "unverified":
            decision = "withheld"
    if any(item["soleRetainedCopy"] for item in nonempty):
        reasons.append("sole retained copy is not deleted without confirmation")
    if document["deleteConfirmation"]:
        reasons.append("recorded confirmation does not discard the remnant during scan")
        questions.append("scan does not apply deletion")
    return _result(decision, reasons, rejected, preserved, questions)


def apply_policy(document: dict, policy: str) -> dict:
    """Apply a recovery policy without implementing the deletion mutant.

    ``delete_lacking_completed_journal`` is rejected. Nonempty paths stay in
    preservedResults. A retain policy is the ordinary cold-start assessment.
    """
    validate_document(document)
    require(policy in {MUTANT_POLICY, RETAIN_POLICY}, "unknown recovery policy")
    if policy == RETAIN_POLICY:
        return assess(document)
    preserved = _inventory(document)
    paths = retained_paths(document)
    require(all(any(path in item for item in preserved) for path in paths),
            "inventory dropped a nonempty remnant")
    questions = ["artefact remains unverified", "normal validation cannot complete"]
    if not paths and not document["journal"]["completedJournalFlag"]:
        questions = ["no nonempty remnant", "incomplete journal was not used as a deletion list"]
    return _result(
        "rejected",
        [
            MUTANT,
            ORACLE,
            "files lacking a completed journal flag are retained",
            "deletion was not applied",
        ],
        ["delete-every-file-lacking-completed-journal"],
        preserved,
        questions,
    )


def request_delete(document: dict, confirmed: bool, paths: list[str]) -> dict:
    """Refuse to drop the sole retained copy unless confirmation is explicit.

    Confirmation authorizes a host record only. The inventory token remains.
    This does not verify the MP4 and does not qualify a physical S23.
    """
    validate_document(document)
    require(type(confirmed) is bool, "confirmed must be a bool")
    require(isinstance(paths, list) and paths, "paths must be a non-empty list")
    require(all(isinstance(item, str) and item for item in paths), "paths must be non-empty strings")
    require(len(paths) == len(set(paths)), "paths must be unique")
    known = {item["path"]: item for item in document["artefacts"]}
    missing = [item for item in paths if item not in known]
    require(not missing, "unknown artefact path: " + ", ".join(missing))
    preserved = _inventory(document)
    sole = [item for item in paths if known[item]["soleRetainedCopy"]]
    reasons = [ORACLE, "the inventory token is retained"]
    if not confirmed:
        claim = "unconfirmed-sole-copy-delete" if sole else "unconfirmed-delete"
        reasons.append("confirmation is required before deleting the sole retained copy")
        reasons.append("the remnant was not discarded")
        return _result(
            "rejected",
            reasons,
            [claim],
            preserved,
            ["unfinished output is not verified"],
        )
    reasons.append("confirmation authorizes a host record only")
    reasons.append("authorized delete does not verify the MP4 or qualify a physical S23")
    if sole:
        reasons.append("sole retained copy remains in the inventory")
    return _result(
        "delete_authorized",
        reasons,
        [],
        preserved,
        ["host authorization is not physical deletion", "unfinished output is not verified"],
    )
