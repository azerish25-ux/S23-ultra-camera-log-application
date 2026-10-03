#!/usr/bin/env python3
"""P014 high-resolution experiment matrix and source-geometry evidence.

Candidate tuples keep 4K and 8K ambitions visible. Capture, encode, decode,
cadence, storage, and thermal experiments stay independent. Native geometry is
tracked separately from crop, binning, downsampling, and upscaling.

A file declared as 7680 by 4320 whose source was a smaller stream enlarged by
the renderer is labelled upscaled output. That label cannot satisfy the native
8K acceptance requirement. Container width and height alone never do.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P014-01 through TC-P014-08.
"""

from __future__ import annotations

import re
from typing import Any


BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MATRIX_ID = "s23-high-resolution-experiment-matrix"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
EXPERIMENTS = ("capture", "encode", "decode", "cadence", "storage", "thermal")
TRANSFORMS = ("native", "crop", "binning", "downsample", "upscale")
EXPERIMENT_STATUS = ("unmeasured", "measured", "failed")
METHOD = (
    "Construct candidate tuples for advertised sizes, including the user targets "
    "where exposed. Require independent capture, encode, decode, cadence, storage, "
    "and thermal experiments. Track native geometry separately from crop, binning, "
    "downsampling, and upscaling."
)
FIXTURE = (
    "A file declared as 7680 by 4320 whose source was a smaller stream enlarged "
    "by the renderer."
)
ORACLE = (
    "The result is labelled upscaled output and cannot satisfy the native 8K "
    "acceptance requirement."
)
MUTANT = "Validate native resolution using only the container width and height."
MUTANT_CLAIM = "container-only-native-resolution"
MATRIX_KEYS = {
    "schemaVersion",
    "phase",
    "matrixId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "requiredExperiments",
    "candidates",
}
CANDIDATE_KEYS = {
    "tupleId",
    "advertised",
    "userTarget",
    "sourceWidth",
    "sourceHeight",
    "outputWidth",
    "outputHeight",
    "containerWidth",
    "containerHeight",
    "transform",
    "rendererEnlarged",
    "experiments",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = {"upscaled", "transformed", "withheld", "recorded", "rejected"}
FORBIDDEN = {"qualified", "allowed", "native_8k"}
PHYSICAL_QUESTION = "physical S23 qualification remains open"


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


def _text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value.strip()) and value == value.strip(),
            context + " must be a non-empty string")
    return value


