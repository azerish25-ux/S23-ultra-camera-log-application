"""TC-P134-06 Premature success indication.

Host reference. A one-hundred-percent banner before required verification is
rejected. The remaining stage stays visible. Fraction 1.0 still requires
drain_complete and every frame accounted, and completion waits for publication.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE = {
    "id": "TC-P134-06",
    "phase": "P134",
    "workstream": 17,
    "name": "Premature success indication",
    "intervention": "Finish frame submission while verification or publication still remains incomplete.",
    "expected": "Show the actual remaining stage and withhold accepted completion until its gate passes.",
    "negative": "A one-hundred-percent banner before required verification must fail.",
    "repeat": "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
}

NEGATIVE_TOKEN = "premature-complete-banner"
REMAINING_HIDDEN = "remaining-stage-hidden"
STAGES = frozenset({"encoder-drain", "full-decode", "sidecar-export", "gallery-commit"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "progress",
    "remainingStage",
    "sidecarExported",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p134_design_transparent_progress_and_failure_states.py"
    spec = importlib.util.spec_from_file_location("p134_gate_for_tc06", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def expected_remaining(progress: dict, info: dict, sidecar: bool) -> str | None:
    if not info["allows_one"]:
        return "encoder-drain"
    if not progress["verification_complete"]:
        return "full-decode"
    if not sidecar:
        return "sidecar-export"
    if not progress["publication_complete"]:
        return "gallery-commit"
    return None


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    progress = bundle["progress"]
    info = bundle["info"]
    sidecar = _GATE.require_bool(payload["sidecarExported"], "sidecarExported")
    stage = payload["remainingStage"]
    if stage is not None:
        stage = _GATE.require_text(stage, "remainingStage")
        _GATE.require(stage in STAGES, "remainingStage is not recognized")
    expected = expected_remaining(progress, info, sidecar)
    if stage != expected:
        faults.append(REMAINING_HIDDEN)
    displayed = progress["displayed_percent"]
    if _GATE.is_hundred(displayed) and not progress["verification_complete"]:
        faults.append(NEGATIVE_TOKEN)
    if progress["publication_complete"] and not sidecar:
        faults.append(REMAINING_HIDDEN)
    stage_token = "remainingStage=" + (stage if stage is not None else "none")
    extra = [
        stage_token,
        {
            "remainingStage": stage,
            "expectedRemaining": expected,
            "sidecarExported": sidecar,
            "displayed_percent": displayed,
        },
    ]
    texts = {
        NEGATIVE_TOKEN: CASE["negative"],
        REMAINING_HIDDEN: "show the actual remaining stage until acceptance and publication pass",
    }
    return _GATE.finish_case(CASE, bundle, faults, extra, texts)
