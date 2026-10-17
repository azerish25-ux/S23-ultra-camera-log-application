"""TC-P139-03 Creative edit overwrites evidence.

Host fixture. Changing virtual aperture, grade, or grain stores a new
reconstruction version. Historical production facts and their fact hash stay
put. User parameters that copy documented fact keys are rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-03"
NAME = "Creative edit overwrites evidence"
INTERVENTION = "Change virtual aperture, grade, or grain inside a user derivative recipe."
EXPECTED = "Create a new reconstruction version without altering historical production facts."
NEGATIVE = "User preferences must not replace the cinematographer\u2019s sourced metadata."
REPEAT = "Repeat recipe save, rename, share, and update from a newer catalogue package."
NEGATIVE_TOKEN = "user-preference-replaced-sourced-metadata"
OPERATIONS = {"save", "rename", "share", "update"}
ALLOWED_REPEATS = set(OPERATIONS) | {REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "operation",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a recipe operation")
    operation = payload["operation"]
    if operation not in OPERATIONS:
        raise ValueError("operation is not save, rename, share, or update")
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", "operation=" + operation]
    reasons.extend(review["reasons"])
    versions = review["versions"]
    if len(versions) < 2:
        raise ValueError("a creative edit needs a parent reconstruction and a new version")
    parent_ids = {version["id"] for version in versions}
    derivatives = [version for version in versions if version["parent_id"] in parent_ids]
    if not derivatives:
        faults.append(_CORE.MISSING_PARENT)
        reasons.append("creative edit did not store a new version")
    for version in versions:
        documented = sorted(set(version["parameters"]) & set(_CORE.DOCUMENTED_FACT_KEYS))
        if documented:
            faults.append(NEGATIVE_TOKEN)
            reasons.append(version["id"] + " copied documented facts into parameters: " + ", ".join(documented))
    if _CORE.DOCUMENTED_KEY_OVERWRITTEN in faults or _CORE.MUTATED_FACTS in faults or _CORE.FACT_HASH_CHANGED in faults:
        faults.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if NEGATIVE_TOKEN in faults and NEGATIVE not in reasons:
        reasons.append(NEGATIVE)
    preserved = [evidence, "operation=" + operation]
    if derivatives:
        child = derivatives[-1]
        preserved.append("version=" + child["id"])
        preserved.append("parent=" + str(child["parent_id"]))
        preserved.append("parameter_hash=" + child["parameter_hash"])
        preserved.append("fact_hash=" + child["fact_hash"])
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
