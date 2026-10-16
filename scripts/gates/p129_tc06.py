"""TC-P129-06 Premature success indication.

Host fixture. The remaining stage stays honest until verification and
publication both pass. A one-hundred-percent banner before that gate is rejected.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path


CASE_ID = "TC-P129-06"
NAME = "Premature success indication"
INTERVENTION = "Finish frame submission while verification or publication still remains incomplete."
EXPECTED = "Show the actual remaining stage and withhold accepted completion until its gate passes."
NEGATIVE = "A one-hundred-percent banner before required verification must fail."
REPEAT = "Repeat encoder drain, full decode, sidecar export, and gallery commit."
NEGATIVE_TOKEN = "hundred-percent-banner-before-verification"
PREMATURE_ACCEPTED = "premature-accepted-completion"
STAGES = frozenset({"encoder-drain", "full-decode", "sidecar-export", "gallery-commit", "accepted"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "bannerPercent",
    "verificationComplete",
    "publicationComplete",
    "remainingStage",
    "capture",
    "monitoring",
    "processing",
    "warnings",
    "record_in_scroll_only",
    "warnings_visible",
)

_SPEC = importlib.util.spec_from_file_location(
    "p129_define_the_camera_screen_information_hierarchy",
    Path(__file__).resolve().parent / "p129_define_the_camera_screen_information_hierarchy.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _percent(value: object) -> float:
    if type(value) is bool or not isinstance(value, (int, float)):
        raise ValueError("bannerPercent must be a number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0 or number > 100.0:
        raise ValueError("bannerPercent must lie in 0..100")
    return number


def _hundred(value: float) -> bool:
    return math.isclose(value, 100.0, rel_tol=0.0, abs_tol=1e-9)


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    banner = _percent(payload["bannerPercent"])
    verification = _bool(payload["verificationComplete"], "verificationComplete")
    publication = _bool(payload["publicationComplete"], "publicationComplete")
    stage = _text(payload["remainingStage"], "remainingStage")
    if stage not in STAGES:
        raise ValueError("remainingStage is unsupported")
    judged = _CORE.judge_hierarchy(
        payload["capture"],
        payload["monitoring"],
        payload["processing"],
        payload["warnings"],
        payload["record_in_scroll_only"],
        payload["warnings_visible"],
    )
    rejected = list(judged["rejectedClaims"])
    gates_passed = verification and publication
    reasons = [
        f"{CASE_ID} {NAME}",
        EXPECTED,
        INTERVENTION,
        f"repeat {repeat}",
        f"bannerPercent={format(banner, '.12g')}",
        f"remainingStage={stage}",
        f"verificationComplete={str(verification).lower()}",
        f"publicationComplete={str(publication).lower()}",
    ]
    reasons.extend(judged["reasons"])
    if _hundred(banner) and not gates_passed:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if stage == "accepted" and not gates_passed:
        _add(rejected, PREMATURE_ACCEPTED)
        reasons.append("accepted completion is withheld until verification and publication pass")
    if gates_passed and stage != "accepted":
        _add(rejected, "remaining-stage-not-accepted")
        reasons.append("gates passed but the remaining stage is not accepted")
    if not rejected:
        reasons.append("remaining stage matches the unfinished or accepted gate")
    decision = "rejected" if rejected else "recorded"
    preserved = [
        evidence,
        f"bannerPercent={format(banner, '.12g')}",
        f"remainingStage={stage}",
    ]
    preserved.extend(judged["preservedResults"])
    questions = [_CORE.PHYSICAL_NOTE, REPEAT]
    return _CORE.seal_result(CASE_ID, decision, reasons, rejected, preserved, questions, evidence)
