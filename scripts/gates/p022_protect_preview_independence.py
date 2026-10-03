#!/usr/bin/env python3
"""P022 host gate for preview independence.

Monitoring branches after source normalization. The preview owns its
downsample, display transform, overlays, and freshness metadata. The clean
master hash is compared with aids enabled and disabled. Reusing the composited
preview framebuffer as the recording source is rejected.

This module does not probe a device, does not qualify a physical S23, and does
not execute TC-P022-01 through TC-P022-08.
"""

from __future__ import annotations

import re
from typing import Any


BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
PHASE_ID = "P022"
CONTRACT_ID = "s23-preview-independence-fixture"
NORMALIZATION_POINT = "source-normalization"
METHOD = (
    "Branch monitoring after the declared source normalization point. "
    "Give the preview its own downsample, display transform, overlays, and freshness metadata. "
    "Tests must compare the recorded pixels or source hashes with preview aids enabled and disabled."
)
FIXTURE = (
    "A false-color overlay, histogram update, and virtual-film preview changed repeatedly "
    "during the same synthetic capture sequence."
)
ORACLE = (
    "The clean master remains identical within its deterministic capture contract "
    "and overlays appear only in monitoring."
)
MUTANT = (
    "Reuse the composited preview framebuffer as the supposedly untouched recording source."
)
MUTANT_CLAIM = "composited-preview-as-recording-source"
DRIFT_CLAIM = "clean-master-drift"
HASH40 = re.compile(r"^[0-9a-f]{40}$")
SIZE_TEXT = re.compile(r"^[1-9]\d*x[1-9]\d*$")
OVERLAYS = ("false-color", "histogram", "virtual-film", "focus-peaking", "virtual-depth")
RECORDED_FROM = ("clean-master", "preview-framebuffer")
FIXTURE_KEYS = {
    "schemaVersion",
    "phase",
    "contractId",
    "implementationBaseRevision",
    "normalizationPoint",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "sequenceId",
    "deterministicContract",
    "cleanMasterHash",
    "monitoring",
    "samples",
}
MONITORING_KEYS = {"downsample", "displayTransform", "overlaySet", "freshnessMaxMs"}
SAMPLE_KEYS = {
    "index",
    "sourceHash",
    "recordedHash",
    "previewFramebufferHash",
    "aidsEnabled",
    "overlays",
    "recordedFrom",
    "freshnessMs",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
HOST_LIMIT = "host fixture does not qualify a physical S23"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object, context: str) -> str:
    require(isinstance(value, str) and bool(value) and value == value.strip(),
            context + " must be a non-empty string")
    return value


def _hash(value: object, context: str) -> str:
    text = _text(value, context)
    require(HASH40.fullmatch(text) is not None, context + " must be 40 lowercase hex characters")
    return text


def _bool(value: object, context: str) -> bool:
    require(type(value) is bool, context + " must be a bool")
    return value


def _overlays(value: object, allowed: set[str], context: str) -> list[str]:
    require(isinstance(value, list), context + " must be a list")
    seen: set[str] = set()
    for item in value:
        require(isinstance(item, str) and item in allowed, context + " has an unknown overlay")
        require(item not in seen, context + " repeats overlay " + item)
        seen.add(item)
    return value


