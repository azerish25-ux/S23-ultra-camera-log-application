"""TC-P072-04 tile seam stress.

Intervention: Position structured detail and bright impulses exactly on tile
boundaries with spatial effects enabled.
Expected: Match the untiled reference within the declared tolerance using
adequate halos and global coordinates.
Negative: Independent tile-local random seeds or missing overlap must fail.
"""

from __future__ import annotations

import re
from decimal import Decimal


CASE_ID = "TC-P072-04"
INTERVENTION = (
    "Position structured detail and bright impulses exactly on tile boundaries with spatial effects enabled."
)
EXPECTED = "Match the untiled reference within the declared tolerance using adequate halos and global coordinates."
NEGATIVE = "Independent tile-local random seeds or missing overlap must fail."
REPEAT = "Repeat at corners, varying tile sizes, and maximum configured blur radius."

_SITES = ("boundary", "corner", "varied-size", "max-blur")
_PAYLOAD_KEYS = (
    "tileId",
    "site",
    "halo",
    "requiredHalo",
    "globalCoordinates",
    "overlap",
    "localSeed",
    "delta",
    "tolerance",
    "referenceId",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_DECISIONS = {"rejected", "seam_matched"}
_TOKEN = re.compile(r"^[A-Za-z0-9._-]+$")
_HALO = re.compile(r"0|[1-9][0-9]*")
_UNSIGNED = re.compile(r"0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9]")


def evaluate(payload: dict) -> dict:
    """Match the untiled reference, or reject local seeds and missing overlap."""
    tile, site, halo, required, global_coords, overlap, local_seed, delta, tolerance, reference = _payload(
        payload
    )
    preserved = [
        tile,
        f"site:{site}",
        f"halo:{halo}",
        f"required-halo:{required}",
        f"delta:{delta}",
        f"tolerance:{tolerance}",
        f"reference:{reference}",
        f"global:{str(global_coords).lower()}",
        f"overlap:{str(overlap).lower()}",
    ]
    reasons = [EXPECTED, INTERVENTION]
    questions = [f"repeat coverage includes {REPEAT}", f"site {site}"]
    rejected: list[str] = []
    if local_seed:
        rejected.append("tile-local-seed")
    if not overlap:
        rejected.append("missing-overlap")
    if local_seed or not overlap:
        reasons.append(NEGATIVE)
        reasons.append(f"tile {tile} kept reference {reference}")
    else:
        if not global_coords:
            rejected.append("local-coordinates")
            reasons.append(f"tile {tile} did not use global coordinates")
        if Decimal(halo) < Decimal(required):
            rejected.append("halo-short")
            reasons.append(f"halo {halo} is below required halo {required}")
        if Decimal(delta) > Decimal(tolerance):
            rejected.append("seam-mismatch")
            reasons.append(f"delta {delta} exceeds tolerance {tolerance} against {reference}")
    if rejected:
        decision = "rejected"
        questions.append("untiled reference identity was retained")
    else:
        decision = "seam_matched"
        reasons.append(f"tile {tile} matched {reference} within tolerance {tolerance}")
    return _result(decision, reasons, rejected, preserved, questions)


def _payload(payload: object) -> tuple:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    tile = payload["tileId"]
    reference = payload["referenceId"]
    if not isinstance(tile, str) or _TOKEN.fullmatch(tile) is None:
        raise ValueError("tileId must be a token")
    if not isinstance(reference, str) or _TOKEN.fullmatch(reference) is None:
        raise ValueError("referenceId must be a token")
    site = payload["site"]
    if site not in _SITES:
        raise ValueError("site is unsupported")
    halo = payload["halo"]
    required = payload["requiredHalo"]
    if not isinstance(halo, str) or _HALO.fullmatch(halo) is None:
        raise ValueError("halo must be a canonical integer string")
    if not isinstance(required, str) or _HALO.fullmatch(required) is None:
        raise ValueError("requiredHalo must be a canonical integer string")
    global_coords = payload["globalCoordinates"]
    overlap = payload["overlap"]
    local_seed = payload["localSeed"]
    for name, value in (
        ("globalCoordinates", global_coords),
        ("overlap", overlap),
        ("localSeed", local_seed),
    ):
        if type(value) is not bool:
            raise ValueError(f"{name} must be a bool")
    delta = payload["delta"]
    tolerance = payload["tolerance"]
    if not isinstance(delta, str) or _UNSIGNED.fullmatch(delta) is None:
        raise ValueError("delta must be a canonical non-negative decimal")
    if not isinstance(tolerance, str) or _UNSIGNED.fullmatch(tolerance) is None:
        raise ValueError("tolerance must be a canonical non-negative decimal")
    if Decimal(tolerance) <= 0:
        raise ValueError("tolerance must be positive")
    return tile, site, halo, required, global_coords, overlap, local_seed, delta, tolerance, reference


def _result(decision, reasons, rejected, preserved, questions) -> dict:
    if decision not in _DECISIONS or decision in {"qualified", "allowed"}:
        raise ValueError("TC-P072-04 must not yield qualified or allowed")
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
