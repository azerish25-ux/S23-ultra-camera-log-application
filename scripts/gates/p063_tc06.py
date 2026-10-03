"""TC-P063-06 source-lineage laundering.

An SDR or HLG acquisition must not be labeled RAW-derived or
native-camera-equivalent. Changing the encoding does not upgrade the
category, even in a ten-bit visually flat file. This host case does not
qualify a physical S23.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P063-06"
INTERVENTION = "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."
REPEAT = "Repeat through import, recipe selection, export naming, and shared metadata."

_ACQUISITIONS = ("sdr", "hlg", "raw")
_LABELS = ("raw-derived", "native-camera-equivalent", "sdr", "hlg")
_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_DEPTHS = ("8", "10")
_UPGRADED = {"raw-derived", "native-camera-equivalent"}
_PAYLOAD_KEYS = (
    "assetId",
    "acquisition",
    "label",
    "stage",
    "containerDepth",
    "visuallyFlat",
    "encodingChanged",
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
    """Reject a label that upgrades SDR or HLG into a RAW-derived claim."""
    asset, acquisition, label, stage, depth, flat, encoding_changed = _payload(payload)
    preserved = [
        asset,
        f"acquisition:{acquisition}",
        f"label:{label}",
        f"stage:{stage}",
        f"depth:{depth}",
        f"visually-flat:{'true' if flat else 'false'}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}"]
    laundered = acquisition in {"sdr", "hlg"} and label in _UPGRADED
    if laundered:
        rejected = ["lineage-laundered"]
        reasons.append(
            f"{acquisition} acquisition cannot wear label {label} at {stage}"
        )
        if depth == "10" or flat:
            reasons.append("ten-bit storage and a flat appearance do not change acquisition")
        if encoding_changed:
            rejected.append("encoding-cannot-upgrade")
            reasons.append(NEGATIVE)
        decision = "rejected"
    else:
        rejected = []
        decision = "withheld"
        reasons.append("the label does not upgrade acquisition and is not qualification")
        if encoding_changed:
            reasons.append(NEGATIVE)
            questions.append("encoding change was recorded and did not upgrade the category")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    asset = payload["assetId"]
    if not isinstance(asset, str) or _TOKEN.fullmatch(asset) is None:
        raise ValueError("assetId must be a token")
    acquisition = payload["acquisition"]
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    label = payload["label"]
    if label not in _LABELS:
        raise ValueError("label is unsupported")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    depth = payload["containerDepth"]
    if depth not in _DEPTHS:
        raise ValueError("containerDepth must be 8 or 10")
    flat = payload["visuallyFlat"]
    encoding_changed = payload["encodingChanged"]
    if type(flat) is not bool or type(encoding_changed) is not bool:
        raise ValueError("visuallyFlat and encodingChanged must be bools")
    return asset, acquisition, label, stage, depth, flat, encoding_changed


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P063-06 must not yield qualified or allowed")
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
