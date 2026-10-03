"""TC-P060-07 double viewing transform.

Intervention: Apply a display or log transform twice through preview,
development, or editor configuration.
Expected: Detect the mismatch using reference patches and preserve separate
clean and rendered branches.
Negative: A generic player thumbnail must not certify correct color interpretation.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


CASE_ID = "TC-P060-07"
INTERVENTION = (
    "Apply a display or log transform twice through preview, development, or editor configuration."
)
EXPECTED = "Detect the mismatch using reference patches and preserve separate clean and rendered branches."
NEGATIVE = "A generic player thumbnail must not certify correct color interpretation."
REPEAT = "Repeat with manual editor assignments and automatically detected source tags."

_TAGS = ("logc3", "scene-linear", "display-709", "hlg")
_ORIGINS = ("manual", "automatic")
_OPS = ("identity", "viewing")
_PATCHES = {
    "black": Decimal("0"),
    "grey": Decimal("0.18"),
    "white": Decimal("1"),
    "red": Decimal("0.8"),
}
_PAYLOAD_KEYS = (
    "sourceTag",
    "tagOrigin",
    "preview",
    "development",
    "patch",
    "thumbnailAgrees",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_QUANT = Decimal("0.000001")


def _q(value: Decimal) -> str:
    return format(value.quantize(_QUANT, rounding=ROUND_HALF_UP), "f")


def _viewing(value: Decimal) -> Decimal:
    clipped = min(Decimal(1), max(Decimal(0), value))
    if clipped == 0:
        return Decimal(0)
    return (clipped.ln() / Decimal("2.4")).exp()


def evaluate(payload: dict) -> dict:
    """Keep clean and rendered branches apart and reject a second viewing transform."""
    tag, origin, preview, development, patch, thumbnail = _payload(payload)
    clean = _PATCHES[patch]
    views = (preview == "viewing") + (development == "viewing")
    rendered = _viewing(clean) if views >= 1 else clean
    doubled = _viewing(rendered) if views >= 2 else None
    preserved = [
        f"source:{tag}",
        f"origin:{origin}",
        f"patch:{patch}",
        f"clean:{_q(clean)}",
        f"rendered:{_q(rendered)}",
        f"doubled:{_q(doubled) if doubled is not None else 'not-applied'}",
        f"preview:{preview}",
        f"development:{development}",
        f"thumbnail:{'yes' if thumbnail else 'no'}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"{origin} tag {tag} patch {patch}"]
    rejected: list[str] = []
    questions = [f"repeat coverage includes {REPEAT}", "clean and rendered branches were both retained"]
    if views >= 2:
        rejected.append("double-viewing-transform")
        reasons.append("reference patch mismatch: two viewing transforms were applied")
        if doubled is not None and _q(doubled) != _q(rendered):
            reasons.append(f"doubled {_q(doubled)} does not match rendered {_q(rendered)}")
        decision = "rejected"
    elif thumbnail:
        rejected.append("thumbnail-not-interpretation")
        reasons.append(NEGATIVE)
        decision = "withheld"
    elif views == 1:
        decision = "branches_separated"
        reasons.append("one viewing transform left the clean branch unchanged")
    else:
        decision = "withheld"
        reasons.append("no viewing transform was certified")
    if thumbnail and "thumbnail-not-interpretation" not in rejected:
        rejected.append("thumbnail-not-interpretation")
        reasons.append(NEGATIVE)
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    tag = payload["sourceTag"]
    origin = payload["tagOrigin"]
    preview = payload["preview"]
    development = payload["development"]
    patch = payload["patch"]
    thumbnail = payload["thumbnailAgrees"]
    if tag not in _TAGS:
        raise ValueError("sourceTag is unsupported")
    if origin not in _ORIGINS:
        raise ValueError("tagOrigin must be manual or automatic")
    if preview not in _OPS or development not in _OPS:
        raise ValueError("transform must be identity or viewing")
    if patch not in _PATCHES:
        raise ValueError("patch is unsupported")
    if type(thumbnail) is not bool:
        raise ValueError("thumbnailAgrees must be a bool")
    return tag, origin, preview, development, patch, thumbnail


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision in {"qualified", "allowed"}:
        raise ValueError("TC-P060-07 must not yield qualified or allowed")
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
