#!/usr/bin/env python3
"""P039 retain sources across cancelled development.

Read-only source handles, separate destination identities, and content hashes
before and after processing. Temporary output is independent. Cancellation
closes leases and records progress while the source and profile records stay
put. A restart retries with another film recipe and reads the original frames.

The mutant reuses the source filename as the destination of a developed movie.
assess rejects that document. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P039-01 through TC-P039-08.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any


PHASE = "P039"
CASE_ID = "P039"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-retain-sources-cancelled-development-fixture"
METHOD = (
    "Use read-only source handles, separate destination identities, and content "
    "hashes before and after processing. Manage temporary output independently. "
    "Cancellation closes leases and records progress while preserving source and "
    "profile records."
)
FIXTURE = (
    "Cancellation halfway through development followed by a process restart and "
    "a retry with another film recipe."
)
ORACLE = (
    "The source hash is unchanged, the partial result is labelled incomplete, "
    "and the retry reads the original frames."
)
MUTANT = "Reuse the source filename as the destination of a developed movie."
HONEST_POLICY = "separate_destination"
MUTANT_POLICY = "reuse_source_filename"
MUTANT_CLAIM = "reuse-source-filename"
PARTIAL_LABEL = "incomplete"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DIGEST = re.compile(r"^[0-9a-f]{64}$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "policy",
    "source",
    "profile",
    "job",
    "retry",
}
SOURCE_KEYS = {"id", "filename", "handle", "readOnly", "hashBefore", "hashAfter", "frames"}
PROFILE_KEYS = {"id", "recipe", "hash"}
JOB_KEYS = {
    "developedFrames",
    "destination",
    "temporary",
    "partialLabel",
    "leasesClosed",
    "progressRecorded",
}
RETRY_KEYS = {"restarted", "recipe", "destination", "readsOriginalFrames", "frameIds"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


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


def content_hash(frames: list[str]) -> str:
    """Content hash of the original frame ids. Processing must not change it."""
    digest = hashlib.sha256()
    for frame in frames:
        digest.update(frame.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def profile_hash(recipe: str) -> str:
    """Content hash of a film-recipe id. It is not a measured film stock."""
    return hashlib.sha256(recipe.encode("ascii")).hexdigest()


def mutant_destination(source_filename: str) -> str:
    """The mutant writes the developed movie onto the source filename."""
    require(isinstance(source_filename, str) and TOKEN.fullmatch(source_filename) is not None,
            "source filename must be a token")
    return source_filename


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _digest(value: object, label: str) -> str:
    require(isinstance(value, str) and DIGEST.fullmatch(value) is not None,
            label + " must be 64 lowercase hex characters")
    return value


def _frames(value: object, label: str) -> list[str]:
    require(isinstance(value, list) and 2 <= len(value) <= 16, label + " must list 2 to 16 frames")
    parsed: list[str] = []
    for item in value:
        parsed.append(_token(item, label))
    require(len(parsed) == len(set(parsed)), label + " must be unique")
    return parsed


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P039 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    require(all(isinstance(item, str) for item in rejected), "rejectedClaims must be strings")
    require(all(isinstance(item, str) and item for item in preserved),
            "preservedResults must be non-empty strings")
    require(all(isinstance(item, str) and item for item in questions),
            "openQuestions must be strings")
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


def _identity(document: dict) -> None:
    require(type(document.get("schemaVersion")) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document.get("phase") == PHASE, "phase must be P039")
    require(document.get("mapId") == MAP_ID,
            "mapId must be s23-retain-sources-cancelled-development-fixture")
    revision = document.get("implementationBaseRevision")
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "document needs the P039 implementation base revision")
    require(document.get("method") == METHOD, "method text drifted")
    require(document.get("fixture") == FIXTURE, "fixture text drifted")
    require(document.get("oracle") == ORACLE, "oracle text drifted")
    require(document.get("mutant") == MUTANT, "mutant text must name source-filename reuse")


def _parse_source(source: object) -> dict[str, Any]:
    item = exact_keys(source, SOURCE_KEYS, "source")
    frames = _frames(item["frames"], "source.frames")
    expected = content_hash(frames)
    before = _digest(item["hashBefore"], "source.hashBefore")
    after = _digest(item["hashAfter"], "source.hashAfter")
    require(before == expected, "source.hashBefore must be the content hash of the original frames")
    require(type(item["readOnly"]) is bool, "source.readOnly must be a bool")
    return {
        "id": _token(item["id"], "source.id"),
        "filename": _token(item["filename"], "source.filename"),
        "handle": _token(item["handle"], "source.handle"),
        "readOnly": item["readOnly"],
        "hashBefore": before,
        "hashAfter": after,
        "frames": frames,
    }


def _parse_profile(profile: object) -> dict[str, str]:
    item = exact_keys(profile, PROFILE_KEYS, "profile")
    recipe = _token(item["recipe"], "profile.recipe")
    digest = _digest(item["hash"], "profile.hash")
    require(digest == profile_hash(recipe), "profile.hash must be the content hash of the recipe")
    return {"id": _token(item["id"], "profile.id"), "recipe": recipe, "hash": digest}


def _parse_job(job: object, frame_count: int) -> dict[str, Any]:
    item = exact_keys(job, JOB_KEYS, "job")
    developed = item["developedFrames"]
    require(type(developed) is int and 0 <= developed <= frame_count,
            "job.developedFrames must be an int inside the frame list")
    require(type(item["leasesClosed"]) is bool, "job.leasesClosed must be a bool")
    require(type(item["progressRecorded"]) is bool, "job.progressRecorded must be a bool")
    return {
        "developedFrames": developed,
        "destination": _token(item["destination"], "job.destination"),
        "temporary": _token(item["temporary"], "job.temporary"),
        "partialLabel": _token(item["partialLabel"], "job.partialLabel"),
        "leasesClosed": item["leasesClosed"],
        "progressRecorded": item["progressRecorded"],
    }


def _parse_retry(retry: object) -> dict[str, Any]:
    item = exact_keys(retry, RETRY_KEYS, "retry")
    require(type(item["restarted"]) is bool, "retry.restarted must be a bool")
    require(type(item["readsOriginalFrames"]) is bool, "retry.readsOriginalFrames must be a bool")
    return {
        "restarted": item["restarted"],
        "recipe": _token(item["recipe"], "retry.recipe"),
        "destination": _token(item["destination"], "retry.destination"),
        "readsOriginalFrames": item["readsOriginalFrames"],
        "frameIds": _frames(item["frameIds"], "retry.frameIds"),
    }


def _outputs(source: dict, job: dict, retry: dict) -> list[str]:
    return [source["filename"], job["destination"], job["temporary"], retry["destination"]]


def _reuses_source_filename(document: dict) -> bool:
    source = document.get("source")
    job = document.get("job")
    retry = document.get("retry")
    if not isinstance(source, dict) or not isinstance(job, dict) or not isinstance(retry, dict):
        return False
    name = source.get("filename")
    return name in {job.get("destination"), job.get("temporary"), retry.get("destination")}


def _parse(document: dict, allow_reuse: bool) -> dict[str, Any]:
    require(isinstance(document, dict), "development document must be an object")
    exact_keys(document, DOCUMENT_KEYS, "development document")
    _identity(document)
    policy = document["policy"]
    require(policy in {HONEST_POLICY, MUTANT_POLICY}, "policy is unknown")
    source = _parse_source(document["source"])
    profile = _parse_profile(document["profile"])
    job = _parse_job(document["job"], len(source["frames"]))
    retry = _parse_retry(document["retry"])
    names = _outputs(source, job, retry)
    if allow_reuse:
        require(policy == MUTANT_POLICY or job["destination"] == source["filename"]
                or job["temporary"] == source["filename"]
                or retry["destination"] == source["filename"],
                "reuse path requires the mutant policy or a source filename destination")
    else:
        require(policy == HONEST_POLICY, "policy must keep a separate destination")
        require(len(names) == len(set(names)), "source, destination, temporary, and retry names must differ")
    return {"policy": policy, "source": source, "profile": profile, "job": job, "retry": retry}


def _inventory(parsed: dict[str, Any]) -> list[str]:
    source = parsed["source"]
    profile = parsed["profile"]
    job = parsed["job"]
    retry = parsed["retry"]
    preserved = [
        f"source:{source['id']}:{source['filename']}:{source['hashBefore']}",
        f"profile:{profile['id']}:{profile['recipe']}:{profile['hash']}",
        f"handle:{source['handle']}",
        f"hashAfter:{source['hashAfter']}",
        f"destination:{job['destination']}",
        f"temporary:{job['temporary']}",
        f"partial:{job['partialLabel']}",
        f"progress:{job['developedFrames']}/{len(source['frames'])}",
        f"retry:{retry['recipe']}:{retry['destination']}",
    ]
    preserved.extend(f"frame:{frame}" for frame in source["frames"])
    return preserved


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is an honest P039 development fixture.

    The source-filename destination is not a valid non-destructive contract.
    assess rejects it before this validator is used.
    """
    require(isinstance(document, dict), "development document must be an object")
    require(document.get("policy") != MUTANT_POLICY, "mutant documents are not a retained-source contract")
    require(not _reuses_source_filename(document), "source filename must not be an output destination")
    _parse(document, allow_reuse=False)


