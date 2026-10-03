"""TC-P037-07 source mutation during development.

A renamed file, changed bytes, a replaced profile, or revoked read access stops
accepted publication. The source id and both digests stay in the inventory.
A published result that did not notice the change is rejected.
"""

from __future__ import annotations

import re

CASE_ID = "TC-P037-07"
INTERVENTION = "Alter the source or profile while a development job is reading it."
EXPECTED = (
    "Detect identity inconsistency, stop accepted publication, and preserve all available "
    "evidence without overwriting originals."
)
NEGATIVE = "A successful result whose source changed unnoticed must fail."

_MUTATIONS = ("renamed", "changed_bytes", "replaced_profile", "revoked_read", "none")
_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_DIGEST = re.compile(r"^[0-9a-f]{4,64}$")
_PAYLOAD_KEYS = (
    "sourceId",
    "profileId",
    "sourceDigest",
    "observedDigest",
    "mutation",
    "noticed",
    "publish",
)
_RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}


def evaluate(payload: dict) -> dict:
    """Stop publication when the source identity changes underneath a read."""
    fields = _payload(payload)
    preserved = [
        f"source:{fields['sourceId']}",
        f"profile:{fields['profileId']}",
        f"sourceDigest:{fields['sourceDigest']}",
        f"observedDigest:{fields['observedDigest']}",
    ]
    reasons = [EXPECTED, INTERVENTION, f"mutation {fields['mutation']}"]
    mutation = fields["mutation"]
    if mutation == "none":
        reasons.append("source identity was unchanged")
        reasons.append("this read is not a qualification")
        return _result("development_read", reasons, [], preserved, [])
    if not fields["noticed"]:
        claim = "unnoticed-source-change" if fields["publish"] else "undetected-mutation"
        reasons.append(NEGATIVE)
        reasons.append("original digests were kept")
        return _result("rejected", reasons, [claim], preserved, ["source change was not a successful publish"])
    reasons.append("accepted publication stopped")
    reasons.append("originals were not overwritten")
    return _result(
        "publication_stopped",
        reasons,
        [mutation],
        preserved,
        [f"{mutation} detected"],
    )


def _payload(payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("payload must be a dict")
    if set(payload) != set(_PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    source_id = _token(payload["sourceId"], "sourceId")
    profile_id = _token(payload["profileId"], "profileId")
    source_digest = _digest(payload["sourceDigest"], "sourceDigest")
    observed = _digest(payload["observedDigest"], "observedDigest")
    mutation = payload["mutation"]
    if mutation not in _MUTATIONS:
        raise ValueError("mutation is not a TC-P037-07 repeat")
    noticed = payload["noticed"]
    publish = payload["publish"]
    if type(noticed) is not bool or type(publish) is not bool:
        raise ValueError("noticed and publish must be bools")
    if mutation == "none":
        if source_digest != observed or noticed:
            raise ValueError("an unchanged source cannot be noticed as mutated")
    elif mutation == "changed_bytes" and source_digest == observed:
        raise ValueError("changed_bytes requires a different digest")
    if mutation != "none" and not noticed and not publish and mutation == "none":
        raise ValueError("unreachable")
    return {
        "sourceId": source_id,
        "profileId": profile_id,
        "sourceDigest": source_digest,
        "observedDigest": observed,
        "mutation": mutation,
        "noticed": noticed,
        "publish": publish,
    }


def _token(value: object, label: str) -> str:
    if not isinstance(value, str) or _TOKEN.fullmatch(value) is None:
        raise ValueError(label + " must be a token")
    return value


def _digest(value: object, label: str) -> str:
    if not isinstance(value, str) or _DIGEST.fullmatch(value) is None:
        raise ValueError(label + " must be lowercase hex")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict:
    if decision in _FORBIDDEN:
        raise ValueError("TC-P037-07 must not yield qualified or allowed")
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
