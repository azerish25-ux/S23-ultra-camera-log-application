"""TC-P041-08 profile replacement and rollback.

A revised profile may be rendered explicitly. The archived recipe identity
stays. Overwriting bytes under the same identifier fails.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P041-08"
INTERVENTION = "Install a revised profile after an existing result has been rendered and archived."
EXPECTED = (
    "Preserve the earlier recipe identity and allow explicit new rendering without "
    "rewriting historical provenance."
)
NEGATIVE = "Overwriting profile bytes under the same identifier must fail."

_ACTIONS = ("install", "rename", "rollback", "firmware-change")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9-]{0,63}$")
_PAYLOAD_KEYS = (
    "archivedRecipeId",
    "archivedProfileId",
    "archivedHash",
    "incomingProfileId",
    "incomingHash",
    "action",
    "newRenderRequested",
    "sameIdentifierOverwrite",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "explicit_rerender", "renamed", "rolled_back", "withheld"}
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep the archived recipe. Reject a same-identifier byte overwrite."""
    fields = _payload(payload)
    preserved = [
        f"recipe:{fields['archivedRecipeId']}",
        f"archived:{fields['archivedProfileId']}:{fields['archivedHash']}",
        f"incoming:{fields['incomingProfileId']}:{fields['incomingHash']}",
        f"action:{fields['action']}",
    ]
    same_id = fields["incomingProfileId"] == fields["archivedProfileId"]
    same_hash = fields["incomingHash"] == fields["archivedHash"]
    questions = ["historical provenance was not rewritten"]
    if fields["sameIdentifierOverwrite"] or (same_id and not same_hash):
        return _result(
            "rejected",
            [NEGATIVE, EXPECTED, "archived profile bytes were not overwritten"],
            ["same-identifier-overwrite"],
            preserved,
            questions,
        )
    action = fields["action"]
    if action == "rollback":
        if not same_hash:
            return _result(
                "rejected",
                [EXPECTED, "rollback refused because the incoming hash is not the archived profile"],
                ["rollback-hash-mismatch"],
                preserved,
                questions,
            )
        return _result(
            "rolled_back",
            [EXPECTED, "rollback restored the archived profile without rewriting it"],
            [],
            preserved,
            questions,
        )
    if action == "rename":
        if same_id:
            return _result(
                "withheld",
                [EXPECTED, "rename did not change the profile identifier"],
                [],
                preserved,
                questions + ["rename did not change the identifier"],
            )
        return _result(
            "renamed",
            [EXPECTED, "user rename kept the archived recipe identity"],
            [],
            preserved,
            questions,
        )
    if action == "firmware-change" and same_id:
        return _result(
            "withheld",
            [EXPECTED, "firmware change did not bind a new profile identifier"],
            [],
            preserved,
            questions + ["firmware change did not bind a new profile id"],
        )
    if fields["newRenderRequested"] and not same_id:
        reason = (
            "firmware change requested an explicit new render"
            if action == "firmware-change"
            else "explicit new rendering was requested"
        )
        return _result(
            "explicit_rerender",
            [EXPECTED, reason, "archived recipe identity was preserved"],
            [],
            preserved,
            questions,
        )
    return _result(
        "withheld",
        [EXPECTED, "new rendering was not explicit"],
        [],
        preserved,
        questions + ["explicit new render was not requested"],
    )


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(label + " must be a token")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _HEX64.fullmatch(value) is None:
        raise ValueError(label + " must be 64 lowercase hex characters")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    action = payload["action"]
    if action not in _ACTIONS:
        raise ValueError("action must be install, rename, rollback, or firmware-change")
    requested = payload["newRenderRequested"]
    overwrite = payload["sameIdentifierOverwrite"]
    if type(requested) is not bool or type(overwrite) is not bool:
        raise ValueError("newRenderRequested and sameIdentifierOverwrite must be bools")
    return {
        "archivedRecipeId": _token(payload["archivedRecipeId"], "archivedRecipeId"),
        "archivedProfileId": _token(payload["archivedProfileId"], "archivedProfileId"),
        "archivedHash": _digest(payload["archivedHash"], "archivedHash"),
        "incomingProfileId": _token(payload["incomingProfileId"], "incomingProfileId"),
        "incomingHash": _digest(payload["incomingHash"], "incomingHash"),
        "action": action,
        "newRenderRequested": requested,
        "sameIdentifierOverwrite": overwrite,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P041-08 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
