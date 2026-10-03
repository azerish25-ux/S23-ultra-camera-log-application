"""TC-P050-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations


CASE_ID = "TC-P050-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase "
    "boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly declared "
    "storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_ANCHORS = ("zero", "source_white", "encoding_boundary")
_PAYLOAD_KEYS = (
    "anchor",
    "samples",
    "black",
    "sourceWhite",
    "storageLimit",
    "displayLimit",
    "implicitClamp",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "retained")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep signed and over-range samples. Detect an implicit zero-to-one clamp."""
    anchor, samples, black, source_white, storage, display, implicit = _payload(payload)
    span = source_white - black
    preserved = [
        f"anchor:{anchor}",
        f"black:{black}",
        f"source-white:{source_white}",
        f"storage-limit:{storage}",
        f"display-limit:{display}",
    ]
    questions: list[str] = []
    for sample in samples:
        signed = sample - black
        preserved.append(f"sample:{sample}")
        preserved.append(f"signed:{sample}:{signed}")
        preserved.append(f"ratio:{sample}:{signed}/{span}")
        if sample > storage or sample > display:
            questions.append(f"declared-limit:{sample}")
    if implicit:
        reasons = [
            EXPECTED,
            NEGATIVE,
            "implicit zero-to-one clamp detected",
            f"anchor:{anchor}",
        ]
        return _result("rejected", reasons, ["implicit-zero-to-one-clamp"], preserved, questions)
    reasons = [
        EXPECTED,
        "signed and over-range values kept until the declared limit",
        f"anchor:{anchor}",
    ]
    if anchor == "zero":
        reasons.append("values around zero were not clamped")
    elif anchor == "source_white":
        reasons.append("source white is a reference, not a hard ceiling")
    else:
        reasons.append("output encoding boundary was explicit")
    if questions:
        reasons.append("explicit limit recorded; value not forced into zero-to-one")
    return _result("retained", reasons, [], preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    anchor = payload["anchor"]
    if anchor not in _ANCHORS:
        raise ValueError("anchor must be zero, source_white, or encoding_boundary")
    samples = payload["samples"]
    if type(samples) is not list or not samples:
        raise ValueError("samples must be a non-empty list")
    parsed: list[int] = []
    for sample in samples:
        if type(sample) is not int:
            raise ValueError("sample must be an int")
        parsed.append(sample)
    black = payload["black"]
    source_white = payload["sourceWhite"]
    storage = payload["storageLimit"]
    display = payload["displayLimit"]
    for label, value in (
        ("black", black),
        ("sourceWhite", source_white),
        ("storageLimit", storage),
        ("displayLimit", display),
    ):
        if type(value) is not int:
            raise ValueError(label + " must be an int")
    if source_white <= black:
        raise ValueError("sourceWhite must exceed black")
    if storage < source_white or display < source_white:
        raise ValueError("declared limits must reach the source white reference")
    if not any(sample < black for sample in parsed):
        raise ValueError("samples must include a value below black")
    if not any(sample > source_white for sample in parsed):
        raise ValueError("samples must include a highlight above source white")
    if anchor == "zero" and 0 not in parsed:
        raise ValueError("zero anchor requires a sample at zero")
    if anchor == "source_white" and source_white not in parsed:
        raise ValueError("source white anchor requires the source white sample")
    if anchor == "encoding_boundary" and storage not in parsed and display not in parsed:
        raise ValueError("encoding boundary anchor requires a declared limit sample")
    implicit = payload["implicitClamp"]
    if type(implicit) is not bool:
        raise ValueError("implicitClamp must be a bool")
    return anchor, parsed, black, source_white, storage, display, implicit


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("range decision cannot be qualified or allowed")
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