def _reject_mutant(document: dict) -> dict[str, Any]:
    parsed = _parse(document, allow_reuse=True)
    name = parsed["source"]["filename"]
    reused = name in {
        parsed["job"]["destination"],
        parsed["job"]["temporary"],
        parsed["retry"]["destination"],
    }
    require(reused or parsed["policy"] == MUTANT_POLICY,
            "mutant rejection requires source-filename reuse")
    if parsed["policy"] == MUTANT_POLICY:
        require(parsed["job"]["destination"] == name,
                "mutant must reuse the source filename as the developed movie destination")
    preserved = _inventory(parsed)
    return _result(
        "rejected",
        [
            MUTANT,
            "a developed movie must not reuse the source filename",
            "cancellation must not delete or replace the original RAW sequence",
            ORACLE,
        ],
        [MUTANT_CLAIM, "source-overwrite"],
        preserved,
        [
            "host fixture only; physical S23 capture was not measured",
            "rejecting the mutant does not qualify a device development pipeline",
        ],
    )


def simulate(document: dict) -> dict[str, Any]:
    """Replay cancellation without writing the developed movie onto the source.

    Frames are copied. The temporary rows name an independent path. The retry
    list is the original frame ids when the document says it read them.
    """
    validate_document(document)
    parsed = _parse(document, allow_reuse=False)
    source = parsed["source"]
    job = parsed["job"]
    retry = parsed["retry"]
    frames = list(source["frames"])
    developed = frames[: job["developedFrames"]]
    temporary = [
        {"frame": frame, "recipe": parsed["profile"]["recipe"], "path": job["temporary"]}
        for frame in developed
    ]
    retry_frames = list(frames) if retry["readsOriginalFrames"] else []
    require(job["destination"] != source["filename"], "simulate refuses the source-filename mutant")
    require(all(row["path"] != source["filename"] for row in temporary),
            "temporary output must stay off the source filename")
    return {
        "frames": frames,
        "developed": developed,
        "temporary": temporary,
        "partialLabel": job["partialLabel"],
        "leasesClosed": job["leasesClosed"],
        "progressRecorded": job["progressRecorded"],
        "hashBefore": source["hashBefore"],
        "hashAfter": source["hashAfter"],
        "retryFrames": retry_frames,
        "retryRecipe": retry["recipe"],
        "profileRecipe": parsed["profile"]["recipe"],
        "restarted": retry["restarted"],
        "destination": job["destination"],
        "retryDestination": retry["destination"],
        "sourceFilename": source["filename"],
        "readOnly": source["readOnly"],
        "declaredRetryFrames": list(retry["frameIds"]),
    }


