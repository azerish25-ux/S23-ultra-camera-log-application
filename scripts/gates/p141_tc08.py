"""TC-P141-08 Preference mistaken for factual accuracy.

Host fixture. A higher user rating does not certify a stock or lens.
Appearance preference stays separate from evidence completeness. Rights are
still judged per asset.
"""

from __future__ import annotations

import importlib.util
import math
from pathlib import Path

CASE = {
    "id": "TC-P141-08",
    "phase": "P141",
    "workstream": 18,
    "name": "Preference mistaken for factual accuracy",
    "intervention": "Give a popular reconstructed recipe higher user ratings than a well-sourced alternative.",
    "expected": "Keep appearance preference separate from evidence completeness and historical claims.",
    "negative": "Popularity cannot certify a stock or lens identification.",
    "repeat": "Repeat blind comparisons, expert review, and conflicting production sources.",
}

NEGATIVE_TOKEN = "popularity-certifies-stock-or-lens"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "assets",
    "popularity",
    "evidenceCompleteness",
    "certifiesStock",
    "certifiesLens",
    "stockEvidence",
    "lensEvidence",
)


def _load_gate():
    path = Path(__file__).resolve().parent / "p141_manage_reference_media_rights_and_attribution.py"
    spec = importlib.util.spec_from_file_location("p141_gate_for_tc08", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_GATE = _load_gate()


def _unit(value: object, label: str) -> float:
    _GATE.require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    _GATE.require(math.isfinite(number) and 0.0 <= number <= 1.0, label + " must be between 0 and 1")
    return number


def evaluate(payload: dict) -> dict:
    bundle = _GATE.begin_case(payload, set(PAYLOAD_KEYS) - set(_GATE.COMMON_KEYS))
    faults = list(bundle["faults"])
    popularity = _unit(payload["popularity"], "popularity")
    evidence = _unit(payload["evidenceCompleteness"], "evidenceCompleteness")
    certifies_stock = _GATE.require_bool(payload["certifiesStock"], "certifiesStock")
    certifies_lens = _GATE.require_bool(payload["certifiesLens"], "certifiesLens")
    stock_evidence = _GATE.require_bool(payload["stockEvidence"], "stockEvidence")
    lens_evidence = _GATE.require_bool(payload["lensEvidence"], "lensEvidence")
    if (certifies_stock and not stock_evidence) or (certifies_lens and not lens_evidence):
        faults.append(NEGATIVE_TOKEN)
    extra = [{
        "popularity": popularity,
        "evidenceCompleteness": evidence,
        "certifiesStock": certifies_stock and stock_evidence,
        "certifiesLens": certifies_lens and lens_evidence,
        "preferenceSeparate": True,
    }]
    return _GATE.finish_case(
        CASE,
        bundle,
        faults,
        extra,
        {NEGATIVE_TOKEN: CASE["negative"]},
    )
