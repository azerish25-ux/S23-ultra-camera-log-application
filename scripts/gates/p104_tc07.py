"""TC-P104-07 Confidence misrepresentation.

Uncalibrated confidence is not a probability. Unstable predictions reduce
rendering reliance instead of claiming certainty.
"""

from __future__ import annotations


CASE_ID = "TC-P104-07"
NAME = "Confidence misrepresentation"
INTERVENTION = "Provide unstable or unreliable predictions while their confidence metadata claims certainty."
EXPECTED = "Expose uncalibrated confidence and reduce rendering reliance according to the declared policy."
NEGATIVE = "An arbitrary confidence score must not be presented as a calibrated probability."
REPEAT = "Repeat transparent surfaces, low texture, mirrors, and unfamiliar scenes."
NEGATIVE_TOKEN = "arbitrary-confidence-presented-as-calibrated-probability"
OPEN_QUESTION = "physical S23 measurement was not run"
SCENES = ("transparent", "low-texture", "mirror", "unfamiliar")
RELIANCE = ("reduced", "full")
PAYLOAD_KEYS = (
    "evidenceId",
    "scene",
    "unstable",
    "claimedCertainty",
    "calibrated",
    "presentedAsProbability",
    "renderingReliance",
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
    evidence, scene, unstable, claimed, calibrated, presented, reliance = _payload(payload)
    rejected: list[str] = []
    if presented and not calibrated:
        rejected.append(NEGATIVE_TOKEN)
    if unstable and reliance != "reduced":
        rejected.append("unstable-rendering-not-reduced")
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION]
    if NEGATIVE_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if "unstable-rendering-not-reduced" in rejected:
        reasons.append("unstable prediction did not reduce rendering reliance")
    if not rejected:
        reasons.append(f"{scene} exposes calibrated={str(calibrated).lower()} with {reliance} reliance")
    preserved = [
        evidence,
        f"scene:{scene}",
        f"unstable:{str(unstable).lower()}",
        f"claimed-certainty:{str(claimed).lower()}",
        f"calibrated:{str(calibrated).lower()}",
        f"presented-as-probability:{str(presented).lower()}",
        f"rendering-reliance:{reliance}",
    ]
    return _finish("rejected" if rejected else "recorded", reasons, rejected, preserved, evidence)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    scene = payload["scene"]
    if scene not in SCENES:
        raise ValueError("scene is unsupported")
    reliance = payload["renderingReliance"]
    if reliance not in RELIANCE:
        raise ValueError("renderingReliance is unsupported")
    flags = []
    for key in ("unstable", "claimedCertainty", "calibrated", "presentedAsProbability"):
        if type(payload[key]) is not bool:
            raise ValueError(key + " must be a bool")
        flags.append(payload[key])
    return (evidence, scene, *flags, reliance)


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
