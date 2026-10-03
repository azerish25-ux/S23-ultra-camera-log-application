"""TC-P047-08 profile replacement and rollback.

Intervention: Install a revised profile after an existing result has been
rendered and archived.
Expected: Preserve the earlier recipe identity and allow explicit new rendering
without rewriting historical provenance.
Negative: Overwriting profile bytes under the same identifier must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P047-08"
INTERVENTION = (
    "Install a revised profile after an existing result has been rendered and archived."
)
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering without "
    "rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_OPERATIONS = ("install", "firmware-change", "user-rename", "rollback")
_IDENT = re.compile(r"[a-z0-9-]{1,64}")
_DIGEST = re.compile(r"[0-9a-f]{8,64}")
_PAYLOAD_KEYS = (
    "archivedProfileId",
    "archivedDigest",
    "installedProfileId",
    "installedDigest",
    "overwriteSameId",
    "operation",
    "rewritesHistory",
    "renderedResultId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "explicit_render", "renamed", "rolled_back")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Same-id byte replacement and history rewrites fail."""
    archived_id, archived_digest, installed_id, installed_digest, overwrite, operation, rewrite, rendered = (
        _payload(payload)
    )
    preserved = [
        f"recipe:{archived_id}:{archived_digest}",
        "rendered:" + rendered,
        "operation:" + operation,
        f"candidate:{installed_id}:{installed_digest}",
    ]
    same_id = installed_id == archived_id
    same_bytes = installed_digest == archived_digest
    rejected: list[str] = []
    if overwrite or (same_id and not same_bytes):
        rejected.append("same-identifier-overwrite")
    if rewrite:
        rejected.append("historical-provenance-rewrite")
    if rejected:
        reasons = [EXPECTED, "historical recipe identity was not rewritten"]
        if "same-identifier-overwrite" in rejected:
            reasons.append(NEGATIVE)
        if rewrite:
            reasons.append("historical provenance rewrite rejected")
        return _result(
            "rejected",
            reasons,
            rejected,
            preserved,
            ["archived recipe bytes retained"],
        )
    if operation == "rollback":
        if not same_id or not same_bytes:
            raise ValueError("rollback must restore the archived profile identity and bytes")
        return _result(
            "rolled_back",
            [
                EXPECTED,
                "rollback restored the previous approved profile",
                "historical provenance was not rewritten",
            ],
            [],
            preserved,
            ["rollback is not a new measured default"],
        )
    if operation == "user-rename":
        if same_id:
            raise ValueError("user rename requires a distinct profile identifier")
        return _result(
            "renamed",
            [
                EXPECTED,
                "user rename kept the archived recipe identity",
                "historical provenance was not rewritten",
            ],
            [],
            preserved,
            ["rename does not rewrite the rendered result"],
        )
    if same_id:
        raise ValueError(operation + " of identical bytes under the same id is not an explicit new render")
    return _result(
        "explicit_render",
        [
            EXPECTED,
            operation + " kept the archived recipe and recorded an explicit new profile",
            "historical provenance was not rewritten",
        ],
        [],
        preserved,
        ["explicit render is not physical S23 qualification"],
    )


def _payload(payload: object) -> tuple[str, str, str, str, bool, str, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    operation = payload["operation"]
    if operation not in _OPERATIONS:
        raise ValueError("operation is unsupported")
    overwrite = payload["overwriteSameId"]
    rewrite = payload["rewritesHistory"]
    if type(overwrite) is not bool or type(rewrite) is not bool:
        raise ValueError("overwrite and history flags must be bools")
    return (
        _ident(payload["archivedProfileId"], "archivedProfileId"),
        _digest(payload["archivedDigest"], "archivedDigest"),
        _ident(payload["installedProfileId"], "installedProfileId"),
        _digest(payload["installedDigest"], "installedDigest"),
        overwrite,
        operation,
        rewrite,
        _ident(payload["renderedResultId"], "renderedResultId"),
    )


def _ident(value: object, label: str) -> str:
    if not isinstance(value, str) or _IDENT.fullmatch(value) is None:
        raise ValueError(label + " must be a canonical identifier")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(label + " must be a hex digest")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("profile decision cannot be qualified or allowed")
    if not reasons or any(type(item) is not str or not item for item in reasons):
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
