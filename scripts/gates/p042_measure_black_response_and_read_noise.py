#!/usr/bin/env python3
"""P042 black response and read noise on a host fixture.

Dark frames are black-subtracted without clamping. A negative mean and a
persistent hot column stay visible. Read noise is the temporal variance of
signed residuals outside that column. Sensor-code saturation is counted
apart from any later normalization offset.

The deliberate mutant — clamping black-subtracted RAW to zero before
statistics — is rejected. This module does not probe a device, does not
qualify a physical S23, and does not execute TC-P042-01 through TC-P042-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P042"
CASE_ID = "P042"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-black-response-fixture"
METHOD = (
    "Acquire controlled dark sequences at selected exposure and gain settings. "
    "Inspect row, column, temporal, and hot-pixel structure. Preserve signed "
    "residuals after black subtraction, report uncertainty, and separate sensor "
    "code saturation from later normalization."
)
FIXTURE = (
    "Dark frames containing a small negative mean after an intentionally "
    "incorrect black subtraction and a persistent hot column."
)
ORACLE = (
    "The fit detects the bias and structured defect rather than clipping all "
    "negative samples to zero."
)
MUTANT = "Clamp black-subtracted RAW to zero before computing statistics."
SIGNED = "signed"
MUTANT_STATISTIC = "clamp-to-zero"
STATISTICS = (SIGNED, MUTANT_STATISTIC)
HOST_LIMIT = "a host estimate does not qualify a physical S23"

HEX40 = re.compile(r"^[0-9a-f]{40}$")
UINT = re.compile(r"0|[1-9][0-9]*")
POSITIVE = re.compile(r"[1-9][0-9]*")
GAIN = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?")
SIGNED_INT = re.compile(r"0|-?[1-9][0-9]*")
FRAME_ID = re.compile(r"[a-z][a-z0-9-]{0,31}")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "exposureNs",
    "gain",
    "blackLevel",
    "uncertaintyDn",
    "saturationCode",
    "normalizationOffset",
    "width",
    "frames",
}
FRAME_KEYS = {"id", "samples"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "bias_detected"}
_SAMPLE_CAP = 65535


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


def _uint(value: object, label: str, positive: bool = False) -> str:
    pattern = POSITIVE if positive else UINT
    require(isinstance(value, str) and pattern.fullmatch(value) is not None,
            label + " must be a canonical integer string")
    return value


def _signed_text(value: object, label: str) -> str:
    require(isinstance(value, str) and SIGNED_INT.fullmatch(value) is not None,
            label + " must be a canonical signed integer string")
    return value


def _gain(value: object) -> str:
    require(isinstance(value, str) and GAIN.fullmatch(value) is not None,
            "gain must be a canonical decimal string")
    return value


def _gcd(left: int, right: int) -> int:
    while right:
        left, right = right, left % right
    return abs(left)


def rational(numer: int, denom: int) -> str:
    """Reduced a/b. Denominator stays positive."""
    require(denom != 0, "rational denominator must be non-zero")
    if denom < 0:
        numer, denom = -numer, -denom
    scale = _gcd(numer, denom)
    return f"{numer // scale}/{denom // scale}"


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P042 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
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


def _frame(value: object, index: int, width: int, saturation: int, seen: set[str]) -> dict:
    item = exact_keys(value, FRAME_KEYS, f"frames[{index}]")
    ident = item["id"]
    require(isinstance(ident, str) and FRAME_ID.fullmatch(ident) is not None,
            f"frames[{index}] id must be a token")
    require(ident not in seen, "duplicate frame id: " + ident)
    seen.add(ident)
    samples = item["samples"]
    require(isinstance(samples, list) and samples, f"frames[{index}] samples must be a non-empty list")
    require(len(samples) % width == 0, f"frames[{index}] length must be a multiple of width")
    height = len(samples) // width
    require(1 <= height <= 32, f"frames[{index}] height is out of range")
    parsed: list[int] = []
    for offset, sample in enumerate(samples):
        text = _uint(sample, f"frames[{index}] samples[{offset}]")
        code = int(text)
        require(0 <= code <= _SAMPLE_CAP, f"frames[{index}] samples[{offset}] is out of range")
        parsed.append(code)
    return {"id": ident, "samples": parsed, "height": height}


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P042 dark-frame fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "dark document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P042")
    require(document["mapId"] == MAP_ID, "mapId must be s23-black-response-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and isinstance(revision, str)
            and HEX40.fullmatch(revision) is not None,
            "dark document needs the P042 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _uint(document["exposureNs"], "exposureNs", positive=True)
    _gain(document["gain"])
    _uint(document["blackLevel"], "blackLevel")
    _uint(document["uncertaintyDn"], "uncertaintyDn")
    saturation = int(_uint(document["saturationCode"], "saturationCode", positive=True))
    require(saturation <= _SAMPLE_CAP, "saturationCode is out of range")
    _signed_text(document["normalizationOffset"], "normalizationOffset")
    width = document["width"]
    require(type(width) is int and 2 <= width <= 32, "width must be an int from 2 to 32")
    frames = document["frames"]
    require(isinstance(frames, list) and 2 <= len(frames) <= 4, "frames must contain 2 to 4 items")
    seen: set[str] = set()
    heights: list[int] = []
    for index, frame in enumerate(frames):
        parsed = _frame(frame, index, width, saturation, seen)
        heights.append(parsed["height"])
    require(len(set(heights)) == 1, "frames must share one height")


def _parsed_frames(document: dict) -> list[dict]:
    width = document["width"]
    saturation = int(document["saturationCode"])
    seen: set[str] = set()
    return [_frame(frame, index, width, saturation, seen) for index, frame in enumerate(document["frames"])]


def _grids(document: dict, clamp: bool) -> list[dict[str, Any]]:
    """Black-subtracted grids. Saturated codes are None, never normalized.

    clamp True is the mutant statistic and is only exposed for the comparison
    that shows clipping hides a negative mean. assess does not publish it.
    """
    black = int(document["blackLevel"])
    saturation = int(document["saturationCode"])
    width = document["width"]
    grids: list[dict[str, Any]] = []
    for frame in _parsed_frames(document):
        residual: list[int | None] = []
        saturated = 0
        for code in frame["samples"]:
            if code >= saturation:
                residual.append(None)
                saturated += 1
                continue
            value = code - black
            if clamp and value < 0:
                value = 0
            residual.append(value)
        grids.append({
            "id": frame["id"],
            "height": frame["height"],
            "width": width,
            "residual": residual,
            "saturated": saturated,
        })
    return grids


def residual_sum(document: dict, clamp: bool = False) -> int:
    """Sum of unsaturated black-subtracted samples. clamp is the mutant."""
    validate_document(document)
    total = 0
    for grid in _grids(document, clamp):
        for value in grid["residual"]:
            if value is not None:
                total += value
    return total


def _column_totals(grid: dict) -> tuple[list[int], list[int]]:
    width = grid["width"]
    sums = [0] * width
    counts = [0] * width
    for index, value in enumerate(grid["residual"]):
        if value is None:
            continue
        column = index % width
        sums[column] += value
        counts[column] += 1
    return sums, counts


def _row_uniform(grid: dict) -> bool:
    width = grid["width"]
    sums: list[int] = []
    counts: list[int] = []
    for row in range(grid["height"]):
        total = 0
        count = 0
        for column in range(width):
            value = grid["residual"][row * width + column]
            if value is None:
                continue
            total += value
            count += 1
        sums.append(total)
        counts.append(count)
    return len(set(sums)) <= 1 and len(set(counts)) <= 1


def _mean_less(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] * right[1] < right[0] * left[1]


def _hot_columns(sums: list[int], counts: list[int], uncertainty: int) -> list[int]:
    active = [(index, sums[index], counts[index]) for index in range(len(sums)) if counts[index] > 0]
    if len(active) < 2:
        return []
    ordered: list[tuple[int, int, int]] = []
    for item in active:
        placed = False
        for offset, other in enumerate(ordered):
            if _mean_less((item[1], item[2]), (other[1], other[2])) or (
                item[1] * other[2] == other[1] * item[2] and item[0] < other[0]
            ):
                ordered.insert(offset, item)
                placed = True
                break
        if not placed:
            ordered.append(item)
    median = ordered[(len(ordered) - 1) // 2]
    hot: list[int] = []
    for index, total, count in active:
        # mean - median_mean > uncertainty
        left = total * median[2] - median[1] * count
        right = uncertainty * count * median[2]
        if left > right:
            hot.append(index)
    return hot


def _read_noise(grids: list[dict], hot: list[int]) -> tuple[int, int] | None:
    if len(grids) < 2:
        return None
    width = grids[0]["width"]
    height = grids[0]["height"]
    series: list[list[int]] = []
    for row in range(height):
        for column in range(width):
            if column in hot:
                continue
            values: list[int] = []
            saturated = False
            for grid in grids:
                value = grid["residual"][row * width + column]
                if value is None:
                    saturated = True
                    break
                values.append(value)
            if saturated:
                continue
            series.append(values)
    if not series:
        return None
    frames = len(series[0])
    numer_sum = 0
    for values in series:
        total = sum(values)
        sumsq = sum(value * value for value in values)
        numer_sum += frames * sumsq - total * total
    return numer_sum, frames * frames * len(series)


def _analyze(document: dict) -> dict[str, Any]:
    """Signed statistics. Normalization is recorded and not subtracted."""
    grids = _grids(document, clamp=False)
    uncertainty = int(document["uncertaintyDn"])
    per_frame = []
    signed_sum = 0
    sample_count = 0
    saturated = 0
    hot_sets: list[set[int]] = []
    uniform = True
    for grid in grids:
        sums, counts = _column_totals(grid)
        frame_sum = sum(sums)
        frame_count = sum(counts)
        signed_sum += frame_sum
        sample_count += frame_count
        saturated += grid["saturated"]
        hot = _hot_columns(sums, counts, uncertainty)
        hot_sets.append(set(hot))
        if not _row_uniform(grid):
            uniform = False
        per_frame.append({
            "id": grid["id"],
            "sum": frame_sum,
            "count": frame_count,
            "hot": hot,
        })
    require(sample_count > 0, "no unsaturated samples")
    persistent = set.intersection(*hot_sets) if hot_sets else set()
    persistent_list = sorted(persistent)
    intermittent = sorted(set.union(*hot_sets) - persistent) if hot_sets else []
    column_sum = [0] * grids[0]["width"]
    column_count = [0] * grids[0]["width"]
    for grid in grids:
        sums, counts = _column_totals(grid)
        for index, total in enumerate(sums):
            column_sum[index] += total
            column_count[index] += counts[index]
    noise = _read_noise(grids, persistent_list)
    hot_pixels = 0
    for grid in grids:
        width = grid["width"]
        for index, value in enumerate(grid["residual"]):
            if value is None:
                continue
            if index % width in persistent:
                hot_pixels += 1
    return {
        "frames": per_frame,
        "signed_sum": signed_sum,
        "sample_count": sample_count,
        "saturated": saturated,
        "persistent": persistent_list,
        "intermittent": intermittent,
        "uniform": uniform,
        "column_sum": column_sum,
        "column_count": column_count,
        "noise": noise,
        "hot_pixels": hot_pixels,
        "mean": rational(signed_sum, sample_count),
    }


def _preserved(document: dict, measured: dict[str, Any]) -> list[str]:
    preserved = [
        f"black-level:{document['blackLevel']}",
        f"exposure:{document['exposureNs']}ns",
        f"gain:{document['gain']}",
        f"uncertainty:{document['uncertaintyDn']}",
        f"saturation-code:{document['saturationCode']}",
        f"normalization-offset:{document['normalizationOffset']}",
    ]
    for frame in measured["frames"]:
        preserved.append(f"frame:{frame['id']}:sum={frame['sum']}:n={frame['count']}")
    preserved.append(f"signed-mean:{measured['mean']}")
    preserved.append(f"signed-sum:{measured['signed_sum']}")
    preserved.append(f"sample-count:{measured['sample_count']}")
    if measured["persistent"]:
        preserved.append("hot-column:" + ",".join(str(index) for index in measured["persistent"]))
        preserved.append(
            "temporal-persistence:" + ",".join(f"column-{index}" for index in measured["persistent"])
        )
    else:
        preserved.append("hot-column:none")
        preserved.append("temporal-persistence:none")
    preserved.append(f"hot-pixel-count:{measured['hot_pixels']}")
    preserved.append("row-structure:" + ("uniform" if measured["uniform"] else "biased"))
    if measured["noise"] is None:
        preserved.append("read-noise-variance:unavailable")
    else:
        numer, denom = measured["noise"]
        preserved.append(f"read-noise-variance:{rational(numer, denom)}")
    if measured["persistent"]:
        preserved.append(
            "read-noise-excluded:" + ",".join(f"hot-column-{index}" for index in measured["persistent"])
        )
    else:
        preserved.append("read-noise-excluded:none")
    preserved.append(f"sensor-saturation:{measured['saturated']}")
    preserved.append("normalization-applied:no")
    return preserved


def assess(document: dict, statistic: str = SIGNED) -> dict:
    """Detect signed black bias and a hot column. Never clamp to certify.

    statistic "clamp-to-zero" is the mutant. It is rejected. preservedResults
    still carry the unclamped signed mean, so a negative bias cannot disappear.
    """
    validate_document(document)
    require(statistic in STATISTICS, "statistic must be signed or clamp-to-zero")
    measured = _analyze(document)
    preserved = _preserved(document, measured)
    claims: list[str] = []
    if measured["signed_sum"] < 0:
        claims.append("negative-black-bias")
    if measured["persistent"]:
        claims.append("persistent-hot-column")
    elif measured["intermittent"]:
        claims.append("intermittent-hot-column")
    if not measured["uniform"]:
        claims.append("row-bias")

    reasons = [ORACLE, f"signed mean {measured['mean']} after black subtraction {document['blackLevel']}"]
    reasons.append(
        f"signed sum {measured['signed_sum']} over {measured['sample_count']} unsaturated samples"
    )
    if measured["persistent"]:
        parts = []
        for index in measured["persistent"]:
            parts.append(
                f"{index} mean {rational(measured['column_sum'][index], measured['column_count'][index])}"
            )
        reasons.append("persistent hot column " + ", ".join(parts))
    else:
        reasons.append("no persistent hot column")
    if measured["noise"] is None:
        reasons.append("read noise temporal variance unavailable")
    else:
        numer, denom = measured["noise"]
        reasons.append(
            f"read noise temporal variance {rational(numer, denom)} dn^2 on signed residuals"
        )
    reasons.append(
        f"uncertainty {document['uncertaintyDn']}dn does not authorize clamping negative samples"
    )
    reasons.append(
        "sensor saturation "
        f"{measured['saturated']} is separate from normalization offset {document['normalizationOffset']}"
    )
    reasons.append("row structure " + ("uniform" if measured["uniform"] else "biased"))
    reasons.append(HOST_LIMIT)

    questions = [
        "host fixture is not a physical S23 measurement",
        "denoising is not a sensor improvement",
    ]
    uncertainty = int(document["uncertaintyDn"])
    if measured["signed_sum"] < 0 and abs(measured["signed_sum"]) < uncertainty * measured["sample_count"]:
        questions.append(
            f"signed mean is inside the {document['uncertaintyDn']}dn uncertainty report and was not clipped"
        )

    if statistic == MUTANT_STATISTIC:
        decision = "rejected"
        claims.insert(0, "clamp-black-subtracted-raw")
        reasons.append(MUTANT)
        questions.append("clamped statistics were rejected")
    elif claims:
        decision = "bias_detected"
    else:
        decision = "withheld"
        questions.append("centered fixture residuals are not a physical read-noise measurement")

    return _result(decision, reasons, claims, preserved, questions)
