"""TC-P109-05 Mixed-pixel boundaries.

Host fixture. Partial coverage stays an unknown band. A dilated binary person
mask does not pass. A negative control must not come back as qualified or allowed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P109-05"
NAME = "Mixed-pixel boundaries"
INTERVENTION = "Use moving hair, glasses, smoke, or motion-blurred edges against detailed backgrounds."
EXPECTED = "Preserve plausible partial coverage and bound temporal halos under the selected safe settings."
NEGATIVE = "A dilated binary person mask must not pass demanding boundary quality by itself."
REPEAT = "Repeat backlighting, crossing subjects, and different foreground-background contrast."
NEGATIVE_TOKEN = "dilated-binary-person-mask"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "hair_threshold",
    "band",
    "minimum_unknown_coverage",
    "inpaint_glass",
    "foreground_colour",
    "samples",
    "dilatedBinaryPersonMask",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p109_refine_hair_and_transparent_boundaries",
    Path(__file__).resolve().parent / "p109_refine_hair_and_transparent_boundaries.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    _require(type(payload["dilatedBinaryPersonMask"]) is bool, "dilatedBinaryPersonMask must be a bool")
    document = {
        "schemaVersion": 1,
        "phase": _GATE.PHASE,
        "implementationBaseRevision": _GATE.BASE_REVISION,
        "evidenceId": evidence,
        "claim": "tc-p109-05",
        "hair_threshold": payload["hair_threshold"],
        "band": payload["band"],
        "minimum_unknown_coverage": payload["minimum_unknown_coverage"],
        "inpaint_glass": payload["inpaint_glass"],
        "foreground_colour": payload["foreground_colour"],
        "samples": payload["samples"],
        "applyMutant": False,
    }
    parsed = _GATE.validate_document(document)
    claims, details, seeds, unknown, coverage = _GATE.boundary_findings(parsed)
    if payload["dilatedBinaryPersonMask"]:
        claims = [NEGATIVE_TOKEN, *claims]
        details = [NEGATIVE, *details]
    decision = "rejected" if claims else "recorded"
    _require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    _require(decision not in {"qualified", "allowed"}, "negative or unmeasured result must not be qualified")
    band_text = ",".join(str(index) for index in unknown) if unknown else "none"
    seed_text = ",".join(str(index) for index in seeds) if seeds else "none"
    reasons = [
        f"{CASE_ID} {NAME} repeat {repeat}",
        EXPECTED,
        "band rule: " + _GATE.BAND_RULE,
        f"seeds {seed_text}",
        f"unknown-band {band_text}",
        f"unknown-coverage {coverage:.6f}",
    ]
    if decision == "rejected":
        reasons.extend(details)
        reasons.append(NEGATIVE)
    else:
        reasons.append("narrower software result retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": claims,
        "preservedResults": [evidence],
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    _require(tuple(result) == RESULT_KEYS, "result keys drifted")
    _require(evidence in result["preservedResults"], "evidence wiped")
    return result
