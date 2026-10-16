"""TC-P123-08 Shared bundle privacy and interpretation.

Host fixture. Private paths are redacted. A Log master keeps its signal and
recipe interpretation and is not presented as universally self-describing
without that record. Unverified partial exports are not marked complete.
"""

from __future__ import annotations


CASE_ID = "TC-P123-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
KINDS = ("clean-log", "rendered-sdr", "hdr-derived", "unverified-partial")
REQUIRED = {
    "clean-log": ("signal", "recipe"),
    "rendered-sdr": ("recipe",),
    "hdr-derived": ("signal", "recipe", "look"),
    "unverified-partial": (),
}
INTERPRETATION_KEYS = {"signal", "recipe", "look"}
PAYLOAD_KEYS = (
    "evidenceId",
    "kind",
    "privatePaths",
    "exportedPaths",
    "interpretation",
    "presentedAsSelfDescribing",
    "repeat",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Reject leaked private paths and a Log master with no interpretation record."""
    fields = _payload(payload)
    rejected: list[str] = []
    reasons = [EXPECTED, INTERVENTION, f"repeat {fields['repeat']}"]
    leaked = [
        private
        for private in fields["privatePaths"]
        if any(private in exported for exported in fields["exportedPaths"])
    ]
    if leaked:
        rejected.append("private-path-not-redacted")
        reasons.append("private paths remain in the export: " + ", ".join(leaked))
    missing = [
        key
        for key in REQUIRED[fields["kind"]]
        if not fields["interpretation"] or not fields["interpretation"].get(key)
    ]
    if fields["kind"] == "clean-log" and missing:
        rejected.append("log-master-without-interpretation-record")
        reasons.append(NEGATIVE)
    elif missing:
        rejected.append("interpretation-record-incomplete")
        reasons.append("technical interpretation required for correct use is missing: " + ",".join(missing))
    if fields["kind"] == "clean-log" and fields["presentedAsSelfDescribing"] and missing:
        if "log-presented-as-universally-self-describing" not in rejected:
            rejected.append("log-presented-as-universally-self-describing")
        reasons.append("Log master presented as self-describing without its interpretation record")
    if fields["kind"] == "unverified-partial" and fields["presentedAsSelfDescribing"]:
        rejected.append("unverified-partial-presented-as-complete")
        reasons.append("an unverified partial export was presented as self-describing")
    decision = "rejected" if rejected else "recorded"
    if decision == "recorded":
        reasons.append("private paths redacted and technical interpretation retained")
    preserved = [
        fields["evidenceId"],
        {
            "kind": fields["kind"],
            "exportedPaths": list(fields["exportedPaths"]),
            "interpretation": None if fields["interpretation"] is None else dict(fields["interpretation"]),
            "presentedAsSelfDescribing": fields["presentedAsSelfDescribing"],
        },
        list(fields["privatePaths"]),
    ]
    return _result(decision, reasons, rejected, preserved, ["physical S23 capture was not run", REPEAT])


def _paths(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be a list")
    paths = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"{label}[{index}] must be a non-empty string")
        paths.append(item)
    return paths


def _interpretation(value: object) -> dict | None:
    if value is None:
        return None
    if not isinstance(value, dict) or not set(value) <= INTERPRETATION_KEYS or not value:
        raise ValueError("interpretation keys are invalid")
    parsed = {}
    for key, item in value.items():
        if not isinstance(item, str) or not item.strip() or item != item.strip():
            raise ValueError(f"interpretation.{key} must be a non-empty string")
        parsed[key] = item
    return parsed


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = payload["evidenceId"]
    if not isinstance(evidence, str) or not evidence.strip() or evidence != evidence.strip():
        raise ValueError("evidenceId must be a non-empty string")
    kind = payload["kind"]
    repeat = payload["repeat"]
    if kind not in KINDS or repeat not in KINDS:
        raise ValueError("kind or repeat is unsupported")
    if kind != repeat:
        raise ValueError("repeat must match kind")
    if type(payload["presentedAsSelfDescribing"]) is not bool:
        raise ValueError("presentedAsSelfDescribing must be a bool")
    return {
        "evidenceId": evidence,
        "kind": kind,
        "privatePaths": _paths(payload["privatePaths"], "privatePaths"),
        "exportedPaths": _paths(payload["exportedPaths"], "exportedPaths"),
        "interpretation": _interpretation(payload["interpretation"]),
        "presentedAsSelfDescribing": payload["presentedAsSelfDescribing"],
        "repeat": repeat,
    }


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in {"recorded", "rejected"}:
        raise ValueError("decision must be recorded or rejected")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    if not reasons or not preserved or preserved[0] not in preserved:
        raise ValueError("evidence wiped")
    return result
