"""TC-P112-05 Mixed-pixel boundaries.

Host fixture. A dilated binary person mask cannot pass boundary quality by
itself. Partial coverage still has to keep temporal halo inside the limit.
This is not an applyNegative stub.
"""

from __future__ import annotations

import math

CASE_ID = "TC-P112-05"
PHASE = "P112"
WORKSTREAM = 14
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask"
HALO_TOKEN = "temporal-halo-exceeds-safe-limit"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = {"evidenceId", "repeat", "samples", "halo", "halo_limit"}
SAMPLE_KEYS = {"coverage", "source"}
SOURCES = {"partial", "dilated-binary"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _number(value: object, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), label + " must be a number")
    number = float(value)
    _require(math.isfinite(number), label + " must be finite")
    if minimum is not None:
        _require(number >= minimum, label + " must be >= " + str(minimum))
    if maximum is not None:
        _require(number <= maximum, label + " must be <= " + str(maximum))
    return number


def _text(value: object, label: str) -> str:
    _require(isinstance(value, str) and value.strip() and value == value.strip(),
             label + " must be a non-empty string")
    return value


def _samples(value: object) -> list[dict]:
    _require(isinstance(value, list) and value, "samples must be a non-empty list")
    parsed: list[dict] = []
    for index, sample in enumerate(value):
        _require(isinstance(sample, dict), f"sample {index} must be an object")
        missing = SAMPLE_KEYS - set(sample)
        extra = set(sample) - SAMPLE_KEYS
        _require(not missing, f"sample {index} missing fields: " + ", ".join(sorted(missing)))
        _require(not extra, f"sample {index} has unexpected fields: " + ", ".join(sorted(extra)))
        coverage = _number(sample["coverage"], f"sample {index} coverage", minimum=0.0, maximum=1.0)
        source = sample["source"]
        _require(isinstance(source, str) and source in SOURCES, f"sample {index} source is not known")
        if source == "dilated-binary":
            _require(coverage in (0.0, 1.0), f"sample {index} dilated-binary coverage must be 0 or 1")
        parsed.append({"coverage": coverage, "source": source})
    return parsed


def evaluate(payload: dict) -> dict:
    """Reject a binary mask presented as boundary quality. Bound halo when coverage is partial."""
    _require(isinstance(payload, dict) and set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    samples = _samples(payload["samples"])
    halo = _number(payload["halo"], "halo", minimum=0.0)
    halo_limit = _number(payload["halo_limit"], "halo_limit", minimum=0.0)
    partial = [index for index, sample in enumerate(samples) if 0.0 < sample["coverage"] < 1.0]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if not partial:
        decision = "rejected"
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
        reasons.append("no partial coverage; a binary mask cannot pass boundary quality by itself")
    elif halo > halo_limit:
        decision = "rejected"
        rejected.append(HALO_TOKEN)
        reasons.append("temporal halo exceeds the selected safe limit")
    else:
        decision = "recorded"
        reasons.append("partial coverage preserved and temporal halo stayed inside the safe limit")
    preserved = [
        evidence,
        f"halo={halo}",
        f"halo_limit={halo_limit}",
        f"partial_count={len(partial)}",
    ]
    preserved.extend(f"sample:{index}:coverage={sample['coverage']}:source={sample['source']}"
                     for index, sample in enumerate(samples))
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(decision in {"recorded", "rejected"} and decision not in {"qualified", "allowed"},
             "decision must be recorded or rejected")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
