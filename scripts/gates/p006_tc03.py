"""TC-P006-03 missing-provenance gate.

P006 baseline remains in force: a firmware experiment with no identified blocked
stream and no verified recovery procedure is deferred. This case only decides
whether claimed fixtures may support provenance-dependent claims.
"""

from __future__ import annotations

CASE_ID = "TC-P006-03"
_PROVENANCE_FIELDS = ("origin", "owner", "acquiredAt", "permittedUse")
_BASELINE_REASON = (
    "Firmware experiment without an identified blocked stream and verified recovery "
    "is deferred while non-destructive capability and application-level investigations remain available."
)


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if payload.get("caseId") != CASE_ID:
        raise ValueError(f"caseId mismatch: expected {CASE_ID}")

    fixtures = payload.get("fixtures")
    claim_ids = payload.get("claimFixtureIds")
    if not isinstance(fixtures, list) or not isinstance(claim_ids, list):
        raise ValueError("fixtures and claimFixtureIds must be lists")

    by_id: dict[str, dict] = {}
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ValueError("each fixture must be a dict")
        fixture_id = fixture.get("id")
        if not isinstance(fixture_id, str) or fixture_id == "":
            raise ValueError("each fixture id must be a non-empty string")
        if fixture_id not in by_id:
            by_id[fixture_id] = fixture

    missing: list[str] = []
    rejected: list[str] = []
    preserved: list[str] = []
    seen: set[str] = set()
    for fixture_id in claim_ids:
        if not isinstance(fixture_id, str):
            raise ValueError("claimFixtureIds must contain strings")
        if fixture_id in seen:
            continue
        seen.add(fixture_id)
        fixture = by_id.get(fixture_id)
        if fixture is None:
            missing.append(fixture_id)
            continue
        if _provenance_complete(fixture.get("provenance")):
            preserved.append(fixture_id)
        else:
            rejected.append(fixture_id)

    if missing or rejected:
        decision = "excluded"
        reasons = [_BASELINE_REASON]
        if missing:
            reasons.append(
                "Claimed fixture ids that do not exist are excluded until the fixture is supplied: "
                + ", ".join(missing)
                + "."
            )
        if rejected:
            reasons.append(
                "Claimed fixtures missing complete provenance "
                "(non-empty origin, owner, acquiredAt, permittedUse) are excluded: "
                + ", ".join(rejected)
                + "."
            )
            reasons.append(
                "A visual result alone must not yield a reproducible or allowed decision."
            )
    else:
        decision = "accepted"
        reasons = [
            _BASELINE_REASON,
            "Every claimed fixture has complete provenance and is preserved.",
            "Accepting provenance does not authorize the deferred firmware experiment.",
        ]

    if decision in ("reproducible", "allowed"):
        raise RuntimeError("visual result must not decide reproducibility or allowance")

    return {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": list(missing),
    }


def _provenance_complete(provenance: object) -> bool:
    if not isinstance(provenance, dict):
        return False
    for field in _PROVENANCE_FIELDS:
        value = provenance.get(field)
        if not isinstance(value, str) or value.strip() == "":
            return False
    return True
