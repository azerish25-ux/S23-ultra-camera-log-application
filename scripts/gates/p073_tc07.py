"""TC-P073-07 unversioned profile change.

Intervention: Modify numerical stock parameters while retaining an existing
immutable recipe identifier.
Expected: Create a new profile version and preserve reproducibility of earlier renders.
Negative: Overwriting stable profile bytes in place must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P073-07"
INTERVENTION = "Modify numerical stock parameters while retaining an existing immutable recipe identifier."
EXPECTED = "Create a new profile version and preserve reproducibility of earlier renders."
NEGATIVE = "Overwriting stable profile bytes in place must fail."
REPEAT = "Repeat with curve, grain, halation, and print-response changes."

_PARAMETERS = ("curve", "grain", "halation", "print-response")
_TOKEN = re.compile(r"^[a-z0-9-]+$")
_PAYLOAD_KEYS = (
    "parameter",
    "recipeId",
    "bytesChanged",
    "versionCreated",
    "priorRenderReproducible",
    "overwriteInPlace",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "version_created", "recipe_unchanged"}


def evaluate(payload: dict) -> dict:
    """Require a new version for numerical edits and keep the prior recipe reproducible."""
    parameter, recipe, changed, versioned, prior, overwrite = _payload(payload)
    preserved = [
        recipe,
        f"parameter:{parameter}",
        f"prior:{recipe}",
        f"bytes-changed:{str(changed).lower()}",
        f"version-created:{str(versioned).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {parameter}"]
    rejected: list[str] = []
    if overwrite or (changed and not versioned):
        decision = "rejected"
        rejected.append("overwrite-in-place")
        reasons.append(NEGATIVE)
        reasons.append(f"prior recipe {recipe} stays reproducible in the inventory")
    elif changed and versioned and not prior:
        decision = "rejected"
        rejected.append("prior-render-lost")
        reasons.append(f"earlier renders of {recipe} must remain reproducible after the {parameter} change")
    elif changed and versioned and prior:
        decision = "version_created"
        reasons.append(f"new version records the {parameter} change without overwriting {recipe}")
        questions.append("a new profile version is not a qualified stock measurement")
    elif not changed and not overwrite:
        decision = "recipe_unchanged"
        reasons.append(f"{recipe} bytes are unchanged for {parameter}")
    else:
        decision = "withheld"
        reasons.append(f"{parameter} change on {recipe} is not a complete version record")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    parameter = payload["parameter"]
    if parameter not in _PARAMETERS:
        raise ValueError("parameter is unsupported")
    recipe = payload["recipeId"]
    if not isinstance(recipe, str) or _TOKEN.fullmatch(recipe) is None:
        raise ValueError("recipeId must be a token")
    flags = []
    for name in ("bytesChanged", "versionCreated", "priorRenderReproducible", "overwriteInPlace"):
        value = payload[name]
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
        flags.append(value)
    return parameter, recipe, flags[0], flags[1], flags[2], flags[3]


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P073-07 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
