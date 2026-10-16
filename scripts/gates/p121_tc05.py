"""TC-P121-05 Temporary storage exhaustion.

Host fixture. Budget intermediate work and duplicate publication bytes, not
only the final output. Pause or fail before source loss and keep recoverable
artifacts.
"""

from __future__ import annotations


CASE_ID = "TC-P121-05"
NAME = "Temporary storage exhaustion"
INTERVENTION = "Make remaining space insufficient for intermediate work or duplicate publication storage."
EXPECTED = "Pause or fail safely before source loss, preserving recoverable artifacts and clear cleanup choices."
NEGATIVE = "Budgeting only final output bytes must fail."
REPEAT = "Repeat before rendering, during chunk assembly, and during gallery publication."
NEGATIVE_TOKEN = "budget-only-final-output-bytes"
SOURCE_TOKEN = "source-loss"
ARTIFACT_TOKEN = "recoverable-artifacts-missing"
REPEATS = ("before-rendering", "chunk-assembly", "gallery-publication")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "remainingBytes",
    "intermediateBytes",
    "duplicatePublicationBytes",
    "finalOutputBytes",
    "budgetedBytes",
    "sourcePreserved",
    "recoverableArtifacts",
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
    """Require a budget that covers intermediates. Do not spend the source."""
    fields = _payload(payload)
    needs = fields["intermediateBytes"] + fields["duplicatePublicationBytes"]
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}", f"required-bytes {needs}"]
    if fields["budgetedBytes"] < needs and fields["budgetedBytes"] <= fields["finalOutputBytes"] and needs > fields["finalOutputBytes"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif fields["budgetedBytes"] < needs:
        rejected.append("intermediate-budget-shortfall")
        reasons.append("budget does not cover intermediate and duplicate publication bytes")
    if not fields["sourcePreserved"]:
        rejected.append(SOURCE_TOKEN)
        reasons.append("source was not preserved")
    if fields["remainingBytes"] < needs and not fields["recoverableArtifacts"]:
        rejected.append(ARTIFACT_TOKEN)
        reasons.append("exhaustion left no recoverable artifacts")
    if fields["remainingBytes"] < needs and not rejected:
        reasons.append("paused-or-failed-before-source-loss")
        reasons.append("cleanup: retain recoverable artifacts and delete only uncommitted intermediates")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded" and fields["remainingBytes"] >= needs:
        reasons.append("remaining space covers intermediate and publication bytes")
    preserved = [
        fields["evidenceId"],
        {
            "remainingBytes": fields["remainingBytes"],
            "requiredBytes": needs,
            "budgetedBytes": fields["budgetedBytes"],
            "finalOutputBytes": fields["finalOutputBytes"],
            "sourcePreserved": fields["sourcePreserved"],
            "recoverableArtifacts": list(fields["recoverableArtifacts"]),
        },
    ]
    questions = ["physical S23 capture was not run", REPEAT]
    return _result(decision, reasons, rejected, preserved, questions)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bytes(value: object, label: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    repeat = payload["repeat"]
    if repeat not in REPEATS:
        raise ValueError("repeat is unsupported")
    if type(payload["sourcePreserved"]) is not bool:
        raise ValueError("sourcePreserved must be a bool")
    artifacts = payload["recoverableArtifacts"]
    if not isinstance(artifacts, list) or any(not isinstance(item, str) or not item.strip() for item in artifacts):
        raise ValueError("recoverableArtifacts must be a list of non-empty strings")
    return {
        "evidenceId": _text(payload["evidenceId"], "evidenceId"),
        "repeat": repeat,
        "remainingBytes": _bytes(payload["remainingBytes"], "remainingBytes"),
        "intermediateBytes": _bytes(payload["intermediateBytes"], "intermediateBytes"),
        "duplicatePublicationBytes": _bytes(payload["duplicatePublicationBytes"], "duplicatePublicationBytes"),
        "finalOutputBytes": _bytes(payload["finalOutputBytes"], "finalOutputBytes"),
        "budgetedBytes": _bytes(payload["budgetedBytes"], "budgetedBytes"),
        "sourcePreserved": payload["sourcePreserved"],
        "recoverableArtifacts": list(artifacts),
    }


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
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
