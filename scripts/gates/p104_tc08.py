"""TC-P104-08 Integrated load and thermal drift.

total_ms = capture_ms + inference_ms + render_ms + encode_ms.
The frame interval is 1000/fps. Standalone inference_ms is not a camera fps.
Severe thermal or memory forces deferred_only. Dropped frames stay visible.
"""

from __future__ import annotations

import math
from decimal import Decimal


CASE_ID = "TC-P104-08"
NAME = "Integrated load and thermal drift"
INTERVENTION = "Run inference alongside actual capture, rendering, and encoding for a sustained interval."
EXPECTED = "Measure complete workload behavior and choose live or deferred operation from evidence."
NEGATIVE = "Standalone model latency must not become a full-camera frame-rate guarantee."
REPEAT = "Repeat cold start, warm operation, memory pressure, and severe thermal conditions."
NEGATIVE_TOKEN = "standalone-model-latency-as-camera-frame-rate"
OPEN_QUESTION = "physical S23 measurement was not run"
CONDITIONS = ("cold", "warm", "memory-pressure", "severe-thermal")
THERMALS = ("nominal", "warm", "severe")
MEMORIES = ("nominal", "pressure", "severe")
LIVE_DEPTHS = ("live", "deferred_only", "lower_cost_preview")
SOURCES = ("integrated", "inference")
PAYLOAD_KEYS = (
    "evidenceId",
    "condition",
    "fps",
    "capture_ms",
    "inference_ms",
    "render_ms",
    "encode_ms",
    "dropped_frames",
    "hide_dropped_frames",
    "live_depth",
    "frame_rate_source",
    "thermal",
    "memory",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def integrated_total_ms(capture_ms: object, inference_ms: object, render_ms: object, encode_ms: object) -> Decimal:
    """capture_ms + inference_ms + render_ms + encode_ms."""
    return (
        _non_negative(capture_ms, "capture_ms")
        + _non_negative(inference_ms, "inference_ms")
        + _non_negative(render_ms, "render_ms")
        + _non_negative(encode_ms, "encode_ms")
    )


def frame_interval_ms(fps: object) -> Decimal:
    """1000/fps."""
    return Decimal(1000) / _positive(fps, "fps")


def evaluate(payload: dict) -> dict:
    fields = _payload(payload)
    total = integrated_total_ms(fields["capture_ms"], fields["inference_ms"], fields["render_ms"], fields["encode_ms"])
    interval = frame_interval_ms(fields["fps"])
    over = total > interval
    fraction = Decimal(1 if over else 0)
    severe = fields["thermal"] == "severe" or fields["memory"] == "severe" or fields["condition"] == "severe-thermal"
    rejected: list[str] = []
    if fields["frame_rate_source"] == "inference":
        rejected.append(NEGATIVE_TOKEN)
    if severe and fields["live_depth"] == "live":
        rejected.append("live-under-severe")
    elif severe and fields["live_depth"] != "deferred_only":
        rejected.append("severe-requires-deferred-only")
    if fields["live_depth"] == "live" and over:
        rejected.append("live-despite-integrated-over-budget")
    if fields["live_depth"] == "live" and fields["dropped_frames"] > 0:
        rejected.append("live-while-dropping-source-frames")
    if fields["hide_dropped_frames"]:
        rejected.append("hidden-dropped-frames")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    reasons.append(
        "total_ms = capture_ms + inference_ms + render_ms + encode_ms = "
        f"{canonical(total)}; interval = 1000/{canonical(_positive(fields['fps'], 'fps'))} = {canonical(interval)}; "
        f"over-budget fraction = {canonical(fraction)}"
    )
    if NEGATIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
        reasons.append(f"inference_ms {canonical(_non_negative(fields['inference_ms'], 'inference_ms'))} was not a camera fps")
    if "live-under-severe" in rejected:
        reasons.append("severe thermal or memory cannot stay live")
    if not rejected:
        reasons.append(f"{fields['condition']} policy {fields['live_depth']} follows the integrated budget")
    preserved = [
        fields["evidenceId"],
        f"condition:{fields['condition']}",
        f"total-ms:{canonical(total)}",
        f"inference-ms:{canonical(_non_negative(fields['inference_ms'], 'inference_ms'))}",
        f"capture-ms:{canonical(_non_negative(fields['capture_ms'], 'capture_ms'))}",
        f"render-ms:{canonical(_non_negative(fields['render_ms'], 'render_ms'))}",
        f"encode-ms:{canonical(_non_negative(fields['encode_ms'], 'encode_ms'))}",
        f"frame-interval:1000/{canonical(_positive(fields['fps'], 'fps'))}",
        f"over-budget:{str(over).lower()}",
        f"over-budget-fraction:{canonical(fraction)}",
        f"dropped-frames:{fields['dropped_frames']}",
        f"hide-dropped-frames:{str(fields['hide_dropped_frames']).lower()}",
        f"live-depth:{fields['live_depth']}",
        f"frame-rate-source:{fields['frame_rate_source']}",
        f"thermal:{fields['thermal']}",
        f"memory:{fields['memory']}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, fields["evidenceId"])


def canonical(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _non_negative(value: object, label: str) -> Decimal:
    number = _number(value, label)
    if number < 0:
        raise ValueError(label + " must be >= 0")
    return number


def _positive(value: object, label: str) -> Decimal:
    number = _number(value, label)
    if number <= 0:
        raise ValueError(label + " must be > 0")
    return number


def _number(value: object, label: str) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a number")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(label + " must be finite")
    return Decimal(value) if isinstance(value, int) else Decimal(str(value))


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    condition = payload["condition"]
    if condition not in CONDITIONS:
        raise ValueError("condition is unsupported")
    thermal = payload["thermal"]
    memory = payload["memory"]
    live = payload["live_depth"]
    source = payload["frame_rate_source"]
    if thermal not in THERMALS:
        raise ValueError("thermal is unsupported")
    if memory not in MEMORIES:
        raise ValueError("memory is unsupported")
    if live not in LIVE_DEPTHS:
        raise ValueError("live_depth is unsupported")
    if source not in SOURCES:
        raise ValueError("frame_rate_source is unsupported")
    if condition == "severe-thermal" and thermal != "severe":
        raise ValueError("severe-thermal condition requires thermal severe")
    if condition == "memory-pressure" and memory not in {"pressure", "severe"}:
        raise ValueError("memory-pressure condition requires memory pressure or severe")
    dropped = payload["dropped_frames"]
    if type(dropped) is not int or dropped < 0:
        raise ValueError("dropped_frames must be a non-negative int")
    hide = payload["hide_dropped_frames"]
    if type(hide) is not bool:
        raise ValueError("hide_dropped_frames must be a bool")
    _positive(payload["fps"], "fps")
    integrated_total_ms(payload["capture_ms"], payload["inference_ms"], payload["render_ms"], payload["encode_ms"])
    return payload


def _finish(decision: str, reasons: list[str], rejected: list[str], preserved: list[str], evidence: str) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    if not any(item.startswith("dropped-frames:") for item in result["preservedResults"]):
        raise ValueError("dropped frames were hidden")
    return result
