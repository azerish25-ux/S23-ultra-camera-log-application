"""TC-P139-05 Publicly accessible but unlicensed asset.

Host fixture. Citation metadata stays. Bytes without a redistribution licence
stay out of the release bundle. Public visibility is not a licence. The movie
fact hash is unchanged.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P139-05"
NAME = "Publicly accessible but unlicensed asset"
INTERVENTION = "Offer a web-accessible still, LUT, or profile whose redistribution permission is unknown."
EXPECTED = "Retain appropriate citation metadata while excluding unapproved bytes from the release bundle."
NEGATIVE = "Public visibility must not be treated as a redistribution licence."
REPEAT = "Repeat promotional images, commercial LUTs, and research model weights."
NEGATIVE_TOKEN = "public-visibility-treated-as-redistribution-licence"
UNLICENSED_BYTES = "unlicensed-bytes-in-release-bundle"
KINDS = {"promotional-images", "commercial-luts", "research-model-weights"}
LICENCES = {"unknown", "granted", "denied"}
ALLOWED_REPEATS = set(KINDS) | {REPEAT}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assetKind",
    "publiclyAccessible",
    "redistributionLicence",
    "citation",
    "includedInBundle",
    "byteCount",
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
        raise ValueError("repeat is not an asset class")
    kind = payload["assetKind"]
    if kind not in KINDS:
        raise ValueError("assetKind is invalid")
    if repeat in KINDS and repeat != kind:
        raise ValueError("repeat does not match assetKind")
    if type(payload["publiclyAccessible"]) is not bool or type(payload["includedInBundle"]) is not bool:
        raise ValueError("visibility flags must be bools")
    licence = payload["redistributionLicence"]
    if licence not in LICENCES:
        raise ValueError("redistributionLicence is invalid")
    citation = _CORE.require_text(payload["citation"], "citation")
    byte_count = payload["byteCount"]
    if type(byte_count) is not int or byte_count < 0:
        raise ValueError("byteCount must be a non-negative integer")
    review = _CORE.review_reconstructions(
        payload["productionFacts"],
        payload["reconstructions"],
        declared_fact_hash=payload["fact_hash"],
        prior_canonical=payload["prior_canonical"],
        mutated_facts=payload["mutated_facts"],
        bound_object_id=None,
    )
    faults = list(review["faults"])
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", "assetKind=" + kind]
    reasons.extend(review["reasons"])
    if licence != "granted" and payload["includedInBundle"]:
        if payload["publiclyAccessible"]:
            faults.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
        else:
            faults.append(UNLICENSED_BYTES)
            reasons.append("unapproved bytes were included in the release bundle")
    excluded = not payload["includedInBundle"]
    preserved = [
        evidence,
        "citation=" + citation,
        "bytesExcluded=" + str(excluded).lower(),
        "byteCount=" + str(byte_count),
        "redistributionLicence=" + licence,
        "publiclyAccessible=" + str(payload["publiclyAccessible"]).lower(),
    ]
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
    if not excluded and licence != "granted" and "citation=" + citation not in result["preservedResults"]:
        raise ValueError("citation dropped")
    return result
