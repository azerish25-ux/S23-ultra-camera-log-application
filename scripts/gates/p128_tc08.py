"""TC-P128-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps its interpretation
record and is not treated as universally self-describing without it. The
long-form account still has to be exact.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


CASE_INDEX = 7
NEGATIVE_TOKEN = "log-master-without-interpretation-record"
LEAK_TOKEN = "private-path-leaked"
MISSING_META_TOKEN = "missing-technical-interpretation"
PARTIAL_TOKEN = "unverified-partial-presented-as-complete"
KINDS = {"log", "sdr", "hdr-derived", "partial"}
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "bundleKind",
    "privatePaths",
    "redactedReport",
    "interpretationRecordPresent",
    "signalMetadataPresent",
    "recipeMetadataPresent",
    "presentedAsComplete",
    "expected_frames",
    "accounted_frames",
    "checkpoint_frames",
    "audio_duration",
    "video_duration",
    "audio_absent",
    "spot_check_only",
)

_SPEC = importlib.util.spec_from_file_location(
    "p128_validate_long_form_development_end_to_end",
    Path(__file__).resolve().parent / "p128_validate_long_form_development_end_to_end.py",
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


def _add(rejected: list[str], token: str) -> None:
    if token not in rejected:
        rejected.append(token)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = _text(payload["repeat"], "repeat")
    kind = _text(payload["bundleKind"], "bundleKind")
    if kind not in KINDS:
        raise ValueError("bundleKind is not log, sdr, hdr-derived, or partial")
    report = _text(payload["redactedReport"], "redactedReport")
    if not isinstance(payload["privatePaths"], list):
        raise ValueError("privatePaths must be a list")
    private_paths = [_text(item, "privatePaths") for item in payload["privatePaths"]]
    for flag in ("interpretationRecordPresent", "signalMetadataPresent", "recipeMetadataPresent", "presentedAsComplete"):
        if type(payload[flag]) is not bool:
            raise ValueError(flag + " must be a bool")
    account = _CORE.validate_long_form(
        payload["expected_frames"],
        payload["accounted_frames"],
        payload["checkpoint_frames"],
        payload["audio_duration"],
        payload["video_duration"],
        payload["audio_absent"],
        payload["spot_check_only"],
    )
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(account["reasons"])
    reasons.append(f"bundleKind={kind}")
    rejected = list(account["rejectedClaims"])
    if kind == "log" and not payload["interpretationRecordPresent"]:
        _add(rejected, NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    elif kind == "log":
        reasons.append("log interpretation record retained")
    if kind != "partial" and not (payload["signalMetadataPresent"] and payload["recipeMetadataPresent"]):
        _add(rejected, MISSING_META_TOKEN)
        reasons.append("technical signal or recipe metadata is missing")
    if kind == "partial" and payload["presentedAsComplete"]:
        _add(rejected, PARTIAL_TOKEN)
        reasons.append("unverified partial export was presented as complete")
    leaked = False
    for path in private_paths:
        if path in report:
            leaked = True
            reasons.append("private path leaked: " + path)
    if leaked:
        _add(rejected, LEAK_TOKEN)
    else:
        reasons.append("personal paths redacted")
    preserved = [evidence, f"bundleKind={kind}"]
    preserved.extend(account["preservedResults"])
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
    return result
