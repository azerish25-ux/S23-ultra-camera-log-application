"""TC-P009-03 incompatible output combination.

Individually supported outputs do not prove they can run together. A physical
member that is not the logical camera id is addressed through that owner and
is not opened as an independent camera. Missing focal length stays unknown.
"""

from __future__ import annotations

CASE_ID = "TC-P009-03"
KINDS = ("preview", "raw", "encoder")
VARIANTS = ("mixed_preview", "raw_plus_encoder", "alternate_lens")
_OUTPUT_FIELDS = (
    "id",
    "routeLogicalId",
    "routePhysicalId",
    "kind",
    "supportedAlone",
)
_PAYLOAD_FIELDS = ("outputs", "constraintsViolated", "variant")
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_COEXISTENCE = "independent support is not coexistence"


def evaluate(payload: dict) -> dict:
    """Reject a combination that violates constraints or is not supported alone."""
    outputs, constraints_violated, _variant = _payload(payload)
    rejected: list[str] = []
    unsupported = [item["id"] for item in outputs if not item["supportedAlone"]]
    if constraints_violated:
        decision = "rejected"
        rejected.extend(item["id"] for item in outputs)
        reasons = [_COEXISTENCE]
    elif unsupported:
        decision = "rejected"
        rejected.extend(unsupported)
        reasons = [f"output {output_id} is not supported alone" for output_id in unsupported]
    else:
        decision = "compatible"
        reasons = ["output combination is compatible"]

    reasons.extend(_owner_reasons(outputs))
    if decision in {"allowed", "qualified"}:
        raise ValueError("TC-P009-03 must not decide allowed or qualified")
    if constraints_violated and (
        decision != "rejected"
        or _COEXISTENCE not in reasons
        or rejected != [item["id"] for item in outputs]
    ):
        raise ValueError("independent support must not be treated as coexistence")
    return _result(decision, reasons, rejected, _logical_ids(outputs))


def _payload(payload: object) -> tuple[list[dict], bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_FIELDS):
        raise ValueError("payload keys must be outputs, constraintsViolated, and variant")
    variant = payload["variant"]
    if variant not in VARIANTS:
        raise ValueError("variant must be mixed_preview, raw_plus_encoder, or alternate_lens")
    constraints_violated = _flag(payload["constraintsViolated"], "constraintsViolated")
    outputs = payload["outputs"]
    if not isinstance(outputs, list):
        raise ValueError("outputs must be a list")
    if not outputs:
        raise ValueError("outputs must be non-empty")
    parsed = [_output(item) for item in outputs]
    seen: set[str] = set()
    for item in parsed:
        if item["id"] in seen:
            raise ValueError("duplicate output id")
        seen.add(item["id"])
    return parsed, constraints_violated, variant


def _output(output: object) -> dict:
    if not isinstance(output, dict):
        raise ValueError("output must be a dict")
    if set(output) != set(_OUTPUT_FIELDS):
        raise ValueError("invalid output fields")
    output_id = _text(output["id"], "id")
    logical = _text(output["routeLogicalId"], "routeLogicalId")
    physical = _optional_text(output["routePhysicalId"], "routePhysicalId")
    kind = output["kind"]
    if kind not in KINDS:
        raise ValueError("kind must be preview, raw, or encoder")
    supported = _flag(output["supportedAlone"], "supportedAlone")
    return {
        "id": output_id,
        "routeLogicalId": logical,
        "routePhysicalId": physical,
        "kind": kind,
        "supportedAlone": supported,
    }


def _owner_reasons(outputs: list[dict]) -> list[str]:
    reasons: list[str] = []
    seen: set[tuple[str, str]] = set()
    for output in outputs:
        physical = output["routePhysicalId"]
        logical = output["routeLogicalId"]
        if physical is None or physical == logical:
            continue
        key = (physical, logical)
        if key in seen:
            continue
        seen.add(key)
        reasons.append(f"{physical} addressed via {logical}")
    return reasons


def _logical_ids(outputs: list[dict]) -> list[str]:
    preserved: list[str] = []
    seen: set[str] = set()
    for output in outputs:
        logical = output["routeLogicalId"]
        if logical in seen:
            continue
        seen.add(logical)
        preserved.append(logical)
    return preserved


def _flag(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
) -> dict:
    if decision != "allowed" and not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["focal unknown"],
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
