#!/usr/bin/env python3
"""P127 Export interoperable result bundles.

Host fixture only. This module does not probe a device, does not qualify a
physical S23, and does not execute the TC-P127-01 through TC-P127-08 modules.

A shareable bundle manifest carries source, recipe, and result hashes, the
color transfer, the container, and explicit non-claims. Missing source lineage
blocks export. Display transfers cannot be relabelled as Log. A graded result
must not reuse the source hash. Personal paths and identifiers are redacted
from the public report while technical provenance stays attached.
"""

from __future__ import annotations

import re
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P127"
WORKSTREAM = 16
TITLE = "Export interoperable result bundles"
GOAL = "Deliver video with the metadata needed to understand and reproduce it."
METHOD = (
    "Include source lineage, recipe, profile and model identities, timing mapping, color interpretation, "
    "calibration status, clipping counts, and verification summary. Redact personal paths and identifiers "
    "in shared reports. Keep optional large intermediates separate from the default share bundle."
)
FIXTURE = (
    "A LogC3 result shared without its sidecar and a rendered movie result containing private filesystem "
    "paths in metadata."
)
ORACLE = (
    "The UI warns about required interpretation information and sanitizes the public report without "
    "losing technical provenance."
)
MUTANT = "Publish private absolute paths or omit essential Log interpretation metadata."
DELIVERABLE = "Export bundle schema and privacy-preserving share tests"
DEPENDENCIES = ("P126",)

