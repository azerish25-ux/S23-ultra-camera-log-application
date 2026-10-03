"""TC-P008-03 missing-provenance gate.

Host-verified only while the physical device gate is pending. A fixture
without provenance is excluded from reproducibility claims. A concurrent
remote commit is preserved. A visual result or a local build never invents
completion.
"""
from __future__ import annotations

CASE_ID = "TC-P008-03"
KINDS = frozenset({"model", "stock_profile", "movie_reference", "generated_screenshot"})
GATES = frozenset({"pending", "passed"})
RESULT_KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
OPEN_PHYSICAL = "physical device gate pending"


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")
    fixtures = _fixtures(_required(payload, "fixtures"))
    claim_ids = _claim_ids(_required(payload, "claimFixtureIds"), fixtures)
    remote_commit = _text(_required(payload, "remoteCommit"), "remoteCommit")
    physical_gate = payload["physicalGate"] if "physicalGate" in payload else "pending"
    if physical_gate not in GATES:
        raise ValueError("physicalGate must be pending or passed")

    by_id = {fixture["id"]: fixture for fixture in fixtures}
    rejected = [fixture_id for fixture_id in claim_ids if not _has_provenance(by_id[fixture_id])]
    preserved = [remote_commit]
    preserved.extend(fixture["id"] for fixture in fixtures if _has_provenance(fixture))
    questions = [OPEN_PHYSICAL] if physical_gate == "pending" else []

    if rejected:
        decision = "excluded"
        reasons = [
            f"fixture {fixture_id} lacks provenance and is excluded; "
            "its visual result is not reproducible or complete"
            for fixture_id in rejected
        ]
    elif physical_gate == "passed":
        decision = "accepted"
        reasons = ["all claimed fixtures have provenance and the physical device gate passed"]
    else:
        decision = "host-verified"
        reasons = [
            "host-verified only while the physical device gate is pending; "
            "the remote commit is preserved and completion is not invented"
        ]
    if physical_gate == "pending":
        reasons.append("physical device gate pending forbids a completion decision")
    return _result(decision, reasons, rejected, preserved, questions)


def _fixtures(value: object) -> list[dict]:
    if not isinstance(value, list):
        raise ValueError("fixtures must be a list")
    fixtures: list[dict] = []
    seen: set[str] = set()
    for fixture in value:
        if not isinstance(fixture, dict):
            raise ValueError("fixture must be an object")
        if "id" not in fixture or "kind" not in fixture or "visualResult" not in fixture:
            raise ValueError("fixture requires id, kind, and visualResult")
        fixture_id = _text(fixture["id"], "fixture id")
        if fixture_id in seen:
            raise ValueError("duplicate fixture id")
        seen.add(fixture_id)
        kind = fixture["kind"]
        if kind not in KINDS:
            raise ValueError("fixture kind is not model, stock_profile, movie_reference, or generated_screenshot")
        _provenance_type(fixture.get("provenance"))
        fixtures.append(fixture)
    return fixtures


def _claim_ids(value: object, fixtures: list[dict]) -> list[str]:
    if not isinstance(value, list):
        raise ValueError("claimFixtureIds must be a list")
    known = {fixture["id"] for fixture in fixtures}
    claims: list[str] = []
    seen: set[str] = set()
    for fixture_id in value:
        fixture_id = _text(fixture_id, "claimFixtureIds")
        if fixture_id not in known:
            raise ValueError("claimFixtureIds references an unknown fixture")
        if fixture_id in seen:
            raise ValueError("duplicate claim fixture id")
        seen.add(fixture_id)
        claims.append(fixture_id)
    return claims


def _provenance_type(value: object) -> None:
    if value is None or isinstance(value, (str, dict, list, tuple)):
        return
    raise ValueError("provenance must be null, text, or a record")


def _has_provenance(fixture: dict) -> bool:
    value = fixture.get("provenance")
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (dict, list, tuple)):
        return len(value) > 0
    return False


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value


def _required(payload: dict, label: str) -> object:
    if label not in payload:
        raise ValueError(f"missing {label}")
    return payload[label]


def _result(decision: str, reasons: list[str], rejected: list[str],
            preserved: list[str], questions: list[str]) -> dict:
    if decision in {"complete", "reproducible", "allowed"}:
        raise ValueError("decision must not invent completion or reproducibility")
    if decision != "allowed" and not reasons:
        raise ValueError("reasons must be non-empty unless decision is allowed")
    if decision == "complete" or (OPEN_PHYSICAL in questions and decision == "complete"):
        raise ValueError("physical device gate pending forbids completion")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys are not exact")
    return result
