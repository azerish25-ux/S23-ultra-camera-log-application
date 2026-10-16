"""TC-P121-01 Ambiguous imported signal.

Host fixture. Detected color, rotation, and timing stay separate from user
interpretation. A filename extension must not choose transfer or range, and an
untagged clip is not silently flattened onto an SDR path.
"""

from __future__ import annotations


CASE_ID = "TC-P121-01"
NAME = "Ambiguous imported signal"
INTERVENTION = "Import media with absent or contradictory color tags, rotation, or timing metadata."
EXPECTED = "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type."
NEGATIVE = "Filename extension alone must not determine transfer or dynamic range."
REPEAT = "Repeat HDR-looking untagged clips, variable rates, and portrait rotation."
NEGATIVE_TOKEN = "filename-extension-determines-transfer-or-range"
SILENT_TOKEN = "silent-normalization-to-assumed-source"
CONTRADICTION_TOKEN = "contradictory-color-tags-resolved-silently"
ROTATION_TOKEN = "rotated-media-without-declared-policy"
VFR_TOKEN = "variable-rate-without-declared-policy"
REPEATS = ("hdr-untagged", "variable-rate", "portrait-rotation")
TIMINGS = ("constant", "vfr")
ROTATIONS = (0, 90, 180, 270)
ASSUMED_SDR = ("bt709", "sdr", "iec61966-2-1")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "detectedTransfer",
    "containerTransfer",
    "detectedRange",
    "detectedRotation",
    "detectedTiming",
    "userTransfer",
    "userRange",
    "userRotationPolicy",
    "userTimingPolicy",
    "emittedTransfer",
    "emittedRange",
    "emittedRotation",
    "emittedTiming",
    "extensionDecidesColor",
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
    """Keep detected facts. Do not let a filename or a silent emit choose the source."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", NEGATIVE]
    contradictory = (
        fields["detectedTransfer"] is not None
        and fields["containerTransfer"] is not None
        and fields["detectedTransfer"] != fields["containerTransfer"]
    )
    if fields["extensionDecidesColor"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append("filename extension was not used as the color decision")
    if contradictory and fields["emittedTransfer"] is not None:
        rejected.append(CONTRADICTION_TOKEN)
        reasons.append("contradictory color tags were not collapsed into one emitted transfer")
    if not contradictory and fields["emittedTransfer"] not in (None, fields["detectedTransfer"]):
        rejected.append(SILENT_TOKEN)
        reasons.append("emitted transfer is not the detected fact")
    if fields["detectedTransfer"] is None and fields["emittedTransfer"] in ASSUMED_SDR:
        if SILENT_TOKEN not in rejected:
            rejected.append(SILENT_TOKEN)
        reasons.append("untagged media was not flattened onto an assumed SDR path")
    if fields["emittedRange"] not in (None, fields["detectedRange"]):
        rejected.append(SILENT_TOKEN)
        reasons.append("emitted range is not the detected fact")
    if fields["emittedTiming"] not in (None, fields["detectedTiming"]):
        rejected.append(SILENT_TOKEN)
        reasons.append("emitted timing is not the detected fact")
    if fields["emittedRotation"] not in (None, fields["detectedRotation"]):
        rejected.append(SILENT_TOKEN)
        reasons.append("emitted rotation is not the detected fact")
    if fields["detectedRotation"] != 0 and not fields["userRotationPolicy"]:
        rejected.append(ROTATION_TOKEN)
        reasons.append("portrait rotation requires a declared policy")
    if fields["detectedTiming"] == "vfr" and not fields["userTimingPolicy"]:
        rejected.append(VFR_TOKEN)
        reasons.append("variable rate requires a declared policy")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("detected facts stayed separate from user interpretation")
    preserved = [
        fields["evidenceId"],
        {
            "facts": {
                "filename": fields["filename"],
                "transfer": fields["detectedTransfer"],
                "containerTransfer": fields["containerTransfer"],
                "range": fields["detectedRange"],
                "rotation": fields["detectedRotation"],
                "timing": fields["detectedTiming"],
            },
            "interpretation": {
                "transfer": fields["userTransfer"],
                "range": fields["userRange"],
                "rotationPolicy": fields["userRotationPolicy"],
                "timingPolicy": fields["userTimingPolicy"],
            },
            "emitted": {
                "transfer": fields["emittedTransfer"],
                "range": fields["emittedRange"],
                "rotation": fields["emittedRotation"],
                "timing": fields["emittedTiming"],
            },
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return _text(value, label)


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    filename = _text(payload["filename"], "filename")
    rotation = payload["detectedRotation"]
    if type(rotation) is not int or rotation not in ROTATIONS:
        raise ValueError("detectedRotation must be 0, 90, 180, or 270")
    timing = payload["detectedTiming"]
    if timing not in TIMINGS:
        raise ValueError("detectedTiming is unsupported")
    emitted_rotation = payload["emittedRotation"]
    if emitted_rotation is not None and (type(emitted_rotation) is not int or emitted_rotation not in ROTATIONS):
        raise ValueError("emittedRotation must be null or 0, 90, 180, or 270")
    extension = payload["extensionDecidesColor"]
    if type(extension) is not bool:
        raise ValueError("extensionDecidesColor must be a bool")
    return {
        "evidenceId": evidence,
        "repeat": repeat,
        "filename": filename,
        "detectedTransfer": _optional_text(payload["detectedTransfer"], "detectedTransfer"),
        "containerTransfer": _optional_text(payload["containerTransfer"], "containerTransfer"),
        "detectedRange": _optional_text(payload["detectedRange"], "detectedRange"),
        "detectedRotation": rotation,
        "detectedTiming": timing,
        "userTransfer": _optional_text(payload["userTransfer"], "userTransfer"),
        "userRange": _optional_text(payload["userRange"], "userRange"),
        "userRotationPolicy": _optional_text(payload["userRotationPolicy"], "userRotationPolicy"),
        "userTimingPolicy": _optional_text(payload["userTimingPolicy"], "userTimingPolicy"),
        "emittedTransfer": _optional_text(payload["emittedTransfer"], "emittedTransfer"),
        "emittedRange": _optional_text(payload["emittedRange"], "emittedRange"),
        "emittedRotation": emitted_rotation,
        "emittedTiming": _optional_text(payload["emittedTiming"], "emittedTiming"),
        "extensionDecidesColor": extension,
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
