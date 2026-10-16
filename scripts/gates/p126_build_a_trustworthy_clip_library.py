#!/usr/bin/env python3
"""P126 Build a trustworthy clip library.

Host fixture only. Index clip rows by exact content identity. This module does
not probe a device, does not qualify a physical S23, and does not execute the
TC-P126-01 through TC-P126-08 modules.

A row is playable only when the file is present, verification is "verified",
byte_count is positive, and any supplied content bytes recompute to
content_sha256. present false forces playable false and verification "missing".
Unverified rows stay unverified. Missing ids are listed. Thumbnail cache is not
availability.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P126"
WORKSTREAM = 16
TITLE = "Build a trustworthy clip library"
GOAL = "Keep source, result, metadata, thumbnail, and recovery identities paired."
METHOD = (
    "Index exact media identities, recipe versions, verification status, duration, geometry, "
    "and availability. Thumbnails are derived previews, not proof of output validity. Handle "
    "revoked grants and missing files without corrupting the library or silently deleting "
    "historical records."
)
FIXTURE = "A thumbnail remains cached after the underlying media permission is revoked."
ORACLE = (
    "The library shows unavailable media clearly and does not imply that the thumbnail "
    "represents accessible verified footage."
)
MUTANT = "Use thumbnail existence as the media availability check."
DELIVERABLE = "Clip library schema and missing-media tests"
DEPENDENCIES = ("P125",)
PLAYABLE_RULE = "present-and-verified-and-matching-hash-and-positive-byte-count"
VERIFICATION_STATES = ("verified", "unverified", "missing")
ROLES = ("source", "result", "metadata", "thumbnail", "recovery")
SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")
CLIP_REQUIRED = {
    "clip_id",
    "content_sha256",
    "byte_count",
    "present",
    "playable",
    "verification",
}
CLIP_OPTIONAL = {
    "content",
    "thumbnail_cached",
    "prior_verification",
    "role",
    "bundle_id",
}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "clips",
    "omitted_ids",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
CASES = (
    {
        "id": "TC-P126-01",
        "name": "Ambiguous imported signal",
        "intervention": "Import media with absent or contradictory color tags, rotation, or timing metadata.",
        "expected": (
            "Separate detected facts from user interpretation and avoid silent normalization "
            "to an assumed source type."
        ),
        "negative": "Filename extension alone must not determine transfer or dynamic range.",
        "repeat": "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.",
    },
    {
        "id": "TC-P126-02",
        "name": "Mutable recipe during export",
        "intervention": "Change UI parameters after a render has begun but before it finishes.",
        "expected": "Keep the running job bound to its frozen recipe and create a new version for subsequent edits.",
        "negative": "Reading live slider values for successive output frames must fail.",
        "repeat": "Repeat stock, focus, grain seed, output range, and source interpretation changes.",
    },
    {
        "id": "TC-P126-03",
        "name": "Checkpoint identity mismatch",
        "intervention": "Replace source, model, profile, or graph while retaining a previously completed chunk cache.",
        "expected": "Reject incompatible resume data or start a distinct job with new identities.",
        "negative": "Filename and frame number alone must not validate a checkpoint.",
        "repeat": "Repeat one changed identity field at a time and inspect specific rejection reasons.",
    },
    {
        "id": "TC-P126-04",
        "name": "Cancellation at acceptance boundary",
        "intervention": "Cancel during rendering, verification, publication, or final cleanup.",
        "expected": (
            "Acknowledge cancellation only after ownership is controlled and never publish a "
            "cancelled job as accepted."
        ),
        "negative": "A late worker callback that reverses cancellation must fail.",
        "repeat": "Repeat with process restart and an already retained partial output.",
    },
    {
        "id": "TC-P126-05",
        "name": "Temporary storage exhaustion",
        "intervention": "Make remaining space insufficient for intermediate work or duplicate publication storage.",
        "expected": (
            "Pause or fail safely before source loss, preserving recoverable artifacts and "
            "clear cleanup choices."
        ),
        "negative": "Budgeting only final output bytes must fail.",
        "repeat": "Repeat before rendering, during chunk assembly, and during gallery publication.",
    },
    {
        "id": "TC-P126-06",
        "name": "Missing or revoked media access",
        "intervention": "Revoke the source grant or remove a file while the library still has a cached thumbnail.",
        "expected": (
            "Show actual availability and preserve historical metadata without treating the "
            "thumbnail as accessible media."
        ),
        "negative": "Thumbnail presence must not certify a valid source or output.",
        "repeat": "Repeat local files, document-provider grants, and recovered private media.",
    },
    {
        "id": "TC-P126-07",
        "name": "Resume boundary duplication",
        "intervention": "Assemble chunks whose temporal overlap contains repeated or omitted output frames.",
        "expected": "Emit the exact intended timeline once and maintain declared temporal continuity.",
        "negative": "A playable movie with duplicated overlap frames must fail cadence integrity.",
        "repeat": "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries.",
    },
    {
        "id": "TC-P126-08",
        "name": "Shared bundle privacy and interpretation",
        "intervention": "Export a result with private paths or without necessary signal and recipe metadata.",
        "expected": "Redact personal information while retaining the technical interpretation needed for correct use.",
        "negative": (
            "A Log master without its required interpretation record must not be silently "
            "presented as universally self-describing."
        ),
        "repeat": "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports.",
    },
)

OPEN_QUESTIONS = (
    "physical S23 measurement was not run",
    "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def content_sha256(data: bytes) -> str:
    """SHA-256 hex digest of exact content bytes. Lowercase, 64 characters."""
    require(isinstance(data, bytes), "content_sha256 expects bytes")
    return hashlib.sha256(data).hexdigest()


def content_bytes(content: Any) -> bytes:
    if isinstance(content, bytes):
        return content
    if isinstance(content, str):
        return content.encode("utf-8")
    if isinstance(content, list):
        require(
            all(type(item) is int and 0 <= item <= 255 for item in content),
            "content byte list is invalid",
        )
        return bytes(content)
    raise ValueError("content must be bytes, str, or a list of byte values")


def _text(value: Any, label: str) -> str:
    require(isinstance(value, str) and value.strip() and value == value.strip(), f"{label} must be a non-empty string")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def _parse_clip(item: Any, index: int) -> dict[str, Any]:
    require(isinstance(item, dict), f"clips[{index}] must be an object")
    keys = set(item)
    missing = CLIP_REQUIRED - keys
    extra = keys - CLIP_REQUIRED - CLIP_OPTIONAL
    require(not missing, f"clips[{index}] missing fields: " + ", ".join(sorted(missing)))
    require(not extra, f"clips[{index}] has unexpected fields: " + ", ".join(sorted(extra)))
    clip_id = _text(item["clip_id"], f"clips[{index}].clip_id")
    digest = item["content_sha256"]
    require(isinstance(digest, str) and SHA256_HEX.fullmatch(digest), f"clips[{index}].content_sha256 must be 64 lowercase hex chars")
    byte_count = item["byte_count"]
    require(type(byte_count) is int and byte_count >= 0, f"clips[{index}].byte_count must be a non-negative int")
    require(type(item["present"]) is bool, f"clips[{index}].present must be a bool")
    require(type(item["playable"]) is bool, f"clips[{index}].playable must be a bool")
    verification = item["verification"]
    require(verification in VERIFICATION_STATES, f"clips[{index}].verification is invalid")
    supplied: bytes | None = None
    if "content" in item:
        supplied = content_bytes(item["content"])
    thumbnail_cached = False
    if "thumbnail_cached" in item:
        require(type(item["thumbnail_cached"]) is bool, f"clips[{index}].thumbnail_cached must be a bool")
        thumbnail_cached = item["thumbnail_cached"]
    prior = None
    if "prior_verification" in item:
        prior = item["prior_verification"]
        require(prior in VERIFICATION_STATES, f"clips[{index}].prior_verification is invalid")
    role = None
    if "role" in item:
        role = item["role"]
        require(role in ROLES, f"clips[{index}].role is invalid")
    bundle_id = None
    if "bundle_id" in item:
        bundle_id = _text(item["bundle_id"], f"clips[{index}].bundle_id")
    return {
        "clip_id": clip_id,
        "content_sha256": digest,
        "byte_count": byte_count,
        "present": item["present"],
        "playable": item["playable"],
        "verification": verification,
        "content": supplied,
        "thumbnail_cached": thumbnail_cached,
        "prior_verification": prior,
        "role": role,
        "bundle_id": bundle_id,
    }


def playable_allowed(row: dict[str, Any], content_matches: bool | None) -> bool:
    """True only when this row may claim playable.

    Bytes must be present, verification must be verified, byte_count must be
    positive, and supplied content must match content_sha256 when it is present.
    A cached thumbnail is not an input to this rule.
    """
    if row["present"] is not True:
        return False
    if row["verification"] != "verified":
        return False
    if type(row["byte_count"]) is not int or row["byte_count"] <= 0:
        return False
    if content_matches is False:
        return False
    return True


def _content_status(row: dict[str, Any]) -> tuple[bool | None, list[str]]:
    tokens: list[str] = []
    if row["content"] is None:
        return None, tokens
    digest = content_sha256(row["content"])
    length_ok = len(row["content"]) == row["byte_count"]
    hash_ok = digest == row["content_sha256"]
    if not row["present"]:
        tokens.append("content-for-absent-clip")
    if not hash_ok:
        tokens.append("content-sha256-mismatch")
    if not length_ok:
        tokens.append("byte-count-mismatch")
    matches = bool(row["present"] and hash_ok and length_ok)
    return matches, tokens


def _clip_token(row: dict[str, Any]) -> str:
    role = row["role"] if row["role"] is not None else "unspecified"
    bundle = row["bundle_id"] if row["bundle_id"] is not None else "unspecified"
    present = "true" if row["present"] else "false"
    playable = "true" if row["playable"] else "false"
    return (
        f"clip_id={row['clip_id']} present={present} playable={playable} "
        f"verification={row['verification']} sha256={row['content_sha256']} "
        f"byte_count={row['byte_count']} role={role} bundle={bundle}"
    )


def evaluate_library(clips: Any, omitted_ids: Any) -> dict[str, Any]:
    """Index clip rows. Missing files stay listed. Bad playable claims are rejected."""
    require(isinstance(clips, list), "clips must be a list")
    require(isinstance(omitted_ids, list), "omitted_ids must be a list")
    seen_omitted: set[str] = set()
    for index, omitted in enumerate(omitted_ids):
        require(isinstance(omitted, str) and omitted.strip() and omitted == omitted.strip(), f"omitted_ids[{index}] must be a non-empty string")
        require(omitted not in seen_omitted, "omitted_ids contains a duplicate")
        seen_omitted.add(omitted)
    rows = [_parse_clip(item, index) for index, item in enumerate(clips)]
    rejected: list[str] = []
    reasons = [
        "playableRule=" + PLAYABLE_RULE,
        "fixture: " + FIXTURE,
    ]
    preserved = ["playableRule=" + PLAYABLE_RULE]
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_id.setdefault(row["clip_id"], []).append(row)
    for clip_id, group in by_id.items():
        if len(group) > 1:
            _add(rejected, "duplicate-clip-id:" + clip_id)
            reasons.append("duplicate clip_id " + clip_id + " is rejected")
            hashes = {item["content_sha256"] for item in group}
            if len(hashes) > 1:
                _add(rejected, "duplicate-clip-id-hash-mismatch:" + clip_id)
                reasons.append("duplicate clip_id " + clip_id + " has differing content hashes")
    role_counts: dict[tuple[str, str], int] = {}
    for row in rows:
        if row["bundle_id"] is not None and row["role"] is not None:
            key = (row["bundle_id"], row["role"])
            role_counts[key] = role_counts.get(key, 0) + 1
    for (bundle_id, role), count in role_counts.items():
        if count > 1:
            token = f"duplicate-bundle-role:{bundle_id}:{role}"
            _add(rejected, token)
            reasons.append(token)

    indexed: set[str] = set()
    for row in rows:
        indexed.add(row["clip_id"])
        matches, content_tokens = _content_status(row)
        for token in content_tokens:
            _add(rejected, token)
            reasons.append(token + ":" + row["clip_id"])
        if row["present"] is False:
            if row["verification"] != "missing":
                _add(rejected, "absent-clip-not-missing")
                reasons.append("absent clip " + row["clip_id"] + " must use verification missing")
            if row["playable"] is True:
                _add(rejected, "playable-absent-bytes")
                reasons.append("playable true while bytes are absent for " + row["clip_id"])
        if row["present"] is True and row["verification"] == "missing":
            _add(rejected, "present-marked-missing")
            reasons.append("present clip " + row["clip_id"] + " cannot be verification missing")
        if row["prior_verification"] == "unverified" and row["verification"] == "verified":
            if matches is not True:
                _add(rejected, "unverified-promoted-without-hash-match")
                reasons.append("unverified clip " + row["clip_id"] + " was promoted without a hash match")
            else:
                reasons.append("promoted-with-hash-match:" + row["clip_id"])
        elif row["verification"] == "unverified":
            reasons.append("stayed-unverified:" + row["clip_id"])
        if row["playable"] is True and not playable_allowed(row, matches):
            if row["present"] is True and row["verification"] == "unverified":
                _add(rejected, "unverified-not-playable")
                reasons.append("unverified clip " + row["clip_id"] + " stays unverified and is not playable")
            elif row["present"] is True and row["verification"] == "verified" and row["byte_count"] <= 0:
                _add(rejected, "playable-without-positive-bytes")
                reasons.append("playable clip " + row["clip_id"] + " needs a positive byte_count")
            elif row["present"] is True and row["verification"] != "verified":
                _add(rejected, "playable-not-verified")
                reasons.append("playable clip " + row["clip_id"] + " is not verified")
        if row["thumbnail_cached"] and row["present"] is False and row["playable"] is True:
            _add(rejected, "thumbnail-certifies-availability")
            reasons.append("thumbnail cache does not make " + row["clip_id"] + " available")
        elif row["thumbnail_cached"] and row["present"] is False:
            reasons.append("thumbnail-not-availability:" + row["clip_id"])
        preserved.append(_clip_token(row))
        if row["present"] is False or row["verification"] == "missing":
            missing_token = "missing:" + row["clip_id"]
            preserved.append(missing_token)
            reasons.append("listed " + missing_token)

    for omitted in omitted_ids:
        if omitted not in indexed:
            token = "omitted-missing-id:" + omitted
            _add(rejected, token)
            reasons.append("known missing id " + omitted + " was omitted from the index")
            continue
        for row in by_id[omitted]:
            unavailable = (
                row["present"] is False
                and row["playable"] is False
                and row["verification"] == "missing"
            )
            if not unavailable:
                token = "omitted-id-not-missing:" + omitted
                _add(rejected, token)
                reasons.append("omitted id " + omitted + " is not recorded as missing")

    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
    }


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle. Thumbnail existence is not media availability."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = _text(document["evidenceId"], "evidenceId")
    claim = _text(document["claim"], "claim")
    require(type(document["applyMutant"]) is bool, "applyMutant must be a bool")
    library = evaluate_library(document["clips"], document["omitted_ids"])
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
    ]
    reasons.extend(library["reasons"])
    rejected = list(library["rejectedClaims"])
    if document["applyMutant"]:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    preserved = [evidence, claim]
    preserved.extend(library["preservedResults"])
    result = {
        "caseId": PHASE,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": list(OPEN_QUESTIONS),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(PLAYABLE_RULE in " ".join(result["reasons"] + result["preservedResults"]), "playable rule missing")
    return result
