"""TC-P133-06 Premature success indication.

Host reference. A 100 percent banner before verification and publication is
rejected. The remaining stage is spoken by a labeled progress control.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P133-06",
    "phase": "P133",
    "workstream": 17,
    "name": "Premature success indication",
    "intervention": "Finish frame submission while verification or publication still remains incomplete.",
    "expected": "Show the actual remaining stage and withhold accepted completion until its gate passes.",
    "negative": "A one-hundred-percent banner before required verification must fail.",
    "repeat": "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
}

NEGATIVE_TOKEN = "premature-complete-banner"
STAGE_HIDDEN = "remaining-stage-hidden"
STAGE_UNSPOKEN = "remaining-stage-not-spoken"
STAGES = frozenset({
    "encoder-drain",
    "full-decode",
    "sidecar-export",
    "gallery-commit",
    "verification",
    "publication",
})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "controls",
    "focusOrder",
    "progressControlId",
    "progressBannerPercent",
    "verificationComplete",
    "publicationComplete",
    "remainingStage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p133_implement_accessible_focus_and_recipe_controls.py"
    spec = importlib.util.spec_from_file_location("p133_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    progress_id = _GATE.require_text(payload["progressControlId"], "progressControlId")
    percent = _GATE.require_number(payload["progressBannerPercent"], "progressBannerPercent")
    _GATE.require(0 <= percent <= 100, "progressBannerPercent must be from 0 through 100")
    verification = _GATE.require_bool(payload["verificationComplete"], "verificationComplete")
    publication = _GATE.require_bool(payload["publicationComplete"], "publicationComplete")
    stage = payload["remainingStage"]
    if stage is not None:
        stage = _GATE.require_text(stage, "remainingStage")
        _GATE.require(stage in STAGES, "remainingStage is not recognized")
    progress = _GATE.find_control(bundle["controls"], progress_id)
    _GATE.require(progress is not None, "progressControlId is not on the surface")
    gates_passed = verification and publication and stage is None
    spoken = progress["state_description"]
    if percent == 100 and not gates_passed:
        faults.append(NEGATIVE_TOKEN)
    if not gates_passed and _GATE.says_complete(spoken):
        faults.append(NEGATIVE_TOKEN)
    if not gates_passed and stage is None:
        faults.append(STAGE_HIDDEN)
    if stage is not None and stage not in spoken.casefold():
        faults.append(STAGE_UNSPOKEN)
    extra = [{
        "progressControlId": progress_id,
        "progressBannerPercent": percent,
        "verificationComplete": verification,
        "publicationComplete": publication,
        "remainingStage": stage,
        "spokenState": spoken,
        "gatesPassed": gates_passed,
    }]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        STAGE_HIDDEN: "the actual remaining stage must stay visible",
        STAGE_UNSPOKEN: "the remaining stage must be spoken, not only drawn",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
