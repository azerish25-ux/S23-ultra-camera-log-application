#!/usr/bin/env python3
"""P151 Generate honest release notes and capability badges.

Host reference only. This module does not probe a device and does not qualify
a physical S23. Every public claim has claim_id, badge, evidence_id or null,
and limit. Badges may be unavailable, experimental, or evidenced. Evidenced
requires a non-empty evidence_id and a limit string. A claim with evidence_id
null must not be in implemented_features. Unavailable must not read as shipped.
Copying an aspirational requirement into implemented_features is rejected.

Badge rule: badges may be unavailable, experimental, or evidenced. Evidenced
requires a non-empty evidence_id and a limit string. A claim with evidence_id
null must not be in implemented_features. Unavailable must not read as shipped.
Copying an aspirational requirement into implemented_features is rejected.
The decision is recorded or rejected, never qualified or allowed.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P151"
WORKSTREAM = 19
TITLE = "Generate honest release notes and capability badges"
GOAL = "Tie every public capability claim to current evidence and documented limits."
METHOD = (
    "Build release summaries from accepted records, including exact supported tuples and "
    "experimental features. Separate software tests from physical qualification. Keep known "
    "failures visible and avoid general camera-equivalence or universal-resolution language."
)
FIXTURE = (
    "A release with qualified SDR recording, experimental RAW development, and "
    "deferred-only depth effects."
)
ORACLE = (
    "The release notes reflect those scopes and do not advertise live RAW cinema capture "
    "or universal 8K support."
)
MUTANT = "Copy aspirational requirements directly into the implemented features list."
DELIVERABLE = "Evidence-driven release notes and claim audit"
DEPENDENCIES = ("P150",)

BADGE_RULE = (
    "Badges may be unavailable, experimental, or evidenced. Evidenced requires a non-empty "
    "evidence_id and a limit string. A claim with evidence_id null must not be in "
    "implemented_features. Unavailable must not read as shipped. Copying an aspirational "
    "requirement into implemented_features is rejected."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p151-release-notes"
CLAIM = "honest-release-notes-and-capability-badges"

BADGES = frozenset({"unavailable", "experimental", "evidenced"})
SDR_ID = "sdr-recording"
RAW_ID = "raw-development"
DEPTH_ID = "depth-effects"
LIVE_RAW_ID = "live-raw-cinema-capture"
UNIVERSAL_8K_ID = "universal-8k"
SDR_LIMIT = (
    "qualified SDR recording; software tests are separate from physical qualification; "
    "not universal 8K"
)
RAW_LIMIT = "experimental RAW development; not live RAW cinema capture"
DEPTH_LIMIT = "deferred-only depth effects"
KNOWN_FAILURES = (
    "physical S23 was not run",
    "live RAW cinema capture is not supported",
    "universal 8K is not supported",
)
ASPIRATIONAL = (LIVE_RAW_ID, UNIVERSAL_8K_ID)

NULL_EVIDENCE_IMPLEMENTED = "null-evidence-in-implemented-features"
ASPIRATIONAL_COPIED = "aspirational-requirement-copied-into-implemented"
UNAVAILABLE_SHIPPED = "unavailable-reads-as-shipped"
EXPERIMENTAL_IMPLEMENTED = "experimental-listed-as-implemented"
SCOPE_NOT_REFLECTED = "release-scopes-not-reflected"
LIVE_RAW_ADVERTISED = "live-raw-cinema-capture-advertised"
UNIVERSAL_8K_ADVERTISED = "universal-8k-advertised"
CAMERA_EQUIVALENCE = "camera-equivalence-language"
UNIVERSAL_RESOLUTION = "universal-resolution-language"

HIGH_COVERAGE = 0.8
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000

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
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "claims",
    "implementedFeatures",
    "aspirationalRequirements",
    "knownFailures",
}
CORE_KEYS = {
    "evidenceId",
    "claim",
    "applyMutant",
    "claims",
    "implementedFeatures",
    "aspirationalRequirements",
    "knownFailures",
}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
CLAIM_KEYS = {"claim_id", "badge", "evidence_id", "limit"}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence", "universal-resolution"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}

FORBIDDEN_PHRASES = (
    ("live raw cinema capture", LIVE_RAW_ADVERTISED),
    ("universal 8k", UNIVERSAL_8K_ADVERTISED),
    ("camera-equivalence", CAMERA_EQUIVALENCE),
    ("camera equivalence", CAMERA_EQUIVALENCE),
    ("universal-resolution", UNIVERSAL_RESOLUTION),
    ("universal resolution", UNIVERSAL_RESOLUTION),
)
SHIPPED_PHRASES = ("shipped", "generally available", "production ready", "production-ready")

FAULT_TEXT = {
    NULL_EVIDENCE_IMPLEMENTED: (
        "a claim with evidence_id null must not be in implemented_features"
    ),
    ASPIRATIONAL_COPIED: MUTANT,
    UNAVAILABLE_SHIPPED: "unavailable must not read as shipped",
    EXPERIMENTAL_IMPLEMENTED: "an experimental capability is not an implemented feature",
    SCOPE_NOT_REFLECTED: ORACLE,
    LIVE_RAW_ADVERTISED: "release notes must not advertise live RAW cinema capture",
    UNIVERSAL_8K_ADVERTISED: "release notes must not advertise universal 8K support",
    CAMERA_EQUIVALENCE: "avoid general camera-equivalence language",
    UNIVERSAL_RESOLUTION: "avoid universal-resolution language",
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


def require_int(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
    return value


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def _negated(text: str, start: int, end: int) -> bool:
    before = text[max(0, start - 16):start].rstrip()
    after = text[end:end + 24].lstrip()
    if before.endswith("not") or before.endswith("no") or before.endswith("without"):
        return True
    if after.startswith("is not") or after.startswith("are not") or after.startswith("not "):
        return True
    return False


def advertises(text: str, phrase: str) -> bool:
    """True when phrase appears without an immediate negation."""
    if not isinstance(text, str) or not isinstance(phrase, str) or not phrase:
        return False
    lowered = text.casefold()
    needle = phrase.casefold()
    start = 0
    while True:
        index = lowered.find(needle, start)
        if index < 0:
            return False
        end = index + len(needle)
        if not _negated(lowered, index, end):
            return True
        start = end


def parse_claim(value: object, index: int) -> dict[str, Any]:
    require(isinstance(value, dict), f"claims[{index}] must be an object")
    require(set(value) == CLAIM_KEYS, f"claims[{index}] keys are invalid")
    claim_id = require_text(value["claim_id"], f"claims[{index}].claim_id")
    badge = require_text(value["badge"], f"claims[{index}].badge")
    require(badge in BADGES, f"claims[{index}].badge is not unavailable, experimental, or evidenced")
    evidence = value["evidence_id"]
    if evidence is not None:
        evidence = require_text(evidence, f"claims[{index}].evidence_id")
    limit = value["limit"]
    require(isinstance(limit, str), f"claims[{index}].limit must be a string")
    require(limit == limit.strip(), f"claims[{index}].limit must not have surrounding whitespace")
    if badge == "evidenced":
        require(evidence is not None, "evidenced requires a non-empty evidence_id")
        require(bool(limit), "evidenced requires a limit string")
    if badge == "experimental":
        require(bool(limit), "experimental requires a limit string")
    return {
        "claim_id": claim_id,
        "badge": badge,
        "evidence_id": evidence,
        "limit": limit,
    }


def parse_claims(value: object) -> list[dict[str, Any]]:
    require(isinstance(value, list), "claims must be a list")
    claims = [parse_claim(item, index) for index, item in enumerate(value)]
    ids = [claim["claim_id"] for claim in claims]
    require(len(ids) == len(set(ids)), "claim_id values must be unique")
    return claims


def parse_id_list(value: object, label: str) -> list[str]:
    require(isinstance(value, list), label + " must be a list")
    ids = [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]
    require(len(ids) == len(set(ids)), label + " entries must be unique")
    return ids


def _public_texts(claims: list[dict[str, Any]], implemented: list[str]) -> list[str]:
    texts: list[str] = []
    for claim in claims:
        texts.append(claim["limit"])
        if claim["badge"] != "unavailable":
            texts.append(claim["claim_id"].replace("-", " "))
    for feature_id in implemented:
        texts.append(feature_id.replace("-", " "))
    return texts


def _scopes_reflected(by_id: dict[str, dict[str, Any]], implemented: list[str]) -> bool:
    sdr = by_id.get(SDR_ID)
    raw = by_id.get(RAW_ID)
    depth = by_id.get(DEPTH_ID)
    if sdr is None or raw is None or depth is None:
        return False
    sdr_limit = sdr["limit"].casefold()
    raw_limit = raw["limit"].casefold()
    depth_limit = depth["limit"].casefold()
    sdr_ok = (
        sdr["badge"] == "evidenced"
        and sdr["evidence_id"] is not None
        and SDR_ID in implemented
        and "sdr" in sdr_limit
        and "qualified" in sdr_limit
        and "separate" in sdr_limit
    )
    raw_ok = (
        raw["badge"] == "experimental"
        and RAW_ID not in implemented
        and "experimental" in raw_limit
        and "raw" in raw_limit
    )
    depth_ok = (
        depth["badge"] == "experimental"
        and DEPTH_ID not in implemented
        and ("deferred-only" in depth_limit or "deferred only" in depth_limit)
    )
    return sdr_ok and raw_ok and depth_ok


def _reads_as_shipped(claim: dict[str, Any], implemented: list[str]) -> bool:
    if claim["badge"] != "unavailable":
        return False
    if claim["claim_id"] in implemented:
        return True
    return any(advertises(claim["limit"], phrase) for phrase in SHIPPED_PHRASES)


def release_lines(
    claims: list[dict[str, Any]],
    implemented: list[str],
    known_failures: list[str],
) -> list[str]:
    """Honest notes: badge, evidence, and limit stay attached to every claim."""
    lines: list[str] = []
    for claim in claims:
        if claim["claim_id"] in implemented:
            status = "implemented"
        else:
            status = claim["badge"]
        evidence = claim["evidence_id"] if claim["evidence_id"] is not None else "none"
        lines.append(
            claim["claim_id"]
            + ": "
            + status
            + "; badge "
            + claim["badge"]
            + "; evidence "
            + evidence
            + "; limit "
            + claim["limit"]
        )
    for failure in known_failures:
        lines.append("known failure: " + failure)
    return lines


def analyze_computation(
    *,
    claims: list[dict[str, Any]],
    implemented: list[str],
    aspirational: list[str],
    known_failures: list[str],
    apply_mutant: bool,
) -> dict[str, Any]:
    by_id = {claim["claim_id"]: claim for claim in claims}
    for feature_id in implemented:
        require(
            feature_id in by_id or feature_id in aspirational,
            "implementedFeatures entry is not a claim or aspirational requirement: " + feature_id,
        )
    effective = list(implemented)
    if apply_mutant:
        for feature_id in aspirational:
            if feature_id not in effective:
                effective.append(feature_id)
    faults: list[str] = []
    reflected = _scopes_reflected(by_id, effective)
    if not reflected:
        faults.append(SCOPE_NOT_REFLECTED)
    for feature_id in effective:
        claim = by_id.get(feature_id)
        if claim is None:
            continue
        if claim["evidence_id"] is None:
            faults.append(NULL_EVIDENCE_IMPLEMENTED)
        if claim["badge"] == "experimental":
            faults.append(EXPERIMENTAL_IMPLEMENTED)
        if _reads_as_shipped(claim, effective):
            faults.append(UNAVAILABLE_SHIPPED)
    for claim in claims:
        if claim["claim_id"] in effective:
            continue
        if _reads_as_shipped(claim, effective):
            faults.append(UNAVAILABLE_SHIPPED)
    copied = [feature_id for feature_id in aspirational if feature_id in effective]
    if copied or apply_mutant:
        faults.append(ASPIRATIONAL_COPIED)
    advertised: list[str] = []
    for text in _public_texts(claims, effective):
        for phrase, token in FORBIDDEN_PHRASES:
            if advertises(text, phrase):
                advertised.append(token)
    faults.extend(advertised)
    notes = release_lines(claims, effective, known_failures)
    snapshot = {
        "badges": {claim["claim_id"]: claim["badge"] for claim in claims},
        "evidenceIds": {claim["claim_id"]: claim["evidence_id"] for claim in claims},
        "limits": {claim["claim_id"]: claim["limit"] for claim in claims},
        "implementedFeatures": effective,
        "submittedImplementedFeatures": list(implemented),
        "aspirationalRequirements": list(aspirational),
        "aspirationalCopied": copied,
        "knownFailures": list(known_failures),
        "scopesReflected": reflected,
        "releaseNotes": notes,
        "physicalS23Run": False,
        "applyMutant": apply_mutant,
    }
    extra_reasons = [
        "badge rule: " + BADGE_RULE,
        "release notes keep known failures visible",
        "software tests are separate from physical qualification",
    ]
    if reflected:
        extra_reasons.append(
            "scopes reflected: qualified SDR recording, experimental RAW development, "
            "deferred-only depth effects"
        )
    if copied:
        extra_reasons.append("aspirational requirements copied: " + ", ".join(copied))
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
    require(result["decision"] != "qualified", "decision is never qualified")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    apply_mutant = require_bool(mapping["applyMutant"], "applyMutant")
    claims = parse_claims(mapping["claims"])
    implemented = parse_id_list(mapping["implementedFeatures"], "implementedFeatures")
    aspirational = parse_id_list(mapping["aspirationalRequirements"], "aspirationalRequirements")
    known = parse_id_list(mapping["knownFailures"], "knownFailures") if mapping["knownFailures"] else []
    require(isinstance(mapping["knownFailures"], list), "knownFailures must be a list")
    if not mapping["knownFailures"]:
        known = []
    analysis = analyze_computation(
        claims=claims,
        implemented=implemented,
        aspirational=aspirational,
        known_failures=known,
        apply_mutant=apply_mutant,
    )
    analysis["evidence"] = evidence
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
        reasons.append("honest release notes recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record honest release notes, or reject claims that outrun evidence."""
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
    if ASPIRATIONAL_COPIED in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core release-notes payload."""
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


def fixture_claims() -> list[dict[str, Any]]:
    return [
        {
            "claim_id": SDR_ID,
            "badge": "evidenced",
            "evidence_id": "ev-sdr-recording",
            "limit": SDR_LIMIT,
        },
        {
            "claim_id": RAW_ID,
            "badge": "experimental",
            "evidence_id": "ev-raw-development",
            "limit": RAW_LIMIT,
        },
        {
            "claim_id": DEPTH_ID,
            "badge": "experimental",
            "evidence_id": "ev-depth-effects",
            "limit": DEPTH_LIMIT,
        },
    ]


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "claims": fixture_claims(),
        "implementedFeatures": [SDR_ID],
        "aspirationalRequirements": list(ASPIRATIONAL),
        "knownFailures": list(KNOWN_FAILURES),
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
        "claims": core["claims"],
        "implementedFeatures": core["implementedFeatures"],
        "aspirationalRequirements": core["aspirationalRequirements"],
        "knownFailures": core["knownFailures"],
    }