def _positive_int(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _size(candidate: dict, prefix: str) -> tuple[int, int]:
    return candidate[prefix + "Width"], candidate[prefix + "Height"]


def _size_text(width: int, height: int) -> str:
    return f"{width}x{height}"


def _geometry_label(candidate: dict) -> str:
    if candidate["transform"] == "upscale":
        return "upscaled output"
    return candidate["transform"]


def _is_declared_upscaled_8k(candidate: dict) -> bool:
    """True for the phase fixture: 7680x4320 declared from a smaller enlargement."""
    source = _size(candidate, "source")
    return (
        candidate["transform"] == "upscale"
        and candidate["rendererEnlarged"] is True
        and _size(candidate, "container") == (7680, 4320)
        and (source[0] < 7680 or source[1] < 4320)
    )


def native_8k_accepted(candidate: dict) -> bool:
    """Host fixtures never satisfy native 8K acceptance.

    Container width and height are read and then ignored. Renderer enlargement,
    a native label, and experiment marks are not a physical measurement.
    """
    require(isinstance(candidate, dict), "candidate must be an object")
    for key in ("sourceWidth", "sourceHeight", "outputWidth", "outputHeight",
                "containerWidth", "containerHeight", "transform", "rendererEnlarged",
                "experiments"):
        require(key in candidate, "candidate missing " + key)
    source = (_positive_int(candidate["sourceWidth"], "sourceWidth"),
              _positive_int(candidate["sourceHeight"], "sourceHeight"))
    output = (_positive_int(candidate["outputWidth"], "outputWidth"),
              _positive_int(candidate["outputHeight"], "outputHeight"))
    container = (_positive_int(candidate["containerWidth"], "containerWidth"),
                 _positive_int(candidate["containerHeight"], "containerHeight"))
    _bool(candidate["rendererEnlarged"], "rendererEnlarged")
    _text(candidate["transform"], "transform")
    require(isinstance(candidate["experiments"], dict), "experiments must be an object")
    # The mutant would return container == (7680, 4320). This gate does not.
    if candidate["rendererEnlarged"] or candidate["transform"] != "native":
        return False
    if source != output or source != container or source != (7680, 4320):
        return False
    if any(candidate["experiments"].get(name) != "measured" for name in EXPERIMENTS):
        return False
    return False


def _check_geometry(candidate: dict, index: int) -> None:
    source = _size(candidate, "source")
    output = _size(candidate, "output")
    transform = candidate["transform"]
    enlarged = candidate["rendererEnlarged"]
    context = f"candidate {index}"
    if transform == "native":
        require(source == output, context + " native geometry requires matching source and output")
        require(enlarged is False, context + " native geometry is not renderer enlargement")
        return
    require(source != output, context + " transform requires source and output to differ")
    if transform == "upscale":
        require(enlarged is True, context + " upscale requires rendererEnlarged")
        require(output[0] >= source[0] and output[1] >= source[1],
                context + " upscale cannot shrink a dimension")
        require(output[0] > source[0] or output[1] > source[1],
                context + " upscale must enlarge a dimension")
        return
    require(enlarged is False, context + " reduction is not renderer enlargement")
    require(output[0] <= source[0] and output[1] <= source[1],
            context + " " + transform + " cannot enlarge a dimension")
    if transform == "binning":
        require(source[0] % output[0] == 0 and source[1] % output[1] == 0,
                context + " binning requires integer factors")


def validate_matrix(document: dict) -> None:
    """Raise ValueError unless document is a P014 high-resolution experiment matrix."""
    exact_keys(document, MATRIX_KEYS, "experiment matrix")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == "P014", "phase must be P014")
    require(document["matrixId"] == MATRIX_ID, "matrixId must be " + MATRIX_ID)
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "experiment matrix needs the P014 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    require(document["requiredExperiments"] == list(EXPERIMENTS),
            "requiredExperiments must be capture, encode, decode, cadence, storage, thermal")
    candidates = document["candidates"]
    require(isinstance(candidates, list) and candidates, "candidates must be a non-empty list")
    seen: set[str] = set()
    for index, candidate in enumerate(candidates):
        exact_keys(candidate, CANDIDATE_KEYS, f"candidate {index}")
        tuple_id = _text(candidate["tupleId"], f"candidate {index} tupleId")
        require(tuple_id not in seen, "duplicate tupleId: " + tuple_id)
        seen.add(tuple_id)
        _bool(candidate["advertised"], f"candidate {index} advertised")
        _bool(candidate["userTarget"], f"candidate {index} userTarget")
        for prefix in ("source", "output", "container"):
            _positive_int(candidate[prefix + "Width"], f"candidate {index} {prefix}Width")
            _positive_int(candidate[prefix + "Height"], f"candidate {index} {prefix}Height")
        require(candidate["transform"] in TRANSFORMS,
                f"candidate {index} transform must be native, crop, binning, downsample, or upscale")
        _bool(candidate["rendererEnlarged"], f"candidate {index} rendererEnlarged")
        experiments = candidate["experiments"]
        exact_keys(experiments, set(EXPERIMENTS), f"candidate {index} experiments")
        for name in EXPERIMENTS:
            require(experiments[name] in EXPERIMENT_STATUS,
                    f"candidate {index} {name} status must be unmeasured, measured, or failed")
        _check_geometry(candidate, index)