def assess(document: dict) -> dict[str, Any]:
    """Judge a cancelled development. The source-filename mutant is rejected.

    The source hash, profile, and frame inventory stay in preservedResults.
    Decision is never qualified or allowed. A partial movie is incomplete.
    """
    require(isinstance(document, dict), "development document must be an object")
    if document.get("policy") == MUTANT_POLICY or _reuses_source_filename(document):
        return _reject_mutant(document)
    validate_document(document)
    observed = simulate(document)
    parsed = _parse(document, allow_reuse=False)
    preserved = _inventory(parsed)
    questions = ["host fixture only; physical S23 capture was not measured"]
    reasons = [METHOD, ORACLE]
    rejected: list[str] = []
    if observed["hashBefore"] != observed["hashAfter"]:
        rejected.append("source-hash-changed")
        reasons.append("source hash changed across processing")
    if observed["readOnly"] is not True:
        rejected.append("writable-source-handle")
        reasons.append("source handle was not read-only")
    if observed["leasesClosed"] is not True:
        rejected.append("leases-left-open")
        reasons.append("cancellation left a source lease open")
    if observed["progressRecorded"] is not True:
        rejected.append("progress-not-recorded")
        reasons.append("cancellation did not record progress")
    if observed["partialLabel"] != PARTIAL_LABEL:
        rejected.append("partial-not-incomplete")
        reasons.append("partial result was not labelled incomplete")
    original = observed["frames"]
    if (
        observed["retryFrames"] != original
        or observed["declaredRetryFrames"] != original
    ):
        rejected.append("retry-missed-original-frames")
        reasons.append("retry did not read the original frames")
    if observed["destination"] == observed["sourceFilename"] or observed["retryDestination"] == observed["sourceFilename"]:
        rejected.append(MUTANT_CLAIM)
        reasons.append(MUTANT)
    halfway = len(original) % 2 == 0 and len(observed["developed"]) * 2 == len(original) and observed["developed"]
    soft: list[str] = []
    if not observed["restarted"]:
        soft.append("restart-not-recorded")
        reasons.append("process restart was not recorded")
    if not halfway:
        soft.append("not-halfway-cancellation")
        reasons.append("cancellation was not halfway through the original frames")
    if observed["retryRecipe"] == observed["profileRecipe"]:
        soft.append("retry-recipe-unchanged")
        reasons.append("retry did not use another film recipe")
    if rejected:
        reasons.append("original source and profile records were preserved")
        return _result("rejected", reasons, rejected, preserved, questions)
    if soft:
        questions.extend(soft)
        reasons.append("source hash and original frames were preserved")
        return _result("withheld", reasons, [], preserved, questions)
    reasons.extend([
        f"source hash {observed['hashBefore']} unchanged",
        f"partial result labelled {observed['partialLabel']}",
        f"developed {len(observed['developed'])} of {len(original)}",
        f"retry recipe {observed['retryRecipe']} read the original frames",
        "temporary output stayed independent of the source filename",
    ])
    questions.append("partial result stayed incomplete and was not a finished export")
    questions.append("retry read the original frames after restart")
    return _result("sources_retained", reasons, [], preserved, questions)
