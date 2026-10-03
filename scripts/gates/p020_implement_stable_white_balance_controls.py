#!/usr/bin/env python3
"""P020 white-balance intent: hardware capture, RAW neutral, and preview look.

Hardware presets, locks, gains, and transforms stay in the capture namespace.
The RAW neutral point stays source metadata and changes only with a new
profile version. A creative temperature or tint slider changes the preview
recipe, not measured sensor white-balance evidence. Unsupported Kelvin stays
unavailable. A supported Kelvin value is provisional unless independently
calibrated.

The mutant writes the creative temperature slider into measured sensor
white-balance evidence. This gate rejects that claim and leaves the measured
record on the hardware observation.

This module does not open a camera, does not qualify a physical Galaxy S23,
and does not execute TC-P020-01 through TC-P020-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


METHOD = (
    "Expose available presets and locks, record gains and transforms where "
    "accessible, and label Kelvin values provisional unless independently "
    "calibrated. A creative tint slider changes the render recipe, not capture "
    "metadata. Avoid changing the RAW neutral interpretation without versioning "
    "the profile."
)
FIXTURE = (
    "A stable RAW neutral point with a creative warm preview and an unsupported "
    "hardware Kelvin request."
)
ORACLE = (
    "The source metadata stays unchanged, the preview recipe records its "
    "adjustment, and unsupported Kelvin remains unavailable."
)
MUTANT = (
    "Write a creative temperature slider value into measured sensor "
    "white-balance evidence."
)

BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MODEL_ID = "s23-white-balance-intent-fixture"
CASE_ID = "P020"
HARDWARE_NAMESPACE = "hardware.white_balance"
RAW_NAMESPACE = "raw.neutral"
PREVIEW_NAMESPACE = "preview.recipe"
KELVIN_UNAVAILABLE = "unavailable"
UNAVAILABLE_QUESTION = "unsupported hardware Kelvin remains unavailable"
PROVISIONAL_QUESTION = "Kelvin values are provisional unless independently calibrated"
GAINS_QUESTION = "gains and transforms were not accessible"
MUTANT_CLAIM = "creative-temperature-as-measured-wb"
METADATA_CLAIM = "creative-tint-wrote-capture-metadata"
UNVERSIONED_CLAIM = "unversioned-raw-neutral"
UNRECORDED_CLAIM = "preview-adjustment-unrecorded"
PRESETS = ("auto", "daylight", "cloudy", "fluorescent")
GAIN_KEYS = ("red", "greenRed", "greenBlue", "blue")

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL_TEXT = re.compile(r"^(?:0|[1-9]\d*)(?:\.\d+)?$")
KELVIN_TEXT = re.compile(r"^[1-9]\d{2,4}$")
TOKEN_TEXT = re.compile(r"^[A-Za-z0-9_.+-]+$")

MODEL_KEYS = {
    "schemaVersion",
    "phase",
    "modelId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "hardware",
    "preview",
    "rawNeutral",
}
HARDWARE_KEYS = {
    "namespace",
    "presets",
    "lockAvailable",
    "locked",
    "selectedPreset",
    "kelvinSupported",
    "independentlyCalibrated",
    "kelvinRequest",
    "transformAccessible",
    "gains",
    "colorTransform",
}
PREVIEW_KEYS = {
    "namespace",
    "creativeTemperature",
    "creativeKelvinSlider",
    "tintSlider",
    "recordsAdjustment",
    "writesCaptureMetadata",
}
RAW_KEYS = {
    "namespace",
    "red",
    "green",
    "blue",
    "profileVersion",
    "priorProfile",
    "sourceMetadataUnchanged",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"rejected", "separated", "withheld", "versioned"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _bool(value: object, name: str) -> bool:
    require(type(value) is bool, name + " must be a bool")
    return value


def _token(value: object, name: str) -> str:
    require(isinstance(value, str) and TOKEN_TEXT.fullmatch(value) is not None, name + " must be a token")
    return value


def _decimal(value: object, name: str) -> str:
    require(
        isinstance(value, str) and DECIMAL_TEXT.fullmatch(value) is not None,
        name + " must be a canonical positive decimal string",
    )
    require(Decimal(value) > 0, name + " must be positive")
    return value


def _kelvin(value: object, name: str) -> str:
    require(
        isinstance(value, str) and KELVIN_TEXT.fullmatch(value) is not None,
        name + " must be a Kelvin integer string",
    )
    return value


def _presets(value: object) -> list[str]:
    require(isinstance(value, list) and value, "hardware presets must be a non-empty list")
    presets = [_token(item, "hardware preset") for item in value]
    require(len(presets) == len(set(presets)), "hardware presets must be unique")
    require(set(presets) <= set(PRESETS), "hardware preset is not exposed")
    return presets


def _gains(value: object) -> dict[str, str] | None:
    if value is None:
        return None
    exact_keys(value, set(GAIN_KEYS), "hardware gains")
    return {key: _decimal(value[key], "hardware gains " + key) for key in GAIN_KEYS}


def validate_model(document: dict) -> None:
    """Raise ValueError unless document is a P020 white-balance intent model."""
    exact_keys(document, MODEL_KEYS, "white-balance model")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == "P020", "phase must be P020")
    require(document["modelId"] == MODEL_ID, "modelId must be s23-white-balance-intent-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "white-balance model needs the P020 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")

    hardware = exact_keys(document["hardware"], HARDWARE_KEYS, "hardware")
    require(hardware["namespace"] == HARDWARE_NAMESPACE, "hardware namespace must stay hardware.white_balance")
    presets = _presets(hardware["presets"])
    lock_available = _bool(hardware["lockAvailable"], "hardware lockAvailable")
    locked = _bool(hardware["locked"], "hardware locked")
    require(not locked or lock_available, "a lock that is not available cannot be engaged")
    selected = _token(hardware["selectedPreset"], "hardware selectedPreset")
    require(selected in presets, "selected preset must be one of the exposed presets")
    supported = _bool(hardware["kelvinSupported"], "hardware kelvinSupported")
    calibrated = _bool(hardware["independentlyCalibrated"], "hardware independentlyCalibrated")
    require(not calibrated or supported, "Kelvin cannot be independently calibrated when hardware Kelvin is unsupported")
    _kelvin(hardware["kelvinRequest"], "hardware kelvinRequest")
    accessible = _bool(hardware["transformAccessible"], "hardware transformAccessible")
    gains = _gains(hardware["gains"])
    transform = hardware["colorTransform"]
    if accessible:
        require(gains is not None, "accessible gains must be recorded")
        _token(transform, "hardware colorTransform")
    else:
        require(gains is None, "inaccessible gains must stay null rather than be invented")
        require(transform is None, "inaccessible color transform must stay null")

    preview = exact_keys(document["preview"], PREVIEW_KEYS, "preview")
    require(preview["namespace"] == PREVIEW_NAMESPACE, "preview namespace must stay preview.recipe")
    require(preview["namespace"] != hardware["namespace"], "preview must not collapse into hardware white balance")
    _token(preview["creativeTemperature"], "preview creativeTemperature")
    _kelvin(preview["creativeKelvinSlider"], "preview creativeKelvinSlider")
    _token(preview["tintSlider"], "preview tintSlider")
    _bool(preview["recordsAdjustment"], "preview recordsAdjustment")
    _bool(preview["writesCaptureMetadata"], "preview writesCaptureMetadata")

    raw = exact_keys(document["rawNeutral"], RAW_KEYS, "rawNeutral")
    require(raw["namespace"] == RAW_NAMESPACE, "raw neutral namespace must stay raw.neutral")
    require(raw["namespace"] not in {hardware["namespace"], preview["namespace"]},
            "raw neutral must stay apart from hardware and preview")
    _decimal(raw["red"], "rawNeutral red")
    _decimal(raw["green"], "rawNeutral green")
    _decimal(raw["blue"], "rawNeutral blue")
    profile = _token(raw["profileVersion"], "rawNeutral profileVersion")
    prior = _token(raw["priorProfile"], "rawNeutral priorProfile")
    unchanged = _bool(raw["sourceMetadataUnchanged"], "rawNeutral sourceMetadataUnchanged")
    if unchanged and profile != prior:
        raise ValueError("unchanged source metadata cannot claim a new RAW neutral profile version")


def _kelvin_label(hardware: dict) -> str:
    if hardware["kelvinSupported"] is not True:
        return KELVIN_UNAVAILABLE
    prefix = "calibrated" if hardware["independentlyCalibrated"] is True else "provisional"
    return prefix + ":" + hardware["kelvinRequest"]


def _gain_text(hardware: dict) -> str:
    gains = hardware["gains"]
    if gains is None:
        return "unavailable"
    return ",".join(gains[key] for key in GAIN_KEYS)


def _point(raw: dict) -> str:
    return raw["red"] + "," + raw["green"] + "," + raw["blue"]


def project_balance(document: dict) -> dict[str, Any]:
    """Project hardware, RAW neutral, and preview without copying the look.

    Measured sensor white balance comes from the hardware preset and, when
    accessible, the recorded gains. Unsupported Kelvin stays unavailable.
    The creative slider is recorded only on the preview recipe.
    """
    validate_model(document)
    hardware = document["hardware"]
    preview = document["preview"]
    raw = document["rawNeutral"]
    label = _kelvin_label(hardware)
    gain_text = _gain_text(hardware)
    measured = {
        "source": "hardware",
        "preset": hardware["selectedPreset"],
        "kelvin": label,
        "gains": gain_text,
    }
    require("creativeKelvinSlider" not in measured, "creative slider leaked into measured evidence")
    require(measured["preset"] != preview["creativeTemperature"], "creative temperature leaked into the preset")
    require(preview["creativeTemperature"] not in measured["kelvin"], "creative temperature leaked into measured Kelvin")
    if label == KELVIN_UNAVAILABLE:
        require(preview["creativeKelvinSlider"] not in measured["kelvin"],
                "creative Kelvin leaked into measured evidence")
    else:
        require(measured["kelvin"].endswith(":" + hardware["kelvinRequest"]),
                "measured Kelvin must come from the hardware request label")
    gains_out: Any
    if hardware["gains"] is None:
        gains_out = None
    else:
        gains_out = {key: hardware["gains"][key] for key in GAIN_KEYS}
    return {
        "hardware": {
            "namespace": hardware["namespace"],
            "preset": hardware["selectedPreset"],
            "presets": list(hardware["presets"]),
            "locked": hardware["locked"] is True,
            "kelvin": label,
            "gains": gains_out,
            "transform": hardware["colorTransform"] if hardware["transformAccessible"] else "unavailable",
        },
        "rawNeutral": {
            "namespace": raw["namespace"],
            "point": _point(raw),
            "profileVersion": raw["profileVersion"],
            "priorProfile": raw["priorProfile"],
            "sourceMetadataUnchanged": raw["sourceMetadataUnchanged"] is True,
        },
        "previewRecipe": {
            "namespace": preview["namespace"],
            "creativeTemperature": preview["creativeTemperature"],
            "creativeKelvinSlider": preview["creativeKelvinSlider"],
            "tintSlider": preview["tintSlider"],
            "recordsAdjustment": preview["recordsAdjustment"] is True,
            "writesCaptureMetadata": preview["writesCaptureMetadata"] is True,
        },
        "measuredSensorWhiteBalance": measured,
    }


def _preserved(document: dict, projected: dict[str, Any]) -> list[str]:
    hardware = document["hardware"]
    raw = document["rawNeutral"]
    preview = document["preview"]
    label = projected["measuredSensorWhiteBalance"]["kelvin"]
    gain_text = _gain_text(hardware)
    items = [
        "hardware.namespace:" + hardware["namespace"],
        "hardware.preset:" + hardware["selectedPreset"],
        "hardware.kelvin:" + label,
        "hardware.gains:" + gain_text,
        "hardware.transform:" + (
            hardware["colorTransform"] if hardware["transformAccessible"] else "unavailable"
        ),
        "raw.namespace:" + raw["namespace"],
        "raw.point:" + _point(raw),
        "raw.profile:" + raw["profileVersion"],
        "raw.priorProfile:" + raw["priorProfile"],
        "raw.sourceMetadata:" + ("unchanged" if raw["sourceMetadataUnchanged"] else "changed"),
        "preview.namespace:" + preview["namespace"],
        "preview.temperature:" + preview["creativeTemperature"],
        "preview.creativeKelvinSlider:" + preview["creativeKelvinSlider"],
        "preview.tint:" + preview["tintSlider"],
        "measured.preset:" + hardware["selectedPreset"],
        "measured.kelvin:" + label,
        "measured.gains:" + gain_text,
        "measured.source:hardware",
    ]
    return items


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in DECISIONS, "decision must be rejected, separated, withheld, or versioned")
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons), "reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_balance(document: dict, mutant: bool = False) -> dict[str, Any]:
    """Assess white-balance intent. The mutant does not rewrite sensor evidence.

    mutant true is the deliberate failure: copy the creative temperature slider
    into measured sensor white-balance evidence. That claim is rejected.
    preservedResults keep the hardware observation, the RAW neutral point, and
    the preview recipe as separate facts.
    """
    require(type(mutant) is bool, "mutant must be a bool")
    projected = project_balance(document)
    hardware = document["hardware"]
    preview = document["preview"]
    raw = document["rawNeutral"]
    measured = projected["measuredSensorWhiteBalance"]
    require(measured["source"] == "hardware", "measured evidence must stay hardware")
    require(measured["preset"] == hardware["selectedPreset"], "measured preset must stay the hardware preset")
    require(measured["kelvin"] == _kelvin_label(hardware), "measured Kelvin must stay the hardware label")
    require(preview["creativeTemperature"] not in measured["kelvin"], "mutant wrote the slider into measured Kelvin")
    if measured["kelvin"] == KELVIN_UNAVAILABLE:
        require(preview["creativeKelvinSlider"] not in measured["kelvin"],
                "mutant wrote creative Kelvin into sensor evidence")

    rejected: list[str] = []
    if mutant:
        rejected.append(MUTANT_CLAIM)
    if preview["writesCaptureMetadata"] is True:
        rejected.append(METADATA_CLAIM)
    if preview["recordsAdjustment"] is not True:
        rejected.append(UNRECORDED_CLAIM)
    changed = raw["sourceMetadataUnchanged"] is not True
    versioned_change = changed and raw["profileVersion"] != raw["priorProfile"]
    if changed and not versioned_change:
        rejected.append(UNVERSIONED_CLAIM)

    reasons: list[str] = []
    if mutant:
        reasons.append(MUTANT)
        reasons.append(
            "creative temperature slider was not written into measured sensor white-balance evidence"
        )
    if preview["writesCaptureMetadata"] is True:
        reasons.append("a creative tint slider changes the render recipe, not capture metadata")
    if preview["recordsAdjustment"] is not True:
        reasons.append("the preview recipe did not record its creative adjustment")
    else:
        reasons.append("preview recipe records its adjustment")
    if raw["sourceMetadataUnchanged"] is True:
        reasons.append("source metadata stays unchanged")
    elif versioned_change:
        reasons.append(
            "RAW neutral interpretation changed under profile " + raw["profileVersion"]
        )
    else:
        reasons.append("RAW neutral interpretation was not changed without versioning the profile")
    if hardware["kelvinSupported"] is not True:
        reasons.append("unsupported Kelvin remains unavailable")
    elif hardware["independentlyCalibrated"] is not True:
        reasons.append("observed Kelvin " + hardware["kelvinRequest"] + " is provisional")
    else:
        reasons.append(
            "observed Kelvin " + hardware["kelvinRequest"]
            + " is labeled calibrated in this host fixture only"
        )
    if hardware["gains"] is None:
        reasons.append(GAINS_QUESTION)

    questions: list[str] = []
    if hardware["kelvinSupported"] is not True:
        questions.append(UNAVAILABLE_QUESTION)
    if hardware["independentlyCalibrated"] is not True:
        questions.append(PROVISIONAL_QUESTION)
    if hardware["gains"] is None:
        questions.append(GAINS_QUESTION)
    if versioned_change:
        questions.append(raw["profileVersion"] + " records a versioned RAW neutral change")

    if rejected:
        decision = "rejected"
    elif versioned_change:
        decision = "versioned"
    elif hardware["kelvinSupported"] is True and hardware["independentlyCalibrated"] is not True:
        decision = "withheld"
    else:
        decision = "separated"
    preserved = _preserved(document, projected)
    require("measured.kelvin:" + measured["kelvin"] in preserved, "measured Kelvin must stay in the inventory")
    require(
        "preview.creativeKelvinSlider:" + preview["creativeKelvinSlider"] in preserved,
        "preview adjustment must stay in the inventory",
    )
    return _result(decision, reasons, rejected, preserved, questions)
