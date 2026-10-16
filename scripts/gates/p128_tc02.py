"""TC-P128-02 Mutable recipe during export.

Host fixture. Output frames stay on the frozen recipe. A later edit creates a
new version. Reading the live slider for a frame fails. The long-form account
still has to be exact.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_INDEX = 1
NEGATIVE_TOKEN = "live-slider-read-for-output-frame"
MUTATION_TOKEN = "running-job-recipe-mutated"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "frozenRecipeId",
    "frameRecipeIds",
    "frozenSliderValue",
    "liveSliderValue",
    "frameBoundValues",
    "editAfterStart",
    "subsequentRecipeId",
    "expected_frames",
    "accounted_frames",
    "checkpoint_frames",
    "audio_duration",
    "video_duration",
    "audio_absent",
    "spot_check_only",
)

_SPEC = importlib.util.spec_from_file_location(
    "p128_validate_long_form_development_end_to_end",
    Path(__file__).resolve().parent / "p128_validate_long_form_development_end_to_end.py",
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


def _number(value, label: str) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{label} must be finite")
    return number


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=0.0, abs_tol=1e-12)


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    frozen_recipe = _text(payload["frozenRecipeId"], "frozenRecipeId")
    subsequent = _text(payload["subsequentRecipeId"], "subsequentRecipeId")
    if type(payload["editAfterStart"]) is not bool:
        raise ValueError("editAfterStart must be a bool")
    edit_after_start = payload["editAfterStart"]
    if not isinstance(payload["frameRecipeIds"], list) or not isinstance(payload["frameBoundValues"], list):
        raise ValueError("frame recipe lists must be lists")
    frozen_slider = _number(payload["frozenSliderValue"], "frozenSliderValue")
    live_slider = _number(payload["liveSliderValue"], "liveSliderValue")
    frame_recipes = [_text(item, "frameRecipeIds") for item in payload["frameRecipeIds"]]
    frame_bounds = [
        _number(item, f"frameBoundValues[{index}]")
        for index, item in enumerate(payload["frameBoundValues"])
    ]
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    expected = payload["expected_frames"]
    if len(frame_recipes) != expected or len(frame_bounds) != expected:
        raise ValueError("frame recipe lists must cover expected_frames")
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"frozenRecipeId={frozen_recipe}")
    reasons.append("frozenSlider=" + format(frozen_slider, ".12g"))
    reasons.append("liveSlider=" + format(live_slider, ".12g"))
    rejected = list(account["rejectedClaims"])
    live_read = False
    for index, (recipe_id, bound) in enumerate(zip(frame_recipes, frame_bounds)):
        if recipe_id != frozen_recipe or not _close(bound, frozen_slider):
            live_read = True
            reasons.append(f"frame {index} left the frozen recipe")
            if _close(bound, live_slider) and not _close(live_slider, frozen_slider):
                reasons.append(f"frame {index} read the live slider")
    if live_read:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    else:
        reasons.append("every output frame stayed on the frozen recipe")
    if edit_after_start:
        if subsequent == frozen_recipe:
            _add(rejected, MUTATION_TOKEN)
            reasons.append("subsequent edit mutated the running recipe instead of creating a new version")
        else:
            reasons.append("subsequent edit created a new version; running job stays on the frozen recipe")
    elif subsequent != frozen_recipe:
        _add(rejected, MUTATION_TOKEN)
        reasons.append("running job recipe changed without a new version")
    else:
        reasons.append("running job remains bound to the frozen recipe")
    preserved = [evidence, f"frozenRecipeId={frozen_recipe}"]
    preserved.extend(account["preservedResults"])
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
