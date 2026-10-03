"""TC-P033-03 oversized source record.

An impossible payload length or dimension is rejected before allocation and
before any read past the bytes on hand. The original file id stays in the
result. Allocating from an unvalidated length field is the negative control.
"""

from __future__ import annotations

CASE_ID = "TC-P033-03"
INTERVENTION = "Inject an impossible payload length or dimension into an otherwise valid source header."
EXPECTED = "Reject before unbounded allocation or out-of-bounds reading, preserving the original file."
NEGATIVE = "Allocating directly from an unvalidated length field must fail."
REPEATS = (
    "declared maximum",
    "maximum plus one",
    "integer overflow boundaries",
    "truncated headers",
)
_CLASSES = (
    "in-bounds",
    "maximum",
    "maximum-plus-one",
    "overflow",
    "truncated-header",
    "impossible-dimension",
)
_OVERFLOW_FLOOR = 2**31
_PAYLOAD_KEYS = (
    "lengthClass",
    "declaredLength",
    "maxLength",
    "declaredWidth",
    "declaredHeight",
    "maxDimension",
    "bytesPresent",
    "headerTruncated",
    "allocateUnvalidated",
    "originalId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject impossible lengths before reserving them."""
    data = _payload(payload)
    problems = _problems(data)
    rejected = list(problems)
    reasons = [
        "length class " + data["lengthClass"],
        "declared length " + str(data["declaredLength"]),
    ]
    if data["allocateUnvalidated"]:
        rejected.insert(0, "unvalidated-length-allocation")
        reasons.append(NEGATIVE)
    if rejected:
        decision = "rejected"
        reserved = 0
        reasons.append(EXPECTED)
        reasons.append("reserved 0 bytes; the declared length was not allocated")
    else:
        decision = "bounded"
        reserved = data["declaredLength"]
        reasons.append("declared length is inside the host bound and was reserved only after the check")
        reasons.append("bounded is not physical qualification")
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-03 must not yield qualified or allowed")
    if data["allocateUnvalidated"] and reserved != 0:
        raise ValueError("unvalidated length must not be allocated")
    questions = ["original file bytes were not rewritten"]
    return _result(decision, reasons, rejected, _preserved(data, reserved), questions)


def _problems(data: dict) -> list[str]:
    kind = data["lengthClass"]
    problems: list[str] = []
    if kind == "truncated-header":
        problems.append("truncated-header")
    if kind == "overflow":
        problems.append("integer-overflow")
    if kind == "maximum-plus-one":
        problems.append("impossible-length")
    if kind == "impossible-dimension":
        problems.append("impossible-dimension")
    return problems


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    kind = payload["lengthClass"]
    if kind not in _CLASSES:
        raise ValueError("lengthClass is not in the host vocabulary")
    declared = _uint(payload["declaredLength"], "declaredLength")
    maximum = _positive(payload["maxLength"], "maxLength")
    width = _positive(payload["declaredWidth"], "declaredWidth")
    height = _positive(payload["declaredHeight"], "declaredHeight")
    max_dimension = _positive(payload["maxDimension"], "maxDimension")
    present = _uint(payload["bytesPresent"], "bytesPresent")
    truncated = _bool(payload["headerTruncated"], "headerTruncated")
    if kind == "truncated-header":
        if not truncated:
            raise ValueError("truncated-header requires headerTruncated")
    elif truncated:
        raise ValueError("headerTruncated is only valid for truncated-header")
    if kind == "maximum" and declared != maximum:
        raise ValueError("maximum class requires declaredLength == maxLength")
    if kind == "maximum-plus-one" and declared != maximum + 1:
        raise ValueError("maximum-plus-one requires declaredLength == maxLength + 1")
    if kind == "overflow" and declared < _OVERFLOW_FLOOR:
        raise ValueError("overflow class requires a length at the 2**31 boundary or beyond")
    if kind == "impossible-dimension" and width <= max_dimension and height <= max_dimension:
        raise ValueError("impossible-dimension requires a dimension past maxDimension")
    if kind in {"in-bounds", "maximum"}:
        if declared == 0 or declared > maximum or declared > present:
            raise ValueError("bounded classes require a covered in-range length")
        if width > max_dimension or height > max_dimension:
            raise ValueError("bounded classes require dimensions inside maxDimension")
    if kind == "maximum-plus-one" and (width > max_dimension or height > max_dimension):
        raise ValueError("maximum-plus-one keeps dimensions inside the declared maximum")
    original = payload["originalId"]
    if not isinstance(original, str) or not original or original != original.strip():
        raise ValueError("originalId must be a non-empty string")
    return {
        "lengthClass": kind,
        "declaredLength": declared,
        "maxLength": maximum,
        "declaredWidth": width,
        "declaredHeight": height,
        "maxDimension": max_dimension,
        "bytesPresent": present,
        "headerTruncated": truncated,
        "allocateUnvalidated": _bool(payload["allocateUnvalidated"], "allocateUnvalidated"),
        "originalId": original,
    }


def _preserved(data: dict, reserved: int) -> list[str]:
    return [
        "original:" + data["originalId"],
        "declared-length:" + str(data["declaredLength"]),
        "declared-dimension:" + str(data["declaredWidth"]) + "x" + str(data["declaredHeight"]),
        "max-length:" + str(data["maxLength"]),
        "bytes-present:" + str(data["bytesPresent"]),
        "reserved:" + str(reserved),
        "length-class:" + data["lengthClass"],
    ]


def _uint(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative int")
    return value


def _positive(value: object, name: str) -> int:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be a positive int")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a bool")
    return value


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P033-03 must not yield qualified or allowed")
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