def export_candidates(document: dict) -> list[dict]:
    """Export every candidate. One upscaled file does not drop the others.

    geometry is ``upscaled output`` for renderer enlargement. native8kAccepted
    is never true: container dimensions are not native 8K acceptance.
    """
    validate_matrix(document)
    exported: list[dict] = []
    for candidate in document["candidates"]:
        exported.append({
            "tupleId": candidate["tupleId"],
            "geometry": _geometry_label(candidate),
            "source": _size_text(*_size(candidate, "source")),
            "output": _size_text(*_size(candidate, "output")),
            "container": _size_text(*_size(candidate, "container")),
            "advertised": candidate["advertised"],
            "userTarget": candidate["userTarget"],
            "native8kAccepted": native_8k_accepted(candidate),
        })
    return exported


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision in DECISIONS, "unexpected decision")
    require(decision not in FORBIDDEN, "decision must not be qualified, allowed, or native_8k")
    require(bool(reasons), "reasons required")
    require(all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    require(all(isinstance(item, str) for item in rejected), "rejectedClaims must be strings")
    require(all(isinstance(item, str) and item for item in preserved), "preservedResults must be strings")
    require(all(isinstance(item, str) and item for item in questions), "openQuestions must be strings")
    result = {
        "caseId": "P014",
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _experiment_notes(candidate: dict, preserved: list[str], rejected: list[str],
                      questions: list[str]) -> None:
    experiments = candidate["experiments"]
    for name in EXPERIMENTS:
        status = experiments[name]
        preserved.append(f"{name}:{status}")
        if status == "failed":
            rejected.append(f"{name}-failed")
        if status != "measured":
            questions.append(f"{name} experiment is {status}")
    questions.append(PHYSICAL_QUESTION)


def _assess_one(candidate: dict) -> dict[str, Any]:
    source = _size(candidate, "source")
    output = _size(candidate, "output")
    container = _size(candidate, "container")
    transform = candidate["transform"]
    preserved = [
        f"source:{_size_text(*source)}",
        f"output:{_size_text(*output)}",
        f"container:{_size_text(*container)}",
        f"tuple:{candidate['tupleId']}",
        f"geometry:{transform}",
    ]
    rejected: list[str] = []
    questions: list[str] = []
    if transform == "upscale" or candidate["rendererEnlarged"]:
        decision = "upscaled"
        reasons = [
            ORACLE,
            "upscaled output",
            "source geometry is tracked separately from renderer enlargement",
            f"source {_size_text(*source)} output {_size_text(*output)} container {_size_text(*container)}",
        ]
        rejected.append("native-8k")
        if container != source:
            rejected.append("container-as-source")
            reasons.append("container dimensions alone must not certify source resolution")
    elif transform in {"crop", "binning", "downsample"}:
        decision = "transformed"
        reasons = [
            f"{transform} is not native acquisition",
            "source and output geometry are preserved separately",
        ]
        rejected.append("native-acquisition")
        if container != source:
            rejected.append("container-as-source")
            reasons.append("container dimensions alone must not certify source resolution")
        if container == (7680, 4320) and source != (7680, 4320):
            rejected.append("native-8k")
            reasons.append("cannot satisfy the native 8K acceptance requirement")
    else:
        failed = [name for name in EXPERIMENTS if candidate["experiments"][name] == "failed"]
        pending = [name for name in EXPERIMENTS if candidate["experiments"][name] != "measured"]
        if container != source:
            decision = "withheld"
            reasons = [
                "native geometry does not follow the container",
                "container dimensions alone must not certify source resolution",
            ]
            rejected.append("container-as-source")
            if container == (7680, 4320) and source != (7680, 4320):
                rejected.append("native-8k")
                reasons.append("cannot satisfy the native 8K acceptance requirement")
        elif failed:
            decision = "rejected"
            reasons = [
                "a failed independent experiment blocks native acceptance",
                "source geometry is preserved",
            ]
        elif pending:
            decision = "withheld"
            reasons = [
                "native geometry is recorded for the advertised size",
                "independent capture, encode, decode, cadence, storage, and thermal experiments are required",
                "4K and 8K ambitions stay visible without promising unmeasured throughput",
            ]
            if source == (7680, 4320):
                rejected.append("native-8k")
                reasons.append("cannot satisfy the native 8K acceptance requirement without measured experiments")
        else:
            decision = "recorded"
            reasons = [
                "native geometry matches source, output, and container in this host fixture",
                "capture, encode, decode, cadence, storage, and thermal experiments are marked measured",
                "host experiment marks are not a physical S23 qualification",
                "host experiment marks are not cinema-camera equivalence",
            ]
            if source == (7680, 4320):
                rejected.append("native-8k")
                reasons.append("cannot satisfy the native 8K acceptance requirement")
    _experiment_notes(candidate, preserved, rejected, questions)
    if _is_declared_upscaled_8k(candidate) and decision != "upscaled":
        raise ValueError("renderer-enlarged 7680x4320 must be labelled upscaled output")
    if _is_declared_upscaled_8k(candidate) and native_8k_accepted(candidate):
        raise ValueError("container width and height must not validate native resolution")
    return _result(decision, reasons, rejected, preserved, questions)


def assess_candidate(document: dict, tuple_id: str) -> dict[str, Any]:
    """Assess one tuple without dropping the rest of the matrix from validation.

    The returned preservedResults include that tuple's source, output, and
    container geometry plus each experiment status.
    """
    validate_matrix(document)
    require(isinstance(tuple_id, str) and bool(tuple_id), "tuple_id must be a non-empty string")
    matches = [item for item in document["candidates"] if item["tupleId"] == tuple_id]
    require(len(matches) == 1, "unknown tuple: " + tuple_id)
    return _assess_one(matches[0])


def assess_matrix(document: dict, container_only: bool = False) -> dict[str, Any]:
    """Apply the P014 oracle to the renderer-enlarged 7680x4320 file.

    Decision is ``upscaled``. rejectedClaims include ``native-8k``. Every
    candidate tuple stays in preservedResults. Container dimensions are not
    native resolution.

    ``container_only`` true is the mutant: native resolution would be read from
    container width and height alone. That path is ``rejected`` and still does
    not accept native 8K. The preserved inventory is unchanged.
    """
    validate_matrix(document)
    require(type(container_only) is bool, "container_only must be a bool")
    oracles = [item for item in document["candidates"] if _is_declared_upscaled_8k(item)]
    require(len(oracles) == 1, "matrix needs one renderer-enlarged 7680x4320 file")
    oracle = oracles[0]
    one = _assess_one(oracle)
    require(one["decision"] == "upscaled", "oracle candidate must be upscaled output")
    require(not native_8k_accepted(oracle), "container width and height must not validate native resolution")
    preserved = []
    for candidate in document["candidates"]:
        preserved.append("tuple:" + candidate["tupleId"])
        preserved.append("source:" + _size_text(*_size(candidate, "source")))
        preserved.append("geometry:" + candidate["transform"])
    preserved.append("container:" + _size_text(*_size(oracle, "container")))
    rejected = ["native-8k", "physical-s23"]
    for claim in one["rejectedClaims"]:
        if claim not in rejected:
            rejected.append(claim)
    if container_only:
        rejected.insert(0, MUTANT_CLAIM)
        reasons = [
            MUTANT,
            "mutant rejected: container width and height do not validate native resolution",
            ORACLE,
            "upscaled output",
            "4K and 8K ambitions stay visible without promising unmeasured throughput",
        ]
        result = _result("rejected", reasons, rejected, preserved, one["openQuestions"])
        require(not native_8k_accepted(oracle), "mutant must not accept native 8K")
        require(result["decision"] == "rejected", "container-only native resolution must be rejected")
        return result
    reasons = [
        ORACLE,
        "upscaled output",
        "declared 7680x4320 was enlarged by the renderer from a smaller source stream",
        "container width and height do not validate native resolution",
        "4K and 8K ambitions stay visible without promising unmeasured throughput",
    ]
    return _result("upscaled", reasons, rejected, preserved, one["openQuestions"])
