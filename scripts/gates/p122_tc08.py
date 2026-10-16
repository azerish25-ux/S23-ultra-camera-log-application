"""TC-P122-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps its interpretation
record and the recipe version hash. Presenting that master as self-describing
without the record is rejected.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P122-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
NEGATIVE_TOKEN = "log-master-without-interpretation-record"
LEAK_TOKEN = "private-path-not-redacted"
MISSING_INTERPRETATION = "missing-interpretation-record"
MISSING_RECIPE = "recipe-metadata-missing"
PARTIAL_TOKEN = "partial-presented-as-self-describing"
KINDS = {"log-master", "rendered-sdr", "hdr-derived", "partial-unverified"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "kind",
    "privatePaths",
    "exportedPaths",
    "interpretationRecordPresent",
    "recipeMetadataPresent",
    "presentedAsSelfDescribing",
    "versions",
    "mutatedInPlace",
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
    "p122_create_non_destructive_recipe_versions",
    Path(__file__).resolve().parent / "p122_create_non_destructive_recipe_versions.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def valid_versions():
    return _CORE.sample_versions()


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _paths(value, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    paths = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label}[{index}] must be a non-empty string")
        paths.append(item)
    return paths


def _leaks(private_paths: list[str], exported_paths: list[str]) -> list[str]:
    found = []
    for private in private_paths:
        prefix = private.rstrip("/") + "/"
        for exported in exported_paths:
            if exported == private or exported.startswith(prefix):
                if private not in found:
                    found.append(private)
    return found


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    kind = _text(payload["kind"], "kind")
    if kind not in KINDS:
        raise ValueError("kind must be a known export interpretation")
    private_paths = _paths(payload["privatePaths"], "privatePaths")
    exported_paths = _paths(payload["exportedPaths"], "exportedPaths")
    if type(payload["interpretationRecordPresent"]) is not bool:
        raise ValueError("interpretationRecordPresent must be a bool")
    if type(payload["recipeMetadataPresent"]) is not bool:
        raise ValueError("recipeMetadataPresent must be a bool")
    if type(payload["presentedAsSelfDescribing"]) is not bool:
        raise ValueError("presentedAsSelfDescribing must be a bool")
    chain = _CORE.review_versions(payload["versions"], mutated_in_place=payload["mutatedInPlace"])
    rejected = list(chain["rejectedClaims"])
    leaked = _leaks(private_paths, exported_paths)
    reasons = [f"{CASE_ID} {NAME}", EXPECTED, INTERVENTION, f"repeat {repeat}", f"kind={kind}"]
    reasons.extend(chain["reasons"])
    if leaked:
        if LEAK_TOKEN not in rejected:
            rejected.append(LEAK_TOKEN)
        reasons.append("private paths remained in the export: " + ",".join(leaked))
    if not payload["recipeMetadataPresent"] and MISSING_RECIPE not in rejected:
        rejected.append(MISSING_RECIPE)
        reasons.append("recipe metadata was not retained")
    if not payload["interpretationRecordPresent"]:
        if MISSING_INTERPRETATION not in rejected:
            rejected.append(MISSING_INTERPRETATION)
        reasons.append("technical interpretation record is missing")
        if kind == "log-master" and payload["presentedAsSelfDescribing"] and NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
            reasons.append(NEGATIVE)
    if kind == "partial-unverified" and payload["presentedAsSelfDescribing"] and PARTIAL_TOKEN not in rejected:
        rejected.append(PARTIAL_TOKEN)
        reasons.append("unverified partial export was presented as self-describing")
    if not rejected:
        reasons.append("personal paths redacted and interpretation retained")
    preserved = [evidence, f"kind={kind}", f"leakedCount={len(leaked)}"]
    preserved.extend(chain["preservedResults"])
    result = _CORE.finish_result(
        CASE_ID,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS or evidence not in result["preservedResults"]:
        raise ValueError("result contract drifted")
    return result
