"""TC-P104-01 Model identity substitution.

A filename match does not establish identical weights. The actual digest is the
identity. Accepting depth from a substituted asset is rejected.
"""

from __future__ import annotations


CASE_ID = "TC-P104-01"
NAME = "Model identity substitution"
INTERVENTION = "Replace a model asset with another variant or converted file while retaining a cached result."
EXPECTED = "Invalidate incompatible caches and report the actual model identity before accepting depth output."
NEGATIVE = "A filename match alone must not establish identical weights."
REPEAT = "Repeat with precision changes, runtime versions, and different model variants."
NEGATIVE_TOKEN = "filename-match-alone-establish-identical-weights"
OPEN_QUESTION = "physical S23 measurement was not run"
PAYLOAD_KEYS = (
    "evidenceId",
    "cachedFilename",
    "cachedDigest",
    "actualFilename",
    "actualDigest",
    "precision",
    "runtimeVersion",
    "variant",
    "reportedIdentity",
    "acceptDepth",
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
    evidence, cached_name, cached_digest, actual_name, actual_digest, precision, runtime, variant, reported, accept = _payload(payload)
    filename_match = cached_name == actual_name
    weights_match = cached_digest == actual_digest
    rejected: list[str] = []
    if accept and not weights_match:
        rejected.append(NEGATIVE_TOKEN)
    if reported != actual_digest:
        rejected.append("actual-model-identity-not-reported")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if rejected:
        reasons.append(NEGATIVE)
        if not weights_match:
            reasons.append("incompatible cache invalidated; filename match is not weight identity")
    else:
        reasons.append("actual model digest reported before depth output is accepted")
        if not weights_match:
            reasons.append("substituted weights were not accepted from the cached filename")
    preserved = [
        evidence,
        f"cached-filename:{cached_name}",
        f"actual-filename:{actual_name}",
        f"cached-digest:{cached_digest}",
        f"actual-digest:{actual_digest}",
        f"precision:{precision}",
        f"runtime:{runtime}",
        f"variant:{variant}",
        f"reported-identity:{reported}",
        f"filename-match:{str(filename_match).lower()}",
        f"weights-match:{str(weights_match).lower()}",
        f"accept-depth:{str(accept).lower()}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip() or any(ch.isspace() for ch in value):
        raise ValueError(label + " must be a non-empty token")
    return value


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    return (
        _text(payload["evidenceId"], "evidenceId"),
        _text(payload["cachedFilename"], "cachedFilename"),
        _text(payload["cachedDigest"], "cachedDigest"),
        _text(payload["actualFilename"], "actualFilename"),
        _text(payload["actualDigest"], "actualDigest"),
        _text(payload["precision"], "precision"),
        _text(payload["runtimeVersion"], "runtimeVersion"),
        _text(payload["variant"], "variant"),
        _text(payload["reportedIdentity"], "reportedIdentity"),
        _bool(payload["acceptDepth"], "acceptDepth"),
    )


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(label + " must be a bool")
    return value


def _finish(decision: str, reasons: list[str], rejected: list[str], preserved: list[str], evidence: str) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [OPEN_QUESTION, REPEAT],
    }
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
