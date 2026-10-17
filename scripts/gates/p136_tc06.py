"""TC-P136-06 Premature success indication.

Host fixture. The remaining stage stays visible. A one-hundred-percent banner
before required verification is rejected. Accepted completion waits for the gate.
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
    "id": "TC-P136-06",
    "phase": "P136",
    "workstream": 17,
    "name": "Premature success indication",
    "intervention": "Finish frame submission while verification or publication still remains incomplete.",
    "expected": "Show the actual remaining stage and withhold accepted completion until its gate passes.",
    "negative": "A one-hundred-percent banner before required verification must fail.",
    "repeat": "Repeat encoder drain, full decode, sidecar export, and gallery commit.",
}
NEGATIVE_TOKEN = "hundred-percent-banner-before-verification"
BEFORE_PUBLICATION = "hundred-percent-before-publication"
ACCEPTED_EARLY = "accepted-before-gate"
STAGE_HIDDEN = "remaining-stage-not-shown"
STAGES = frozenset({"capture", "verification", "publication", "complete"})
PAYLOAD_KEYS = {
    "evidenceId",
    "repeat",
    "report",
    "framesSubmitted",
    "shownStage",
    "verificationComplete",
    "publicationComplete",
    "bannerPercent",
    "acceptedComplete",
}


def remaining_stage(frames_submitted: bool, verification: bool, publication: bool) -> str | None:
    if not frames_submitted:
        return "capture"
    if not verification:
        return "verification"
    if not publication:
        return "publication"
    return None


def evaluate(payload: dict) -> dict:
    _GATE.require(isinstance(payload, dict), "payload must be an object")
    _GATE.require(set(payload) == PAYLOAD_KEYS, "invalid payload keys")
    evidence = _GATE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _GATE.require_text(payload["repeat"], "repeat")
    report = _GATE.parse_report(payload["report"])
    frames = _GATE.require_bool(payload["framesSubmitted"], "framesSubmitted")
    shown = _GATE.require_text(payload["shownStage"], "shownStage")
    _GATE.require(shown in STAGES, "shownStage is not recognized")
    verification = _GATE.require_bool(payload["verificationComplete"], "verificationComplete")
    publication = _GATE.require_bool(payload["publicationComplete"], "publicationComplete")
    banner = payload["bannerPercent"]
    if banner is not None:
        banner = _GATE.require_number(banner, "bannerPercent")
        _GATE.require(0 <= banner <= 100, "bannerPercent must be from 0 to 100")
    accepted = _GATE.require_bool(payload["acceptedComplete"], "acceptedComplete")
    remaining = remaining_stage(frames, verification, publication)
    full_banner = banner is not None and abs(banner - 100.0) <= 1e-9
    faults = []
    if full_banner and not verification:
        faults.append(NEGATIVE_TOKEN)
    elif full_banner and not publication:
        faults.append(BEFORE_PUBLICATION)
    if accepted and not (verification and publication):
        faults.append(ACCEPTED_EARLY)
    if remaining is not None and shown != remaining:
        faults.append(STAGE_HIDDEN)
    if remaining is None and shown != "complete":
        faults.append(STAGE_HIDDEN)
    reasons = [
        f"framesSubmitted={str(frames).lower()} shownStage={shown} remaining={remaining}",
        f"verificationComplete={str(verification).lower()} publicationComplete={str(publication).lower()}",
        f"bannerPercent={banner} acceptedComplete={str(accepted).lower()}",
    ]
    preserved = [{
        "framesSubmitted": frames,
        "shownStage": shown,
        "remainingStage": remaining,
        "verificationComplete": verification,
        "publicationComplete": publication,
        "bannerPercent": banner,
        "acceptedComplete": accepted,
    }]
    return _GATE.finish_tc(
        CASE,
        evidence,
        repeat,
        report,
        faults,
        reasons,
        preserved,
        {
            NEGATIVE_TOKEN: CASE["negative"],
            BEFORE_PUBLICATION: CASE["expected"],
            ACCEPTED_EARLY: CASE["expected"],
            STAGE_HIDDEN: CASE["expected"],
        },
        {
            NEGATIVE_TOKEN: "Do not show a one-hundred-percent banner before verification.",
            BEFORE_PUBLICATION: "Do not show one hundred percent before publication completes.",
            ACCEPTED_EARLY: "Withhold accepted completion until verification and publication pass.",
            STAGE_HIDDEN: "Show the actual remaining stage.",
        },
    )
