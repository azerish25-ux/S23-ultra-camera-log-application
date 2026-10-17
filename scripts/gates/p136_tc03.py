"""TC-P136-03 Invalid control draft.

Host fixture. An incomplete or out-of-range draft stays unapplied. Partially
typed input that reaches the camera is rejected. The committed value is kept.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_run_usability_acceptance_on_the_physical_phone",
    Path(__file__).resolve().parent / "p136_run_usability_acceptance_on_the_physical_phone.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE = {
    "id": "TC-P136-03",
    "phase": "P136",
    "workstream": 17,
    "name": "Invalid control draft",
    "intervention": "Enter an incomplete or out-of-range numeric value and interrupt editing before Apply.",
    "expected": "Preserve committed settings and keep the draft visibly unapplied or invalid.",
    "negative": "Partially typed input reaching the camera must fail.",
    "repeat": "Repeat shutter, ISO, focus distance, ROI coordinates, and output dimensions.",
}
NEGATIVE_TOKEN = "partial-input-reached-camera"
DRAFT_HIDDEN = "invalid-draft-hidden"
CONTROLS = frozenset({"shutter", "iso", "focus-distance", "roi", "output-dimension"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "control",
    "committed",
    "draft",
    "minimum",
    "maximum",
    "interruptedBeforeApply",
    "reachedCamera",
    "draftVisible",
}


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    control = _GATE.require_text(payload["control"], "control")
    _GATE.require(control in CONTROLS, "control is not recognized")
    committed = _GATE.require_number(payload["committed"], "committed")
    draft = payload["draft"]
    _GATE.require(isinstance(draft, str), "draft must be a string")
    minimum = _GATE.require_number(payload["minimum"], "minimum")
    maximum = _GATE.require_number(payload["maximum"], "maximum")
    _GATE.require(minimum < maximum, "minimum must be less than maximum")
    interrupted = _GATE.require_bool(payload["interruptedBeforeApply"], "interruptedBeforeApply")
    reached = _GATE.require_bool(payload["reachedCamera"], "reachedCamera")
    visible = _GATE.require_bool(payload["draftVisible"], "draftVisible")
    parsed, kind = _GATE.parse_draft_number(draft)
    in_range = parsed is not None and minimum <= parsed <= maximum
    if kind == "complete" and not in_range:
        kind = "out-of-range"
    bad = kind != "complete"
    faults = []
    if (bad or interrupted) and reached:
        faults.append(NEGATIVE_TOKEN)
    if bad and not visible:
        faults.append(DRAFT_HIDDEN)
    reasons = [
        f"control={control} committed={committed} draft={draft!r} kind={kind}",
        f"interruptedBeforeApply={str(interrupted).lower()} reachedCamera={str(reached).lower()} draftVisible={str(visible).lower()}",
    ]
    preserved = [{
        "control": control,
        "committed": committed,
        "draft": draft,
        "draftKind": kind,
        "parsed": parsed,
        "inRange": in_range,
        "appliedValue": committed,
        "reachedCamera": reached,
        "draftVisible": visible,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {NEGATIVE_TOKEN: CASE["negative"], DRAFT_HIDDEN: CASE["expected"]},
        {
            NEGATIVE_TOKEN: "Do not send a partial or out-of-range draft to the camera.",
            DRAFT_HIDDEN: "Keep an invalid draft visible and unapplied.",
        },
    )
