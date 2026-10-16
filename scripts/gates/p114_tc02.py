"""TC-P114-02 Existing blur ambiguity.

Host fixture. Exact shutter conversion is not available from an arbitrary source.
Already blurred or undersampled motion is labelled unsupported. Scope weights and
estimated-frame disclosure still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_define_synthetic_shutter_scope",
    Path(__file__).resolve().parent / "p114_define_synthetic_shutter_scope.py",
)
_GATE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_GATE)

CASE_ID = "TC-P114-02"
NAME = "Existing blur ambiguity"
INTERVENTION = "Supply sources with different amounts of already-recorded motion blur to the same synthetic-shutter request."
EXPECTED = "Apply only qualified additional processing and identify cases that cannot be faithfully reconstructed."
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
NEGATIVE_TOKEN = "exact-arbitrary-shutter-conversion"
UNLABELLED_TOKEN = "unsupported-reconstruction-unlabelled"
SOURCE_BLURS = frozenset({"short", "long", "undersampled_thin"})
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "shutter_angle_degrees",
    "fps",
    "contains_estimated",
    "disclosed",
    "labelled_as_longer_sensor_exposure",
    "frames",
    "source_blur",
    "claim_exact_conversion",
    "unsupported_labelled",
)


def evaluate(payload: dict) -> dict:
    document = _GATE.exact_keys(payload, set(PAYLOAD_KEYS), "payload")
    evidence = _GATE.evidence_id(document["evidenceId"])
    repeat = _GATE.repeat_text(document["repeat"])
    frames = _GATE.parse_frames(document["frames"])
    angle = _GATE.optional_positive(document["shutter_angle_degrees"], "shutter_angle_degrees")
    fps = _GATE.optional_positive(document["fps"], "fps")
    contains_estimated = _GATE.flag(document["contains_estimated"], "contains_estimated")
    disclosed = _GATE.flag(document["disclosed"], "disclosed")
    labelled = _GATE.flag(document["labelled_as_longer_sensor_exposure"], "labelled_as_longer_sensor_exposure")
    source_blur = document["source_blur"]
    _GATE.require(source_blur in SOURCE_BLURS, "source_blur must be short, long, or undersampled_thin")
    claim_exact = _GATE.flag(document["claim_exact_conversion"], "claim_exact_conversion")
    unsupported_labelled = _GATE.flag(document["unsupported_labelled"], "unsupported_labelled")

    rejected, scope_reasons = _GATE.scope_problems(
        frames,
        contains_estimated=contains_estimated,
        disclosed=disclosed,
        labelled_as_longer_sensor_exposure=labelled,
        shutter_angle_degrees=angle,
        fps=fps,
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, *scope_reasons, f"source blur {source_blur}"]
    if claim_exact:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if source_blur != "short":
        if unsupported_labelled and not claim_exact:
            reasons.append("unsupported reconstruction labelled; exact conversion is not claimed")
        elif not unsupported_labelled:
            rejected.append(UNLABELLED_TOKEN)
            reasons.append("already blurred or undersampled motion was not labelled unsupported")
    elif not claim_exact:
        reasons.append("short exposure may receive only additional disclosed integration")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("blur limitation retained; physical behavior stays open")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": _GATE.preserved_for(evidence, angle, fps, [f"blur:{source_blur}"]),
        "openQuestions": _GATE.open_questions(REPEAT),
    }
    return _GATE.seal(result, evidence)
