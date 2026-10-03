"""TC-P038-08 throughput stage conflation.

Intervention: Supply fast acquisition-only evidence but a slower or failing
saved-source experiment.
Expected: Report separate stage rates and qualify only the successfully retained
complete path.
Negative: Advertising discarded-frame acquisition speed as saved RAW recording
performance must fail.

The retained-path label is a host accounting result. It is not the decision
``qualified`` and it is not physical S23 qualification.
"""

from __future__ import annotations

CASE_ID = "TC-P038-08"
INTERVENTION = (
    "Supply fast acquisition-only evidence but a slower or failing saved-source experiment."
)
EXPECTED = "Report separate stage rates and qualify only the successfully retained complete path."
NEGATIVE = (
    "Advertising discarded-frame acquisition speed as saved RAW recording performance must fail."
)

_THERMAL = ("nominal", "warm", "severe")
_PAYLOAD_KEYS = (
    "acquisitionFps",
    "savedFps",
    "savedComplete",
    "discardedFrames",
    "advertiseAcquisitionAsSaved",
    "durationS",
    "storagePressure",
    "audioSelected",
    "thermalState",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = ("rejected", "retained_path", "withheld")
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Keep acquisition and saved-source rates apart. Do not advertise discards as saved RAW."""
    acquired, saved, complete, discarded, advertise, duration, pressure, audio, thermal = _payload(
        payload
    )
    preserved = [
        f"acquisitionFps:{acquired}",
        f"savedFps:{saved}",
        f"discardedFrames:{discarded}",
        f"durationS:{duration}",
        f"storagePressure:{str(pressure).lower()}",
        f"audio:{str(audio).lower()}",
        f"thermal:{thermal}",
    ]
    if advertise:
        return _result(
            "rejected",
            [
                NEGATIVE,
                EXPECTED,
                "acquisition speed was not reported as saved RAW performance",
            ],
            ["acquisition-advertised-as-saved"],
            preserved,
            ["saved performance not advertised from discarded frames"],
        )
    questions = []
    if pressure:
        questions.append("storage pressure recorded separately")
    if thermal != "nominal":
        questions.append(f"thermal:{thermal}")
    if audio:
        questions.append("audio selection does not change the saved RAW rate")
    if complete:
        return _result(
            "retained_path",
            [
                EXPECTED,
                "stage rates reported separately",
                "only the retained complete path is the saved result",
                "retained_path is not a qualified or allowed physical capture",
            ],
            [],
            preserved,
            questions,
        )
    questions.append("saved source incomplete")
    return _result(
        "withheld",
        [
            EXPECTED,
            "saved path did not complete",
            "acquisition rate is not a saved RAW result",
        ],
        [],
        preserved,
        questions,
    )


def _payload(payload: object) -> tuple[str, str, bool, int, bool, int, bool, bool, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    acquired = _rate(payload["acquisitionFps"], "acquisitionFps")
    saved = _rate(payload["savedFps"], "savedFps")
    complete = payload["savedComplete"]
    discarded = payload["discardedFrames"]
    advertise = payload["advertiseAcquisitionAsSaved"]
    duration = payload["durationS"]
    pressure = payload["storagePressure"]
    audio = payload["audioSelected"]
    thermal = payload["thermalState"]
    if type(complete) is not bool or type(advertise) is not bool:
        raise ValueError("completion flags must be bools")
    if type(pressure) is not bool or type(audio) is not bool:
        raise ValueError("condition flags must be bools")
    if type(discarded) is not int or discarded < 0:
        raise ValueError("discardedFrames must be a non-negative int")
    if type(duration) is not int or duration <= 0:
        raise ValueError("durationS must be a positive int")
    if thermal not in _THERMAL:
        raise ValueError("thermalState must be nominal, warm, or severe")
    return acquired, saved, complete, discarded, advertise, duration, pressure, audio, thermal


def _rate(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(label + " must be a canonical positive decimal string")
    whole, dot, frac = value.partition(".")
    if dot == "":
        if not whole.isdigit() or whole[0] == "0":
            raise ValueError(label + " must be a canonical positive decimal string")
        return value
    if (
        not whole.isdigit()
        or whole[0] == "0"
        or not frac.isdigit()
        or frac[-1] == "0"
    ):
        raise ValueError(label + " must be a canonical positive decimal string")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision not in _DECISIONS or decision in _FORBIDDEN:
        raise ValueError("throughput decision cannot be qualified or allowed")
    if not reasons:
        raise ValueError("reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result
