#!/usr/bin/env python3
"""P006 risk register and phase-entry decision assessor.

High-risk work is conditional on demonstrated benefit, not fascination with
low-level access. Reversible experiments are assessed first. A firmware
proposal that lacks an identified blocked stream and a verified recovery
procedure is deferred. User enthusiasm is not flash authorization.

This module does not qualify a physical S23, authorize a firmware flash, or
execute acceptance cases TC-P006-01 through TC-P006-08. Those cases belong to
separate gate modules.
"""
from __future__ import annotations

import math
import re
from typing import Any

RISK_IDS = (
    "footage_loss",
    "misleading_labels",
    "thermal_load",
    "rendering_instability",
    "licensing",
    "firmware_modification",
)
REGISTER_ID = "s23-risk-register"
BASE_REVISION = "fffd5c9a63cb732e103052acae29ae0c251585cc"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
REGISTER_KEYS = {"schemaVersion", "phase", "registerId", "implementationBaseRevision", "risks"}
RISK_KEYS = {"id", "title", "irreversible", "stopCondition", "requiredEvidence", "reversibleAlternative"}
LOG_KEYS = {"schemaVersion", "phase", "decisions"}
DECISION_KEYS = {
    "id", "riskId", "proposal", "irreversible", "blockedStreamIdentified",
    "recoveryProcedureVerified", "authorizedByEnthusiasmOnly", "alternatives",
    "evidence", "resourceCost", "fallback", "stopCondition", "decision", "rationale",
}
PROPOSAL_KEYS = DECISION_KEYS - {"id", "decision", "rationale"}
COST_KEYS = {"value", "unit", "domain"}
BOOL_FIELDS = (
    "irreversible",
    "blockedStreamIdentified",
    "recoveryProcedureVerified",
    "authorizedByEnthusiasmOnly",
)
RESULT_KEYS = ("decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, f"{context} missing fields: {', '.join(sorted(missing))}")
    require(not extra, f"{context} has unexpected fields: {', '.join(sorted(extra))}")
    return value


def string_list(value: object, context: str) -> None:
    require(isinstance(value, list) and all(text(item) for item in value),
            context + " must be a list of non-empty strings")


def validate_register(register: dict) -> None:
    exact_keys(register, REGISTER_KEYS, "register")
    require(type(register["schemaVersion"]) is int and register["schemaVersion"] == 1
            and register["phase"] == "P006", "Unsupported risk register")
    require(register["registerId"] == REGISTER_ID, "Unexpected risk register id")
    require(register["implementationBaseRevision"] == BASE_REVISION
            and HEX40.fullmatch(register["implementationBaseRevision"] or "") is not None,
            "Risk register needs the P006 implementation base revision")
    require(isinstance(register["risks"], list), "Risks must be a list")
    seen: dict[str, dict] = {}
    for item in register["risks"]:
        exact_keys(item, RISK_KEYS, "risk")
        require(text(item["id"]) and item["id"] not in seen, "Risk needs a unique id")
        require(text(item["title"]) and text(item["stopCondition"]) and text(item["reversibleAlternative"]),
                "Risk " + item["id"] + " needs title, stop condition, and reversible alternative")
        require(type(item["irreversible"]) is bool, "Risk " + item["id"] + " irreversible must be a boolean")
        string_list(item["requiredEvidence"], "Risk " + item["id"] + " requiredEvidence")
        require(item["requiredEvidence"], "Risk " + item["id"] + " needs required evidence")
        seen[item["id"]] = item
    require([item["id"] for item in register["risks"]] == list(RISK_IDS),
            "Risk register must list the six P006 risks in canonical order")
    require(seen["firmware_modification"]["irreversible"] is True,
            "Firmware modification is an irreversible risk")


def _proposal_shape(proposal: dict) -> None:
    exact_keys(proposal, PROPOSAL_KEYS, "proposal")
    require(text(proposal["riskId"]), "Proposal riskId is required")
    require(text(proposal["proposal"]), "Proposal text is required")
    for key in BOOL_FIELDS:
        require(type(proposal[key]) is bool, "Proposal " + key + " must be a boolean")
    string_list(proposal["alternatives"], "Proposal alternatives")
    string_list(proposal["evidence"], "Proposal evidence")
    require(isinstance(proposal["fallback"], str) and isinstance(proposal["stopCondition"], str),
            "Proposal fallback and stopCondition must be strings")
    cost = proposal["resourceCost"]
    require(isinstance(cost, dict), "resourceCost must be an object")
    require(not (set(cost) - COST_KEYS),
            "resourceCost has unexpected fields: " + ", ".join(sorted(set(cost) - COST_KEYS)))


def _missing_cost_dimensions(cost: dict) -> list[str]:
    missing = []
    if not text(cost.get("unit")):
        missing.append("unit")
    if not text(cost.get("domain")):
        missing.append("domain")
    return missing


def _result(decision: str, reasons: list[str], rejected: list[str], preserved: list[str],
            questions: list[str]) -> dict[str, Any]:
    require(reasons and questions, "Assessment needs reasons and open questions")
    result = {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    require(tuple(result) == RESULT_KEYS, "Assessment keys drifted")
    return result


def assess_proposal(register: dict, proposal: dict) -> dict:
    """Return deferred, allowed, or clarification_required.

    Safety deferral outranks cost clarification: a missing unit does not turn
    an enthusiasm-only or unrecovered irreversible proposal into an allowable
    quantitative question. ``allowed`` is only a complete non-destructive
    proposal whose risk is not firmware modification.
    """
    validate_register(register)
    _proposal_shape(proposal)
    known = {item["id"] for item in register["risks"]}
    require(proposal["riskId"] in known, "Unknown riskId: " + proposal["riskId"])
    cost = proposal["resourceCost"]
    missing_cost = _missing_cost_dimensions(cost)
    if not missing_cost:
        require("value" in cost and finite(cost["value"]), "resourceCost needs a finite value")

    enthusiasm = proposal["authorizedByEnthusiasmOnly"]
    blocked = proposal["blockedStreamIdentified"]
    recovered = proposal["recoveryProcedureVerified"]
    firmware = proposal["riskId"] == "firmware_modification"
    irreversible = proposal["irreversible"]
    lacks_safety = not (blocked and recovered)
    unsafe = (firmware or irreversible) and lacks_safety
    reasons: list[str] = []
    rejected: list[str] = []
    preserved: list[str] = []
    questions: list[str] = []

    if enthusiasm:
        reasons.append("User enthusiasm is not authorization.")
        rejected.append("enthusiasm-as-authorization")
    if firmware and lacks_safety:
        reasons.append(
            "Firmware modification is deferred until a blocked stream is identified "
            "and a recovery procedure is verified."
        )
    elif irreversible and lacks_safety:
        reasons.append(
            "Irreversible proposal is deferred until a blocked stream is identified "
            "and a recovery procedure is verified."
        )
    if enthusiasm or unsafe:
        if firmware or irreversible:
            preserved.append("Non-destructive capability and application-level investigations remain available.")
        else:
            preserved.append("The narrower non-destructive investigation remains available.")
        if firmware and lacks_safety:
            questions.append(
                "Which measured stream is blocked on the identified device and firmware, "
                "and which device-specific recovery procedure has been verified?"
            )
        elif irreversible and lacks_safety:
            questions.append("What recovery procedure is verified before this irreversible action?")
        if enthusiasm:
            questions.append("What demonstrated benefit, other than user enthusiasm, would reopen this proposal?")
        if missing_cost:
            reasons.append(
                "Resource cost is also missing " + " and ".join(missing_cost)
                + "; a number alone cannot authorize work."
            )
            questions.append("What unit and domain bind the resource cost?")
        return _result("deferred", reasons, rejected, preserved, questions)

    if missing_cost:
        reasons.append(
            "Resource cost is missing " + " and ".join(missing_cost)
            + "; clarification is required before the gate can be evaluated."
        )
        if "value" in cost and finite(cost["value"]):
            preserved.append(
                f"Resource cost value {cost['value']} is retained but not comparable without unit and domain."
            )
        else:
            preserved.append("No comparable resource cost is established.")
        questions.append("Which unit and domain make this resource cost comparable?")
        return _result("clarification_required", reasons, rejected, preserved, questions)

    complete = (
        not irreversible
        and not enthusiasm
        and not firmware
        and bool(proposal["alternatives"])
        and bool(proposal["evidence"])
        and text(proposal["fallback"])
        and text(proposal["stopCondition"])
    )
    if complete:
        reasons.append(
            "Reversible proposal records alternatives, evidence, a resource cost with unit and domain, "
            "a fallback, and an explicit stop condition."
        )
        preserved.append(proposal["proposal"])
        questions.append(
            "Physical S23 qualification remains open; this allowance is not a device or firmware claim."
        )
        return _result("allowed", reasons, rejected, preserved, questions)

    if firmware or irreversible:
        reasons.append(
            "A recorded blocked stream and recovery procedure do not authorize firmware modification "
            "or an irreversible action."
        )
        preserved.append("Non-destructive capability and application-level investigations remain available.")
        questions.append(
            "Which separate device-specific authorization would still be required after recovery is verified?"
        )
        return _result("deferred", reasons, rejected, preserved, questions)

    reasons.append("Non-destructive proposal is missing alternatives, evidence, fallback, or a stop condition.")
    preserved.append("No destructive action is authorized.")
    questions.append("Which alternatives, evidence, fallback, and stop condition complete this gate?")
    return _result("deferred", reasons, rejected, preserved, questions)


def _proposal_from_decision(decision: dict) -> dict:
    return {key: decision[key] for key in sorted(PROPOSAL_KEYS)}


def validate_log(log: dict, register: dict) -> None:
    validate_register(register)
    exact_keys(log, LOG_KEYS, "phase-entry log")
    require(type(log["schemaVersion"]) is int and log["schemaVersion"] == 1 and log["phase"] == "P006",
            "Unsupported phase-entry log")
    require(isinstance(log["decisions"], list) and log["decisions"], "Phase-entry log needs decisions")
    seen: set[str] = set()
    for decision in log["decisions"]:
        exact_keys(decision, DECISION_KEYS, "decision")
        require(text(decision["id"]) and decision["id"] not in seen, "Decision needs a unique id")
        seen.add(decision["id"])
        require(decision["decision"] in {"deferred", "allowed"},
                "Logged decision must be deferred or allowed: " + decision["id"])
        require(text(decision["rationale"]), "Decision " + decision["id"] + " needs a rationale")
        proposal = _proposal_from_decision(decision)
        assessed = assess_proposal(register, proposal)
        require(assessed["decision"] == decision["decision"],
                "Logged decision " + decision["id"] + " does not match assessment: "
                + assessed["decision"])
