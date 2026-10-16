"""TC-P126-02 Mutable recipe during export.

Host fixture. Output frames stay on the frozen recipe hash. Live slider values
are a different version and must not feed the running job. Clip rows still
follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

CASE_INDEX = 1
NEGATIVE_TOKEN = "live-slider-values-for-output-frames"
LEFT_TOKEN = "frame-left-frozen-recipe"
REUSE_TOKEN = "subsequent-edit-reuses-running-recipe"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frozenRecipe",
    "liveSliders",
    "frameRecipes",
    "runningRecipeId",
    "nextEditRecipeId",
    "clips",
    "omitted_ids",
)

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parent / "p126_build_a_trustworthy_clip_library.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
CASE = _CORE.CASES[CASE_INDEX]
CASE_ID = CASE["id"]
NAME = CASE["name"]
INTERVENTION = CASE["intervention"]
EXPECTED = CASE["expected"]
NEGATIVE = CASE["negative"]
REPEAT = CASE["repeat"]
RESULT_KEYS = _CORE.RESULT_KEYS


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def _recipe(value, label: str) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a non-empty object")
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError(f"{label} keys must be non-empty strings")
        if isinstance(item, str):
            if not item.strip() or item != item.strip():
                raise ValueError(f"{label}.{key} must be a non-empty string")
        elif type(item) is bool or not isinstance(item, (int, float)):
            raise ValueError(f"{label}.{key} must be a string or number")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError(f"{label}.{key} must be finite")
    return value


def recipe_sha256(recipe: dict) -> str:
    encoded = json.dumps(recipe, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _CORE.content_sha256(encoded)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frozen = _recipe(payload["frozenRecipe"], "frozenRecipe")
    live = _recipe(payload["liveSliders"], "liveSliders")
    frames = payload["frameRecipes"]
    if not isinstance(frames, list) or not frames:
        raise ValueError("frameRecipes must be a non-empty list")
    parsed = [_recipe(frame, f"frameRecipes[{index}]") for index, frame in enumerate(frames)]
    running = _text(payload["runningRecipeId"], "runningRecipeId")
    nxt = _text(payload["nextEditRecipeId"], "nextEditRecipeId")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    frozen_hash = recipe_sha256(frozen)
    live_hash = recipe_sha256(live)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append("frozenRecipeSha256=" + frozen_hash)
    rejected = list(library["rejectedClaims"])
    for index, frame in enumerate(parsed):
        frame_hash = recipe_sha256(frame)
        if frame_hash == frozen_hash:
            continue
        if frame_hash == live_hash:
            _add(rejected, NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        else:
            _add(rejected, LEFT_TOKEN)
        reasons.append(f"frame {index} left the frozen recipe")
    if nxt == running:
        _add(rejected, REUSE_TOKEN)
        reasons.append("subsequent edit reused the running recipe id")
    else:
        reasons.append("subsequent edit uses " + nxt)
    preserved = [evidence, "frozenRecipeSha256=" + frozen_hash]
    preserved.extend(library["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    return result
