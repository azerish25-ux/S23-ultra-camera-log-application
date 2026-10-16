"""TC-P110-07 Bokeh ordering and leakage.

Host fixture. Depth-ordered blur is recorded. Uniform background blur is not.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_render_depth_ordered_foreground_and_background_blur",
    Path(__file__).resolve().parent / "p110_render_depth_ordered_foreground_and_background_blur.py",
)
_MAIN = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MAIN)

CASE_ID = "TC-P110-07"
NAME = "Bokeh ordering and leakage"
INTERVENTION = "Render strong foreground defocus with bright lights behind an in-focus opaque subject."
EXPECTED = "Respect layering and normalized energy while declaring unavoidable missing-background approximations."
NEGATIVE = "Uniform background blur with no foreground coverage model must fail."
REPEAT = "Repeat perfect-depth and estimated-depth inputs to isolate the faulty subsystem."
NEGATIVE_TOKEN = "uniform-background-blur-without-foreground-coverage"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = ("evidenceId", "repeat", "focus", "samples", "label")
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    _require(isinstance(evidence, str) and evidence.strip() and evidence == evidence.strip(),
             "evidenceId must be a non-empty string")
    _require(isinstance(repeat, str) and repeat.strip(), "repeat must be a non-empty string")
    label = payload["label"]
    _require(label in _MAIN.LABELS, "label is invalid")
    document = {
        "schemaVersion": 1,
        "phase": _MAIN.PHASE,
        "implementationBaseRevision": _MAIN.BASE_REVISION,
        "evidenceId": evidence,
        "focus": payload["focus"],
        "samples": payload["samples"],
        "claim": "occlusion-aware-bokeh",
        "label": label,
    }
    assessed = _MAIN.assess(document)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, *assessed["reasons"]]
    rejected = list(assessed["rejectedClaims"])
    if label == "uniform-background" and NEGATIVE_TOKEN not in rejected:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    decision = assessed["decision"]
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
