"""TC-P012-02 dynamic-range profile discovery: advertised but unusable route.

Advertisement is historical evidence only. A configure request without samples,
or a session rejection, startup timeout, or emitted stream that differs from
the request, is not operational qualification and is not a recording badge.
"""

from __future__ import annotations

INTERVENTION = 'Return an advertised candidate that fails actual configuration or produces no qualifying samples.'
EXPECTED = 'Keep advertisement as historical evidence but deny operational qualification for the failed exact tuple.'
NEGATIVE = 'A configure request alone must not create a supported recording badge.'

def _assert_case_contract() -> None:
    if not isinstance(INTERVENTION, str) or not INTERVENTION:
        raise ValueError("intervention missing")
    if not isinstance(EXPECTED, str) or not EXPECTED:
        raise ValueError("expected missing")
    if not isinstance(NEGATIVE, str) or not NEGATIVE:
        raise ValueError("negative missing")
    if "must fail" not in NEGATIVE and "must not" not in NEGATIVE:
        raise ValueError("negative control missing")


CASE_ID = "TC-P012-02"
FAILURE_MODES = ("none", "session_rejected", "startup_timeout", "stream_mismatch")
_STREAM_FIELDS = (
    "logicalId",
    "format",
    "width",
    "height",
    "advertised",
    "configured",
    "samples",
    "queryError",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def evaluate(payload: dict) -> dict:
    """Qualify one profile route only when it was configured and sampled.

    Advertised and (not configured, or no samples, or a non-none failure mode)
    stays ``advertised_only``. The measured tuple can be ``qualified``. Neither
    path returns ``allowed``.
    """
    _assert_case_contract()
    stream, failure_mode = _payload(payload)
    identity = _identity(stream)
    advertised_token = _advertised_token(stream)
    reasons: list[str] = []
    rejected: list[str] = []
    preserved: list[str] = []
    open_questions: list[str] = []

    advertised = stream["advertised"]
    configured = stream["configured"]
    samples = stream["samples"]
    unusable = (not configured) or samples == 0 or failure_mode != "none"
    qualified = advertised and configured and samples > 0 and failure_mode == "none"

    if qualified:
        decision = "qualified"
        preserved.append(identity)
        reasons.append(f"{identity} qualified")
    elif advertised and unusable:
        decision = "advertised_only"
        preserved.append(advertised_token)
        rejected.extend(_unusable_claims(stream, failure_mode))
        reasons.append("advertisement is not operational qualification")
        reasons.append(f"operational qualification denied for {identity}")
        if configured and samples == 0 and failure_mode == "none":
            reasons.append("configure request alone is not a recording badge")
        elif failure_mode == "session_rejected":
            reasons.append("session rejection denies operational qualification")
        elif failure_mode == "startup_timeout":
            reasons.append("startup timeout denies operational qualification")
        elif failure_mode == "stream_mismatch":
            reasons.append("emitted stream differs from the request")
        else:
            reasons.append("no qualifying samples")
        if decision in {"qualified", "allowed"}:
            raise ValueError("advertised unusable stream must not be qualified or allowed")
    else:
        decision = "rejected"
        rejected.append(identity)
        if failure_mode != "none":
            rejected.append(failure_mode)
        if samples == 0:
            rejected.append("no-samples")
        reasons.append(f"{identity} is not advertised for qualification")

    if decision == "allowed":
        raise ValueError("TC-P012-02 must not decide allowed")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons required")
    if advertised and unusable and decision in {"qualified", "allowed"}:
        raise ValueError("configure or failure evidence must not qualify the stream")

    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": open_questions,
    }
    if tuple(result) != _RESULT_KEYS:
        raise ValueError("invalid result keys")
    return result


def _unusable_claims(stream: dict, failure_mode: str) -> list[str]:
    claims: list[str] = []
    if failure_mode != "none":
        claims.append(failure_mode)
    if stream["samples"] == 0 or (failure_mode == "none" and not stream["configured"]):
        claims.append("no-samples")
    if not claims:
        claims.append("no-samples")
    return claims


def _payload(payload: object) -> tuple[dict, str]:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != {"stream", "failureMode"}:
        raise ValueError("payload keys must be stream and failureMode")
    failure = payload["failureMode"]
    if failure not in FAILURE_MODES:
        raise ValueError(
            "failureMode must be none, session_rejected, startup_timeout, or stream_mismatch"
        )
    return _stream(payload["stream"]), failure


def _stream(stream: object) -> dict:
    if not isinstance(stream, dict):
        raise ValueError("stream must be a dict")
    if set(stream) != set(_STREAM_FIELDS):
        raise ValueError("invalid stream fields")
    logical = stream["logicalId"]
    if not isinstance(logical, str) or not logical:
        raise ValueError("logicalId must be a non-empty string")
    fmt = stream["format"]
    if not isinstance(fmt, str) or not fmt:
        raise ValueError("format must be a non-empty string")
    _positive_int(stream["width"], "width")
    _positive_int(stream["height"], "height")
    for key in ("advertised", "configured"):
        if not isinstance(stream[key], bool):
            raise ValueError(f"{key} must be a bool")
    samples = stream["samples"]
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 0:
        raise ValueError("samples must be a non-negative int")
    query = stream["queryError"]
    if query is not None and (not isinstance(query, str) or not query):
        raise ValueError("queryError must be a non-empty string or null")
    return stream


def _positive_int(value: object, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int")


def _identity(stream: dict) -> str:
    return f"{stream['width']}x{stream['height']}:{stream['format']}@{stream['logicalId']}"


def _advertised_token(stream: dict) -> str:
    return f"advertised:{stream['width']}x{stream['height']}:{stream['format']}"
