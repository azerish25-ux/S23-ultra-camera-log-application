"""TC-P124-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps the interpretation
record required to use it and is not presented as universally self-describing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P124-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
PRIVATE_PATH = "private-path-not-redacted"
LOG_WITHOUT = "log-master-without-interpretation"
HDR_WITHOUT = "hdr-derived-without-interpretation"
PARTIAL = "partial-presented-as-self-describing"
WIPED = "interpretation-wiped"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "exportedPaths",
    "kind",
    "interpretationRecordPresent",
    "presentedAsSelfDescribing",
    "technicalInterpretationRetained",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
KINDS = ("log", "sdr", "hdr-derived", "unverified-partial")
PRIVATE_MARKERS = ("/data/user/", "/sdcard/", "/home/", "DCIM", "Android/data")

_SPEC = importlib.util.spec_from_file_location(
    "p124_checkpoint_temporal_rendering_safely",
    Path(__file__).resolve().parent / "p124_checkpoint_temporal_rendering_safely.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _bool(value, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _private(path: str) -> bool:
    return any(marker in path for marker in PRIVATE_MARKERS)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    repeat = payload["repeat"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    if not isinstance(repeat, str) or not repeat.strip():
        raise ValueError("repeat must be a non-empty string")
    paths = payload["exportedPaths"]
    if not isinstance(paths, list) or not paths or not all(isinstance(item, str) and item.strip() for item in paths):
        raise ValueError("exportedPaths must be a non-empty list of strings")
    kind = payload["kind"]
    if kind not in KINDS:
        raise ValueError("kind is invalid")
    interpretation = _bool(payload["interpretationRecordPresent"], "interpretationRecordPresent")
    self_describing = _bool(payload["presentedAsSelfDescribing"], "presentedAsSelfDescribing")
    retained = _bool(payload["technicalInterpretationRetained"], "technicalInterpretationRetained")

    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, "kind=" + kind]
    rejected: list[str] = []
    leaked = [path for path in paths if _private(path)]
    if leaked:
        rejected.append(PRIVATE_PATH)
        reasons.append("private paths were not redacted")
    if kind == "log" and (not interpretation or self_describing):
        rejected.append(LOG_WITHOUT)
        reasons.append(NEGATIVE)
    if kind == "hdr-derived" and not interpretation:
        rejected.append(HDR_WITHOUT)
        reasons.append("HDR-derived look is missing its interpretation record")
    if kind == "unverified-partial" and self_describing:
        rejected.append(PARTIAL)
        reasons.append("an unverified partial export was presented as self-describing")
    if interpretation and not retained:
        rejected.append(WIPED)
        reasons.append("redaction removed the technical interpretation")
    if kind == "sdr" and not leaked and retained:
        reasons.append("rendered SDR does not require a Log interpretation record")
    if not rejected:
        reasons.append("personal paths are redacted and technical interpretation remains")
    decision = "rejected" if rejected else "recorded"
    preserved = [evidence, "kind=" + kind]
    preserved.extend("path=" + path for path in paths if not _private(path))
    if interpretation and retained:
        preserved.append("interpretation-record")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 measurement was not run", REPEAT],
    }
    return _CORE.seal(result)
