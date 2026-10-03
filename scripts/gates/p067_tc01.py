"""TC-P067-01 unsupported precision format.

Intervention: Remove a required renderable or importable format while leaving
the graphics API otherwise available.
Expected: Report the specific backend route unavailable or choose a separately
qualified alternative.
Negative: Silently replacing a high-precision intermediate with RGBA8 must fail.
"""

from __future__ import annotations

import re


CASE_ID = "TC-P067-01"
INTERVENTION = (
    "Remove a required renderable or importable format while leaving the graphics API otherwise available."
)
EXPECTED = "Report the specific backend route unavailable or choose a separately qualified alternative."
NEGATIVE = "Silently replacing a high-precision intermediate with RGBA8 must fail."
REPEAT = "Repeat with missing extensions, incompatible surfaces, and unavailable image imports."

_FORMATS = ("rgba32f", "rgba16f", "rgba8", "yuv420")
_REPEATS = ("baseline", "missing-extension", "incompatible-surface", "unavailable-import")
_ALTERNATIVES = ("none", "cpu-reference")
_PAYLOAD_KEYS = (
    "routeId",
    "apiAvailable",
    "requiredFormat",
    "formatPresent",
    "silentRgba8",
    "alternative",
    "repeat",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "withheld", "route_unavailable", "alternative_selected", "format_retained"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")


def evaluate(payload: dict) -> dict:
    """Name the missing format route, or reject a silent RGBA8 replacement."""
    route, api, required, present, silent, alternative, repeat = _payload(payload)
    preserved = [
        route,
        f"format:{required}",
        f"api:{str(api).lower()}",
        f"present:{str(present).lower()}",
        f"alternative:{alternative}",
        f"repeat:{repeat}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"repeat site {repeat}"]
    rejected: list[str] = []
    if not api:
        decision = "withheld"
        reasons.append("graphics API was not otherwise available, so no route was substituted")
        questions.append(f"route {route} was kept without a format substitution")
    elif silent:
        decision = "rejected"
        rejected.append("silent-rgba8")
        reasons.append(NEGATIVE)
        reasons.append(f"{required} on {route} was not silently replaced with RGBA8")
        questions.append("high-precision format requirement remains in the inventory")
    elif not present and alternative != "none":
        decision = "alternative_selected"
        reasons.append(
            f"backend route {route} unavailable for {required}; separately recorded alternative {alternative}"
        )
        questions.append("alternative selection is not a qualified or allowed decision")
    elif not present:
        decision = "route_unavailable"
        reasons.append(f"backend route {route} unavailable for {required}")
        questions.append("the specific route was reported unavailable")
    else:
        decision = "format_retained"
        reasons.append(f"{required} remains available on {route}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    route = payload["routeId"]
    if not isinstance(route, str) or _TOKEN.fullmatch(route) is None:
        raise ValueError("routeId must be a token")
    api = payload["apiAvailable"]
    present = payload["formatPresent"]
    silent = payload["silentRgba8"]
    for name, value in (
        ("apiAvailable", api),
        ("formatPresent", present),
        ("silentRgba8", silent),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    required = payload["requiredFormat"]
    if required not in _FORMATS:
        raise ValueError("requiredFormat is unsupported")
    alternative = payload["alternative"]
    if alternative not in _ALTERNATIVES:
        raise ValueError("alternative is unsupported")
    repeat = payload["repeat"]
    if repeat not in _REPEATS:
        raise ValueError("repeat is unsupported")
    return route, api, required, present, silent, alternative, repeat


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P067-01 must not yield qualified or allowed")
    if not reasons:
        raise ValueError("reasons must be non-empty")
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
