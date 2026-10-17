#!/usr/bin/env python3
"""P152 Run the production readiness review.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A dossier lists risks with severity critical|major|minor and
status open|accepted|closed. An open critical risk blocks release
(release_decision must be hold). Waiving a critical data-loss issue (severity
critical, status accepted, reason looks_convincing or empty) is rejected.
Release go is recorded only when no open critical risks remain and the decision
cites the risk ids. Promotional footage is not evidence. The decision is never
qualified or allowed.

Release rule: an open critical risk blocks release, so release_decision must be
hold. A critical data-loss waiver whose reason is looks_convincing or empty is
rejected. A go is recorded only with no open critical risk and every risk id
cited. Promotional footage is not evidence. Preservation must be fixed and
regression evidence must exist before a go. Visual quality cannot waive a
data-loss gate.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P152"
WORKSTREAM = 19
TITLE = "Run the production readiness review"
GOAL = "Make a deliberate release decision based on critical risks and complete workflows."
METHOD = (
    "Review footage retention, crash recovery, color signalling, temporal artifacts, "
    "licensing, privacy, accessibility, and update safety. Resolve or explicitly defer "
    "noncritical issues. A critical data-loss or misleading-capture defect blocks release "
    "regardless of visual quality."
)
FIXTURE = "A visually excellent build that occasionally deletes the only staging copy after a failed publication."
ORACLE = "The release is blocked until preservation is fixed and regression evidence exists."
MUTANT = "Waive a critical data-loss issue because promotional footage looks convincing."
DELIVERABLE = "Production readiness dossier and signed-off decision record"
DEPENDENCIES = ("P151",)

RELEASE_RULE = (
    "An open critical risk blocks release (release_decision must be hold). "
    "Waiving a critical data-loss issue (severity critical, status accepted, reason "
    "looks_convincing or empty) is rejected. Release go is recorded only when no open "
    "critical risks remain and the decision cites the risk ids. Promotional footage is "
    "not evidence. The decision is never qualified."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p152-production-readiness"
CLAIM = "production-readiness-review-host-reference"

OPEN_CRITICAL_REQUIRES_HOLD = "open-critical-requires-hold"
DATA_LOSS_WAIVER_REJECTED = "critical-data-loss-waiver-rejected"
CRITICAL_DEFECT_BLOCKS = "critical-defect-blocks-release"
RISK_IDS_NOT_CITED = "risk-ids-not-cited"
PRESERVATION_NOT_FIXED = "preservation-not-fixed"
PROMOTIONAL_FOOTAGE = "promotional-footage-not-evidence"
NONCRITICAL_OPEN = "noncritical-not-resolved-or-deferred"
DEFERRAL_NOT_EXPLICIT = "deferral-not-explicit"
REVIEW_AREA_MISSING = "review-area-missing"
VISUAL_QUALITY_CANNOT_WAIVE = "visual-quality-cannot-waive"
DATA_LOSS_RISK_MISSING = "critical-data-loss-risk-missing"

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
]
SEVERITIES = frozenset({"critical", "major", "minor"})
STATUSES = frozenset({"open", "accepted", "closed"})
RELEASE_DECISIONS = frozenset({"go", "hold"})
REVIEW_AREAS = (
    "footage-retention",
    "crash-recovery",
    "color-signalling",
    "temporal-artifacts",
    "licensing",
    "privacy",
    "accessibility",
    "update-safety",
)
CATEGORIES = frozenset({
    "data-loss",
    "misleading-capture",
    *REVIEW_AREAS,
})
BLOCKING_CATEGORIES = frozenset({"data-loss", "misleading-capture"})
EVIDENCE_KINDS = frozenset({
    "regression",
    "host-test",
    "workflow",
    "promotional-footage",
})
WAIVER_REASONS = frozenset({"", "looks_convincing"})
RISK_KEYS = {"id", "area", "severity", "status", "category", "reason"}
EVIDENCE_ITEM_KEYS = {"id", "kind"}
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "visualQuality",
    "release_decision",
    "citedRiskIds",
    "risks",
    "evidence",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "visualQuality",
    "release_decision",
    "citedRiskIds",
    "risks",
    "evidence",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}

RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}
HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000

FAULT_TEXT = {
    OPEN_CRITICAL_REQUIRES_HOLD: (
        "an open critical risk blocks release; release_decision must be hold"
    ),
    DATA_LOSS_WAIVER_REJECTED: (
        "waiving a critical data-loss issue with reason looks_convincing or empty is rejected"
    ),
    CRITICAL_DEFECT_BLOCKS: (
        "a critical data-loss or misleading-capture defect blocks release regardless of visual quality"
    ),
    RISK_IDS_NOT_CITED: "the decision must cite every risk id",
    PRESERVATION_NOT_FIXED: ORACLE,
    PROMOTIONAL_FOOTAGE: "promotional footage is not evidence",
    NONCRITICAL_OPEN: "noncritical issues must be resolved or explicitly deferred",
    DEFERRAL_NOT_EXPLICIT: (
        "an accepted issue needs an explicit reason that is not looks_convincing or empty"
    ),
    REVIEW_AREA_MISSING: "the readiness review must cover every required workflow area",
    VISUAL_QUALITY_CANNOT_WAIVE: "visual quality cannot waive a critical data-loss defect",
    DATA_LOSS_RISK_MISSING: "the dossier must list the critical data-loss risk",
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


def require_reason(value: object, label: str) -> str:
    require(isinstance(value, str) and value == value.strip(), label + " must be an empty or trimmed string")
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_int(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def waiver_reason(reason: str) -> bool:
    return reason.casefold() in WAIVER_REASONS or reason.casefold() == "looks_convincing"


def parse_risks(value: object) -> list[dict[str, str]]:
    require(isinstance(value, list) and bool(value), "risks must be a non-empty list")
    risks: list[dict[str, str]] = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"risks[{index}] must be an object")
        require(set(item) == RISK_KEYS, f"risks[{index}] keys are invalid")
        severity = require_text(item["severity"], f"risks[{index}].severity")
        status = require_text(item["status"], f"risks[{index}].status")
        area = require_text(item["area"], f"risks[{index}].area")
        category = require_text(item["category"], f"risks[{index}].category")
        require(severity in SEVERITIES, f"risks[{index}].severity is not recognized")
        require(status in STATUSES, f"risks[{index}].status is not recognized")
        require(area in REVIEW_AREAS, f"risks[{index}].area is not recognized")
        require(category in CATEGORIES, f"risks[{index}].category is not recognized")
        risks.append({
            "id": require_text(item["id"], f"risks[{index}].id"),
            "area": area,
            "severity": severity,
            "status": status,
            "category": category,
            "reason": require_reason(item["reason"], f"risks[{index}].reason"),
        })
    ids = [risk["id"] for risk in risks]
    require(len(ids) == len(set(ids)), "risk ids must be unique")
    return risks


def parse_cited(value: object, risk_ids: list[str]) -> list[str]:
    require(isinstance(value, list), "citedRiskIds must be a list")
    cited = [require_text(item, f"citedRiskIds[{index}]") for index, item in enumerate(value)]
    require(len(cited) == len(set(cited)), "citedRiskIds must be unique")
    unknown = [item for item in cited if item not in risk_ids]
    require(not unknown, "citedRiskIds names an unknown risk: " + ", ".join(unknown))
    return cited


def parse_evidence(value: object) -> list[dict[str, str]]:
    require(isinstance(value, list), "evidence must be a list")
    rows: list[dict[str, str]] = []
    for index, item in enumerate(value):
        require(isinstance(item, dict), f"evidence[{index}] must be an object")
        require(set(item) == EVIDENCE_ITEM_KEYS, f"evidence[{index}] keys are invalid")
        kind = require_text(item["kind"], f"evidence[{index}].kind")
        require(kind in EVIDENCE_KINDS, f"evidence[{index}].kind is not recognized")
        rows.append({
            "id": require_text(item["id"], f"evidence[{index}].id"),
            "kind": kind,
        })
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)), "evidence ids must be unique")
    return rows


def analyze_computation(
    risks: list[dict[str, str]],
    cited: list[str],
    evidence: list[dict[str, str]],
    release_decision: str,
    visual_quality: str,
    apply_mutant: bool,
) -> dict[str, Any]:
    """Apply the production-readiness release rule to one dossier."""
    faults: list[str] = []
    risk_ids = [risk["id"] for risk in risks]
    missing = [risk_id for risk_id in risk_ids if risk_id not in set(cited)]
    if missing:
        faults.append(RISK_IDS_NOT_CITED)

    present_areas = {risk["area"] for risk in risks}
    missing_areas = [area for area in REVIEW_AREAS if area not in present_areas]
    if missing_areas:
        faults.append(REVIEW_AREA_MISSING)

    open_critical = [
        risk["id"] for risk in risks if risk["severity"] == "critical" and risk["status"] == "open"
    ]
    if open_critical and release_decision != "hold":
        faults.append(OPEN_CRITICAL_REQUIRES_HOLD)

    critical_data_loss = [
        risk for risk in risks if risk["severity"] == "critical" and risk["category"] == "data-loss"
    ]
    if not critical_data_loss:
        faults.append(DATA_LOSS_RISK_MISSING)

    waived: list[str] = []
    for risk in risks:
        bad_reason = waiver_reason(risk["reason"])
        if risk["status"] == "accepted" and bad_reason:
            if risk["severity"] == "critical" and risk["category"] == "data-loss":
                faults.append(DATA_LOSS_WAIVER_REJECTED)
                waived.append(risk["id"])
            else:
                faults.append(DEFERRAL_NOT_EXPLICIT)
        if risk["severity"] in {"major", "minor"} and risk["status"] == "open":
            faults.append(NONCRITICAL_OPEN)
        blocking = risk["severity"] == "critical" and risk["category"] in BLOCKING_CATEGORIES
        if blocking and risk["status"] != "closed" and release_decision == "go":
            faults.append(CRITICAL_DEFECT_BLOCKS)

    promotional = [item["id"] for item in evidence if item["kind"] == "promotional-footage"]
    if promotional:
        faults.append(PROMOTIONAL_FOOTAGE)
    regression = [item["id"] for item in evidence if item["kind"] == "regression"]
    preservation_fixed = bool(critical_data_loss) and all(
        risk["status"] == "closed" and not waiver_reason(risk["reason"]) for risk in critical_data_loss
    ) and bool(regression)
    data_loss_open = any(risk["status"] != "closed" for risk in critical_data_loss)
    if release_decision == "go" and not preservation_fixed:
        faults.append(PRESERVATION_NOT_FIXED)
    if (
        visual_quality.casefold() == "excellent"
        and data_loss_open
        and release_decision == "go"
    ):
        faults.append(VISUAL_QUALITY_CANNOT_WAIVE)
    if apply_mutant:
        faults.append(DATA_LOSS_WAIVER_REJECTED)
        faults.append(PROMOTIONAL_FOOTAGE)
        if visual_quality.casefold() == "excellent":
            faults.append(VISUAL_QUALITY_CANNOT_WAIVE)

    data_loss_rows = [
        {"id": risk["id"], "status": risk["status"], "reason": risk["reason"]}
        for risk in critical_data_loss
    ]
    snapshot = {
        "release_decision": release_decision,
        "openCriticalIds": open_critical,
        "citedRiskIds": list(cited),
        "missingCitations": missing,
        "missingAreas": missing_areas,
        "preservationFixed": preservation_fixed,
        "regressionEvidenceIds": regression,
        "promotionalFootageIds": promotional,
        "waivedDataLossIds": waived,
        "visualQuality": visual_quality,
        "dataLoss": data_loss_rows,
        "mutantApplied": apply_mutant,
    }
    extra_reasons = [
        "release rule: " + RELEASE_RULE,
        "release_decision " + release_decision,
        "open critical " + (", ".join(open_critical) if open_critical else "none"),
        "cited " + str(len(cited)) + " of " + str(len(risk_ids)) + " risk ids",
    ]
    if preservation_fixed:
        extra_reasons.append(
            "preservation fixed; regression evidence " + ", ".join(regression)
        )
    else:
        extra_reasons.append("preservation is not fixed; " + ORACLE)
    if promotional:
        extra_reasons.append("promotional footage is not evidence: " + ", ".join(promotional))
    if waived:
        extra_reasons.append("critical data-loss waiver rejected: " + ", ".join(waived))
    if waived or apply_mutant:
        extra_reasons.append("mutant rejected: " + MUTANT)
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
    evidence_id = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    visual_quality = require_text(mapping["visualQuality"], "visualQuality")
    release_decision = require_text(mapping["release_decision"], "release_decision")
    require(
        release_decision in RELEASE_DECISIONS,
        "release_decision must be go or hold, never qualified or allowed",
    )
    risks = parse_risks(mapping["risks"])
    cited = parse_cited(mapping["citedRiskIds"], [risk["id"] for risk in risks])
    evidence_rows = parse_evidence(mapping["evidence"])
    analysis = analyze_computation(
        risks,
        cited,
        evidence_rows,
        release_decision,
        visual_quality,
        apply_mutant,
    )
    analysis["evidence"] = evidence_id
    analysis["claim"] = claim
    analysis["applyMutant"] = apply_mutant
    analysis["label"] = label
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        decision = analysis["snapshot"]["release_decision"]
        if decision == "go":
            reasons.append(
                "release go recorded; no open critical risks remain and the decision cites the risk ids"
            )
        else:
            reasons.append("release hold recorded because an open critical risk blocks release")
        reasons.append("production readiness dossier recorded; not a physical qualification")
    if DATA_LOSS_WAIVER_REJECTED in analysis["faults"] or analysis.get("applyMutant"):
        reasons.append(MUTANT)
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a go or an honest hold, or reject a dossier that breaks the release rule."""
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
    """Evaluate a phase document or a core production-readiness payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if (
        "schemaVersion" in payload
        or "implementationBaseRevision" in payload
        or "phase" in payload
    ):
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


def fixture_risks() -> list[dict[str, str]]:
    return [
        {
            "id": "staging-copy-deleted",
            "area": "footage-retention",
            "severity": "critical",
            "status": "closed",
            "category": "data-loss",
            "reason": "preservation fixed and regression evidence exists",
        },
        {
            "id": "crash-checkpoint",
            "area": "crash-recovery",
            "severity": "major",
            "status": "accepted",
            "category": "crash-recovery",
            "reason": "deferred with explicit recovery checkpoint retained",
        },
        {
            "id": "color-range",
            "area": "color-signalling",
            "severity": "major",
            "status": "closed",
            "category": "misleading-capture",
            "reason": "legal-range signalling corrected before release",
        },
        {
            "id": "temporal-cadence",
            "area": "temporal-artifacts",
            "severity": "minor",
            "status": "closed",
            "category": "temporal-artifacts",
            "reason": "cadence gaps remain visible and are not hidden",
        },
        {
            "id": "license-attribution",
            "area": "licensing",
            "severity": "minor",
            "status": "closed",
            "category": "licensing",
            "reason": "reference media attribution recorded",
        },
        {
            "id": "offline-privacy",
            "area": "privacy",
            "severity": "major",
            "status": "closed",
            "category": "privacy",
            "reason": "offline default transmits no private media",
        },
        {
            "id": "focus-order",
            "area": "accessibility",
            "severity": "minor",
            "status": "closed",
            "category": "accessibility",
            "reason": "focus order matches the camera screen hierarchy",
        },
        {
            "id": "signed-update",
            "area": "update-safety",
            "severity": "major",
            "status": "closed",
            "category": "update-safety",
            "reason": "signed update preserves sources profiles and recovery data",
        },
    ]


def fixture_evidence() -> list[dict[str, str]]:
    return [
        {"id": "regression-staging-copy", "kind": "regression"},
        {"id": "workflow-review", "kind": "workflow"},
    ]


def cited_for(risks: list[dict[str, str]]) -> list[str]:
    return [risk["id"] for risk in risks]


def replace_risk(risk_id: str, **overrides: Any) -> list[dict[str, str]]:
    risks = fixture_risks()
    found = False
    for risk in risks:
        if risk["id"] == risk_id:
            risk.update(overrides)
            found = True
    require(found, "unknown risk " + risk_id)
    return risks


def core_payload(**overrides: Any) -> dict[str, Any]:
    risks = fixture_risks()
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "visualQuality": "excellent",
        "release_decision": "go",
        "citedRiskIds": cited_for(risks),
        "risks": risks,
        "evidence": fixture_evidence(),
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
        "visualQuality": core["visualQuality"],
        "release_decision": core["release_decision"],
        "citedRiskIds": core["citedRiskIds"],
        "risks": core["risks"],
        "evidence": core["evidence"],
    }
