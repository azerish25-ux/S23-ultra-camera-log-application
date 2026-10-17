"""TC-P139-06 Reference edition conflict.

Host fixture. Theatrical, digital, HDR, and unidentified references stay
separate targets or explicit uncertainty. Averaging their contrast into one
historical fact or one blended reconstruction is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-06"
NAME = "Reference edition conflict"
INTERVENTION = "Supply references from different film releases or display assumptions with different appearance."
EXPECTED = "Keep separate targets or explicit uncertainty rather than inventing one definitive look."
NEGATIVE = "Averaging inconsistent editions into a historical fact must fail."
REPEAT = "Repeat theatrical, digital, HDR, and unidentified reference versions."
NEGATIVE_TOKEN = "averaged-inconsistent-editions-into-historical-fact"
INVENTED = "invented-definitive-look"
UNIDENTIFIED = "unidentified-edition-resolved-without-uncertainty"
EDITIONS = {"theatrical", "digital", "hdr", "unidentified"}
ALLOWED_REPEATS = set(EDITIONS) | {REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "editions",
    "separateTargets",
    "uncertaintyExplicit",
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


def _number(value) -> bool:
    return type(value) is int or type(value) is float


def _same(value, target: float) -> bool:
    if not _number(value):
        return False
    return abs(float(value) - target) <= 1e-9


def _editions(value):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError("editions must list more than one reference")
    parsed = []
    seen = set()
    for index, item in enumerate(value):
        if type(item) is not dict or set(item) != {"id", "release", "printContrast"}:
            raise ValueError(f"editions[{index}] keys are invalid")
        edition_id = _CORE.require_text(item["id"], f"editions[{index}].id")
        if edition_id not in EDITIONS:
            raise ValueError(f"editions[{index}].id is not a reference edition")
        if edition_id in seen:
            raise ValueError("edition id repeated")
        seen.add(edition_id)
        contrast = item["printContrast"]
        if contrast is not None and not _number(contrast):
            raise ValueError(f"editions[{index}].printContrast must be a number or null")
        if type(contrast) is float and contrast != contrast:
            raise ValueError("printContrast must be finite")
        parsed.append(
            {
                "id": edition_id,
                "release": _CORE.require_text(item["release"], f"editions[{index}].release"),
                "printContrast": contrast,
            }
        )
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId")
    repeat = _CORE.require_text(payload["repeat"], "repeat")
    if repeat not in ALLOWED_REPEATS:
        raise ValueError("repeat is not a reference edition")
    if type(payload["separateTargets"]) is not bool or type(payload["uncertaintyExplicit"]) is not bool:
        raise ValueError("edition flags must be bools")
    editions = _editions(payload["editions"])
    if repeat in EDITIONS and repeat not in {item["id"] for item in editions}:
        raise ValueError("repeat edition is missing")
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    facts = _CORE.parse_facts(payload["productionFacts"], "productionFacts")
    distinct = []
    for edition in editions:
        if edition["printContrast"] is None:
            if not payload["uncertaintyExplicit"]:
                pass
            continue
        number = float(edition["printContrast"])
        if number not in distinct:
            distinct.append(number)
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}"]
    reasons.extend(review["reasons"])
    unidentified = [item for item in editions if item["printContrast"] is None]
    if unidentified and not payload["uncertaintyExplicit"]:
        faults.append(UNIDENTIFIED)
        reasons.append("an unidentified reference was resolved without explicit uncertainty")
    if len(distinct) > 1:
        mean = sum(distinct) / len(distinct)
        blended = any(_same(version["parameters"]["printContrast"], mean) for version in review["versions"])
        written = _same(facts.get("documentedPrintContrast"), mean)
        if not payload["separateTargets"] and not payload["uncertaintyExplicit"]:
            faults.append(INVENTED)
            reasons.append(EXPECTED)
        if blended or written:
            faults.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
            reasons.append("meanContrast=" + str(mean))
    preserved = [
        evidence,
        "separateTargets=" + str(payload["separateTargets"]).lower(),
        "uncertaintyExplicit=" + str(payload["uncertaintyExplicit"]).lower(),
    ]
    for edition in editions:
        preserved.append("edition=" + edition["id"] + " contrast=" + str(edition["printContrast"]))
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
