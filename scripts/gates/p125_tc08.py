"""TC-P125-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps its interpretation
record and is not presented as universally self-describing without one.
"""

from __future__ import annotations


CASE_ID = "TC-P125-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
PATH_TOKEN = "private-paths-not-redacted"
RECIPE_TOKEN = "missing-recipe-metadata"
SIGNAL_TOKEN = "missing-signal-interpretation"
LOG_TOKEN = "log-master-without-interpretation"
PARTIAL_TOKEN = "unverified-presented-as-self-describing"
REPEATS = ("clean-log", "rendered-sdr", "hdr-derived", "unverified-partial")
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "presentation",
    "privatePaths",
    "pathsRedacted",
    "signalInterpretationPresent",
    "recipeMetadataPresent",
    "presentedAsSelfDescribing",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} must be a bool")
    return value


def _paths(value: object) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("privatePaths must be a list")
    paths = []
    for index, item in enumerate(value):
        paths.append(_text(item, f"privatePaths[{index}]"))
    return paths


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _text(payload["evidenceId"], "evidenceId")
    repeat = payload["repeat"]
    presentation = payload["presentation"]
    if repeat not in REPEATS or presentation != repeat:
        raise ValueError("repeat is unsupported")
    private_paths = _paths(payload["privatePaths"])
    redacted = _bool(payload["pathsRedacted"], "pathsRedacted")
    signal = _bool(payload["signalInterpretationPresent"], "signalInterpretationPresent")
    recipe = _bool(payload["recipeMetadataPresent"], "recipeMetadataPresent")
    self_describing = _bool(payload["presentedAsSelfDescribing"], "presentedAsSelfDescribing")
    rejected: list[str] = []
    if private_paths and not redacted:
        rejected.append(PATH_TOKEN)
    if not recipe:
        rejected.append(RECIPE_TOKEN)
    if presentation in ("clean-log", "hdr-derived") and not signal:
        rejected.append(SIGNAL_TOKEN)
    if presentation == "clean-log" and not signal and self_describing:
        rejected.append(LOG_TOKEN)
    if presentation == "unverified-partial" and self_describing:
        rejected.append(PARTIAL_TOKEN)
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    if PATH_TOKEN in rejected:
        reasons.append("personal paths were not copied into the shared bundle")
    if RECIPE_TOKEN in rejected or SIGNAL_TOKEN in rejected:
        reasons.append("technical interpretation required for correct use was retained")
    if LOG_TOKEN in rejected:
        reasons.append(NEGATIVE)
    if PARTIAL_TOKEN in rejected:
        reasons.append("an unverified partial export is not universally self-describing")
    if not rejected:
        reasons.append("personal information redacted; technical interpretation retained")
    preserved = [
        evidence,
        {
            "presentation": presentation,
            "privatePathCount": len(private_paths),
            "pathsRedacted": redacted or not private_paths,
            "signalInterpretationPresent": signal,
            "recipeMetadataPresent": recipe,
            "presentedAsSelfDescribing": self_describing,
        },
    ]
    return _result("rejected" if rejected else "recorded", reasons, rejected, preserved, private_paths)


def _result(decision, reasons, rejected, preserved, private_paths) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": ["physical S23 capture was not run", REPEAT],
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    rendered = repr(result)
    for path in private_paths:
        if path in rendered:
            raise ValueError("private path leaked into the result")
    return result
