#!/usr/bin/env python3
"""P130 Implement source and look selection separately.

Host reference only. This module does not probe a device and does not qualify
a physical S23. A selection keeps source identity (source_id, source_sha256,
source_transfer) apart from look_id and look_params. Changing the look copies
nothing into those source fields. A look whose name contains "log" or "LogC3"
cannot rewrite source_transfer, and relabelling bt709 or hlg as logc3 through
the look is rejected. Applying a look with no source is rejected. Clearing the
look (look_id null) keeps the source and is recorded only while source_retained
stays true.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any

BASE_REVISION = "3fbad4bc0e0336e273d2723ec873f001e8865323"
PHASE = "P130"
WORKSTREAM = 17
TITLE = "Implement source and look selection separately"
GOAL = "Prevent users from confusing capture capability with a virtual film format."
METHOD = (
    "Use distinct selectors for physical source mode, virtual format, stock, lens interpretation, "
    "and finishing recipe. Show computational cost and calibration status where relevant. "
    "Changing a look must not silently alter recording resolution or source lineage."
)
FIXTURE = "Selecting an IMAX-style recipe while the active source is a qualified 1080p SDR mode."
ORACLE = (
    "The interface preserves and displays the source mode while labelling the large-format "
    "appearance as simulated."
)
MUTANT = "Rename the active recording mode IMAX 70mm after a preset selection."
DELIVERABLE = "Separated control model and truthfulness UI tests"
DEPENDENCIES = ("P129",)

OPEN_QUESTION = "physical S23 measurement was not run"
FIXTURE_SOURCE_ID = "qualified-1080p-sdr"
FIXTURE_TRANSFER = "bt709"
FIXTURE_RECORDING_MODE = "1080p SDR"
FIXTURE_LOOK_ID = "imax-style-simulated"
EVIDENCE_ID = "p130-source-look"
CLAIM = "source-look-separation-host-reference"
IMAX_70MM = "imax 70mm"

SOURCE_FIELDS = ("source_id", "source_sha256", "source_transfer")
SELECTION_KEYS = (
    "source_id",
    "source_sha256",
    "source_transfer",
    "look_id",
    "look_params",
    "source_retained",
    "recording_mode",
)
FORBIDDEN_LOOK_PARAM_KEYS = frozenset(
    {"source_id", "source_sha256", "source_transfer", "recording_mode", "source_retained"}
)
DISPLAY_TRANSFERS = frozenset({"bt709", "rec709", "hlg"})
LOG_TRANSFER = "logc3"

LOOK_APPLIED_WITHOUT_SOURCE = "look-applied-without-source"
LOOK_ALTERED_SOURCE = "look-change-altered-source"
LOOK_REWROTE_TRANSFER = "look-rewrote-source-transfer"
LOOK_RELABELLED_LOGC3 = "look-relabelled-bt709-or-hlg-as-logc3"
LOOK_PARAMS_ALTER_SOURCE = "look-params-alter-source"
LOOK_ALTERED_RECORDING_MODE = "look-change-altered-recording-mode"
RENAMED_IMAX_70MM = "renamed-recording-mode-imax-70mm"
SOURCE_NOT_RETAINED = "source-not-retained"
SOURCE_MISSING = "source-missing"
LARGE_FORMAT_UNLABELLED = "large-format-appearance-not-labelled-simulated"
CALIBRATION_QUALIFIED = "calibration-status-qualified"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "committed",
    "proposed",
}
COMMON_KEYS = {"evidenceId", "repeat", "committed", "proposed"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
COMPLETE_NUMBER = re.compile(r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?\Z")
SHA256_TEXT = re.compile(r"^[0-9a-fA-F]{64}\Z")
_MISSING = object()

FAULT_TEXT = {
    LOOK_APPLIED_WITHOUT_SOURCE: "applying a look with no source is rejected",
    LOOK_ALTERED_SOURCE: (
        "changing look_id or look_params must leave source_id, source_sha256, "
        "and source_transfer unchanged"
    ),
    LOOK_REWROTE_TRANSFER: "a look name containing log or LogC3 must not rewrite source_transfer",
    LOOK_RELABELLED_LOGC3: "relabel of bt709/hlg into logc3 via the look is rejected",
    LOOK_PARAMS_ALTER_SOURCE: "look_params must not carry source identity fields",
    LOOK_ALTERED_RECORDING_MODE: (
        "changing a look must not silently alter recording resolution or source lineage"
    ),
    RENAMED_IMAX_70MM: MUTANT,
    SOURCE_NOT_RETAINED: "clearing or changing a look must not delete source bytes; source_retained stays true",
    SOURCE_MISSING: "source_id, source_sha256, and source_transfer are required to keep a source",
    LARGE_FORMAT_UNLABELLED: ORACLE,
    CALIBRATION_QUALIFIED: "a look calibration status must not be marked qualified",
}

FIXTURE_SOURCE_SHA256 = hashlib.sha256(
    f"{FIXTURE_SOURCE_ID}|{FIXTURE_TRANSFER}|{FIXTURE_RECORDING_MODE}".encode("utf-8")
).hexdigest()


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


def normalize_transfer(value: str) -> str:
    return "".join(ch for ch in value.casefold() if ch.isalnum())


def is_bt709_or_hlg(value: str | None) -> bool:
    if value is None:
        return False
    return normalize_transfer(value) in DISPLAY_TRANSFERS


def is_logc3(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    return normalize_transfer(value) == LOG_TRANSFER


def look_name_contains_log(look_id: str | None) -> bool:
    if not isinstance(look_id, str):
        return False
    folded = look_id.casefold()
    return "log" in folded or "logc3" in folded


def is_imax_70mm(recording_mode: str | None) -> bool:
    if not isinstance(recording_mode, str):
        return False
    return " ".join(recording_mode.casefold().split()) == IMAX_70MM


def same_sha(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return left.casefold() == right.casefold()


def same_transfer(left: str | None, right: str | None) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return normalize_transfer(left) == normalize_transfer(right)


def same_json(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return math.isclose(float(left), float(right), rel_tol=1e-12, abs_tol=1e-12)
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(same_json(a, b) for a, b in zip(left, right))
    if isinstance(left, dict) and isinstance(right, dict):
        if set(left) != set(right):
            return False
        return all(same_json(left[key], right[key]) for key in left)
    return False


def _validate_json_value(value: Any, label: str) -> None:
    if value is None or type(value) is bool or isinstance(value, str):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        require(math.isfinite(float(value)), label + " must be finite")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{label}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            require(
                isinstance(key, str) and bool(key.strip()) and key == key.strip(),
                label + " keys must be non-empty strings",
            )
            _validate_json_value(item, label + "." + key)
        return
    raise ValueError(label + " must be JSON-compatible")


def parse_selection(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(SELECTION_KEYS), label + " keys are invalid")
    source_id = value["source_id"]
    source_sha = value["source_sha256"]
    source_transfer = value["source_transfer"]
    look_id = value["look_id"]
    look_params = value["look_params"]
    if source_id is not None:
        source_id = require_text(source_id, label + ".source_id")
    if source_sha is not None:
        require(
            isinstance(source_sha, str) and SHA256_TEXT.fullmatch(source_sha) is not None,
            label + ".source_sha256 must be 64 hex characters or null",
        )
    if source_transfer is not None:
        source_transfer = require_text(source_transfer, label + ".source_transfer")
    if look_id is not None:
        look_id = require_text(look_id, label + ".look_id")
    if look_params is not None:
        require(isinstance(look_params, dict), label + ".look_params must be an object or null")
        _validate_json_value(look_params, label + ".look_params")
    retained = require_bool(value["source_retained"], label + ".source_retained")
    recording_mode = require_text(value["recording_mode"], label + ".recording_mode")
    return {
        "source_id": source_id,
        "source_sha256": source_sha,
        "source_transfer": source_transfer,
        "look_id": look_id,
        "look_params": look_params,
        "source_retained": retained,
        "recording_mode": recording_mode,
    }


def source_complete(selection: dict[str, Any]) -> bool:
    return all(selection[field] is not None for field in SOURCE_FIELDS)


def changed_source_fields(committed: dict[str, Any], proposed: dict[str, Any]) -> list[str]:
    changed: list[str] = []
    if committed["source_id"] != proposed["source_id"]:
        changed.append("source_id")
    if not same_sha(committed["source_sha256"], proposed["source_sha256"]):
        changed.append("source_sha256")
    if not same_transfer(committed["source_transfer"], proposed["source_transfer"]):
        changed.append("source_transfer")
    return changed


def look_changed(committed: dict[str, Any], proposed: dict[str, Any]) -> bool:
    if committed["look_id"] != proposed["look_id"]:
        return True
    return not same_json(committed["look_params"], proposed["look_params"])


def claims_large_format(look_id: str | None, look_params: Any) -> bool:
    name = look_id.casefold() if isinstance(look_id, str) else ""
    if any(token in name for token in ("imax", "70mm", "large-format", "large format")):
        return True
    if isinstance(look_params, dict):
        appearance = look_params.get("appearance")
        if isinstance(appearance, str) and appearance.casefold() in {"large-format", "imax", "70mm"}:
            return True
    return False


def param_transfer(look_params: Any) -> str | None:
    if not isinstance(look_params, dict):
        return None
    value = look_params.get("source_transfer")
    if isinstance(value, str):
        return value
    return None


def analyze_selection(committed: dict[str, Any], proposed: dict[str, Any]) -> dict[str, Any]:
    """Compare a committed selection with a proposed one.

    Look edits are isolated from source identity. The committed source triple is
    what later results preserve, even when the proposal is rejected.
    """
    changed = changed_source_fields(committed, proposed)
    changed_look = look_changed(committed, proposed)
    applying = proposed["look_id"] is not None
    faults: list[str] = []
    if applying and not source_complete(proposed):
        faults.append(LOOK_APPLIED_WITHOUT_SOURCE)
    elif not source_complete(proposed):
        faults.append(SOURCE_MISSING)
    if changed_look and changed:
        faults.append(LOOK_ALTERED_SOURCE)
    transfer_rewritten = not same_transfer(
        committed["source_transfer"], proposed["source_transfer"]
    )
    if look_name_contains_log(proposed["look_id"]) and transfer_rewritten:
        faults.append(LOOK_REWROTE_TRANSFER)
    smuggled = param_transfer(proposed["look_params"])
    params_touch_source = isinstance(proposed["look_params"], dict) and bool(
        FORBIDDEN_LOOK_PARAM_KEYS.intersection(proposed["look_params"])
    )
    if params_touch_source:
        faults.append(LOOK_PARAMS_ALTER_SOURCE)
    relabel_field = is_bt709_or_hlg(committed["source_transfer"]) and is_logc3(
        proposed["source_transfer"]
    )
    relabel_param = is_bt709_or_hlg(committed["source_transfer"]) and is_logc3(smuggled)
    via_look = changed_look or look_name_contains_log(proposed["look_id"]) or params_touch_source
    if via_look and (relabel_field or relabel_param):
        faults.append(LOOK_RELABELLED_LOGC3)
    if changed_look and committed["recording_mode"] != proposed["recording_mode"]:
        faults.append(LOOK_ALTERED_RECORDING_MODE)
    if is_imax_70mm(proposed["recording_mode"]) and not is_imax_70mm(committed["recording_mode"]):
        faults.append(RENAMED_IMAX_70MM)
    if proposed["source_retained"] is not True:
        faults.append(SOURCE_NOT_RETAINED)
    if claims_large_format(proposed["look_id"], proposed["look_params"]):
        params = proposed["look_params"] if isinstance(proposed["look_params"], dict) else {}
        if params.get("simulated") is not True:
            faults.append(LARGE_FORMAT_UNLABELLED)
        status = params.get("calibrationStatus")
        if isinstance(status, str) and status.casefold() == "qualified":
            faults.append(CALIBRATION_QUALIFIED)
    return {
        "lookChanged": changed_look,
        "changedSourceFields": changed,
        "sourceRetained": proposed["source_retained"] is True,
        "committed": committed,
        "proposed": proposed,
        "faults": dedupe(faults),
    }


def isolation_reasons(info: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if info["lookChanged"] and not info["changedSourceFields"]:
        reasons.append(
            "look change isolated: source_id, source_sha256, and source_transfer unchanged"
        )
    elif info["lookChanged"]:
        reasons.append(
            "look change altered source fields: " + ",".join(info["changedSourceFields"])
        )
    else:
        reasons.append("look selectors unchanged")
    retained = "true" if info["sourceRetained"] else "false"
    committed = info["committed"]
    proposed = info["proposed"]
    reasons.append("source_retained=" + retained)
    reasons.append(
        "source_id="
        + str(committed["source_id"])
        + " source_sha256="
        + str(committed["source_sha256"])
        + " source_transfer="
        + str(committed["source_transfer"])
        + " look_id="
        + str(proposed["look_id"])
    )
    params = proposed["look_params"] if isinstance(proposed["look_params"], dict) else {}
    if "computationalCost" in params:
        reasons.append("computationalCost=" + str(params["computationalCost"]))
    if "calibrationStatus" in params:
        reasons.append("calibrationStatus=" + str(params["calibrationStatus"]))
    if proposed["look_id"] is None and info["sourceRetained"] and not info["changedSourceFields"]:
        reasons.append("look cleared; source bytes retained")
    return reasons


def public_isolation(info: dict[str, Any]) -> dict[str, Any]:
    committed = info["committed"]
    proposed = info["proposed"]
    return {
        "source_id": committed["source_id"],
        "source_sha256": committed["source_sha256"],
        "source_transfer": committed["source_transfer"],
        "look_id": proposed["look_id"],
        "look_params": proposed["look_params"],
        "source_retained": proposed["source_retained"],
        "recording_mode": committed["recording_mode"],
        "lookChanged": info["lookChanged"],
        "changedSourceFields": list(info["changedSourceFields"]),
    }


def make_selection(
    *,
    source_id: str | None = FIXTURE_SOURCE_ID,
    source_sha256: Any = _MISSING,
    source_transfer: str | None = FIXTURE_TRANSFER,
    look_id: Any = _MISSING,
    look_params: Any = _MISSING,
    source_retained: bool = True,
    recording_mode: str = FIXTURE_RECORDING_MODE,
) -> dict[str, Any]:
    if source_sha256 is _MISSING:
        source_sha256 = FIXTURE_SOURCE_SHA256
    if look_id is _MISSING:
        look_id = "neutral"
    if look_params is _MISSING:
        look_params = {"contrast": 1}
    return {
        "source_id": source_id,
        "source_sha256": source_sha256,
        "source_transfer": source_transfer,
        "look_id": look_id,
        "look_params": look_params,
        "source_retained": source_retained,
        "recording_mode": recording_mode,
    }


def imax_proposal(**overrides: Any) -> dict[str, Any]:
    selection = make_selection(
        look_id=FIXTURE_LOOK_ID,
        look_params={
            "appearance": "large-format",
            "simulated": True,
            "computationalCost": "preview-only",
            "calibrationStatus": "not-qualified",
        },
    )
    selection.update(overrides)
    return selection


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "committed": make_selection(),
        "proposed": imax_proposal(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    committed = parse_selection(payload["committed"], "committed")
    proposed = parse_selection(payload["proposed"], "proposed")
    info = analyze_selection(committed, proposed)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "committed": committed,
        "proposed": proposed,
        "info": info,
        "faults": list(info["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(isolation_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append("selection recorded; source and look stay separate; not a physical qualification")
    preserved = [bundle["evidence"], public_isolation(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def assess(document: dict) -> dict[str, Any]:
    """Record an isolated source/look selection or reject a look that rewrites the source."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    committed = parse_selection(document["committed"], "committed")
    proposed = parse_selection(document["proposed"], "proposed")
    info = analyze_selection(committed, proposed)
    faults = list(info["faults"])
    if apply_mutant and RENAMED_IMAX_70MM not in faults:
        faults.append(RENAMED_IMAX_70MM)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    reasons.extend(isolation_reasons(info))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(FAULT_TEXT[token])
    if RENAMED_IMAX_70MM in ordered:
        reasons.append("mutant rejected: " + MUTANT)
    if not ordered:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("selection recorded; source and look stay separate; not a physical qualification")
    preserved = [evidence, public_isolation(info), claim]
    return assemble(PHASE, ordered, reasons, preserved, NON_CLAIM_QUESTIONS, evidence)


def parse_complete_number(text: str, label: str) -> tuple[float | None, str]:
    require(isinstance(text, str), label + " must be a string")
    stripped = text.strip()
    if COMPLETE_NUMBER.fullmatch(stripped) is None:
        return None, "incomplete"
    value = float(stripped)
    if not math.isfinite(value):
        return None, "invalid"
    return value, "complete"
