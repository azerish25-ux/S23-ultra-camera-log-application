"""TC-P063-07 double viewing transform.

A second display or log transform is a mismatch. Clean and rendered
branches stay separate. A generic player thumbnail does not certify color.
This host case does not qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P063-07"
INTERVENTION = "Apply a display or log transform twice through preview, development, or editor configuration."
EXPECTED = "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."
REPEAT = "Repeat with manual editor assignments and automatically detected source tags."

_STAGES = ("preview", "development", "editor", "manual-assignment", "auto-tag")
_COUNTS = ("1", "2")
_PAYLOAD_KEYS = (
    "clipId",
    "stage",
    "transformCount",
    "referencePatch",
    "cleanBranch",
    "renderedBranch",
    "thumbnailOnly",
    "playerOpened",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Detect a double viewing transform and keep both branches."""
    clip, stage, count, patch, clean, rendered, thumbnail, opened = _payload(payload)
    preserved = [
        clip,
        f"stage:{stage}",
        f"transforms:{count}",
        f"patch:{patch}",
        f"clean:{clean}",
        f"rendered:{rendered}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    rejected: list[str] = []
    if count == "2":
        rejected.append("double-viewing-transform")
        reasons.append(f"reference patch {patch} shows two viewing transforms at {stage}")
        questions.append(f"clean branch {clean} kept separate from rendered branch {rendered}")
    if thumbnail:
        rejected.append("generic-player-thumbnail")
        reasons.append(NEGATIVE)
        if opened:
            reasons.append("player open plus a thumbnail is not color interpretation")
    if "generic-player-thumbnail" in rejected:
        decision = "rejected"
    elif count == "2":
        decision = "mismatch_detected"
    else:
        decision = "branches_separated"
        reasons.append(f"clean {clean} and rendered {rendered} stay separate")
        questions.append("branches_separated is not qualification")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    clip = payload["clipId"]
    patch = payload["referencePatch"]
    clean = payload["cleanBranch"]
    rendered = payload["renderedBranch"]
    for name, value in (
        ("clipId", clip),
        ("referencePatch", patch),
        ("cleanBranch", clean),
        ("renderedBranch", rendered),
    ):
        if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
            raise ValueError(f"{name} must be a token")
    if clean == rendered:
        raise ValueError("clean and rendered branches must stay distinct")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    count = payload["transformCount"]
    if count not in _COUNTS:
        raise ValueError("transformCount must be 1 or 2")
    thumbnail = payload["thumbnailOnly"]
    opened = payload["playerOpened"]
    if type(thumbnail) is not bool or type(opened) is not bool:
        raise ValueError("thumbnailOnly and playerOpened must be bools")
    return clip, stage, count, patch, clean, rendered, thumbnail, opened


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-07 must not yield qualified or allowed")
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
