#!/usr/bin/env python3
"""P132 Build scopes with declared signal domains.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Each scope has a kind (histogram, waveform, clipping,
false_color) and a domain in {display_sdr, hlg_signal, sensor_code, unknown}.
A missing domain is not a domain. A histogram whose samples are display RGB
must not be labelled sensor_exposure. Labelling sensor_exposure while the
domain is unknown or missing is rejected. Relabeling a display histogram as
sensor_exposure is rejected. False color must name its input domain. Clipping
counts are the number of samples strictly above a declared threshold and are
retained with the evidence.
"""

from __future__ import annotations

import math
import re
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P132"
WORKSTREAM = 17
TITLE = "Build scopes with declared signal domains"
GOAL = "Make waveform, histogram, clipping, and false color informative rather than misleading."
METHOD = (
    "Label whether a scope measures source, working image, encoded Log, or display preview. "
    "Record sampling resolution and freshness. Preview-only RGB8 aids cannot certify sensor "
    "clipping or ten-bit precision. Keep scope computation off critical capture ownership."
)
FIXTURE = (
    "A clipped display preview of an unclipped high-range source and a stale waveform "
    "after inference load spikes."
)
ORACLE = (
    "The scope identifies its domain and stale status rather than falsely declaring "
    "source clipping from the preview."
)
MUTANT = "Label every preview histogram sensor exposure regardless of its input."
DELIVERABLE = "Scope domain model and monitoring correctness tests"
DEPENDENCIES = ("P131",)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p132-signal-domains"
CLAIM = "declared-signal-domain-host-reference"
SENSOR_EXPOSURE = "sensor_exposure"
DOMAIN_RULE = (
    "A scope domain is display_sdr, hlg_signal, sensor_code, or unknown; a missing domain "
    "is not a domain. A histogram whose samples are display RGB must not be labelled "
    "sensor_exposure. A sensor_exposure label with domain unknown or missing is rejected. "
    "Relabeling a display histogram as sensor_exposure is rejected. False color must name "
    "its input domain as display_sdr, hlg_signal, or sensor_code. Clipping counts are the "
    "number of samples strictly above a declared threshold and are retained."
)

KINDS = frozenset({"histogram", "waveform", "clipping", "false_color"})
DOMAINS = frozenset({"display_sdr", "hlg_signal", "sensor_code", "unknown"})
NAMED_DOMAINS = frozenset({"display_sdr", "hlg_signal", "sensor_code"})
ENCODINGS = frozenset({"display_rgb", "hlg_signal", "sensor_code", "unspecified"})
RESOLUTIONS = frozenset({"rgb8", "ten_bit", "sensor"})
REQUIRED_KINDS = ("histogram", "waveform", "clipping", "false_color")
DISPLAY_PRIOR_LABELS = frozenset({
    "display_preview",
    "display_histogram",
    "display_sdr",
    "display_clipping",
    "preview",
    "display_false_color",
    "stale_display_waveform",
})

DISPLAY_RGB_HISTOGRAM_LABELLED_SENSOR_EXPOSURE = "display-rgb-histogram-labelled-sensor-exposure"
UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE = "unknown-or-missing-domain-labelled-sensor-exposure"
RELABELLED_DISPLAY_HISTOGRAM = "relabelled-display-histogram-as-sensor-exposure"
FALSE_COLOR_UNNAMED_DOMAIN = "false-color-missing-input-domain"
FALSE_COLOR_DOMAIN_MISMATCH = "false-color-input-domain-disagrees"
CLIPPING_THRESHOLD_UNDECLARED = "clipping-threshold-not-declared"
CLAIMED_CLIP_MISMATCH = "claimed-clipping-count-disagrees"
PREVIEW_DECLARES_SOURCE_CLIPPING = "preview-declares-source-clipping"
RGB8_CERTIFIES_SENSOR = "rgb8-certifies-sensor-clipping"
RGB8_CERTIFIES_BIT_DEPTH = "rgb8-certifies-source-bit-depth"
RGB8_CERTIFIES_TEN_BIT = "rgb8-certifies-ten-bit"
STALE_REPORTS_SENSOR = "stale-scope-reports-sensor-conditions"
SCOPE_OWNS_CAPTURE = "scope-computation-owns-capture"
MUTANT_TOKEN = "labelled-every-preview-histogram-sensor-exposure"
MISSING_SCOPE_KIND = "missing-scope-kind"

