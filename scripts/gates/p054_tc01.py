"""TC-P054-01 negative and bright intermediate values.

Intervention: Exercise values below black and highlights above diffuse white
through the phase boundary.
Expected: Preserve valid signed and over-range information until the explicitly
declared storage or display limit.
Negative: An implicit zero-to-one clamp must be detected.
"""

from __future__ import annotations

import re
from decimal import Decimal

CASE_ID = "TC-P054-01"
INTERVENTION = (
    "Exercise values below black and highlights above diffuse white through the phase boundary."
)
EXPECTED = (
    "Preserve valid signed and over-range information until the explicitly "
    "declared storage or display limit."
)
NEGATIVE = "An implicit zero-to-one clamp must be detected."

_LOCI = ("around-zero", "source-white", "encoding-boundary", "below-black", "above-white")
_PAYLOAD_KEYS = ("sampleId", "locus", "codeValue", "sourceWhite", "storageLimit", "implicitClamp")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,63}")
_DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
_SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")


def evaluate(payload: dict) -> dict:
    """Retain signed and over-range codes until a declared limit. Detect a 0..1 clamp."""
    sample, locus, code, white, limit, clamp = _payload(payload)
    preserved = [
        sample,
        f"locus:{locus}",
        f"code:{code}",
        f"source-white:{white}",
        f"storage-limit:{limit}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    rejected: list[str] = []
    questions: list[str] = []
    if clamp:
        decision = "rejected"
        rejected.append("implicit-zero-to-one-clamp")
        reasons.append(NEGATIVE)
        questions.append("implicit clamp detected; signed and over-range values stay in the inventory")
    elif limit == "none":
        decision = "retained"
        reasons.append("no storage limit is declared, so the signed or over-range code is retained")
        questions.append(f"{locus} value {code} is retained ahead of a storage limit")
    else:
        if Decimal(code) > Decimal(limit):
            decision = "storage-limited"
            rejected.append("beyond-declared-limit")
            reasons.append("code exceeds the declared storage limit and is limited only there")
            questions.append(f"code {code} exceeds declared limit {limit}")
            preserved.append(f"stored:{limit}")
        else:
            decision = "retained"
            reasons.append("code is inside the declared limit, including signed values below black")
            questions.append(f"{locus} value {code} stays unclamped")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple[str, str, str, str, str, bool]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    sample = payload["sampleId"]
    if not isinstance(sample, str) or _TOKEN.fullmatch(sample) is None:
        raise ValueError("sampleId must be a token")
    locus = payload["locus"]
    if locus not in _LOCI:
        raise ValueError("locus is unsupported")
    code = payload["codeValue"]
    if not isinstance(code, str) or _SIGNED.fullmatch(code) is None or code == "-0":
        raise ValueError("codeValue must be a canonical signed decimal")
    white = payload["sourceWhite"]
    if not isinstance(white, str) or _DECIMAL.fullmatch(white) is None or Decimal(white) <= 0:
        raise ValueError("sourceWhite must be a positive canonical decimal")
    limit = payload["storageLimit"]
    if limit != "none" and (not isinstance(limit, str) or _SIGNED.fullmatch(limit) is None or limit == "-0"):
        raise ValueError("storageLimit must be none or a canonical signed decimal")
    clamp = payload["implicitClamp"]
    if type(clamp) is not bool:
        raise ValueError("implicitClamp must be a bool")
    return sample, locus, code, white, limit, clamp


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P054-01 must not yield qualified or allowed")
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
