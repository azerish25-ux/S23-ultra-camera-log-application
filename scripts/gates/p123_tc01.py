"""TC-P123-01 Ambiguous imported signal.

Host fixture. Detected facts stay separate from user interpretation. A filename
extension does not become transfer or dynamic range, and missing or
contradictory metadata is not silently normalized to an assumed source type.
"""

from __future__ import annotations


CASE_ID = "TC-P123-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
REPEATS = ("hdr-untagged", "variable-rate", "portrait-rotation")
TIMING = ("absent", "constant", "variable", "contradictory")
PAYLOAD_KEYS = (
    "evidenceId",
    "filename",
    "extension",
    "colorTag",
    "rotationDegrees",
    "timingMetadata",
    "detectedTransfer",
    "detectedDynamicRange",
    "extensionImpliedTransfer",
    "extensionImpliedDynamicRange",
    "userInterpretation",
    "assumedSourceType",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject extension-derived transfer or range and silent source-type normalization."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    untagged = fields["colorTag"] is None
    if untagged and fields["detectedTransfer"] is not None and fields["detectedTransfer"] == fields["extensionImpliedTransfer"]:
        rejected.append("filename-extension-determines-transfer-or-dynamic-range")
        reasons.append(NEGATIVE)
    if (
        untagged
        and fields["detectedDynamicRange"] is not None
        and fields["detectedDynamicRange"] == fields["extensionImpliedDynamicRange"]
    ):
        if "filename-extension-determines-transfer-or-dynamic-range" not in rejected:
            rejected.append("filename-extension-determines-transfer-or-dynamic-range")
        reasons.append(NEGATIVE)
    ambiguous = untagged or fields["timingMetadata"] in {"absent", "contradictory"} or fields["rotationDegrees"] is None
    if ambiguous and fields["assumedSourceType"] is not None:
        rejected.append("silent-normalization-to-assumed-source-type")
        reasons.append("absent or contradictory metadata was normalized to an assumed source type")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("detected facts stayed separate from user interpretation")
    facts = {
        "colorTag": fields["colorTag"],
        "rotationDegrees": fields["rotationDegrees"],
        "timingMetadata": fields["timingMetadata"],
        "transfer": fields["detectedTransfer"],
        "dynamicRange": fields["detectedDynamicRange"],
    }
    preserved = [
        fields["evidenceId"],
        {"detectedFacts": facts, "userInterpretation": fields["userInterpretation"]},
        fields["assumedSourceType"],
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string or null")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    filename = payload["filename"]
    extension = payload["extension"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(filename, str) or not filename.strip() or filename != filename.strip():
        raise ValueError("filename must be a non-empty string")
    if not isinstance(extension, str) or not extension.strip() or extension != extension.strip() or "." in extension:
        raise ValueError("extension must be a non-empty string without a dot")
    if not filename.endswith("." + extension):
        raise ValueError("filename extension does not match extension")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    timing = payload["timingMetadata"]
    if timing not in TIMING:
        raise ValueError("unknown timing metadata")
    rotation = payload["rotationDegrees"]
    if rotation is not None and (type(rotation) is not int or isinstance(rotation, bool)):
        raise ValueError("rotationDegrees must be an integer or null")
    if type(rotation) is int and rotation not in {0, 90, 180, 270}:
        raise ValueError("rotationDegrees is not a quarter turn")
    interpretation = payload["userInterpretation"]
    if not isinstance(interpretation, str) or not interpretation.strip() or interpretation != interpretation.strip():
        raise ValueError("userInterpretation must be a non-empty string")
    if repeat == "hdr-untagged" and payload["colorTag"] is not None:
        raise ValueError("hdr-untagged repeat has a color tag")
    if repeat == "variable-rate" and timing != "variable":
        raise ValueError("variable-rate repeat requires variable timing")
    if repeat == "portrait-rotation" and rotation not in {90, 270}:
        raise ValueError("portrait-rotation repeat requires 90 or 270 degrees")
    return {
        "evidenceId": evidence,
        "filename": filename,
        "extension": extension,
        "colorTag": _optional_text(payload["colorTag"], "colorTag"),
        "rotationDegrees": rotation,
        "timingMetadata": timing,
        "detectedTransfer": _optional_text(payload["detectedTransfer"], "detectedTransfer"),
        "detectedDynamicRange": _optional_text(payload["detectedDynamicRange"], "detectedDynamicRange"),
        "extensionImpliedTransfer": _optional_text(payload["extensionImpliedTransfer"], "extensionImpliedTransfer"),
        "extensionImpliedDynamicRange": _optional_text(payload["extensionImpliedDynamicRange"], "extensionImpliedDynamicRange"),
        "userInterpretation": interpretation,
        "assumedSourceType": _optional_text(payload["assumedSourceType"], "assumedSourceType"),
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