SCOPE_KEYS = (
    "id",
    "kind",
    "domain",
    "sampleEncoding",
    "label",
    "priorLabel",
    "samples",
    "threshold",
    "inputDomain",
    "samplingResolution",
    "fresh",
    "certifiesSensorClipping",
    "certifiesTenBit",
    "certifiesSourceBitDepth",
    "declaresSourceClipping",
    "ownsCapture",
    "claimedClippingCount",
)
SOURCE_KEYS = ("domain", "samples", "threshold", "highRange")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "scopes",
    "source",
}
EVALUATE_KEYS = {
    "caseId",
    "evidenceId",
    "claim",
    "scopes",
    "source",
    "applyMutant",
}
COMMON_KEYS = {"evidenceId", "repeat", "scopes", "source", "applyMutant"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")

PREVIEW_CLIP_SAMPLES = [0.2, 0.95, 0.99, 1.0, 0.96]
PREVIEW_CLIP_THRESHOLD = 0.95
PREVIEW_CLIP_COUNT = 3
SOURCE_SAMPLES = [0.4, 1.5, 3.0, 6.0]
SOURCE_THRESHOLD = 14.0

FAULT_TEXT = {
    DISPLAY_RGB_HISTOGRAM_LABELLED_SENSOR_EXPOSURE: (
        "a histogram whose samples are display RGB must not be labelled sensor_exposure"
    ),
    UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE: (
        "domain unknown or missing while labelled sensor_exposure is rejected"
    ),
    RELABELLED_DISPLAY_HISTOGRAM: (
        "relabeling a display histogram as sensor_exposure is rejected"
    ),
    FALSE_COLOR_UNNAMED_DOMAIN: "false color must name its input domain",
    FALSE_COLOR_DOMAIN_MISMATCH: "false color input domain must agree with the scope domain",
    CLIPPING_THRESHOLD_UNDECLARED: "clipping counts require a declared threshold",
    CLAIMED_CLIP_MISMATCH: "a claimed clipping count must match the samples above the threshold",
    PREVIEW_DECLARES_SOURCE_CLIPPING: ORACLE,
    RGB8_CERTIFIES_SENSOR: "an RGB8 preview must not certify sensor clipping",
    RGB8_CERTIFIES_BIT_DEPTH: "an RGB8 preview must not certify source bit depth",
    RGB8_CERTIFIES_TEN_BIT: "preview-only RGB8 aids cannot certify ten-bit precision",
    STALE_REPORTS_SENSOR: "a stale scope must identify staleness instead of reporting sensor conditions",
    SCOPE_OWNS_CAPTURE: "scope computation must stay off critical capture ownership",
    MUTANT_TOKEN: MUTANT,
    MISSING_SCOPE_KIND: "histogram, waveform, clipping, and false color scopes are all required",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def optional_text(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def domain_name(domain: str | None) -> str:
    if domain is None:
        return "missing"
    return domain


def parse_samples(value: object, label: str) -> list[Any]:
    require(isinstance(value, (list, tuple)) and len(value) > 0, label + " must be a non-empty list")
    parsed: list[Any] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if isinstance(item, (list, tuple)):
            require(len(item) == 3, item_label + " RGB sample must have 3 channels")
            parsed.append([require_number(channel, f"{item_label}[{channel_index}]")
                           for channel_index, channel in enumerate(item)])
        else:
            parsed.append(require_number(item, item_label))
    return parsed


def sample_peak(sample: Any) -> float:
    if isinstance(sample, list):
        return max(sample)
    return float(sample)


def clipping_count(samples: object, threshold: object) -> int:
    """Count samples strictly above a declared threshold.

    RGB triples use the peak channel. A sample equal to the threshold is not
    clipped and is not counted.
    """
    parsed = samples if _parsed_samples(samples) else parse_samples(samples, "samples")
    limit = require_number(threshold, "threshold")
    return sum(1 for sample in parsed if sample_peak(sample) > limit)


def _parsed_samples(samples: object) -> bool:
    if not isinstance(samples, list) or not samples:
        return False
    for item in samples:
        if isinstance(item, list):
            if not item or any(isinstance(channel, bool) or not isinstance(channel, (int, float)) for channel in item):
                return False
        elif isinstance(item, bool) or not isinstance(item, (int, float)):
            return False
    return True


def samples_are_display_rgb(scope: dict[str, Any]) -> bool:
    if scope["sampleEncoding"] == "display_rgb":
        return True
    if scope["domain"] == "display_sdr" and all(isinstance(sample, list) for sample in scope["samples"]):
        return True
    return False


def is_preview(scope: dict[str, Any]) -> bool:
    return (
        scope["domain"] == "display_sdr"
        or scope["sampleEncoding"] == "display_rgb"
        or scope["samplingResolution"] == "rgb8"
    )


def parse_scope(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(SCOPE_KEYS), label + " keys are invalid")
    scope_id = require_text(value["id"], label + ".id")
    kind = require_text(value["kind"], label + ".kind")
    require(kind in KINDS, label + ".kind is not a scope kind")
    domain = value["domain"]
    if domain is not None:
        domain = require_text(domain, label + ".domain")
        require(domain in DOMAINS, label + ".domain is not a signal domain")
    encoding = require_text(value["sampleEncoding"], label + ".sampleEncoding")
    require(encoding in ENCODINGS, label + ".sampleEncoding is not recognized")
    scope_label = require_text(value["label"], label + ".label")
    prior = optional_text(value["priorLabel"], label + ".priorLabel")
    samples = parse_samples(value["samples"], label + ".samples")
    threshold = value["threshold"]
    if threshold is not None:
        threshold = require_number(threshold, label + ".threshold")
    input_domain = value["inputDomain"]
    if input_domain is not None:
        input_domain = require_text(input_domain, label + ".inputDomain")
        require(input_domain in DOMAINS, label + ".inputDomain is not a signal domain")
    if kind != "false_color":
        require(input_domain is None, label + ".inputDomain is only named by false color")
    resolution = require_text(value["samplingResolution"], label + ".samplingResolution")
    require(resolution in RESOLUTIONS, label + ".samplingResolution is not recognized")
    fresh = require_bool(value["fresh"], label + ".fresh")
    certifies_sensor = require_bool(value["certifiesSensorClipping"], label + ".certifiesSensorClipping")
    certifies_ten = require_bool(value["certifiesTenBit"], label + ".certifiesTenBit")
    certifies_depth = require_bool(value["certifiesSourceBitDepth"], label + ".certifiesSourceBitDepth")
    declares = require_bool(value["declaresSourceClipping"], label + ".declaresSourceClipping")
    owns = require_bool(value["ownsCapture"], label + ".ownsCapture")
    claimed = value["claimedClippingCount"]
    if claimed is not None:
        require(type(claimed) is int and claimed >= 0, label + ".claimedClippingCount must be a non-negative int or null")
    return {
        "id": scope_id,
        "kind": kind,
        "domain": domain,
        "sampleEncoding": encoding,
        "label": scope_label,
        "priorLabel": prior,
        "samples": samples,
        "threshold": threshold,
        "inputDomain": input_domain,
        "samplingResolution": resolution,
        "fresh": fresh,
        "certifiesSensorClipping": certifies_sensor,
        "certifiesTenBit": certifies_ten,
        "certifiesSourceBitDepth": certifies_depth,
        "declaresSourceClipping": declares,
        "ownsCapture": owns,
        "claimedClippingCount": claimed,
    }


def parse_scopes(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list), "scopes must be a list")
    parsed = [parse_scope(item, f"scopes[{index}]") for index, item in enumerate(value)]
    seen: set[str] = set()
    for scope in parsed:
        require(scope["id"] not in seen, "duplicate scope id " + scope["id"])
        seen.add(scope["id"])
    return parsed


def parse_source(value: object) -> dict[str, Any]:
    require(isinstance(value, dict), "source must be an object")
    require(set(value) == set(SOURCE_KEYS), "source keys are invalid")
    domain = require_text(value["domain"], "source.domain")
    require(domain in NAMED_DOMAINS, "source.domain must name display_sdr, hlg_signal, or sensor_code")
    samples = parse_samples(value["samples"], "source.samples")
    threshold = require_number(value["threshold"], "source.threshold")
    high_range = require_bool(value["highRange"], "source.highRange")
    return {
        "domain": domain,
        "samples": samples,
        "threshold": threshold,
        "highRange": high_range,
    }


def _computed_clip_count(scope: dict[str, Any]) -> int | None:
    if scope["kind"] != "clipping":
        return None
    if scope["threshold"] is None:
        return None
    return clipping_count(scope["samples"], scope["threshold"])


def scope_faults(scope: dict[str, Any]) -> list[str]:
    faults: list[str] = []
    labelled_sensor = scope["label"] == SENSOR_EXPOSURE
    display_rgb = samples_are_display_rgb(scope)
    if scope["kind"] == "histogram" and display_rgb and labelled_sensor:
        faults.append(DISPLAY_RGB_HISTOGRAM_LABELLED_SENSOR_EXPOSURE)
    if labelled_sensor and (scope["domain"] is None or scope["domain"] == "unknown"):
        faults.append(UNKNOWN_OR_MISSING_DOMAIN_SENSOR_EXPOSURE)
    prior = scope["priorLabel"]
    prior_display = isinstance(prior, str) and prior in DISPLAY_PRIOR_LABELS and prior != SENSOR_EXPOSURE
    if scope["kind"] == "histogram" and labelled_sensor and (scope["domain"] == "display_sdr" or prior_display):
        faults.append(RELABELLED_DISPLAY_HISTOGRAM)
    if scope["kind"] == "false_color":
        named = scope["inputDomain"]
        if named not in NAMED_DOMAINS:
            faults.append(FALSE_COLOR_UNNAMED_DOMAIN)
        elif scope["domain"] in NAMED_DOMAINS and named != scope["domain"]:
            faults.append(FALSE_COLOR_DOMAIN_MISMATCH)
    count = _computed_clip_count(scope)
    if scope["kind"] == "clipping" and scope["threshold"] is None:
        faults.append(CLIPPING_THRESHOLD_UNDECLARED)
    elif (
        scope["kind"] == "clipping"
        and scope["claimedClippingCount"] is not None
        and count is not None
        and scope["claimedClippingCount"] != count
    ):
        faults.append(CLAIMED_CLIP_MISMATCH)
    if scope["samplingResolution"] == "rgb8" and scope["certifiesSensorClipping"]:
        faults.append(RGB8_CERTIFIES_SENSOR)
    if scope["samplingResolution"] == "rgb8" and scope["certifiesSourceBitDepth"]:
        faults.append(RGB8_CERTIFIES_BIT_DEPTH)
    if scope["samplingResolution"] == "rgb8" and scope["certifiesTenBit"]:
        faults.append(RGB8_CERTIFIES_TEN_BIT)
    if is_preview(scope) and scope["declaresSourceClipping"]:
        faults.append(PREVIEW_DECLARES_SOURCE_CLIPPING)
    if not scope["fresh"] and (
        scope["declaresSourceClipping"]
        or scope["certifiesSensorClipping"]
        or scope["label"] == SENSOR_EXPOSURE
    ):
        faults.append(STALE_REPORTS_SENSOR)
    if scope["ownsCapture"]:
        faults.append(SCOPE_OWNS_CAPTURE)
    return faults


def public_scope(scope: dict[str, Any], count: int | None) -> dict[str, Any]:
    return {
        "id": scope["id"],
        "kind": scope["kind"],
        "domain": domain_name(scope["domain"]),
        "label": scope["label"],
        "priorLabel": scope["priorLabel"],
        "sampleEncoding": scope["sampleEncoding"],
        "samples": scope["samples"],
        "threshold": scope["threshold"],
        "inputDomain": scope["inputDomain"],
        "samplingResolution": scope["samplingResolution"],
        "fresh": scope["fresh"],
        "clippingCount": count,
        "declaresSourceClipping": scope["declaresSourceClipping"],
        "certifiesSensorClipping": scope["certifiesSensorClipping"],
        "certifiesTenBit": scope["certifiesTenBit"],
        "certifiesSourceBitDepth": scope["certifiesSourceBitDepth"],
        "ownsCapture": scope["ownsCapture"],
    }


def analyze(scopes: list[dict[str, Any]], source: dict[str, Any], apply_mutant: bool) -> dict[str, Any]:
    """Judge declared domains and retain clipping counts computed from samples."""
    faults: list[str] = []
    records: list[dict[str, Any]] = []
    preview_clips = 0
    for scope in scopes:
        faults.extend(scope_faults(scope))
        count = _computed_clip_count(scope)
        if scope["kind"] == "clipping" and count is not None and is_preview(scope):
            preview_clips += count
        records.append(public_scope(scope, count))
    present = {scope["kind"] for scope in scopes}
    for kind in REQUIRED_KINDS:
        if kind not in present:
            faults.append(MISSING_SCOPE_KIND + ":" + kind)
    preview_histograms = [scope for scope in scopes if scope["kind"] == "histogram" and is_preview(scope)]
    if preview_histograms and all(scope["label"] == SENSOR_EXPOSURE for scope in preview_histograms):
        faults.append(MUTANT_TOKEN)
    if apply_mutant:
        faults.append(MUTANT_TOKEN)
    source_count = clipping_count(source["samples"], source["threshold"])
    stale = [record["id"] for record in records if record["fresh"] is False]
    return {
        "faults": dedupe(faults),
        "records": records,
        "sourceClippingCount": source_count,
        "previewClippingCount": preview_clips,
        "sourceDomain": source["domain"],
        "highRange": source["highRange"],
        "staleScopeIds": stale,
        "scopes": scopes,
        "source": source,
    }


def public_record(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "scopes": info["records"],
        "sourceClippingCount": info["sourceClippingCount"],
        "previewClippingCount": info["previewClippingCount"],
        "sourceDomain": info["sourceDomain"],
        "highRange": info["highRange"],
        "staleScopeIds": list(info["staleScopeIds"]),
    }


def scope_reasons(info: dict[str, Any]) -> list[str]:
    high = "true" if info["highRange"] else "false"
    reasons = [
        (
            f"sourceDomain={info['sourceDomain']} sourceClippingCount={info['sourceClippingCount']} "
            f"previewClippingCount={info['previewClippingCount']} highRange={high}"
        )
    ]
    for scope in info["records"]:
        freshness = "fresh" if scope["fresh"] else "stale"
        reasons.append(
            f"scope {scope['id']} kind={scope['kind']} domain={scope['domain']} "
            f"freshness={freshness} samplingResolution={scope['samplingResolution']} "
            f"label={scope['label']}"
        )
        if scope["kind"] == "clipping":
            reasons.append(
                f"clippingCount[{scope['id']}]={scope['clippingCount']} threshold={scope['threshold']}"
            )
        if scope["kind"] == "false_color":
            reasons.append(f"inputDomain[{scope['id']}]={scope['inputDomain']}")
    if info["staleScopeIds"]:
        reasons.append("stale scopes: " + ",".join(info["staleScopeIds"]))
    reasons.append(DOMAIN_RULE)
    return reasons


def source_status_text(info: dict[str, Any]) -> str:
    state = "clipped" if info["sourceClippingCount"] else "unclipped"
    return f"{info['sourceDomain']} {state}"


def scope_by_kind(info: dict[str, Any], kind: str) -> dict[str, Any]:
    matches = [record for record in info["records"] if record["kind"] == kind]
    require(bool(matches), "missing scope kind " + kind)
    return matches[0]


def scope_by_id(info: dict[str, Any], scope_id: str) -> dict[str, Any]:
    matches = [record for record in info["records"] if record["id"] == scope_id]
    require(bool(matches), "missing scope id " + scope_id)
    return matches[0]


def make_scope(
    *,
    id: str,
    kind: str,
    domain: str | None,
    sampleEncoding: str,
    label: str,
    samples: list,
    samplingResolution: str,
    fresh: bool,
    priorLabel: str | None = None,
    threshold: float | None = None,
    inputDomain: str | None = None,
    certifiesSensorClipping: bool = False,
    certifiesTenBit: bool = False,
    certifiesSourceBitDepth: bool = False,
    declaresSourceClipping: bool = False,
    ownsCapture: bool = False,
    claimedClippingCount: int | None = None,
) -> dict[str, Any]:
    return {
        "id": id,
        "kind": kind,
        "domain": domain,
        "sampleEncoding": sampleEncoding,
        "label": label,
        "priorLabel": priorLabel,
        "samples": samples,
        "threshold": threshold,
        "inputDomain": inputDomain,
        "samplingResolution": samplingResolution,
        "fresh": fresh,
        "certifiesSensorClipping": certifiesSensorClipping,
        "certifiesTenBit": certifiesTenBit,
        "certifiesSourceBitDepth": certifiesSourceBitDepth,
        "declaresSourceClipping": declaresSourceClipping,
        "ownsCapture": ownsCapture,
        "claimedClippingCount": claimedClippingCount,
    }


def replace_scope(scopes: list[dict[str, Any]], scope_id: str, **overrides: Any) -> list[dict[str, Any]]:
    found = False
    updated: list[dict[str, Any]] = []
    for scope in scopes:
        if scope["id"] == scope_id:
            found = True
            item = dict(scope)
            item.update(overrides)
            updated.append(item)
        else:
            updated.append(dict(scope))
    require(found, "unknown scope " + scope_id)
    return updated


def fixture_scopes() -> list[dict[str, Any]]:
    return [
        make_scope(
            id="preview-histogram",
            kind="histogram",
            domain="display_sdr",
            sampleEncoding="display_rgb",
            label="display_preview",
            samples=[[16, 32, 48], [255, 250, 240], [8, 8, 8], [255, 255, 255]],
            samplingResolution="rgb8",
            fresh=True,
        ),
        make_scope(
            id="preview-clipping",
            kind="clipping",
            domain="display_sdr",
            sampleEncoding="display_rgb",
            label="display_clipping",
            samples=list(PREVIEW_CLIP_SAMPLES),
            threshold=PREVIEW_CLIP_THRESHOLD,
            claimedClippingCount=PREVIEW_CLIP_COUNT,
            samplingResolution="rgb8",
            fresh=True,
        ),
        make_scope(
            id="stale-waveform",
            kind="waveform",
            domain="display_sdr",
            sampleEncoding="display_rgb",
            label="stale_display_waveform",
            samples=[0.15, 0.42, 0.33],
            samplingResolution="rgb8",
            fresh=False,
        ),
        make_scope(
            id="preview-false-color",
            kind="false_color",
            domain="display_sdr",
            sampleEncoding="display_rgb",
            label="display_false_color",
            inputDomain="display_sdr",
            samples=[0.25, 0.5, 1.0],
            samplingResolution="rgb8",
            fresh=True,
        ),
    ]


def fixture_source() -> dict[str, Any]:
    return {
        "domain": "sensor_code",
        "samples": list(SOURCE_SAMPLES),
        "threshold": SOURCE_THRESHOLD,
        "highRange": True,
    }


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "scopes": fixture_scopes(),
        "source": fixture_source(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "decision cannot be qualified or allowed")
    require(bool(result["rejectedClaims"]) == (result["decision"] == "rejected"), "decision does not match claims")
    return result


def _reasons(info: dict[str, Any], ordered: list[str], *, include_goal: bool) -> list[str]:
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
    ]
    if include_goal:
        reasons.extend([
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
        ])
    reasons.extend(scope_reasons(info))
    for token in ordered:
        if token.startswith(MISSING_SCOPE_KIND + ":"):
            reasons.append("missing " + token.split(":", 1)[1] + " scope")
        else:
            reasons.append(FAULT_TEXT.get(token, token))
    if MUTANT_TOKEN in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        if include_goal:
            reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("scopes recorded; domains declared; not a physical qualification")
    return reasons


def judge_document(scopes: object, source: object, apply_mutant: bool) -> dict[str, Any]:
    parsed_scopes = parse_scopes(scopes)
    parsed_source = parse_source(source)
    return analyze(parsed_scopes, parsed_source, apply_mutant)


def assess(document: dict) -> dict[str, Any]:
    """Record scopes with declared domains, or reject a misleading label."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    info = judge_document(document["scopes"], document["source"], apply_mutant)
    ordered = list(info["faults"])
    reasons = _reasons(info, ordered, include_goal=True)
    preserved = [evidence, public_record(info), claim]
    return assemble(PHASE, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a scope payload, or the phase document when one is given."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "implementationBaseRevision" in payload:
        return assess(payload)
    if payload.get("decision") in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified or allowed")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    info = judge_document(payload["scopes"], payload["source"], apply_mutant)
    ordered = list(info["faults"])
    reasons = _reasons(info, ordered, include_goal=False)
    preserved = [evidence, public_record(info), claim]
    return assemble(case_id, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    info = judge_document(payload["scopes"], payload["source"], apply_mutant)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "info": info,
        "faults": list(info["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(scope_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        if token.startswith(MISSING_SCOPE_KIND + ":"):
            reasons.append("missing " + token.split(":", 1)[1] + " scope")
        else:
            reasons.append(text.get(token, token))
    if not ordered:
        reasons.append("scopes recorded; domains declared; not a physical qualification")
    preserved = [bundle["evidence"], public_record(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"
