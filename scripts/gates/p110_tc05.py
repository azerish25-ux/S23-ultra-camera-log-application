"""TC-P110-05 Mixed-pixel boundaries.

Host fixture. Partial coverage is kept. A dilated binary mask is not enough.
"""

from __future__ import annotations

CASE_ID = "TC-P110-05"
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask"
HALO_TOKEN = "unbounded-temporal-halo"
HALO_LIMIT = 3
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "coverage", "mask")
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


def _coverage(values) -> list[float]:
    _require(isinstance(values, list) and len(values) >= 1, "coverage must be a non-empty list")
    numbers: list[float] = []
    for index, item in enumerate(values):
        _require(isinstance(item, (int, float)) and not isinstance(item, bool), f"coverage[{index}] must be a number")
        number = float(item)
        _require(0.0 <= number <= 1.0, f"coverage[{index}] must be inside [0, 1]")
        numbers.append(number)
    return numbers


def dilated_binary(coverage: list[float]) -> list[float]:
    binary = [1.0 if value >= 0.5 else 0.0 for value in coverage]
    dilated = binary[:]
    count = len(binary)
    for index, value in enumerate(binary):
        if value != 1.0:
            continue
        if index - 1 >= 0:
            dilated[index - 1] = 1.0
        if index + 1 < count:
            dilated[index + 1] = 1.0
    return dilated


def destroys_partial_coverage(coverage: list[float], produced: list[float]) -> bool:
    for original, output in zip(coverage, produced):
        if 0.0 < original < 1.0 and output in (0.0, 1.0):
            return True
        if original == 0.0 and output == 1.0:
            return True
    return False


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    coverage = _coverage(payload["coverage"])
    mask = payload["mask"]
    _require(mask in {"partial", "dilated-binary"}, "mask must be partial or dilated-binary")
    fractional = sum(1 for value in coverage if 0.0 < value < 1.0)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    rejected: list[str] = []
    if mask == "dilated-binary":
        produced = dilated_binary(coverage)
        if destroys_partial_coverage(coverage, produced) or produced != coverage:
            decision = "rejected"
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append("dilated binary mask flattened partial coverage or grew into neighbouring pixels")
        else:
            decision = "rejected"
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append("a binary person mask has no partial-coverage model")
    elif fractional > HALO_LIMIT:
        decision = "rejected"
        rejected.append(HALO_TOKEN)
        reasons.append(f"temporal halo has {fractional} partial pixels; limit is {HALO_LIMIT}")
    else:
        decision = "recorded"
        reasons.append(f"partial coverage preserved; fractional halo count {fractional} is within {HALO_LIMIT}")
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": [evidence],
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