HASH_WIDTH = 64
REQUIRED_NON_CLAIM = "not a physical S23 qualification"
COLOR_TRANSFERS = frozenset({"bt709", "hlg", "logc3", "pq", "unknown"})
DISPLAY_TRANSFERS = frozenset({"bt709", "hlg"})
MANIFEST_FIELDS = (
    "source_sha256",
    "recipe_version_sha256",
    "result_sha256",
    "color_transfer",
    "container",
    "non_claims",
)
MANIFEST_REQUIRED = frozenset(MANIFEST_FIELDS) - {"source_sha256"}
BUNDLE_KEYS = frozenset({
    "manifest",
    "export_allowed",
    "grade_applied",
    "labels",
    "filename",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
})
DOCUMENT_KEYS = BUNDLE_KEYS | {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
}
EVALUATE_KEYS = BUNDLE_KEYS | {"caseId", "evidenceId", "claim", "applyMutant"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
MISSING_SOURCE = "missing-source-sha256"
RELABEL = "display-transfer-relabelled-as-log"
MISSING_NON_CLAIM = "missing-required-non-claim"
GRADED_SAME_HASH = "graded-result-reuses-source-hash"
UNGRADED_CHANGED = "ungraded-result-hash-changed"
PRIVATE_PATH = "private-absolute-path"
LOG_SELF_DESCRIBING = "log-master-presented-as-self-describing"
LOG_EXPORT_BLOCKED = "log-interpretation-required"
PASS_THROUGH = "pass-through copy"
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_PRIVATE_PATH = re.compile(
    r"file://\S+"
    r"|[A-Za-z]:[\\/](?:[^\\/\s\"']+[\\/])*[^\s\"']*"
    r"|/(?:home|Users|data|storage|sdcard|var|private|opt|mnt|tmp)/[^\s\"']*"
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: Any, label: str, *, stripped: bool) -> str:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    if stripped:
        require(value == value.strip(), f"{label} must not have surrounding whitespace")
    return value


def require_bool(value: Any, label: str) -> bool:
    require(type(value) is bool, f"{label} must be a bool")
    return value


def require_hash(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and _HEX64.fullmatch(value) is not None,
        f"{label} must be {HASH_WIDTH} lowercase hex",
    )
    return value


def mentions_log(text: str) -> bool:
    """True when a label or filename says logc3 (any case) or Log."""
    return "logc3" in text.lower() or "Log" in text


def redact_text(text: str, identifiers: list[str]) -> tuple[str, bool]:
    updated = text
    changed = False
    for identifier in sorted(identifiers, key=len, reverse=True):
        if identifier in updated:
            updated = updated.replace(identifier, "[redacted-identifier]")
            changed = True
    redacted = _PRIVATE_PATH.sub("[redacted-path]", updated)
    if redacted != updated:
        changed = True
    return redacted, changed


def _optional_text(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label, stripped=True)


def _parse_manifest(manifest: Any) -> dict[str, Any]:
    require(isinstance(manifest, dict), "manifest must be an object")
    missing = MANIFEST_REQUIRED - set(manifest)
    extra = set(manifest) - set(MANIFEST_FIELDS)
    require(not missing, "manifest missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "manifest has unexpected fields: " + ", ".join(sorted(extra)))
    if "source_sha256" not in manifest or manifest["source_sha256"] is None or manifest["source_sha256"] == "":
        source = None
    else:
        source = require_hash(manifest["source_sha256"], "source_sha256")
    color = manifest["color_transfer"]
    require(color in COLOR_TRANSFERS, "color_transfer must be bt709, hlg, logc3, pq, or unknown")
    container = require_text(manifest["container"], "container", stripped=True)
    non_claims = manifest["non_claims"]
    require(isinstance(non_claims, list), "non_claims must be a list of strings")
    parsed_claims: list[str] = []
    for index, item in enumerate(non_claims):
        parsed_claims.append(require_text(item, f"non_claims[{index}]", stripped=False))
    return {
        "source_sha256": source,
        "recipe_version_sha256": require_hash(manifest["recipe_version_sha256"], "recipe_version_sha256"),
        "result_sha256": require_hash(manifest["result_sha256"], "result_sha256"),
        "color_transfer": color,
        "container": container,
        "non_claims": parsed_claims,
    }


def _parse_interpretation(value: Any, color_transfer: str) -> dict[str, str] | None:
    if value is None:
        return None
    require(isinstance(value, dict), "interpretation must be an object or null")
    require(set(value) == {"transfer", "note"}, "interpretation keys must be transfer and note")
    transfer = require_text(value["transfer"], "interpretation.transfer", stripped=True)
    note = require_text(value["note"], "interpretation.note", stripped=False)
    require(transfer == color_transfer, "interpretation.transfer must match color_transfer")
    return {"transfer": transfer, "note": note}


def _parse_string_list(value: Any, label: str, *, minimum: int) -> list[str]:
    require(isinstance(value, list), f"{label} must be a list of strings")
    parsed: list[str] = []
    for index, item in enumerate(value):
        text = require_text(item, f"{label}[{index}]", stripped=False)
        if minimum:
            require(len(text.strip()) >= minimum, f"{label}[{index}] is too short")
        parsed.append(text)
    return parsed


def judge_bundle(payload: dict) -> dict[str, Any]:
    """Judge one bundle manifest. Invalid shapes raise ValueError.

    ``source_sha256`` may be null. A null source blocks export and is rejected
    when ``export_allowed`` is true. Equal hashes with ``grade_applied`` false
    are a pass-through copy. Equal hashes with a grade are rejected.
    """
    require(isinstance(payload, dict), "payload must be an object")
    missing = BUNDLE_KEYS - set(payload)
    require(not missing, "bundle inputs missing: " + ", ".join(sorted(missing)))
    manifest = _parse_manifest(payload["manifest"])
    export_allowed = require_bool(payload["export_allowed"], "export_allowed")
    grade_applied = require_bool(payload["grade_applied"], "grade_applied")
    labels = _parse_string_list(payload["labels"], "labels", minimum=1)
    filename = require_text(payload["filename"], "filename", stripped=True)
    metadata_texts = _parse_string_list(payload["metadataTexts"], "metadataTexts", minimum=0)
    self_describing = require_bool(payload["selfDescribing"], "selfDescribing")
    publish_private = require_bool(payload["publishPrivatePaths"], "publishPrivatePaths")
    identifiers = _parse_string_list(payload["personalIdentifiers"], "personalIdentifiers", minimum=3)
    interpretation = _parse_interpretation(payload["interpretation"], manifest["color_transfer"])

    reasons: list[str] = []
    rejected: list[str] = []
    preserved: list[str] = []
    source = manifest["source_sha256"]
    result = manifest["result_sha256"]
    color = manifest["color_transfer"]

    if source is None:
        reasons.append("missing source_sha256 blocks export")
        if export_allowed:
            rejected.append(MISSING_SOURCE)
            reasons.append("rejected because export_allowed is true while source_sha256 is missing")
        else:
            reasons.append("export withheld")
    elif grade_applied and source == result:
        rejected.append(GRADED_SAME_HASH)
        reasons.append("identical hashes with grade_applied are rejected")
    elif grade_applied:
        reasons.append("grade applied; result_sha256 differs from source_sha256")
    elif source == result:
        reasons.append(PASS_THROUGH)
        preserved.append(PASS_THROUGH)
    else:
        rejected.append(UNGRADED_CHANGED)
        reasons.append("result_sha256 must equal source_sha256 when grade_applied is false")

    if color in DISPLAY_TRANSFERS and any(mentions_log(item) for item in [*labels, filename]):
        rejected.append(RELABEL)
        reasons.append(
            "relabel rejected: color_transfer " + color + " was labelled logc3 or Log"
        )

    if not any(REQUIRED_NON_CLAIM in item for item in manifest["non_claims"]):
        rejected.append(MISSING_NON_CLAIM)
        reasons.append('non_claims must include "not a physical S23 qualification"')

    if color == "logc3" and interpretation is None:
        reasons.append("required interpretation information is missing for LogC3")
        if self_describing:
            rejected.append(LOG_SELF_DESCRIBING)
            reasons.append(
                "a Log master without its interpretation record was presented as self-describing"
            )
        elif export_allowed:
            rejected.append(LOG_EXPORT_BLOCKED)
            reasons.append("export blocked until Log interpretation metadata is present")
        else:
            reasons.append("warning: LogC3 is not universally self-describing")
    elif interpretation is not None:
        reasons.append("interpretation transfer=" + interpretation["transfer"])
        preserved.append("interpretation=" + interpretation["note"])

    found_private = False
    for text in metadata_texts:
        redacted, changed = redact_text(text, identifiers)
        found_private = found_private or changed
        if redacted.strip():
            preserved.append("public=" + redacted)
    if found_private and publish_private:
        rejected.append(PRIVATE_PATH)
        reasons.append("private absolute paths or identifiers must not be published")
    elif found_private:
        reasons.append("public report sanitized without dropping technical provenance")

    if source is not None:
        preserved.append("source_sha256=" + source)
    preserved.append("recipe_version_sha256=" + manifest["recipe_version_sha256"])
    preserved.append("result_sha256=" + result)
    preserved.append("color_transfer=" + color)
    preserved.append("container=" + manifest["container"])
    for item in manifest["non_claims"]:
        preserved.append("non_claim=" + item)
    preserved.append("grade_applied=" + ("true" if grade_applied else "false"))
    preserved.append("export_allowed=" + ("true" if export_allowed else "false"))
    return {
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
    }


def host_questions() -> list[str]:
    return [
        "physical S23 measurement was not run",
        "fixed cadence, sensor-derived Log, ten-bit fidelity, film-stock fidelity, and cinema-camera equivalence are not claimed",
    ]


def seal(
    case_id: str,
    evidence: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    open_questions: list[str],
) -> dict[str, Any]:
    decision = "rejected" if rejected else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    require(decision not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(
        any("physical S23" in item and "not run" in item for item in open_questions),
        "physical S23 measurement must stay open",
    )
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": list(rejected),
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(result["decision"] not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    return result


def _assemble(
    case_id: str,
    evidence: str,
    claim: str,
    apply_mutant: bool,
    bundle: dict[str, Any],
) -> dict[str, Any]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "goal: " + GOAL,
    ]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    if apply_mutant:
        rejected.insert(0, MUTANT)
        reasons.append("mutant rejected: " + MUTANT)
    decision_recorded = not rejected
    if decision_recorded:
        reasons.append("method: " + METHOD)
        reasons.append("deliverable: " + DELIVERABLE)
    preserved = [evidence, claim]
    preserved.extend(bundle["preservedResults"])
    return seal(case_id, evidence, reasons, rejected, preserved, host_questions())


def _identity(payload: dict) -> tuple[str, str, bool]:
    evidence = require_text(payload["evidenceId"], "evidenceId", stripped=True)
    claim = require_text(payload["claim"], "claim", stripped=False)
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    return evidence, claim, apply_mutant


def assess(document: dict) -> dict[str, Any]:
    """Apply the phase oracle to one export-bundle document."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, apply_mutant = _identity(document)
    bundle = judge_bundle(document)
    return _assemble(PHASE, evidence, claim, apply_mutant, bundle)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one bundle payload. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId", stripped=True)
    evidence, claim, apply_mutant = _identity(payload)
    bundle = judge_bundle(payload)
    return _assemble(case_id, evidence, claim, apply_mutant, bundle)
