"""TC-P139-01 Missing production fact.

Host fixture. An unknown lens or stock stays unknown. A labelled creative
reconstruction may still exist. A plausible equipment guess marked documented
is rejected. Production-fact hashes are reviewed with the phase gate.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-01"
NAME = "Missing production fact"
INTERVENTION = "Remove verified lens or scene-specific stock information from an otherwise complete movie record."
EXPECTED = "Keep the fact unknown while allowing a clearly labelled creative reconstruction."
NEGATIVE = "A plausible equipment guess marked documented must fail."
REPEAT = "Repeat camera, lens, stock, process, and release-version fields."
NEGATIVE_TOKEN = "plausible-equipment-guess-marked-documented"
STILL_DOCUMENTED = "removed-field-still-documented"
FIELD_BY_REPEAT = {
    "camera": "camera",
    "lens": "lens",
    "stock": "stock",
    "process": "process",
    "release-version": "releaseVersion",
}
ALLOWED_REPEATS = set(FIELD_BY_REPEAT) | {REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "removedField",
    "guess",
    "productionFacts",
    "fact_hash",
    "prior_canonical",
    "reconstructions",
    "mutated_facts",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p139_version_creative_reconstruction_parameters",
    Path(__file__).resolve().parent / "p139_version_creative_reconstruction_parameters.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _guess(value):
    if value is None:
        return None
    if type(value) is not dict or set(value) != {"field", "value", "marked"}:
        raise ValueError("guess must be null or field, value, marked")
    field = _CORE.require_text(value["field"], "guess.field")
    if field not in _CORE.DOCUMENTED_FACT_KEYS:
        raise ValueError("guess field is not a production fact")
    marked = _CORE.require_text(value["marked"], "guess.marked")
    if marked not in {"documented", _CORE.CREATIVE_LABEL, _CORE.USER_LABEL}:
        raise ValueError("guess.marked is not an evidence label")
    guessed = _CORE.require_text(value["value"], "guess.value")
    return {"field": field, "value": guessed, "marked": marked}


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a production-fact field")
    removed = payload["removedField"]
    if removed not in _CORE.DOCUMENTED_FACT_KEYS:
        raise ValueError("removedField is not a production fact")
    if repeat in FIELD_BY_REPEAT and FIELD_BY_REPEAT[repeat] != removed:
        raise ValueError("repeat does not match removedField")
    guess = _guess(payload["guess"])
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    facts = _CORE.parse_facts(payload["productionFacts"], "productionFacts")
    prior = _CORE.require_canonical_facts(payload["prior_canonical"], "prior_canonical")
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}"]
    reasons.extend(review["reasons"])
    if facts[removed] is not None:
        faults.append(STILL_DOCUMENTED)
        reasons.append("removed production fact was not kept unknown")
    labels = {version["label"] for version in review["versions"]}
    if not labels & {_CORE.CREATIVE_LABEL, _CORE.USER_LABEL}:
        faults.append("creative-reconstruction-unlabelled")
        reasons.append(EXPECTED)
    if guess is not None and guess["marked"] == "documented":
        if prior[guess["field"]] is None or prior[guess["field"]] != guess["value"]:
            faults.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    preserved = [evidence, "removedField=" + removed, "unknown=" + removed]
    if guess is not None:
        preserved.append("guess=" + guess["field"] + ":" + guess["marked"])
    else:
        preserved.append("guess=none")
    preserved.extend(review["preserved"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        faults,
        preserved,
        [_CORE.OPEN_QUESTION, REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
