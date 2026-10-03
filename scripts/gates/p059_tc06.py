"""TC-P059-06 source-lineage laundering.

Intervention: Export an SDR or HLG-derived source under a RAW-derived or
native-camera-equivalent label.
Expected: Reject the label even when the final file is ten-bit and visually flat.
Negative: Changing the encoding cannot upgrade the source acquisition category.
"""

from __future__ import annotations


CASE_ID = "TC-P059-06"
INTERVENTION = (
    "Export an SDR or HLG-derived source under a RAW-derived or native-camera-equivalent label."
)
EXPECTED = "Reject the label even when the final file is ten-bit and visually flat."
NEGATIVE = "Changing the encoding cannot upgrade the source acquisition category."

_ACQUISITIONS = ("sdr", "hlg", "raw")
_LABELS = ("sdr", "hlg", "raw-derived", "native-camera-equivalent")
_STAGES = ("import", "recipe", "export-name", "shared-metadata")
_UPGRADES = ("raw-derived", "native-camera-equivalent")
_PAYLOAD_KEYS = (
    "acquisition",
    "exportLabel",
    "bitDepth",
    "visuallyFlat",
    "stage",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Reject an upgraded acquisition label. Encoding changes do not launder lineage."""
    acquisition, label, bit_depth, flat, stage = _payload(payload)
    preserved = [
        "acquisition:" + acquisition,
        "label:" + label,
        f"bit-depth:{bit_depth}",
        "flat:" + ("true" if flat else "false"),
        "stage:" + stage,
    ]
    upgraded = acquisition in {"sdr", "hlg"} and label in _UPGRADES
    reasons = [EXPECTED, INTERVENTION]
    if upgraded:
        reasons.append(NEGATIVE)
        reasons.append(
            f"{bit_depth}-bit {'flat' if flat else 'graded'} encoding did not upgrade {acquisition}"
        )
        return _result(
            "rejected",
            reasons,
            ["lineage-laundering"],
            preserved,
            ["source acquisition category was not upgraded"],
        )
    reasons.append("export label does not upgrade the recorded acquisition category")
    return _result(
        "withheld",
        reasons,
        [],
        preserved,
        ["matching lineage is not cinema-camera equivalence"],
    )


def _payload(payload: object) -> tuple[str, str, int, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquisition = payload["acquisition"]
    if acquisition not in _ACQUISITIONS:
        raise ValueError("acquisition is unsupported")
    label = payload["exportLabel"]
    if label not in _LABELS:
        raise ValueError("exportLabel is unsupported")
    bit_depth = payload["bitDepth"]
    if bit_depth not in (8, 10) or type(bit_depth) is not int:
        raise ValueError("bitDepth must be 8 or 10")
    flat = payload["visuallyFlat"]
    if type(flat) is not bool:
        raise ValueError("visuallyFlat must be a bool")
    stage = payload["stage"]
    if stage not in _STAGES:
        raise ValueError("stage is unsupported")
    return acquisition, label, bit_depth, flat, stage


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("TC-P059-06 must not yield qualified or allowed")
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
