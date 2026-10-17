#!/usr/bin/env python3
"""P154 Survey public firmware and HAL information.

Host reference only. This module does not probe a device, does not flash a
device, and does not qualify a physical S23. A survey lists sources with url,
public, and what each source actually documents. phone_modified must be false.
Assuming a kernel source tree exposes every camera mode (claims_all_modes true)
is rejected. A source that is not public cannot be used as evidence. Architecture
notes may be recorded only as unverified against the user's phone.

A kernel source tree does not prove every camera algorithm, every sensor mode,
proprietary camera processing components, or behavior on the user's phone.
The decision is recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P154"
WORKSTREAM = 20
TITLE = "Survey public firmware and HAL information"
GOAL = "Research the device architecture without modifying the user’s phone."
METHOD = (
    "Inspect official architecture documentation, available source releases, public logs, "
    "and lawful device diagnostics. Record exact model and firmware applicability. Separate "
    "kernel source availability from access to proprietary camera processing components."
)
FIXTURE = "A public source package that lacks the proprietary imaging component needed for the proposed change."
ORACLE = (
    "The report records the missing component rather than claiming the source package is a "
    "complete camera firmware implementation."
)
MUTANT = "Assume publishing a kernel source tree exposes every camera algorithm and sensor mode."
DELIVERABLE = "Non-destructive architecture research report"
DEPENDENCIES = ("P153",)

PROPRIETARY_COMPONENT = "proprietary-imaging-component"
UNVERIFIED_NOTES = "unverified-against-user-phone"
OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p154-firmware-hal-survey"
CLAIM = "public-firmware-and-hal-survey-host-reference"

KERNEL_TREE_DOES_NOT_PROVE = (
    "every camera algorithm",
    "every sensor mode",
    "proprietary camera processing components",
    "behavior on the user's phone",
)

SURVEY_RULE = (
    "A survey lists sources with url, public bool, and what each source actually documents. "
    "phone_modified must be false. Assuming a kernel source tree exposes every camera mode "
    "(claims_all_modes true) is rejected. A source that is not public cannot be used as evidence. "
    "The report may record architecture notes only as unverified against the user's phone. "
    "A kernel source tree does not prove every camera algorithm, every sensor mode, proprietary "
    "camera processing components, or behavior on the user's phone. "
    "The decision is recorded or rejected, never qualified."
)

PHONE_MODIFIED = "phone-modified"
CLAIMS_ALL_MODES = "kernel-source-exposes-every-camera-mode"
NON_PUBLIC_EVIDENCE = "non-public-source-used-as-evidence"
NOTES_NOT_UNVERIFIED = "architecture-notes-not-unverified-against-phone"
MISSING_COMPONENT_UNRECORDED = "missing-proprietary-component-not-recorded"
COMPLETE_FIRMWARE_CLAIM = "source-package-called-complete-camera-firmware"

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
    "kernel source does not prove proprietary imaging or every sensor mode",
]
SOURCE_KEYS = {"url", "public", "documents"}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "sources",
    "phone_modified",
    "claims_all_modes",
    "usedAsEvidence",
    "architectureNotes",
    "notesStatus",
    "missingComponents",
    "claimsCompleteFirmware",
    "modelApplicability",
    "firmwareApplicability",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
DOCUMENT_KEYS = CORE_KEYS | {"schemaVersion", "phase", "implementationBaseRevision"}

ARCHITECTURE_NOTES = (
    "Public kernel packages and AOSP camera HAL documents describe interfaces and released "
    "source packages. They are recorded only as unverified against the user's phone. Kernel "
    "source availability is separated from access to proprietary camera processing components. "
    "A kernel source tree does not prove every camera algorithm, every sensor mode, or those "
    "proprietary components."
)
MODEL_APPLICABILITY = (
    "Not matched to a specific Galaxy S23 unit. A public kernel tree for one model or build "
    "does not establish every S23 variant."
)
FIRMWARE_APPLICABILITY = (
    "Unverified against the user's phone firmware. The source package version was not read "
    "from the device."
)

FAULT_TEXT = {
    PHONE_MODIFIED: "phone_modified must be false; the user's phone was not modified",
    CLAIMS_ALL_MODES: (
        "Assuming a kernel source tree exposes every camera mode (claims_all_modes true) is rejected"
    ),
    NON_PUBLIC_EVIDENCE: "a source that is not public cannot be used as evidence",
    NOTES_NOT_UNVERIFIED: (
        "architecture notes may be recorded only as unverified against the user's phone"
    ),
    MISSING_COMPONENT_UNRECORDED: ORACLE,
    COMPLETE_FIRMWARE_CLAIM: (
        "a source package that lacks the proprietary imaging component is not a complete "
        "camera firmware implementation"
    ),
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


def require_url(value: object, label: str) -> str:
    url = require_text(value, label)
    require(
        url.startswith("https://") or url.startswith("http://"),
        label + " must be an http(s) url",
    )
    return url


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def kernel_tree_does_not_prove() -> tuple[str, ...]:
    """What publishing a kernel source tree does not prove."""
    return KERNEL_TREE_DOES_NOT_PROVE


def parse_source(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"sources[{index}] must be an object")
    require(set(value) == SOURCE_KEYS, f"sources[{index}] keys are invalid")
    return {
        "url": require_url(value["url"], f"sources[{index}].url"),
        "public": require_bool(value["public"], f"sources[{index}].public"),
        "documents": require_text(value["documents"], f"sources[{index}].documents"),
    }


def parse_sources(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), "sources must be a non-empty list")
    sources = [parse_source(item, index) for index, item in enumerate(value)]
    urls = [source["url"] for source in sources]
    require(len(urls) == len(set(urls)), "source urls must be unique")
    return sources


def parse_string_list(value: object, label: str, *, allow_empty: bool) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    if not allow_empty:
        require(bool(value), label + " must be non-empty")
    items = [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    require(len(items) == len(set(items)), label + " entries must be unique")
    return items


def analyze_survey(
    *,
    sources: list[dict[str, Any]],
    phone_modified: bool,
    claims_all_modes: bool,
    used_as_evidence: list[str],
    notes_status: str,
    missing_components: list[str],
    claims_complete_firmware: bool,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Judge a public-firmware survey. Never returns a qualified decision."""
    by_url = {source["url"]: source for source in sources}
    faults: list[str] = []
    if phone_modified:
        faults.append(PHONE_MODIFIED)
    assumes_every_mode = claims_all_modes or apply_mutant
    if assumes_every_mode:
        faults.append(CLAIMS_ALL_MODES)
    non_public_evidence: list[str] = []
    for url in used_as_evidence:
        require(url in by_url, "usedAsEvidence cites an unknown source: " + url)
        if by_url[url]["public"] is not True:
            non_public_evidence.append(url)
    if non_public_evidence:
        faults.append(NON_PUBLIC_EVIDENCE)
    if notes_status != UNVERIFIED_NOTES:
        faults.append(NOTES_NOT_UNVERIFIED)
    proprietary_missing = PROPRIETARY_COMPONENT in missing_components
    if not proprietary_missing:
        faults.append(MISSING_COMPONENT_UNRECORDED)
    if claims_complete_firmware:
        faults.append(COMPLETE_FIRMWARE_CLAIM)
    public_sources = [source["url"] for source in sources if source["public"]]
    private_sources = [source["url"] for source in sources if not source["public"]]
    snapshot = {
        "sources": sources,
        "phone_modified": phone_modified,
        "claims_all_modes": claims_all_modes,
        "assumesEveryCameraMode": assumes_every_mode,
        "usedAsEvidence": list(used_as_evidence),
        "nonPublicEvidence": non_public_evidence,
        "publicSources": public_sources,
        "privateSources": private_sources,
        "missingComponents": list(missing_components),
        "proprietaryImagingRecordedMissing": proprietary_missing,
        "claimsCompleteFirmware": claims_complete_firmware,
        "notesStatus": notes_status,
        "architectureNotesUnverified": notes_status == UNVERIFIED_NOTES,
        "kernelTreeDoesNotProve": list(KERNEL_TREE_DOES_NOT_PROVE),
    }
    extra_reasons = [
        "survey rule: " + SURVEY_RULE,
        "a kernel source tree does not prove: " + "; ".join(KERNEL_TREE_DOES_NOT_PROVE),
        "phone_modified=" + str(phone_modified).lower(),
        "claims_all_modes=" + str(claims_all_modes).lower(),
        "architecture notes status: " + notes_status,
    ]
    if proprietary_missing and not claims_complete_firmware:
        extra_reasons.append(
            "missing component recorded: " + PROPRIETARY_COMPONENT + "; source package is not complete camera firmware"
        )
    if non_public_evidence:
        extra_reasons.append("non-public evidence rejected: " + ", ".join(non_public_evidence))
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    sources = parse_sources(mapping["sources"])
    phone_modified = require_bool(mapping["phone_modified"], "phone_modified")
    claims_all_modes = require_bool(mapping["claims_all_modes"], "claims_all_modes")
    used = parse_string_list(mapping["usedAsEvidence"], "usedAsEvidence", allow_empty=True)
    notes = require_text(mapping["architectureNotes"], "architectureNotes")
    notes_status = require_text(mapping["notesStatus"], "notesStatus")
    missing = parse_string_list(mapping["missingComponents"], "missingComponents", allow_empty=True)
    claims_complete = require_bool(mapping["claimsCompleteFirmware"], "claimsCompleteFirmware")
    model = require_text(mapping["modelApplicability"], "modelApplicability")
    firmware = require_text(mapping["firmwareApplicability"], "firmwareApplicability")
    analysis = analyze_survey(
        sources=sources,
        phone_modified=phone_modified,
        claims_all_modes=claims_all_modes,
        used_as_evidence=used,
        notes_status=notes_status,
        missing_components=missing,
        claims_complete_firmware=claims_complete,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["label"] = label
    analysis["architectureNotes"] = notes
    analysis["modelApplicability"] = model
    analysis["firmwareApplicability"] = firmware
    analysis["snapshot"]["architectureNotes"] = notes
    analysis["snapshot"]["modelApplicability"] = model
    analysis["snapshot"]["firmwareApplicability"] = firmware
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if analysis.get("applyMutant"):
        reasons.append("mutant rejected: " + MUTANT)
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("public firmware and HAL survey recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a non-destructive public firmware survey, or reject overclaims."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core public-firmware survey payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "implementationBaseRevision" in payload or "phase" in payload:
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _core_from_mapping(payload, "case")
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def fixture_sources() -> list[dict[str, Any]]:
    """Public packages and HAL documents. None of them is complete camera firmware."""
    return [
        {
            "url": "https://opensource.samsung.com/",
            "public": True,
            "documents": (
                "Samsung Open Source Release Center kernel and platform packages for announced "
                "models. The listing is kernel source availability, not Samsung proprietary camera "
                "processing and not every sensor mode."
            ),
        },
        {
            "url": "https://source.android.com/docs/core/camera",
            "public": True,
            "documents": (
                "AOSP camera architecture: camera HAL, camera device, and the request and stream "
                "model. This is a public interface contract, not an S23 imaging firmware image."
            ),
        },
        {
            "url": "https://source.android.com/docs/core/camera/camera3",
            "public": True,
            "documents": (
                "Public Camera HAL3 operation and request lifecycle. It does not disclose "
                "proprietary Samsung imaging components or prove the modes on a user's phone."
            ),
        },
    ]


def private_source() -> dict[str, Any]:
    return {
        "url": "https://example.invalid/samsung/private-camera-hal",
        "public": False,
        "documents": "Claimed internal camera HAL drop. Not a public source and not usable as evidence.",
    }


def core_payload(**overrides: Any) -> dict[str, Any]:
    sources = fixture_sources()
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "sources": sources,
        "phone_modified": False,
        "claims_all_modes": False,
        "usedAsEvidence": [source["url"] for source in sources],
        "architectureNotes": ARCHITECTURE_NOTES,
        "notesStatus": UNVERIFIED_NOTES,
        "missingComponents": [PROPRIETARY_COMPONENT],
        "claimsCompleteFirmware": False,
        "modelApplicability": MODEL_APPLICABILITY,
        "firmwareApplicability": FIRMWARE_APPLICABILITY,
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": core["evidenceId"],
        "claim": core["claim"],
        "applyMutant": False,
        "sources": core["sources"],
        "phone_modified": False,
        "claims_all_modes": False,
        "usedAsEvidence": core["usedAsEvidence"],
        "architectureNotes": core["architectureNotes"],
        "notesStatus": core["notesStatus"],
        "missingComponents": core["missingComponents"],
        "claimsCompleteFirmware": False,
        "modelApplicability": core["modelApplicability"],
        "firmwareApplicability": core["firmwareApplicability"],
    }
