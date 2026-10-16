#!/usr/bin/env python3
"""P101 Integrate the first on-device inference path.

Host reference only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P101-01 through TC-P101-08 modules.
Model identity, letterbox restoration, offline failure, depth identity,
confidence labelling, and workload selection are computed here.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P101"
GOAL = "Run the approved model locally with bounded ownership and an explicit fallback policy."
METHOD = "Benchmark the selected runtime and delegate under actual app load. Separate model download or installation from inference. The app must work offline after assets are present, and failure must leave capture usable without virtual blur."
FIXTURE = "Airplane mode, a missing model asset, and a delegate initialization failure during preview."
ORACLE = "The UI reports the issue, avoids network-dependent generation, and preserves ordinary recording."
MUTANT = "Block camera startup until a cloud inference service responds."
DELIVERABLE = "Offline inference integration and no-network tests"

TOKEN_FILENAME = "filename-match-alone-establish-identical-weights"
TOKEN_STRETCH = "unrecorded-stretching-swapped-color-channels-fail"
TOKEN_MERELY_RUNS = "model-merely-runs-numerically-qualified"
TOKEN_CLOUD = "offline-camera-hang-waiting-undisclosed-cloud"
TOKEN_BACKEND = "silently-changing-untested-backend-uploading-frames"
TOKEN_FLOATS = "float-array-without-temporal-geometric-identity"
TOKEN_CONFIDENCE = "arbitrary-confidence-score-presented-calibrated-probability"
TOKEN_LATENCY = "standalone-model-latency-become-full-camera"
TOKEN_STALE = "stale-depth-timestamp-or-crop-mismatch"

QUALIFIED_FALLBACKS = frozenset({"cpu-reference"})
CHANNEL_ORDERS = frozenset({"rgb", "bgr"})
PREPARATIONS = frozenset({"letterbox", "stretch"})
PRESENTED_AS = frozenset({"uncalibrated-score", "calibrated-probability"})
RELIANCE = frozenset({"reduced", "full"})
OPERATIONS = frozenset({"live", "deferred"})

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "networkingEnabled",
    "blockCameraUntilCloud",
    "virtualBlurApplied",
    "model",
    "geometry",
    "conversion",
    "offlineFailure",
    "delegate",
    "depth",
    "confidence",
    "load",
}
MODEL_KEYS = (
    "filename",
    "content",
    "precision",
    "runtimeVersion",
    "cachedFilename",
    "cachedContent",
    "cachedPrecision",
    "cachedRuntimeVersion",
    "keepCachedDepth",
)
GEOMETRY_KEYS = (
    "sourceWidth",
    "sourceHeight",
    "tensorSize",
    "channelOrder",
    "recordedChannelOrder",
    "preparation",
    "stretchRecorded",
)
CONVERSION_KEYS = (
    "baseline",
    "exported",
    "tolerance",
    "boundaryBaseline",
    "boundaryExported",
    "boundaryTolerance",
    "loads",
    "experimental",
)
OFFLINE_KEYS = (
    "networkingEnabled",
    "assetPresent",
    "assetCorrupt",
    "missingCapability",
    "captureUsable",
    "blockCaptureUntilCloud",
    "sourceRetained",
)
DELEGATE_KEYS = (
    "initFailed",
    "fallbackName",
    "fallbackQualified",
    "depthDisabled",
    "disableReason",
    "silentBackendChange",
    "uploadsFrames",
)
DEPTH_KEYS = (
    "sourceTimestampNs",
    "sourceCrop",
    "values",
    "identity",
    "reprojected",
)
IDENTITY_KEYS = {"timestampNs", "crop"}
CONFIDENCE_KEYS = (
    "scores",
    "label",
    "presentedAs",
    "renderingReliance",
)
LOAD_KEYS = (
    "modelLatencyMs",
    "captureMs",
    "renderMs",
    "encodeMs",
    "frameBudgetMs",
    "operation",
    "reportedAsFrameRateGuarantee",
    "workloadMeasured",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_CORNER_TOLERANCE = 1e-6


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def _text(value: object, label: str, allow_empty: bool = False) -> str:
    require(isinstance(value, str), f"{label} must be a string")
    require(value == value.strip(), f"{label} must not have surrounding whitespace")
    require(allow_empty or bool(value.strip()), f"{label} must be a non-empty string")
    return value


def _number(value: object, label: str) -> float:
    require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{label} must be a number")
    number = float(value)
    require(math.isfinite(number), f"{label} must be finite")
    return number


def _non_negative(value: object, label: str) -> float:
    number = _number(value, label)
    require(number >= 0.0, f"{label} must be >= 0")
    return number


def _positive_int(value: object, label: str) -> int:
    require(type(value) is int and value > 0, f"{label} must be a positive int")
    return value


def _int(value: object, label: str) -> int:
    require(type(value) is int, f"{label} must be an int")
    return value


def _exact_keys(value: object, keys: set[str] | tuple[str, ...], label: str) -> dict:
    require(isinstance(value, dict), f"{label} must be an object")
    expected = set(keys)
    require(set(value) == expected, f"{label} keys must be {sorted(expected)}")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def _fmt(value: float) -> str:
    return format(value, ".6f")


def _series(value: object, label: str) -> list[float]:
    require(isinstance(value, list) and len(value) >= 1, f"{label} must be a non-empty list")
    return [_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def _crop(value: object, label: str) -> list[float]:
    require(isinstance(value, list) and len(value) == 4, f"{label} must have four components")
    return [_number(item, f"{label}[{index}]") for index, item in enumerate(value)]


def model_identity(content: bytes, precision: str, runtime_version: str) -> str:
    """SHA-256 of content plus precision and runtime version.

    The digest covers the raw content bytes, a NUL separator, the precision
    string, a NUL separator, and the runtime version. A filename is not an input.
    """
    require(isinstance(content, bytes), "content must be bytes")
    require(isinstance(precision, str) and precision.strip(), "precision must be text")
    require(isinstance(runtime_version, str) and runtime_version.strip(), "runtime version must be text")
    hasher = hashlib.sha256()
    hasher.update(content)
    hasher.update(b"\0")
    hasher.update(precision.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(runtime_version.encode("utf-8"))
    return hasher.hexdigest()


def content_sha256(content: bytes) -> str:
    require(isinstance(content, bytes), "content must be bytes")
    return hashlib.sha256(content).hexdigest()


def _content_bytes(value: object, label: str) -> bytes:
    text = _text(value, label)
    return text.encode("utf-8")


def letterbox_geometry(source_width: int, source_height: int, tensor_size: int) -> dict[str, float]:
    """Fit a non-square frame inside a square tensor and record scale and pad."""
    width = _positive_int(source_width, "sourceWidth")
    height = _positive_int(source_height, "sourceHeight")
    tensor = _positive_int(tensor_size, "tensorSize")
    require(width != height, "source frame must be non-square")
    long_side = max(width, height)
    scale = tensor / long_side
    scaled_width = width * scale
    scaled_height = height * scale
    return {
        "scale": scale,
        "padX": (tensor - scaled_width) / 2.0,
        "padY": (tensor - scaled_height) / 2.0,
        "scaledWidth": scaled_width,
        "scaledHeight": scaled_height,
    }


def source_corners(source_width: int, source_height: int) -> list[tuple[float, float]]:
    width = float(_positive_int(source_width, "sourceWidth"))
    height = float(_positive_int(source_height, "sourceHeight"))
    return [
        (0.0, 0.0),
        (width - 1.0, 0.0),
        (0.0, height - 1.0),
        (width - 1.0, height - 1.0),
    ]


def restore_source_corners(source_width: int, source_height: int, tensor_size: int) -> list[tuple[float, float]]:
    """Map the four source corners into the letterbox and back to source space."""
    geometry = letterbox_geometry(source_width, source_height, tensor_size)
    scale = geometry["scale"]
    pad_x = geometry["padX"]
    pad_y = geometry["padY"]
    restored: list[tuple[float, float]] = []
    for x_coord, y_coord in source_corners(source_width, source_height):
        tensor_x = x_coord * scale + pad_x
        tensor_y = y_coord * scale + pad_y
        restored.append(((tensor_x - pad_x) / scale, (tensor_y - pad_y) / scale))
    return restored


def _corner_text(points: list[tuple[float, float]]) -> str:
    return ";".join(f"({_fmt(x_coord)},{_fmt(y_coord)})" for x_coord, y_coord in points)


def max_abs_error(left: list[float], right: list[float]) -> float:
    require(len(left) == len(right) and len(left) >= 1, "series must be the same non-empty length")
    return max(abs(a_value - b_value) for a_value, b_value in zip(left, right))


def workload_total_ms(model_ms: float, capture_ms: float, render_ms: float, encode_ms: float) -> float:
    return model_ms + capture_ms + render_ms + encode_ms


def choose_operation(total_ms: float, frame_budget_ms: float) -> str:
    """Pick live or deferred from the measured whole workload, not model latency alone."""
    require(frame_budget_ms > 0.0, "frame budget must be positive")
    if total_ms > frame_budget_ms:
        return "deferred"
    return "live"


def parse_evidence_repeat(payload: dict) -> tuple[str, str]:
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
            "evidenceId must be a non-empty string")
    require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    return evidence, repeat


def assess_model_cache(section: dict) -> tuple[list[str], list[str]]:
    filename = _text(section["filename"], "filename")
    precision = _text(section["precision"], "precision")
    runtime = _text(section["runtimeVersion"], "runtimeVersion")
    cached_filename = _text(section["cachedFilename"], "cachedFilename")
    cached_precision = _text(section["cachedPrecision"], "cachedPrecision")
    cached_runtime = _text(section["cachedRuntimeVersion"], "cachedRuntimeVersion")
    keep_cached = _bool(section["keepCachedDepth"], "keepCachedDepth")
    content = _content_bytes(section["content"], "content")
    cached_content = _content_bytes(section["cachedContent"], "cachedContent")
    identity = model_identity(content, precision, runtime)
    cached_identity = model_identity(cached_content, cached_precision, cached_runtime)
    digest = content_sha256(content)
    cached_digest = content_sha256(cached_content)
    rejected: list[str] = []
    reasons = [
        f"modelIdentity={identity}",
        f"contentSha256={digest}",
        f"precision={precision}",
        f"runtimeVersion={runtime}",
        "filename was not used as the identity",
    ]
    if identity == cached_identity:
        reasons.append("cache-compatible")
        return rejected, reasons
    differed = []
    if digest != cached_digest:
        differed.append("digest")
    if precision != cached_precision:
        differed.append("precision")
    if runtime != cached_runtime:
        differed.append("runtime")
    reasons.append("cache-invalidated")
    reasons.append("identity-differs=" + ",".join(differed))
    reasons.append(f"actualModelIdentity={identity}")
    if keep_cached:
        if filename == cached_filename:
            _add(rejected, TOKEN_FILENAME)
            reasons.append("filename match did not establish identical weights")
        else:
            _add(rejected, "cached-depth-retained-for-incompatible-identity")
            reasons.append("cached depth retained after the model identity changed")
    else:
        reasons.append("cached depth dropped after identity invalidation")
    return rejected, reasons


def assess_geometry(section: dict) -> tuple[list[str], list[str]]:
    width = _positive_int(section["sourceWidth"], "sourceWidth")
    height = _positive_int(section["sourceHeight"], "sourceHeight")
    tensor = _positive_int(section["tensorSize"], "tensorSize")
    require(width != height, "source frame must be non-square")
    channel_order = _text(section["channelOrder"], "channelOrder")
    recorded_order = _text(section["recordedChannelOrder"], "recordedChannelOrder")
    require(channel_order in CHANNEL_ORDERS, "channelOrder must be rgb or bgr")
    require(recorded_order in CHANNEL_ORDERS, "recordedChannelOrder must be rgb or bgr")
    preparation = _text(section["preparation"], "preparation")
    require(preparation in PREPARATIONS, "preparation must be letterbox or stretch")
    stretch_recorded = _bool(section["stretchRecorded"], "stretchRecorded")
    rejected: list[str] = []
    reasons: list[str] = []
    if preparation == "stretch":
        _add(rejected, TOKEN_STRETCH)
        if stretch_recorded:
            reasons.append("recorded stretch does not match the specified letterbox preparation")
        else:
            reasons.append("unrecorded stretch")
        return rejected, reasons
    geometry = letterbox_geometry(width, height, tensor)
    restored = restore_source_corners(width, height, tensor)
    original = source_corners(width, height)
    reasons.append(
        f"scale={_fmt(geometry['scale'])} padX={_fmt(geometry['padX'])} "
        f"padY={_fmt(geometry['padY'])} channelOrder={channel_order} "
        f"recordedChannelOrder={recorded_order}"
    )
    reasons.append("restoredCorners=" + _corner_text(restored))
    for (x_coord, y_coord), (restored_x, restored_y) in zip(original, restored):
        if abs(x_coord - restored_x) > _CORNER_TOLERANCE or abs(y_coord - restored_y) > _CORNER_TOLERANCE:
            _add(rejected, "corner-restoration-failed")
            reasons.append("corner restoration left source space")
            break
    if channel_order != recorded_order:
        _add(rejected, TOKEN_STRETCH)
        reasons.append("swapped color channels")
    return rejected, reasons


def assess_conversion(section: dict) -> tuple[list[str], list[str]]:
    baseline = _series(section["baseline"], "baseline")
    exported = _series(section["exported"], "exported")
    boundary_baseline = _series(section["boundaryBaseline"], "boundaryBaseline")
    boundary_exported = _series(section["boundaryExported"], "boundaryExported")
    require(len(baseline) == len(exported), "baseline and exported length mismatch")
    require(len(boundary_baseline) == len(boundary_exported), "boundary series length mismatch")
    tolerance = _non_negative(section["tolerance"], "tolerance")
    boundary_tolerance = _non_negative(section["boundaryTolerance"], "boundaryTolerance")
    loads = _bool(section["loads"], "loads")
    experimental = _bool(section["experimental"], "experimental")
    depth_error = max_abs_error(baseline, exported)
    boundary_error = max_abs_error(boundary_baseline, boundary_exported)
    within = depth_error <= tolerance and boundary_error <= boundary_tolerance
    rejected: list[str] = []
    reasons = [
        f"maxAbsError={_fmt(depth_error)}",
        f"boundaryAbsError={_fmt(boundary_error)}",
        f"tolerance={_fmt(tolerance)}",
        f"boundaryTolerance={_fmt(boundary_tolerance)}",
    ]
    if not loads:
        _add(rejected, "model-not-loaded")
        reasons.append("exported model did not load")
        return rejected, reasons
    if within:
        reasons.append("declared depth and boundary tolerances met; decision stays recorded not qualified")
        return rejected, reasons
    if experimental:
        reasons.append("outside tolerance; remains experimental despite successful loading")
        return rejected, reasons
    _add(rejected, TOKEN_MERELY_RUNS)
    reasons.append("a model that merely runs is not numerically qualified")
    return rejected, reasons


def assess_offline(section: dict) -> tuple[list[str], list[str]]:
    networking = _bool(section["networkingEnabled"], "networkingEnabled")
    present = _bool(section["assetPresent"], "assetPresent")
    corrupt = _bool(section["assetCorrupt"], "assetCorrupt")
    capability = _text(section["missingCapability"], "missingCapability", allow_empty=True)
    capture_usable = _bool(section["captureUsable"], "captureUsable")
    block_cloud = _bool(section["blockCaptureUntilCloud"], "blockCaptureUntilCloud")
    retained = _bool(section["sourceRetained"], "sourceRetained")
    rejected: list[str] = []
    reasons: list[str] = []
    if networking:
        _add(rejected, "networking-not-disabled")
        reasons.append("networking is enabled")
    else:
        reasons.append("networking-disabled")
    unavailable = (not present) or corrupt
    if unavailable:
        reasons.append("local-model-unavailable")
        if capability:
            reasons.append(f"missingCapability={capability}")
        else:
            _add(rejected, "missing-capability-unreported")
            reasons.append("missing capability was not reported")
    else:
        reasons.append("local-model-present")
        if capability:
            _add(rejected, "missing-capability-reported-for-present-asset")
    if capture_usable:
        reasons.append("capture_usable=True")
    else:
        _add(rejected, "capture-usable-not-preserved")
        reasons.append("capture_usable was not left true")
    if retained:
        reasons.append("source-retained")
    else:
        _add(rejected, "source-retention-lost")
    if block_cloud:
        _add(rejected, TOKEN_CLOUD)
        reasons.append("blocked capture until a cloud inference service responded")
    return rejected, reasons


def assess_delegate(section: dict) -> tuple[list[str], list[str]]:
    init_failed = _bool(section["initFailed"], "initFailed")
    fallback_name = _text(section["fallbackName"], "fallbackName", allow_empty=True)
    fallback_qualified = _bool(section["fallbackQualified"], "fallbackQualified")
    depth_disabled = _bool(section["depthDisabled"], "depthDisabled")
    disable_reason = _text(section["disableReason"], "disableReason", allow_empty=True)
    silent = _bool(section["silentBackendChange"], "silentBackendChange")
    uploads = _bool(section["uploadsFrames"], "uploadsFrames")
    rejected: list[str] = []
    reasons: list[str] = []
    if silent or uploads:
        _add(rejected, TOKEN_BACKEND)
        if silent:
            reasons.append("silent backend change")
        if uploads:
            reasons.append("frames uploaded")
    qualified = (
        fallback_name in QUALIFIED_FALLBACKS
        and fallback_qualified
        and not silent
        and not uploads
    )
    disabled = depth_disabled and bool(disable_reason) and not silent and not uploads
    if init_failed:
        reasons.append("delegate-init-failed")
        if qualified:
            reasons.append(f"qualified-fallback={fallback_name}")
        elif disabled:
            reasons.append(f"depth-disabled={disable_reason}")
        else:
            _add(rejected, "delegate-failure-without-qualified-fallback")
            reasons.append("no explicitly qualified fallback and depth was not disabled")
        if fallback_qualified and fallback_name not in QUALIFIED_FALLBACKS and not disabled:
            reasons.append("caller flag did not qualify an unknown fallback")
    else:
        reasons.append("delegate-init-ok")
    if depth_disabled and not disable_reason:
        _add(rejected, "depth-disabled-without-reason")
    return rejected, reasons


def assess_depth(section: dict) -> tuple[list[str], list[str]]:
    source_timestamp = _int(section["sourceTimestampNs"], "sourceTimestampNs")
    source_crop = _crop(section["sourceCrop"], "sourceCrop")
    values = _series(section["values"], "values")
    reprojected = _bool(section["reprojected"], "reprojected")
    identity = section["identity"]
    rejected: list[str] = []
    reasons = [f"depthSamples={len(values)}", f"reprojected={reprojected}"]
    if identity is None:
        _add(rejected, TOKEN_FLOATS)
        reasons.append("float list has no temporal or geometric identity")
        return rejected, reasons
    identity_object = _exact_keys(identity, IDENTITY_KEYS, "identity")
    result_timestamp = _int(identity_object["timestampNs"], "identity.timestampNs")
    result_crop = _crop(identity_object["crop"], "identity.crop")
    reasons.append(f"resultTimestampNs={result_timestamp}")
    reasons.append("resultCrop=" + ",".join(_fmt(item) for item in result_crop))
    timestamp_mismatch = result_timestamp != source_timestamp
    crop_mismatch = result_crop != source_crop
    if timestamp_mismatch or crop_mismatch:
        _add(rejected, TOKEN_STALE)
        if reprojected:
            reasons.append("reprojection flag did not make a mismatched timestamp or crop current")
        else:
            reasons.append("timestamp or crop does not match the source")
        return rejected, reasons
    reasons.append("depth timestamp and crop match the source")
    return rejected, reasons


def assess_confidence(section: dict) -> tuple[list[str], list[str]]:
    scores = _series(section["scores"], "scores")
    label = _text(section["label"], "label")
    presented = _text(section["presentedAs"], "presentedAs")
    require(presented in PRESENTED_AS, "presentedAs must be uncalibrated-score or calibrated-probability")
    reliance = _text(section["renderingReliance"], "renderingReliance")
    require(reliance in RELIANCE, "renderingReliance must be reduced or full")
    rejected: list[str] = []
    reasons = [f"confidenceSamples={len(scores)}", f"label={label}", f"renderingReliance={reliance}"]
    if presented == "calibrated-probability":
        _add(rejected, TOKEN_CONFIDENCE)
        reasons.append("arbitrary confidence presented as a calibrated probability")
    elif label != "uncalibrated":
        _add(rejected, "confidence-not-labelled-uncalibrated")
        reasons.append("confidence values are not labelled uncalibrated")
    else:
        reasons.append("confidence labelled uncalibrated")
    if reliance != "reduced":
        _add(rejected, "rendering-reliance-not-reduced")
        reasons.append("rendering reliance was not reduced for uncalibrated confidence")
    return rejected, reasons


def assess_load(section: dict) -> tuple[list[str], list[str]]:
    model_ms = _non_negative(section["modelLatencyMs"], "modelLatencyMs")
    capture_ms = _non_negative(section["captureMs"], "captureMs")
    render_ms = _non_negative(section["renderMs"], "renderMs")
    encode_ms = _non_negative(section["encodeMs"], "encodeMs")
    budget = _number(section["frameBudgetMs"], "frameBudgetMs")
    require(budget > 0.0, "frameBudgetMs must be positive")
    operation = _text(section["operation"], "operation")
    require(operation in OPERATIONS, "operation must be live or deferred")
    as_guarantee = _bool(section["reportedAsFrameRateGuarantee"], "reportedAsFrameRateGuarantee")
    measured = _bool(section["workloadMeasured"], "workloadMeasured")
    rejected: list[str] = []
    reasons: list[str] = []
    if not measured:
        _add(rejected, "workload-not-measured")
        reasons.append("complete workload was not measured")
        total = workload_total_ms(model_ms, capture_ms, render_ms, encode_ms)
    else:
        total = workload_total_ms(model_ms, capture_ms, render_ms, encode_ms)
        chosen = choose_operation(total, budget)
        reasons.append(f"workloadMs={_fmt(total)}")
        reasons.append(f"frameBudgetMs={_fmt(budget)}")
        reasons.append(f"chosenOperation={chosen}")
        reasons.append(f"modelLatencyMs={_fmt(model_ms)} is not a frame-rate guarantee")
        if operation != chosen:
            _add(rejected, "operation-not-chosen-from-workload-evidence")
            reasons.append("operation was not chosen from the measured workload")
    if as_guarantee:
        _add(rejected, TOKEN_LATENCY)
        reasons.append("standalone model latency reported as a camera frame-rate guarantee")
    return rejected, reasons


def gate_result(
    case_id: str,
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(all(isinstance(item, str) and item for item in preserved), "preserved results must be non-empty strings")
    require(any("physical S23 measurement was not run" in item for item in questions),
            "openQuestions must mention that physical S23 measurement was not run")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    return result


def finish_case(
    case_id: str,
    name: str,
    expected: str,
    repeat: str,
    evidence: str,
    rejected: list[str],
    extra_reasons: list[str],
    negative: str,
    repeat_text: str,
) -> dict[str, Any]:
    reasons = [f"{case_id} {name} repeat {repeat}", expected, *extra_reasons]
    if rejected:
        decision = "rejected"
        reasons.append(negative)
    else:
        decision = "recorded"
        reasons.append("narrower software result retained; physical behavior stays open")
    return gate_result(
        case_id,
        decision,
        reasons,
        rejected,
        [evidence],
        ["physical S23 measurement was not run", repeat_text],
    )


def _merge(rejected: list[str], reasons: list[str], extra_rejected: list[str], extra_reasons: list[str]) -> None:
    for token in extra_rejected:
        _add(rejected, token)
    reasons.extend(extra_reasons)


def assess(document: dict) -> dict[str, Any]:
    """Record an offline on-device inference reference or reject a domain failure.

    Blocking camera startup on a cloud response is the phase mutant. Cache
    compatibility, letterbox restoration, numeric tolerance, offline capture,
    delegate fallback, depth identity, uncalibrated confidence, and workload
    selection are computed from the document rather than from a boolean flag.
    """
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = document["evidenceId"]
    require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
            "evidenceId must be a non-empty string")
    claim = _text(document["claim"], "claim")
    networking = _bool(document["networkingEnabled"], "networkingEnabled")
    block_camera = _bool(document["blockCameraUntilCloud"], "blockCameraUntilCloud")
    virtual_blur = _bool(document["virtualBlurApplied"], "virtualBlurApplied")
    model = _exact_keys(document["model"], MODEL_KEYS, "model")
    geometry = _exact_keys(document["geometry"], GEOMETRY_KEYS, "geometry")
    conversion = _exact_keys(document["conversion"], CONVERSION_KEYS, "conversion")
    offline = _exact_keys(document["offlineFailure"], OFFLINE_KEYS, "offlineFailure")
    delegate = _exact_keys(document["delegate"], DELEGATE_KEYS, "delegate")
    depth = _exact_keys(document["depth"], DEPTH_KEYS, "depth")
    confidence = _exact_keys(document["confidence"], CONFIDENCE_KEYS, "confidence")
    load = _exact_keys(document["load"], LOAD_KEYS, "load")

    rejected: list[str] = []
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
    ]
    if block_camera:
        _add(rejected, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    if networking:
        _add(rejected, "network-dependent-generation")
        reasons.append("network-dependent generation")
    else:
        reasons.append("network-dependent generation avoided")
    if virtual_blur:
        _add(rejected, "virtual-blur-substituted-for-capture")
        reasons.append("virtual blur substituted for ordinary capture")
    else:
        reasons.append("virtual blur not applied")
    _merge(rejected, reasons, *assess_model_cache(model))
    _merge(rejected, reasons, *assess_geometry(geometry))
    _merge(rejected, reasons, *assess_conversion(conversion))
    _merge(rejected, reasons, *assess_offline(offline))
    _merge(rejected, reasons, *assess_delegate(delegate))
    _merge(rejected, reasons, *assess_depth(depth))
    _merge(rejected, reasons, *assess_confidence(confidence))
    _merge(rejected, reasons, *assess_load(load))
    if rejected:
        decision = "rejected"
    else:
        decision = "recorded"
        reasons.append("method: " + METHOD)
        reasons.append("finite host reference retained for " + evidence)
    questions = [
        "physical S23 measurement was not run",
        "sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]
    result = gate_result(PHASE, decision, reasons, rejected, [evidence, claim], questions)
    require(evidence in result["preservedResults"], "evidence must be preserved")
    return result
