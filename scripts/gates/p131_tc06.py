"""TC-P131-06 Premature success indication.

Host reference. A 100 percent banner before verification and publication is
rejected. The remaining stage stays visible. Completion is never qualified.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P131-06",
    "phase": "P131",
    "workstream": 17,
    "name": "Premature success indication",
    "intervention": "Finish frame submission while verification or publication still remains incomplete.",
    "expected": "Show the actual remaining stage and withhold accepted completion until its gate passes.",
    "negative": "A one-hundred-percent banner before required verification must fail.",
    "repeat": "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
}

NEGATIVE_TOKEN = "premature-complete-banner"
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
    "committed",
    "proposed",
    "progressBannerPercent",
    "verificationComplete",
    "publicationComplete",
    "remainingStage",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p131_design_manual_controls_for_deliberate_operation.py"
    spec = importlib.util.spec_from_file_location("p131_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    percent = _GATE.require_number(payload["progressBannerPercent"], "progressBannerPercent")
    _GATE.require(0 <= percent <= 100, "progressBannerPercent must be from 0 through 100")
    verification = _GATE.require_bool(payload["verificationComplete"], "verificationComplete")
    publication = _GATE.require_bool(payload["publicationComplete"], "publicationComplete")
    stage = payload["remainingStage"]
    if stage is not None:
        stage = _GATE.require_text(stage, "remainingStage")
        _GATE.require(stage in STAGES, "remainingStage is not recognized")
    gates_passed = verification and publication and stage is None
    if percent == 100 and not gates_passed:
        faults.append(NEGATIVE_TOKEN)
    stage_token = "remainingStage=" + (stage if stage is not None else "none")
    extra = [
        stage_token,
        {
            "progressBannerPercent": percent,
            "verificationComplete": verification,
            "publicationComplete": publication,
            "remainingStage": stage,
            "applied": bundle["info"]["surviving"],
        },
    ]
    return _GATE.finish_case(CASE, bundle, faults, extra, {NEGATIVE_TOKEN: CASE["negative"]})
