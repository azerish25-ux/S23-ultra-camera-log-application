"""TC-P126-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are replaced by SHA-256 identities. A Log master
without an interpretation record is not treated as self-describing. Clip rows
still follow the P126 playable rule.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path

CASE_INDEX = 7
NEGATIVE_TOKEN = "log-master-without-interpretation"
RECIPE_TOKEN = "recipe-metadata-missing"
HDR_TOKEN = "missing-signal-interpretation"
PARTIAL_TOKEN = "unverified-partial-self-describing"
MASTER_KINDS = ("log", "sdr", "hdr-derived", "partial")
PRIVATE_MARKERS = ("/storage/emulated", "/data/user", "/data/data", "DCIM", "/home/", "Users/")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "paths",
    "masterKind",
    "interpretation",
    "presentedAsSelfDescribing",
    "recipeRetained",
    "clips",
    "omitted_ids",
)

_SPEC = importlib.util.spec_from_file_location(
    "p126_build_a_trustworthy_clip_library",
    Path(__file__).resolve().parent / "p126_build_a_trustworthy_clip_library.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)
CASE = _CORE.CASES[CASE_INDEX]
CASE_ID = CASE["id"]
NAME = CASE["name"]
INTERVENTION = CASE["intervention"]
EXPECTED = CASE["expected"]
NEGATIVE = CASE["negative"]
REPEAT = CASE["repeat"]
RESULT_KEYS = _CORE.RESULT_KEYS


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _flag(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def _private(path: str) -> bool:
    return any(marker in path for marker in PRIVATE_MARKERS)


def _interpretation(value):
    if value is None:
        return None
    if not isinstance(value, dict) or not value:
        raise ValueError("interpretation must be a non-empty object or null")
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError("interpretation keys must be non-empty strings")
        if isinstance(item, str):
            if not item.strip() or item != item.strip():
                raise ValueError("interpretation values must be non-empty strings or numbers")
        elif type(item) is bool or not isinstance(item, (int, float)):
            raise ValueError("interpretation values must be non-empty strings or numbers")
        elif isinstance(item, float) and not math.isfinite(item):
            raise ValueError("interpretation values must be finite")
    return value


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    paths = payload["paths"]
    if not isinstance(paths, list) or not paths:
        raise ValueError("paths must be a non-empty list")
    parsed_paths = [_text(path, f"paths[{index}]") for index, path in enumerate(paths)]
    master = _text(payload["masterKind"], "masterKind")
    if master not in MASTER_KINDS:
        raise ValueError("masterKind is invalid")
    interpretation = _interpretation(payload["interpretation"])
    presented = _flag(payload["presentedAsSelfDescribing"], "presentedAsSelfDescribing")
    recipe = _flag(payload["recipeRetained"], "recipeRetained")
    library = _CORE.evaluate_library(payload["clips"], payload["omitted_ids"])
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(library["reasons"])
    rejected = list(library["rejectedClaims"])
    preserved = [evidence]
    for path in parsed_paths:
        digest = _CORE.content_sha256(path.encode("utf-8"))
        token = "redactedPathSha256=" + digest if _private(path) else "path=" + path
        reasons.append(token)
        preserved.append(token)
    if interpretation is not None:
        canonical = json.dumps(interpretation, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        token = "interpretationSha256=" + _CORE.content_sha256(canonical.encode("utf-8"))
        reasons.append(token)
        preserved.append(token)
    if not recipe:
        _add(rejected, RECIPE_TOKEN)
        reasons.append("recipe metadata was not retained")
    if master == "log" and interpretation is None:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif master == "log":
        reasons.append("interpretation-retained")
    if master == "hdr-derived" and interpretation is None:
        _add(rejected, HDR_TOKEN)
        reasons.append("hdr-derived master is missing its signal interpretation")
    if master == "partial" and presented and interpretation is None:
        _add(rejected, PARTIAL_TOKEN)
        reasons.append("unverified partial export was presented as self-describing")
    if master == "partial" and not presented:
        reasons.append("partial-export-not-self-describing")
    preserved.extend(library["preservedResults"])
    decision = "rejected" if rejected else "recorded"
    if decision in {"qualified", "allowed"}:
        raise ValueError("negative or unmeasured result must not be qualified")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if evidence not in result["preservedResults"]:
        raise ValueError("evidence wiped")
    for path in parsed_paths:
        if _private(path) and path in " ".join(result["reasons"] + result["preservedResults"] + result["rejectedClaims"]):
            raise ValueError("private path leaked")
    return result
