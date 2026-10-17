#!/usr/bin/env python3
"""P144 Validate recipe fidelity and honesty.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. A recipe evaluation report keeps three qualities apart:

* coherence, a finite number in [0, 1]
* enjoyment, a finite number in [0, 1] or null
* identification, correct only when source_id is present and evidence_kind is
  exactly "source"

A star_rating is preference data. Using evidence_kind "star_rating" as
identification evidence is rejected. High enjoyment does not flip
identification to correct. A recipe may be recorded while enjoyable and
unidentified. Historical accuracy is not claimed without a source. The decision
is recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

import json
import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P144"
WORKSTREAM = 18
TITLE = "Validate recipe fidelity and honesty"
GOAL = (
    "Evaluate whether recipes are coherent and enjoyable without overstating "
    "historical or physical accuracy."
)
METHOD = (
    "Use matched owned sources, blind preference tests, parameter ablations, and expert review "
    "where possible. Score evidence completeness separately from appearance preference. "
    "A popular recipe may remain reconstructed; a well-sourced recipe may need artistic refinement."
)
FIXTURE = (
    "One visually preferred recipe with uncertain production facts and another fully sourced "
    "but less preferred interpretation."
)
ORACLE = "The app reports these different qualities without promoting preference into factual certainty."
MUTANT = "Use user star ratings as evidence that a stock identification is correct."
DELIVERABLE = "Recipe evaluation report and catalogue quality policy"
DEPENDENCIES = ("P143",)

OPEN_QUESTION = "physical S23 capture was not run"
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
STAR_NOTE = "a star rating cannot prove a stock or lens identification"

HIGH_ENJOYMENT = 0.8
SOURCE_EVIDENCE = "source"
STAR_RATING_EVIDENCE = "star_rating"
EVIDENCE_KINDS = frozenset({
    "source",
    "star_rating",
    "guess",
    "title_match",
    "preference",
    "reconstruction",
    "none",
})
IDENTIFICATION_STATUSES = frozenset({"correct", "unidentified", "reconstructed"})
UNIDENTIFIED_STATUSES = frozenset({"unidentified", "reconstructed"})

STAR_RATING_AS_IDENTIFICATION = "star-rating-as-identification-evidence"
HIGH_ENJOYMENT_DOES_NOT_CERTIFY = "high-enjoyment-does-not-certify-identification"
IDENTIFICATION_REQUIRES_SOURCE = "identification-correct-requires-source"
HISTORICAL_ACCURACY_WITHOUT_SOURCE = "historical-accuracy-without-source"
EVIDENCE_NOT_SEPARATED = "evidence-not-separated-from-preference"
POPULAR_DENIED = "popular-recipe-denied-reconstructed-status"
SOURCED_EXEMPT = "sourced-recipe-exempted-from-artistic-refinement"
POLICY_WITHOUT_SOURCE = "policy-allows-historical-accuracy-without-source"

EVIDENCE_ID = "p144-recipe-fidelity"
CLAIM = "recipe-fidelity-and-honesty-host-reference"
PREFERRED_ID = "visually-preferred-uncertain"
SOURCED_ID = "fully-sourced-less-preferred"
OWNED_SOURCE_ID = "owned-print-source"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "preferred",
    "sourced",
    "policy",
}
RECIPE_KEYS = {
    "recipe_id",
    "coherence",
    "enjoyment",
    "identification",
    "historical_accuracy_claimed",
    "star_rating",
}
IDENTIFICATION_KEYS = {"status", "source_id", "evidence_kind"}
POLICY_KEYS = {
    "separate_evidence_from_preference",
    "popular_may_remain_reconstructed",
    "sourced_may_need_artistic_refinement",
    "star_rating_identifies_stock",
    "historical_accuracy_requires_source",
}
SINGLE_KEYS = {"evidenceId", "claim", "caseId", "applyMutant", "recipe"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

FAULT_TEXT = {
    STAR_RATING_AS_IDENTIFICATION: (
        "using star_rating as identification evidence is rejected; " + STAR_NOTE
    ),
    HIGH_ENJOYMENT_DOES_NOT_CERTIFY: "high enjoyment must not flip identification to correct",
    IDENTIFICATION_REQUIRES_SOURCE: (
        "identification is correct only with a source_id and evidence_kind \"source\""
    ),
    HISTORICAL_ACCURACY_WITHOUT_SOURCE: "do not claim historical accuracy without a source",
    EVIDENCE_NOT_SEPARATED: (
        "catalogue policy must score evidence completeness separately from appearance preference"
    ),
    POPULAR_DENIED: "a popular recipe may remain reconstructed",
    SOURCED_EXEMPT: "a well-sourced recipe may need artistic refinement",
    POLICY_WITHOUT_SOURCE: "catalogue policy must require a source before historical accuracy",
    MUTANT: MUTANT,
}

PREFERRED_RECIPE = {
    "recipe_id": PREFERRED_ID,
    "coherence": 0.91,
    "enjoyment": 0.96,
    "identification": {
        "status": "reconstructed",
        "source_id": None,
        "evidence_kind": "reconstruction",
    },
    "historical_accuracy_claimed": False,
    "star_rating": 5,
}
SOURCED_RECIPE = {
    "recipe_id": SOURCED_ID,
    "coherence": 0.78,
    "enjoyment": 0.42,
    "identification": {
        "status": "correct",
        "source_id": OWNED_SOURCE_ID,
        "evidence_kind": "source",
    },
    "historical_accuracy_claimed": True,
    "star_rating": 2,
}
CATALOGUE_POLICY = {
    "separate_evidence_from_preference": True,
    "popular_may_remain_reconstructed": True,
    "sourced_may_need_artistic_refinement": True,
    "star_rating_identifies_stock": False,
    "historical_accuracy_requires_source": True,
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_keys(payload: object, keys: set[str], label: str = "payload") -> dict:
    require(isinstance(payload, dict), label + " must be an object")
    require(set(payload) == set(keys), label + " keys are invalid")
    return payload


def require_unit(value: object, label: str, allow_null: bool) -> float | None:
    if value is None:
        require(allow_null, label + " must not be null")
        return None
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    require(0.0 <= number <= 1.0, label + " must be between 0 and 1")
    return number


def require_star(value: object, label: str = "star_rating") -> float | None:
    if value is None:
        return None
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number or null",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    require(0.0 <= number <= 5.0, label + " must be between 0 and 5")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def identification_correct(
    source_id: str | None,
    evidence_kind: str,
    enjoyment: float | None,
    star_rating: float | None,
) -> bool:
    """Return whether identification is correct.

    Correct only with a source_id and evidence_kind "source". Enjoyment and
    star_rating are visible inputs so a caller cannot hide them, and they are
    not allowed to change the result. High enjoyment must not flip this to True.
    """
    del enjoyment, star_rating
    return source_id is not None and evidence_kind == SOURCE_EVIDENCE


def parse_identification(value: object, label: str = "identification") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == IDENTIFICATION_KEYS, label + " keys are invalid")
    status = require_text(value["status"], label + ".status")
    require(status in IDENTIFICATION_STATUSES, label + ".status is not recognized")
    source_id = value["source_id"]
    if source_id is not None:
        source_id = require_text(source_id, label + ".source_id")
    evidence_kind = require_text(value["evidence_kind"], label + ".evidence_kind")
    require(evidence_kind in EVIDENCE_KINDS, label + ".evidence_kind is not recognized")
    return {"status": status, "source_id": source_id, "evidence_kind": evidence_kind}


def parse_recipe(value: object, label: str = "recipe") -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == RECIPE_KEYS, label + " keys are invalid")
    return {
        "recipe_id": require_text(value["recipe_id"], label + ".recipe_id"),
        "coherence": require_unit(value["coherence"], label + ".coherence", False),
        "enjoyment": require_unit(value["enjoyment"], label + ".enjoyment", True),
        "identification": parse_identification(value["identification"], label + ".identification"),
        "historical_accuracy_claimed": require_bool(
            value["historical_accuracy_claimed"], label + ".historical_accuracy_claimed"
        ),
        "star_rating": require_star(value["star_rating"], label + ".star_rating"),
    }


def parse_policy(value: object) -> dict[str, bool]:
    require(isinstance(value, dict), "policy must be an object")
    require(set(value) == POLICY_KEYS, "policy keys are invalid")
    return {key: require_bool(value[key], "policy." + key) for key in (
        "separate_evidence_from_preference",
        "popular_may_remain_reconstructed",
        "sourced_may_need_artistic_refinement",
        "star_rating_identifies_stock",
        "historical_accuracy_requires_source",
    )}


def score_recipe(value: object, label: str = "recipe") -> dict[str, Any]:
    """Separate coherence, enjoyment, and identification. Do not promote preference."""
    recipe = parse_recipe(value, label)
    ident = recipe["identification"]
    correct = identification_correct(
        ident["source_id"],
        ident["evidence_kind"],
        recipe["enjoyment"],
        recipe["star_rating"],
    )
    faults: list[str] = []
    if ident["evidence_kind"] == STAR_RATING_EVIDENCE:
        faults.append(STAR_RATING_AS_IDENTIFICATION)
        if ident["status"] == "correct":
            faults.append(MUTANT)
    if ident["status"] == "correct" and not correct:
        enjoyment = recipe["enjoyment"]
        if enjoyment is not None and enjoyment >= HIGH_ENJOYMENT:
            faults.append(HIGH_ENJOYMENT_DOES_NOT_CERTIFY)
        if ident["evidence_kind"] != STAR_RATING_EVIDENCE:
            faults.append(IDENTIFICATION_REQUIRES_SOURCE)
    if recipe["historical_accuracy_claimed"] and not correct:
        faults.append(HISTORICAL_ACCURACY_WITHOUT_SOURCE)
    enjoyment = recipe["enjoyment"]
    enjoyable = enjoyment is not None and enjoyment > 0.0
    unidentified = (not correct) and ident["status"] in UNIDENTIFIED_STATUSES
    report = {
        "recipe_id": recipe["recipe_id"],
        "coherence": recipe["coherence"],
        "enjoyment": enjoyment,
        "identification": {
            "correct": correct,
            "status": ident["status"],
            "source_id": ident["source_id"],
            "evidence_kind": ident["evidence_kind"],
        },
        "historical_accuracy_claimed": recipe["historical_accuracy_claimed"],
        "star_rating": recipe["star_rating"],
        "enjoyable_and_unidentified": enjoyable and unidentified,
    }
    require(
        set(("coherence", "enjoyment", "identification")).issubset(report),
        "report must separate coherence, enjoyment, and identification",
    )
    require(report["identification"]["correct"] is correct, "identification was rewritten")
    if enjoyment is not None and enjoyment >= HIGH_ENJOYMENT and not (
        ident["source_id"] is not None and ident["evidence_kind"] == SOURCE_EVIDENCE
    ):
        require(report["identification"]["correct"] is False, "high enjoyment flipped identification")
    return {"recipe": recipe, "report": report, "faults": faults}


def score_policy(value: object) -> list[str]:
    policy = parse_policy(value)
    faults: list[str] = []
    if policy["star_rating_identifies_stock"]:
        faults.append(MUTANT)
    if not policy["separate_evidence_from_preference"]:
        faults.append(EVIDENCE_NOT_SEPARATED)
    if not policy["popular_may_remain_reconstructed"]:
        faults.append(POPULAR_DENIED)
    if not policy["sourced_may_need_artistic_refinement"]:
        faults.append(SOURCED_EXEMPT)
    if not policy["historical_accuracy_requires_source"]:
        faults.append(POLICY_WITHOUT_SOURCE)
    return faults


def preferred_recipe() -> dict[str, Any]:
    return json.loads(json.dumps(PREFERRED_RECIPE))


def sourced_recipe() -> dict[str, Any]:
    return json.loads(json.dumps(SOURCED_RECIPE))


def catalogue_policy() -> dict[str, bool]:
    return dict(CATALOGUE_POLICY)


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "preferred": preferred_recipe(),
        "sourced": sourced_recipe(),
        "policy": catalogue_policy(),
    }


def same_facts(left: object, right: object) -> bool:
    try:
        encoded_left = json.dumps(
            left, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
        encoded_right = json.dumps(
            right, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("facts must be JSON-compatible") from exc
    return encoded_left == encoded_right


def seal(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(all(isinstance(item, str) and item for item in reasons), "reasons must be strings")
    require(reasons, "reasons must be non-empty")
    require(all(isinstance(item, str) and item for item in ordered), "rejectedClaims must be strings")
    require(bool(ordered) == (decision == "rejected"), "decision does not match rejected claims")
    question_out = list(open_questions)
    require(all(isinstance(item, str) and item for item in question_out), "openQuestions must be strings")
    require(OPEN_QUESTION in question_out, "physical S23 was not noted")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": ordered,
        "preservedResults": list(preserved),
        "openQuestions": question_out,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(result["decision"] not in {"qualified", "allowed"}, "decision cannot be qualified")
    return result


def _quality_reasons(report: dict[str, Any], role: str) -> list[str]:
    ident = report["identification"]
    enjoyment = "null" if report["enjoyment"] is None else str(report["enjoyment"])
    lines = [
        (
            role + " coherence=" + str(report["coherence"])
            + " enjoyment=" + enjoyment
            + " identification.correct=" + str(ident["correct"]).lower()
            + " evidence_kind=" + ident["evidence_kind"]
        ),
        STAR_NOTE,
    ]
    if report["enjoyable_and_unidentified"]:
        lines.append(role + " recorded as enjoyable and unidentified")
    if ident["correct"]:
        lines.append(role + " identification rests on source_id " + str(ident["source_id"]))
    else:
        lines.append(role + " identification was not promoted from preference")
    return lines


def case_result(
    case: dict,
    evidence: str,
    repeat: str,
    faults: list[str],
    preserved_tail: list,
    fault_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + repeat,
        STAR_NOTE,
    ]
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append(case["name"] + " recorded; preference is not factual certainty")
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"], repeat]
    preserved = [evidence, *preserved_tail]
    return seal(case["id"], ordered, reasons, preserved, questions, evidence)


def _document_reasons(preferred: dict[str, Any], sourced: dict[str, Any], ordered: list[str]) -> list[str]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
        "coherence, enjoyment, and identification are reported separately",
        STAR_NOTE,
    ]
    reasons.extend(_quality_reasons(preferred, "preferred"))
    reasons.extend(_quality_reasons(sourced, "sourced"))
    if (
        preferred["enjoyment"] is not None
        and sourced["enjoyment"] is not None
        and preferred["enjoyment"] > sourced["enjoyment"]
        and preferred["identification"]["correct"] is False
        and sourced["identification"]["correct"] is True
    ):
        reasons.append("higher enjoyment did not certify the preferred recipe")
        reasons.append("the less preferred recipe stays identified only by its source")
    for token in ordered:
        reasons.append(FAULT_TEXT.get(token, token))
    if MUTANT in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("catalogue quality policy keeps evidence apart from appearance preference")
        reasons.append("recipe evaluation recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record separated recipe qualities, or reject preference promoted into fact."""
    require(isinstance(document, dict), "document must be an object")
    if document.get("decision") in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    preferred = score_recipe(document["preferred"], "preferred")
    sourced = score_recipe(document["sourced"], "sourced")
    faults = list(preferred["faults"]) + list(sourced["faults"]) + score_policy(document["policy"])
    if apply_mutant:
        faults.append(MUTANT)
    ordered = dedupe(faults)
    report = {
        "preferred": preferred["report"],
        "sourced": sourced["report"],
        "policy": parse_policy(document["policy"]),
        "separated": True,
    }
    reasons = _document_reasons(preferred["report"], sourced["report"], ordered)
    preserved = [evidence, claim, report]
    return seal(PHASE, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one recipe report, or the phase document when one is given."""
    require(isinstance(payload, dict), "payload must be an object")
    if payload.get("decision") in {"qualified", "allowed"}:
        raise ValueError("decision cannot be qualified")
    if "schemaVersion" in payload or "preferred" in payload:
        return assess(payload)
    require_keys(payload, SINGLE_KEYS)
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim")
    case_id = require_text(payload["caseId"], "caseId")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    scored = score_recipe(payload["recipe"], "recipe")
    faults = list(scored["faults"])
    if apply_mutant:
        faults.append(MUTANT)
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "coherence, enjoyment, and identification are reported separately",
        STAR_NOTE,
    ]
    reasons.extend(_quality_reasons(scored["report"], scored["recipe"]["recipe_id"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(FAULT_TEXT.get(token, token))
    if not ordered:
        reasons.append("recipe recorded without promoting preference into factual certainty")
        if scored["report"]["enjoyable_and_unidentified"]:
            reasons.append("enjoyable unidentified recipe kept")
    preserved = [evidence, claim, scored["report"]]
    return seal(case_id, ordered, reasons, preserved, list(NON_CLAIM_QUESTIONS), evidence)
