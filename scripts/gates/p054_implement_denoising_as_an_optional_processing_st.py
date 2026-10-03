#!/usr/bin/env python3
"""P054 optional denoise stage on a host fixture.

A conservative spatial reference is scored first. Temporal candidates are
accepted only with motion confidence, and occlusion drops invalid history.
Sensor-noise characterization stays distinct from artistic grain. Processing
strength and the algorithm version are exported. The stage can be disabled,
and residuals stay inspectable. Clean source storage is not rewritten.

The deliberate mutant — frame averaging without motion or occlusion handling —
is rejected even when it reports a lower noise figure. Smearing texture or
leaving motion trails beyond the declared quality gate cannot pass. This
module does not probe a device, does not qualify a physical S23, and does not
execute TC-P054-01 through TC-P054-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P054"
CASE_ID = "P054"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-optional-denoise-fixture"
METHOD = (
    "Start with a conservative spatial reference, then evaluate temporal candidates "
    "with motion confidence. Keep noise characterization distinct from artistic grain. "
    "Export the processing strength and algorithm version; allow disabling the stage "
    "and inspecting residuals."
)
FIXTURE = (
    "Low-light hair, moving fabric, a static wall, and a slowly moving colored point light."
)
ORACLE = (
    "Noise reduction cannot pass by smearing all texture or leaving motion trails "
    "beyond the declared quality gate."
)
MUTANT = "Use frame averaging without motion or occlusion handling."
HONEST = "spatial-then-temporal"
MUTANT_METHOD = "frame-average-without-motion"
PROCESSING = {HONEST, MUTANT_METHOD}
MUTANT_ACCEPT = "frame_averaged"
SPATIAL = "conservative-box-3"
NOISE_CHAR = "sensor-read-noise"
GRAIN = "not-applied"
STRENGTH_CAP = Decimal("0.35")
CONFIDENCE_FLOOR = Decimal("0.5")
SCENE_IDS = ("low-light-hair", "moving-fabric", "static-wall", "point-light")
HOST_LIMIT = (
    "host fixture does not qualify a physical S23, a measured denoise, "
    "or cinema-camera equivalence"
)

HEX40 = re.compile(r"^[0-9a-f]{40}$")
DECIMAL = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]{0,63}")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "algorithmVersion",
    "strength",
    "stageEnabled",
    "residualInspectable",
    "cleanSourceUntouched",
    "noiseCharacterization",
    "artisticGrain",
    "spatialReference",
    "qualityGate",
    "scenes",
}
QUALITY_KEYS = {"maxMotionTrail", "minTextureRetention"}
SCENE_KEYS = {
    "id",
    "textureRetention",
    "motionTrail",
    "motionConfidence",
    "occlusion",
    "noiseBefore",
    "noiseAfter",
    "residual",
    "frameAverageTexture",
    "frameAverageTrail",
    "frameAverageNoise",
}
_FORBIDDEN = {"qualified", "allowed", MUTANT_ACCEPT}
_DECIMAL_FIELDS = (
    "textureRetention",
    "motionTrail",
    "motionConfidence",
    "noiseBefore",
    "noiseAfter",
    "residual",
    "frameAverageTexture",
    "frameAverageTrail",
    "frameAverageNoise",
)


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


def canonical(value: Decimal) -> str:
    """Render a Decimal without exponent notation or trailing zeros."""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
        label + " must be a canonical decimal string",
    )
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in _FORBIDDEN, "P054 must not decide qualified, allowed, or frame_averaged")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
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


def _scene(value: object, index: int) -> dict:
    item = exact_keys(value, SCENE_KEYS, f"scene {index}")
    require(item["id"] == SCENE_IDS[index], f"scene {index} id must be {SCENE_IDS[index]}")
    for field in _DECIMAL_FIELDS:
        _decimal(item[field], f"scene {index} {field}")
    confidence = Decimal(item["motionConfidence"])
    require(Decimal(0) <= confidence <= Decimal(1), f"scene {index} motion confidence must be in 0..1")
    _bool(item["occlusion"], f"scene {index} occlusion")
    return item


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P054 optional-denoise fixture."""
    exact_keys(document, DOCUMENT_KEYS, "denoise")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P054")
    require(document["mapId"] == MAP_ID, "mapId must be s23-optional-denoise-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "denoise needs the P054 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _token(document["algorithmVersion"], "algorithmVersion")
    strength = _decimal(document["strength"], "strength")
    require(Decimal(strength) > 0, "strength must be positive")
    _bool(document["stageEnabled"], "stageEnabled")
    _bool(document["residualInspectable"], "residualInspectable")
    _bool(document["cleanSourceUntouched"], "cleanSourceUntouched")
    _token(document["noiseCharacterization"], "noiseCharacterization")
    _token(document["artisticGrain"], "artisticGrain")
    _token(document["spatialReference"], "spatialReference")
    gate = exact_keys(document["qualityGate"], QUALITY_KEYS, "qualityGate")
    trail = _decimal(gate["maxMotionTrail"], "maxMotionTrail")
    texture = _decimal(gate["minTextureRetention"], "minTextureRetention")
    require(Decimal(trail) > 0, "maxMotionTrail must be positive")
    require(Decimal(texture) > 0, "minTextureRetention must be positive")
    scenes = document["scenes"]
    require(type(scenes) is list and len(scenes) == len(SCENE_IDS), "scenes must be the four fixture scenes")
    for index, item in enumerate(scenes):
        _scene(item, index)


def _metrics(scene: dict, processing: str) -> tuple[str, str, str]:
    if processing == MUTANT_METHOD:
        return scene["frameAverageTexture"], scene["frameAverageTrail"], scene["frameAverageNoise"]
    return scene["textureRetention"], scene["motionTrail"], scene["noiseAfter"]


def _gate_claims(scene: dict, texture: str, trail: str, gate: dict) -> list[str]:
    claims: list[str] = []
    if Decimal(texture) < Decimal(gate["minTextureRetention"]):
        claims.append(f"texture-smear:{scene['id']}")
    if Decimal(trail) > Decimal(gate["maxMotionTrail"]):
        claims.append(f"motion-trail:{scene['id']}")
    return claims


def _residual_claims(scene: dict) -> list[str]:
    claims: list[str] = []
    before = Decimal(scene["noiseBefore"])
    after = Decimal(scene["noiseAfter"])
    residual = Decimal(scene["residual"])
    if after > before:
        claims.append(f"noise-increased:{scene['id']}")
    if residual != before - after:
        claims.append(f"residual-mismatch:{scene['id']}")
    return claims


def frame_average_is_quieter(document: dict) -> bool:
    """True when every frame-average noise figure is below the spatial residual noise.

    A quieter average is not a pass. ``assess`` must not turn this predicate
    into ``frame_averaged``, ``optional-stage``, ``qualified``, or ``allowed``.
    """
    validate_document(document)
    return all(
        Decimal(scene["frameAverageNoise"]) < Decimal(scene["noiseAfter"])
        for scene in document["scenes"]
    )


def _preserved(document: dict) -> list[str]:
    preserved: list[str] = []
    for scene in document["scenes"]:
        occlusion = "yes" if scene["occlusion"] else "no"
        preserved.append(
            "scene:{id}:texture={textureRetention}:trail={motionTrail}:"
            "noise-before={noiseBefore}:noise-after={noiseAfter}:residual={residual}:"
            "confidence={motionConfidence}:occlusion={occ}".format(occ=occlusion, **scene)
        )
        preserved.append(
            "frame-average:{id}:texture={frameAverageTexture}:trail={frameAverageTrail}:"
            "noise={frameAverageNoise}".format(**scene)
        )
    preserved.append("strength:" + document["strength"])
    preserved.append("algorithm:" + document["algorithmVersion"])
    preserved.append("spatial:" + document["spatialReference"])
    preserved.append("noise-char:" + document["noiseCharacterization"])
    preserved.append("grain:" + document["artisticGrain"])
    preserved.append("stage:" + ("on" if document["stageEnabled"] else "off"))
    preserved.append("residuals:" + ("inspectable" if document["residualInspectable"] else "hidden"))
    preserved.append(
        "clean-source:" + ("untouched" if document["cleanSourceUntouched"] else "contaminated")
    )
    gate = document["qualityGate"]
    preserved.append(
        "gate:trail<=" + gate["maxMotionTrail"] + ":texture>=" + gate["minTextureRetention"]
    )
    return preserved


def _document_claims(document: dict) -> list[str]:
    claims: list[str] = []
    if not document["cleanSourceUntouched"]:
        claims.append("clean-source-contaminated")
    if document["noiseCharacterization"] == document["artisticGrain"]:
        claims.append("noise-grain-conflated")
    if document["artisticGrain"] != GRAIN:
        claims.append("artistic-grain-applied")
    if document["noiseCharacterization"] != NOISE_CHAR:
        claims.append("noise-characterization-undeclared")
    if document["spatialReference"] != SPATIAL:
        claims.append("non-conservative-spatial")
    if Decimal(document["strength"]) > STRENGTH_CAP:
        claims.append("aggressive-strength")
    if not document["residualInspectable"]:
        claims.append("residuals-not-inspectable")
    return claims


def assess(document: dict, processing: str = HONEST) -> dict:
    """Score the optional denoise stage and reject frame averaging without motion.

    ``processing`` ``frame-average-without-motion`` is the mutant. It is
    rejected even when the average is quieter or numerically inside the gate.
    Scene inventory, strength, algorithm version, and residuals stay in
    preservedResults. The decision is never ``qualified``, ``allowed``, or
    ``frame_averaged``.
    """
    validate_document(document)
    require(processing in PROCESSING, "processing must be spatial-then-temporal or frame-average-without-motion")
    preserved = _preserved(document)
    gate = document["qualityGate"]
    questions = ["host fixture is not a physical S23 measurement"]
    reasons = [
        ORACLE,
        METHOD,
        f"algorithm {document['algorithmVersion']} strength {document['strength']}",
        f"spatial reference {document['spatialReference']}",
        (
            f"noise characterization {document['noiseCharacterization']} "
            f"is compared with artistic grain {document['artisticGrain']}"
        ),
    ]
    rejected: list[str] = []
    if processing == MUTANT_METHOD:
        rejected.append("frame-average-without-motion")
        rejected.append("motion-confidence-ignored")
        if any(scene["occlusion"] for scene in document["scenes"]):
            rejected.append("occlusion-ignored")
        reasons.append(MUTANT)
        questions.append("frame averaging without motion or occlusion handling was rejected")
    for scene in document["scenes"]:
        texture, trail, noise = _metrics(scene, processing)
        rejected.extend(_gate_claims(scene, texture, trail, gate))
        if (
            Decimal(texture) >= Decimal(gate["minTextureRetention"])
            and Decimal(trail) <= Decimal(gate["maxMotionTrail"])
        ):
            reasons.append(
                f"{scene['id']} texture {texture} trail {trail} noise {noise} is inside the quality gate"
            )
        else:
            reasons.append(
                f"{scene['id']} texture {texture} trail {trail} noise {noise} is outside the quality gate"
            )
        if Decimal(scene["motionConfidence"]) < CONFIDENCE_FLOOR:
            questions.append(
                f"temporal candidate {scene['id']} motion confidence {scene['motionConfidence']} "
                f"is below {canonical(CONFIDENCE_FLOOR)}"
            )
        if scene["occlusion"]:
            questions.append(f"occlusion on {scene['id']} limits temporal history")
    for scene in document["scenes"]:
        rejected.extend(_residual_claims(scene))
    rejected.extend(_document_claims(document))
    if not document["stageEnabled"]:
        questions.append("stage is disabled and was not applied to clean source")
    if rejected:
        decision = "rejected"
    elif not document["stageEnabled"]:
        decision = "disabled"
        reasons.append("the optional stage is disabled; clean source storage is unchanged")
    else:
        decision = "optional-stage"
        reasons.append("conservative spatial reference stayed inside the declared quality gate")
    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, questions)
