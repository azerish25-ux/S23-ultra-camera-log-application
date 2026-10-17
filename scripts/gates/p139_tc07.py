"""TC-P139-07 Parameter matching alters content.

Host fixture. A look suggestion may change declared rendering parameters only.
Facial geometry, text, fine patterns, scene texture, and moving objects are
rejected as content synthesis. Production facts stay immutable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-07"
NAME = "Parameter matching alters content"
INTERVENTION = "Use an automatic look suggestion that changes facial geometry or replaces scene texture."
EXPECTED = "Reject unrequested content synthesis and restrict matching to declared rendering parameters."
NEGATIVE = "A visually similar generated scene is not preserved camera footage."
REPEAT = "Repeat faces, text, fine patterns, and moving objects."
NEGATIVE_TOKEN = "generated-scene-is-not-preserved-footage"
SYNTHESIS = "unrequested-content-synthesis"
CONTENT_FIELDS = {
    "faces": "facialGeometry",
    "text": "renderedText",
    "fine-patterns": "finePattern",
    "moving-objects": "movingObjects",
}
CONTENT_KEYS = set(CONTENT_FIELDS.values()) | {"sceneTexture"}
ALLOWED_REPEATS = set(CONTENT_FIELDS) | {REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "suggestion",
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


def _suggestion(value):
    if type(value) is not dict or not value:
        raise ValueError("suggestion must be a non-empty object")
    parsed = {}
    for key, item in value.items():
        if type(key) is not str or not key.strip():
            raise ValueError("suggestion keys must be strings")
        if item is None or type(item) is str or type(item) is bool or type(item) is int:
            parsed[key] = item
            continue
        if type(item) is float:
            if item != item:
                raise ValueError("suggestion values must be finite")
            parsed[key] = item
            continue
        raise ValueError("suggestion value is not a parameter")
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a content class")
    suggestion = _suggestion(payload["suggestion"])
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}"]
    reasons.extend(review["reasons"])
    illegal = sorted(key for key in suggestion if key not in _CORE.CREATIVE_PARAMETER_KEYS)
    content = sorted(key for key in illegal if key in CONTENT_KEYS or key not in _CORE.CREATIVE_PARAMETER_KEYS)
    if content:
        faults.append(SYNTHESIS)
        faults.append(NEGATIVE_TOKEN)
        reasons.append("content fields " + ",".join(content))
        reasons.append(NEGATIVE)
    latest = review["versions"][-1]
    for key, value in suggestion.items():
        if key in _CORE.CREATIVE_PARAMETER_KEYS and latest["parameters"].get(key) != value:
            faults.append("suggestion-not-restricted-to-stored-parameters")
            reasons.append(key + " was not stored as a declared rendering parameter")
    preserved = [evidence, "suggestionKeys=" + ",".join(sorted(suggestion))]
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
