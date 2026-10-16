"""TC-P126-05 Temporary storage exhaustion.

Host fixture. The budget is source plus proxy, temporary, finalization, and
publication bytes, not the final output alone. Shortage pauses before source
loss. Clip rows still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_INDEX = 4
NEGATIVE_TOKEN = "budget-only-final-output-bytes"
SHORT_TOKEN = "budget-below-required"
LOST_TOKEN = "source-lost-on-exhaustion"
DROPPED_TOKEN = "source-not-retained"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "sourceBytes",
    "proxyBytes",
    "temporaryBytes",
    "finalizationBytes",
    "publicationBytes",
    "finalOutputBytes",
    "remainingBytes",
    "reserveBytes",
    "budgetBytes",
    "sourceRetained",
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


def _bytes(value, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative int")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def required_bytes(source: int, proxy: int, temporary: int, finalization: int, publication: int) -> int:
    """Separate source, proxy, temporary, finalization, and publication requirements."""
    return source + proxy + temporary + finalization + publication


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    source = _bytes(payload["sourceBytes"], "sourceBytes")
    proxy = _bytes(payload["proxyBytes"], "proxyBytes")
    temporary = _bytes(payload["temporaryBytes"], "temporaryBytes")
    finalization = _bytes(payload["finalizationBytes"], "finalizationBytes")
    publication = _bytes(payload["publicationBytes"], "publicationBytes")
    final_output = _bytes(payload["finalOutputBytes"], "finalOutputBytes")
    remaining = _bytes(payload["remainingBytes"], "remainingBytes")
    reserve = _bytes(payload["reserveBytes"], "reserveBytes")
    budget = _bytes(payload["budgetBytes"], "budgetBytes")
    if type(payload["sourceRetained"]) is not bool:
        raise ValueError("sourceRetained must be a bool")
    retained = payload["sourceRetained"]
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    required = required_bytes(source, proxy, temporary, finalization, publication)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    reasons.append(f"requiredBytes={required}")
    reasons.append(f"finalOutputBytes={final_output}")
    rejected = list(library["rejectedClaims"])
    if budget == final_output and required != final_output:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif budget < required:
        _add(rejected, SHORT_TOKEN)
        reasons.append("budget is below source plus intermediate and publication bytes")
    if remaining < required + reserve:
        if retained:
            reasons.append("paused-before-source-loss")
        else:
            _add(rejected, LOST_TOKEN)
            reasons.append("source bytes were not retained")
    elif retained:
        reasons.append("source-retained")
    else:
        _add(rejected, DROPPED_TOKEN)
        reasons.append("source bytes were not retained")
    preserved = [evidence, f"requiredBytes={required}"]
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
