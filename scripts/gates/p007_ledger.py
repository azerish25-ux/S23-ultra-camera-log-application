"""P007 provenance ledger: rights-state validation and attribution export.

Content identity is the sha256 digest, never the display name. Unknown rights
exclude a record from redistribution. They do not, by themselves, forbid
private comparison. This host module does not qualify a physical S23.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_SHA256 = re.compile(r"[0-9a-f]{64}")


def validate_ledger(ledger: dict) -> None:
    """Reject secret-like strings, missing sha256 values, and duplicate digests.

    Duplicate displayName values are allowed. Two profiles may share a name
    when their content hashes differ.
    """
    if not isinstance(ledger, dict):
        raise ValueError("ledger must be an object")
    _reject_secrets(ledger)
    records = ledger.get("records")
    if not isinstance(records, list):
        raise ValueError("ledger records must be a list")
    seen_sha: set[str] = set()
    seen_ids: set[str] = set()
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {index} must be an object")
        digest = record.get("sha256")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise ValueError(f"record {index} missing sha256")
        if digest in seen_sha:
            raise ValueError(f"duplicate sha256: {digest}")
        seen_sha.add(digest)
        local_id = record.get("localId")
        if isinstance(local_id, str):
            if local_id in seen_ids:
                raise ValueError(f"duplicate localId: {local_id}")
            seen_ids.add(local_id)
    return None


def public_bundle(ledger: dict) -> list[str]:
    """Return localIds whose rights are exactly permitted.

    Unknown or any other rights state is omitted. That blocks redistribution.
    The record may remain in the ledger for private comparison.
    """
    validate_ledger(ledger)
    selected: list[str] = []
    for record in ledger["records"]:
        if record.get("rights") == "permitted" and isinstance(record.get("localId"), str):
            selected.append(record["localId"])
    return selected


def attribute(ledger: dict, localId: str) -> dict:
    """Export attribution for one local id. Raise KeyError when it is absent."""
    validate_ledger(ledger)
    for record in ledger["records"]:
        if record.get("localId") == localId:
            return _attribution(record)
    raise KeyError(localId)


def assess_identity(records: list[dict]) -> dict:
    """Decide whether same-name records are distinct content versions.

    ``records`` may be a ledger object. Identity is read from
    ``identityPolicy``, which must be ``sha256``. ``keyedByDisplayName`` true
    is a collapse attempt. A policy other than ``sha256`` is rejected when two
    records share a displayName and differ in sha256. A sha256 policy keeps
    those records distinct and lists both digests in ``preservedResults``.
    A bare record list is assessed as identityPolicy ``sha256``.
    """
    items, policy, keyed_by_display_name = _payload(records)
    groups = _colliding_groups(items)
    preserved = _digests(groups)
    rejected: list[str] = []
    reasons: list[str] = []
    if groups and policy != "sha256":
        decision = "rejected"
        rejected.append("displayName-only identity")
        if keyed_by_display_name:
            rejected.append("keyedByDisplayName")
        reasons.append(
            "identityPolicy is "
            f"{policy!r}; keying identity only by display name would collapse "
            "distinct sha256 versions: " + ", ".join(preserved)
        )
    elif groups and policy == "sha256":
        decision = "distinct"
        if keyed_by_display_name:
            rejected.append("keyedByDisplayName")
            reasons.append(
                "keyedByDisplayName was set, but identityPolicy is sha256, so "
                "shared display names with different sha256 stay distinct versions: "
                + ", ".join(preserved)
            )
        else:
            reasons.append(
                "shared displayName values with different sha256 are distinct "
                "versions under identityPolicy sha256: " + ", ".join(preserved)
            )
    elif policy != "sha256":
        decision = "rejected"
        rejected.append("displayName-only identity")
        reasons.append(f"identityPolicy must be 'sha256', not {policy!r}")
    else:
        decision = "distinct"
        reasons.append("no displayName collision; identityPolicy is sha256")
        preserved = _digests([(None, items)])
    return {
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": rejected,
        "preservedResults": preserved,
        "openQuestions": [
            "Physical S23 qualification is not established by this host ledger.",
            "Unknown redistribution rights remain unresolved and block public-bundle inclusion only.",
        ],
    }


def _payload(records: list[dict]) -> tuple[list[dict], str, bool]:
    if isinstance(records, dict):
        items = records.get("records", [])
        if not isinstance(items, list):
            raise TypeError("ledger records must be a list")
        policy = records.get("identityPolicy", "sha256")
        if not isinstance(policy, str) or not policy:
            policy = "sha256"
        return list(items), policy, bool(records.get("keyedByDisplayName", False))
    if not isinstance(records, list):
        raise TypeError("records must be a list")
    return list(records), "sha256", False


def _colliding_groups(items: list[dict]) -> list[tuple[Any, list[dict]]]:
    grouped: dict[str, list[dict]] = {}
    order: list[str] = []
    for record in items:
        if not isinstance(record, dict):
            continue
        name = record.get("displayName")
        if not isinstance(name, str):
            continue
        if name not in grouped:
            grouped[name] = []
            order.append(name)
        grouped[name].append(record)
    collisions: list[tuple[Any, list[dict]]] = []
    for name in order:
        group = grouped[name]
        digests = {
            record.get("sha256")
            for record in group
            if isinstance(record.get("sha256"), str)
        }
        if len(group) >= 2 and len(digests) >= 2:
            collisions.append((name, group))
    return collisions


def _digests(groups: list[tuple[Any, list[dict]]]) -> list[str]:
    preserved: list[str] = []
    for _name, group in groups:
        for record in group:
            if not isinstance(record, dict):
                continue
            digest = record.get("sha256")
            if isinstance(digest, str) and digest not in preserved:
                preserved.append(digest)
    return preserved


def _attribution(record: dict) -> dict:
    provenance = record.get("provenance")
    source = provenance if isinstance(provenance, dict) else record
    transformations = record.get("transformations", [])
    if not isinstance(transformations, list):
        transformations = []
    return {
        "localId": record.get("localId"),
        "sha256": record.get("sha256"),
        "displayName": record.get("displayName"),
        "origin": source.get("origin", record.get("origin")),
        "owner": source.get("owner", record.get("owner")),
        "acquiredAt": source.get("acquiredAt", record.get("acquiredAt")),
        "permittedUse": source.get("permittedUse", record.get("permittedUse")),
        "rights": record.get("rights"),
        "transformations": list(transformations),
    }


def _reject_secrets(value: Any) -> None:
    for text in _strings(value):
        lowered = text.lower()
        if "token" in lowered or "bearer" in lowered:
            raise ValueError("secret-like string rejected")
        if _EMAIL.search(text):
            raise ValueError("email-like string rejected")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                yield key
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)