def validate_fixture(document: dict) -> None:
    """Raise ValueError unless document is the P022 monitoring-branch fixture."""
    exact_keys(document, FIXTURE_KEYS, "preview contract")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE_ID, "phase must be P022")
    require(document["contractId"] == CONTRACT_ID, "contractId must be s23-preview-independence-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HASH40.fullmatch(revision or "") is not None,
            "preview contract needs the P022 implementation base revision")
    require(document["normalizationPoint"] == NORMALIZATION_POINT,
            "normalizationPoint must be source-normalization")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    _text(document["sequenceId"], "sequenceId")
    _text(document["deterministicContract"], "deterministicContract")
    _hash(document["cleanMasterHash"], "cleanMasterHash")
    monitoring = exact_keys(document["monitoring"], MONITORING_KEYS, "monitoring")
    require(SIZE_TEXT.fullmatch(_text(monitoring["downsample"], "downsample")) is not None,
            "downsample must look like 160x90")
    _text(monitoring["displayTransform"], "displayTransform")
    allowed = set(_overlays(monitoring["overlaySet"], set(OVERLAYS), "overlaySet"))
    require(bool(allowed), "overlaySet must name the monitoring overlays")
    freshness_max = monitoring["freshnessMaxMs"]
    require(type(freshness_max) is int and freshness_max > 0, "freshnessMaxMs must be a positive int")
    samples = document["samples"]
    require(isinstance(samples, list) and samples, "samples must be a non-empty list")
    for index, sample in enumerate(samples):
        exact_keys(sample, SAMPLE_KEYS, f"sample {index}")
        require(type(sample["index"]) is int and sample["index"] == index,
                f"sample {index} index must be contiguous from zero")
        _hash(sample["sourceHash"], f"sample {index} sourceHash")
        _hash(sample["recordedHash"], f"sample {index} recordedHash")
        _hash(sample["previewFramebufferHash"], f"sample {index} previewFramebufferHash")
        aids = _bool(sample["aidsEnabled"], f"sample {index} aidsEnabled")
        overlays = _overlays(sample["overlays"], allowed, f"sample {index} overlays")
        require(sample["recordedFrom"] in RECORDED_FROM,
                f"sample {index} recordedFrom must be clean-master or preview-framebuffer")
        freshness = sample["freshnessMs"]
        require(type(freshness) is int and 0 <= freshness <= freshness_max,
                f"sample {index} freshnessMs must be inside the monitoring budget")
        if aids:
            require(bool(overlays), f"sample {index} aids require a monitoring overlay")
        else:
            require(not overlays, f"sample {index} disabled aids cannot carry overlays")


def reuses_preview_framebuffer(sample: dict) -> bool:
    """True when the recording source is the composited preview framebuffer.

    The mutant copies that framebuffer into the supposedly untouched master.
    A matching hash is enough: the preview buffer is a different branch.
    """
    if sample["recordedFrom"] == "preview-framebuffer":
        return True
    return sample["recordedHash"] == sample["previewFramebufferHash"]


def aid_toggle_hashes(document: dict) -> dict[str, list[str]]:
    """Recorded hashes split by whether preview aids were enabled."""
    validate_fixture(document)
    enabled: list[str] = []
    disabled: list[str] = []
    for sample in document["samples"]:
        bucket = enabled if sample["aidsEnabled"] else disabled
        bucket.append(sample["recordedHash"])
    return {"enabled": enabled, "disabled": disabled}


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
    require(all(isinstance(item, str) and item for item in reasons), "reasons must be non-empty strings")
    result = {
        "caseId": PHASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess_independence(document: dict) -> dict:
    """Compare the clean master with aids on and off, and reject the mutant.

    decision is invariant when every recorded hash matches the clean master
    and overlays stay on the monitoring branch. decision is withheld when the
    aid toggle is incomplete. decision is rejected when a sample reuses the
    composited preview framebuffer or the clean master drifts. preservedResults
    keep the clean-master hash and the sequence even when the decision fails.
    """
    validate_fixture(document)
    samples = document["samples"]
    clean = document["cleanMasterHash"]
    preserved = [clean, document["sequenceId"]]
    for sample in samples:
        if sample["sourceHash"] not in preserved:
            preserved.append(sample["sourceHash"])

    rejected: list[str] = []
    mutant = any(reuses_preview_framebuffer(sample) for sample in samples)
    drift = any(
        sample["recordedHash"] != clean or sample["sourceHash"] != clean
        for sample in samples
    )
    if mutant:
        rejected.append(MUTANT_CLAIM)
    if drift:
        rejected.append(DRIFT_CLAIM)

    enabled = [sample for sample in samples if sample["aidsEnabled"]]
    disabled = [sample for sample in samples if not sample["aidsEnabled"]]
    questions = [HOST_LIMIT]
    reasons: list[str] = [
        "monitoring branched after " + document["normalizationPoint"],
    ]
    if mutant or drift:
        decision = "rejected"
        if mutant:
            reasons.append("recording source must not be the composited preview framebuffer")
        if drift:
            reasons.append("clean master hash diverged from the deterministic capture contract")
    elif not enabled or not disabled:
        decision = "withheld"
        reasons.append("aid toggle comparison is incomplete")
        questions.append("both aids-enabled and aids-disabled samples are required")
    else:
        recorded = {sample["recordedHash"] for sample in samples}
        require(recorded == {clean}, "invariant path must share the clean master hash")
        for sample in enabled:
            require(sample["previewFramebufferHash"] != sample["recordedHash"],
                    "enabled aids must change the preview branch only")
        decision = "invariant"
        reasons.append("recorded hashes match with preview aids enabled and disabled")
        reasons.append("overlays appear only in monitoring")

    return _result(decision, reasons, rejected, preserved, questions)
