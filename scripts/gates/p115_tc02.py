"""TC-P115-02 Existing blur ambiguity.

Host fixture. Exact arbitrary shutter conversion from any source is rejected.
Already blurred or undersampled motion must be identified, not reconstructed away.
"""

from __future__ import annotations


CASE_ID = "TC-P115-02"
NAME = "Existing blur ambiguity"
INTERVENTION = "Supply sources with different amounts of already-recorded motion blur to the same synthetic-shutter request."
EXPECTED = "Apply only qualified additional processing and identify cases that cannot be faithfully reconstructed."
NEGATIVE = "Claiming exact arbitrary shutter conversion from any source must fail."
REPEAT = "Repeat short exposure, long exposure, and undersampled thin motion."
BLURS = ("short-exposure", "long-exposure", "undersampled-thin")
PROCESSING = ("none", "qualified-additional", "identified-unreconstructable")
HARD = ("long-exposure", "undersampled-thin")
PAYLOAD_KEYS = (
    "evidenceId",
    "existingBlur",
    "claimExactConversion",
    "additionalProcessing",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Record only qualified handling. Exact conversion claims are rejected."""
    evidence, blur, exact, processing, repeat = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {repeat}", f"existing blur {blur}"]
    if exact:
        rejected.append("exact-arbitrary-shutter-conversion")
        reasons.append(NEGATIVE)
    if blur in HARD:
        if processing != "identified-unreconstructable":
            rejected.append("unfaithful-reconstruction")
            reasons.append("already blurred or undersampled motion cannot always be reconstructed")
    elif processing == "identified-unreconstructable":
        rejected.append("short-exposure-misidentified")
        reasons.append("short exposure was marked unreconstructable")
    elif processing not in {"none", "qualified-additional"}:
        rejected.append("unqualified-additional-processing")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("additional processing stays inside the identified source limit")
    preserved = [evidence, f"blur:{blur}", f"processing:{processing}", f"exact:{str(exact).lower()}"]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    blur = payload["existingBlur"]
    if blur not in BLURS:
        raise ValueError("existingBlur is unsupported")
    processing = payload["additionalProcessing"]
    if processing not in PROCESSING:
        raise ValueError("additionalProcessing is unsupported")
    repeat = payload["repeat"]
    if repeat not in BLURS:
        raise ValueError("repeat is unsupported")
    exact = payload["claimExactConversion"]
    if type(exact) is not bool:
        raise ValueError("claimExactConversion must be a bool")
    return evidence, blur, exact, processing, repeat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS or not reasons or preserved[0] not in preserved:
        raise ValueError("result contract drifted")
    return result
