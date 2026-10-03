"""TC-P036-02 metadata callback reordering.

Intervention: Deliver metadata in a different callback order from Images with
one exact match delayed.
Expected: Pair only matching sensor timestamps within the bounded policy and
retain unresolved status otherwise.
Negative: Nearest-time or latest-metadata association must fail.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P036-02"
INTERVENTION = (
    "Deliver metadata in a different callback order from Images with one exact match delayed."
)
EXPECTED = (
    "Pair only matching sensor timestamps within the bounded policy and retain unresolved "
    "status otherwise."
)
NEGATIVE = "Nearest-time or latest-metadata association must fail."

_ORDERS = ("image_before_metadata", "metadata_before_image")
_ASSOCIATIONS = ("exact_timestamp", "nearest_time", "latest_metadata")
_UINT = re.compile(r"0|[1-9][0-9]*")
_PAYLOAD_KEYS = (
    "imageTimestampNs",
    "metadataTimestampNs",
    "callbackOrder",
    "policyBoundNs",
    "delayNs",
    "association",
    "duplicateTimestamp",
    "missingMetadata",
    "delayedAfterStop",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "unresolved", "paired")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Pair exact sensor timestamps inside the bound. Keep unresolved status."""
    fields = _payload(payload)
    metadata = "metadata:missing" if fields["missingMetadata"] else (
        f"metadata:{fields['metadataTimestampNs']}"
    )
    preserved = [
        f"image:{fields['imageTimestampNs']}",
        metadata,
        f"order:{fields['callbackOrder']}",
        f"delay:{fields['delayNs']}",
        f"bound:{fields['policyBoundNs']}",
    ]
    rejected: list[str] = []
    if fields["association"] == "nearest_time":
        rejected.append("nearest-time")
    elif fields["association"] == "latest_metadata":
        rejected.append("latest-metadata")

    timestamps_match = (
        not fields["missingMetadata"]
        and fields["metadataTimestampNs"] == fields["imageTimestampNs"]
    )
    within_bound = fields["delayNs"] <= fields["policyBoundNs"]
    exact = (
        fields["association"] == "exact_timestamp"
        and timestamps_match
        and within_bound
        and not fields["duplicateTimestamp"]
        and not fields["delayedAfterStop"]
    )

    questions: list[str] = []
    if fields["association"] != "exact_timestamp":
        decision = "rejected"
        reasons = [NEGATIVE, EXPECTED, "unresolved status retained"]
        questions.append("association was not an exact sensor timestamp")
    elif exact:
        decision = "paired"
        reasons = [
            EXPECTED,
            "exact sensor timestamps paired within the bounded policy",
        ]
        if fields["delayNs"]:
            reasons.append("delayed exact match stayed inside the bound")
        reasons.append("callback order did not select a different metadata record")
    else:
        decision = "unresolved"
        reasons = [EXPECTED, "unresolved status retained"]
        if fields["missingMetadata"]:
            reasons.append("missing metadata was not replaced")
            questions.append("metadata missing")
        if fields["duplicateTimestamp"]:
            reasons.append("duplicate timestamps were not collapsed to one pair")
            questions.append("duplicate timestamp")
        if fields["delayedAfterStop"]:
            reasons.append("metadata delayed after stop stayed unresolved")
            questions.append("delayed after stop")
        if not timestamps_match and not fields["missingMetadata"]:
            reasons.append("sensor timestamps did not match")
            questions.append("timestamp mismatch")
        if timestamps_match and not within_bound:
            reasons.append("exact match arrived outside the bounded policy")
            questions.append("outside bounded policy")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    image = payload["imageTimestampNs"]
    if not isinstance(image, str) or _UINT.fullmatch(image) is None:
        raise ValueError("imageTimestampNs must be a canonical non-negative integer string")
    missing = payload["missingMetadata"]
    if type(missing) is not bool:
        raise ValueError("missingMetadata must be a bool")
    metadata = payload["metadataTimestampNs"]
    if missing:
        if metadata is not None:
            raise ValueError("missing metadata cannot carry a timestamp")
    elif not isinstance(metadata, str) or _UINT.fullmatch(metadata) is None:
        raise ValueError("metadataTimestampNs must be a canonical non-negative integer string")
    order = payload["callbackOrder"]
    if order not in _ORDERS:
        raise ValueError("callbackOrder is not a known order")
    bound = payload["policyBoundNs"]
    delay = payload["delayNs"]
    if type(bound) is not int or bound <= 0:
        raise ValueError("policyBoundNs must be a positive int")
    if type(delay) is not int or delay < 0:
        raise ValueError("delayNs must be a non-negative int")
    association = payload["association"]
    if association not in _ASSOCIATIONS:
        raise ValueError("association is not a known policy")
    duplicate = payload["duplicateTimestamp"]
    after_stop = payload["delayedAfterStop"]
    if type(duplicate) is not bool or type(after_stop) is not bool:
        raise ValueError("duplicateTimestamp and delayedAfterStop must be bools")
    return {
        "imageTimestampNs": image,
        "metadataTimestampNs": metadata,
        "callbackOrder": order,
        "policyBoundNs": bound,
        "delayNs": delay,
        "association": association,
        "duplicateTimestamp": duplicate,
        "missingMetadata": missing,
        "delayedAfterStop": after_stop,
    }


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("metadata decision cannot be qualified or allowed")
    if not reasons:
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
