#!/usr/bin/env python3
"""P024 bounded capture queues and backpressure.

Host fixture only. Queues are budgeted in frames and bytes. Preview and
inference may discard stale work. Source overflow stops capture visibly and
records a gap. One unbounded queue shared by source, preview, and inference
is the mutant and is rejected.

This module does not probe a device, does not qualify a physical S23, and
does not execute TC-P024-01 through TC-P024-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P024"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
POLICY_ID = "s23-backpressure-fixture"
METHOD = (
    "Budget queues in bytes and frames, use explicit policies for preview drops "
    "versus source failure, and instrument outstanding leases. Source overflow "
    "causes a controlled visible stop with gap evidence. Preview and ML queues "
    "may discard stale work without altering source timestamps."
)
FIXTURE = (
    "A depth worker blocked for several seconds while the source writer remains "
    "healthy, followed by a deliberately stalled source writer."
)
ORACLE = (
    "The first condition only reduces monitoring freshness; the second triggers "
    "a documented capture stop rather than hidden loss."
)
MUTANT = "Use one unbounded queue for source writing, preview, and inference."

HEX40 = re.compile(r"^[0-9a-f]{40}$")
TS_TEXT = re.compile(r"^(0|[1-9][0-9]*)$")
ROLES = ("source", "preview", "inference")
POLICIES = {"visible_stop_with_gap", "discard_stale", "unbounded", "overwrite"}
POLICY_KEYS = {
    "schemaVersion",
    "phase",
    "policyId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "budgets",
    "queues",
    "leases",
    "conditions",
}
BUDGET_KEYS = {
    "sourceFrames",
    "sourceBytes",
    "previewFrames",
    "previewBytes",
    "inferenceFrames",
    "inferenceBytes",
    "leaseLimit",
}
QUEUE_KEYS = {
    "name",
    "role",
    "bounded",
    "frameCapacity",
    "byteCapacity",
    "overflowPolicy",
}
LEASE_KEYS = {"id", "queue", "bytes"}
CONDITION_KEYS = {
    "id",
    "kind",
    "blockedConsumer",
    "blockedSeconds",
    "sourceWriter",
    "frameBytes",
    "frames",
}
FRAME_KEYS = {"id", "timestampNs"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
BUDGET_FIELDS = {
    "source": ("sourceFrames", "sourceBytes"),
    "preview": ("previewFrames", "previewBytes"),
    "inference": ("inferenceFrames", "inferenceBytes"),
}
CASE_ID = "P024"
MUTANT_CLAIM = "unbounded-shared-queue"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value == value.strip()


def _positive_int(value: object, context: str) -> int:
    require(type(value) is int and value > 0, context + " must be a positive int")
    return value


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision not in {"qualified", "allowed"}, "decision must not be qualified or allowed")
    require(bool(reasons), "reasons required")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _frame_token(frame: dict) -> str:
    return f"{frame['id']}@{frame['timestampNs']}"


def _parse_frame(frame: object, context: str) -> dict[str, str]:
    _exact_keys(frame, FRAME_KEYS, context)
    require(_text(frame["id"]), context + " id must be a non-empty string")
    require(
        isinstance(frame["timestampNs"], str) and TS_TEXT.fullmatch(frame["timestampNs"]) is not None,
        context + " timestampNs must be a canonical non-negative integer string",
    )
    return {"id": frame["id"], "timestampNs": frame["timestampNs"]}


def _inventory(document: dict) -> list[str]:
    preserved: list[str] = []
    source_frames = document.get("sourceFrames")
    if isinstance(source_frames, list):
        for index, frame in enumerate(source_frames):
            preserved.append(_frame_token(_parse_frame(frame, f"sourceFrames[{index}]")))
    conditions = document.get("conditions")
    if isinstance(conditions, list):
        for index, condition in enumerate(conditions):
            if not isinstance(condition, dict):
                continue
            frames = condition.get("frames")
            if not isinstance(frames, list):
                continue
            prefix = condition.get("id")
            label = prefix if isinstance(prefix, str) and prefix else f"condition-{index}"
            for frame_index, frame in enumerate(frames):
                token = _frame_token(_parse_frame(frame, f"conditions[{index}].frames[{frame_index}]"))
                preserved.append(f"{label}:{token}")
    require(preserved, "frame inventory must be preserved")
    return preserved


def is_mutant(document: object) -> bool:
    """True when one unbounded queue serves source, preview, and inference."""
    if not isinstance(document, dict):
        return False
    if document.get("sharedUnbounded") is True:
        return True
    queues = document.get("queues")
    if not isinstance(queues, list) or len(queues) != 1 or not isinstance(queues[0], dict):
        return False
    queue = queues[0]
    roles = queue.get("roles")
    if roles is None and "role" in queue:
        roles = [queue.get("role")]
    if not isinstance(roles, list):
        return False
    unbounded = (
        queue.get("bounded") is False
        or queue.get("overflowPolicy") == "unbounded"
        or queue.get("frameCapacity") is None
        or queue.get("byteCapacity") is None
    )
    return unbounded and {"source", "preview", "inference"} <= set(roles)


def _identity(document: dict) -> None:
    require(type(document.get("schemaVersion")) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document.get("phase") == PHASE, "phase must be P024")
    revision = document.get("implementationBaseRevision")
    require(revision == BASE_REVISION and isinstance(revision, str) and HEX40.fullmatch(revision) is not None,
            "policy needs the P024 implementation base revision")
    require(document.get("mutant") == MUTANT, "mutant text must name the unbounded shared queue")


def _reject_mutant(document: dict) -> dict[str, Any]:
    require(isinstance(document, dict), "policy must be an object")
    _identity(document)
    preserved = _inventory(document)
    return _result(
        "rejected",
        [
            MUTANT,
            "one unbounded queue for source writing, preview, and inference hides source loss",
            "the mutant does not budget frames or bytes and does not record a capture gap",
            ORACLE,
        ],
        [MUTANT_CLAIM, "hidden-source-loss"],
        preserved,
        [
            "host fixture only; physical S23 capture was not measured",
            "rejecting the mutant does not qualify a device queue",
        ],
    )


def _check_frames(frames: object, context: str) -> list[dict[str, str]]:
    require(isinstance(frames, list) and frames, context + " must be a non-empty list")
    parsed: list[dict[str, str]] = []
    seen: set[str] = set()
    previous: int | None = None
    for index, frame in enumerate(frames):
        item = _parse_frame(frame, f"{context}[{index}]")
        require(item["id"] not in seen, context + " duplicate frame id " + item["id"])
        seen.add(item["id"])
        stamp = int(item["timestampNs"])
        require(previous is None or stamp > previous, context + " timestamps must strictly increase")
        previous = stamp
        parsed.append(item)
    return parsed


def validate_policy(document: dict) -> None:
    """Raise ValueError unless document is a structurally valid P024 policy.

    Overflow choices that hide loss are structurally allowed and rejected by
    assess. The shared unbounded mutant is not a valid separate-queue policy.
    """
    require(isinstance(document, dict), "policy must be an object")
    require(not is_mutant(document), "mutant documents are not a bounded policy")
    _exact_keys(document, POLICY_KEYS, "policy")
    _identity(document)
    require(document["policyId"] == POLICY_ID, "policyId must be s23-backpressure-fixture")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    budgets = _exact_keys(document["budgets"], BUDGET_KEYS, "budgets")
    for key in sorted(BUDGET_KEYS):
        _positive_int(budgets[key], "budgets." + key)
    queues = document["queues"]
    require(isinstance(queues, list) and len(queues) == 3, "queues must list source, preview, and inference")
    seen_roles: set[str] = set()
    for index, queue in enumerate(queues):
        item = _exact_keys(queue, QUEUE_KEYS, f"queues[{index}]")
        require(item["name"] == item["role"] and item["role"] in ROLES, f"queues[{index}] role is unknown")
        require(item["role"] not in seen_roles, "duplicate queue role " + item["role"])
        seen_roles.add(item["role"])
        require(type(item["bounded"]) is bool, f"queues[{index}] bounded must be a bool")
        _positive_int(item["frameCapacity"], f"queues[{index}] frameCapacity")
        _positive_int(item["byteCapacity"], f"queues[{index}] byteCapacity")
        require(item["overflowPolicy"] in POLICIES, f"queues[{index}] overflowPolicy is unknown")
        frame_key, byte_key = BUDGET_FIELDS[item["role"]]
        require(item["frameCapacity"] == budgets[frame_key], f"{item['role']} frame budget mismatch")
        require(item["byteCapacity"] == budgets[byte_key], f"{item['role']} byte budget mismatch")
    require(seen_roles == set(ROLES), "queues must include source, preview, and inference")
    leases = document["leases"]
    require(isinstance(leases, list) and leases, "leases must be a non-empty list")
    seen_leases: set[str] = set()
    for index, lease in enumerate(leases):
        item = _exact_keys(lease, LEASE_KEYS, f"leases[{index}]")
        require(_text(item["id"]), f"leases[{index}] id must be a non-empty string")
        require(item["id"] not in seen_leases, "duplicate lease id " + item["id"])
        seen_leases.add(item["id"])
        require(item["queue"] in ROLES, f"leases[{index}] queue is unknown")
        _positive_int(item["bytes"], f"leases[{index}] bytes")
    conditions = document["conditions"]
    require(isinstance(conditions, list) and len(conditions) == 2, "conditions must be the two-step fixture")
    expected = (
        ("depth_blocked", "monitoring_stall", "inference", "healthy"),
        ("source_stalled", "source_stall", "source", "stalled"),
    )
    for index, condition in enumerate(conditions):
        item = _exact_keys(condition, CONDITION_KEYS, f"conditions[{index}]")
        ident, kind, blocked, writer = expected[index]
        require(item["id"] == ident, f"conditions[{index}] id must be {ident}")
        require(item["kind"] == kind, f"conditions[{index}] kind must be {kind}")
        require(item["blockedConsumer"] == blocked, f"conditions[{index}] blockedConsumer mismatch")
        require(item["sourceWriter"] == writer, f"conditions[{index}] sourceWriter mismatch")
        require(type(item["blockedSeconds"]) is int and item["blockedSeconds"] >= 2,
                f"conditions[{index}] blockedSeconds must be an int of at least 2")
        _positive_int(item["frameBytes"], f"conditions[{index}] frameBytes")
        _check_frames(item["frames"], f"conditions[{index}].frames")


def _policy_faults(document: dict) -> list[str]:
    by_role = {queue["role"]: queue for queue in document["queues"]}
    faults: list[str] = []
    source = by_role["source"]
    if source["bounded"] is not True or source["overflowPolicy"] == "unbounded":
        faults.append("unbounded-source-queue")
    elif source["overflowPolicy"] == "overwrite":
        faults.append("hidden-frame-replacement")
    elif source["overflowPolicy"] != "visible_stop_with_gap":
        faults.append("hidden-source-loss")
    for role in ("preview", "inference"):
        queue = by_role[role]
        if queue["bounded"] is not True or queue["overflowPolicy"] != "discard_stale":
            faults.append(role + "-policy-alters-source")
    return faults


class _Queue:
    def __init__(self, name: str, frame_capacity: int, byte_capacity: int, policy: str) -> None:
        self.name = name
        self.frame_capacity = frame_capacity
        self.byte_capacity = byte_capacity
        self.policy = policy
        self.items: list[dict[str, Any]] = []
        self.bytes_used = 0
        self.dropped: list[dict[str, Any]] = []
        self.gaps: list[dict[str, Any]] = []
        self.stopped = False
        self.accepted: list[dict[str, Any]] = []

    def offer(self, frame: dict[str, Any]) -> str:
        if self.stopped:
            self.gaps.append(dict(frame))
            return "rejected_after_stop"
        fits_frames = len(self.items) < self.frame_capacity
        fits_bytes = self.bytes_used + frame["bytes"] <= self.byte_capacity
        if fits_frames and fits_bytes:
            stored = {
                "id": frame["id"],
                "timestampNs": frame["timestampNs"],
                "bytes": frame["bytes"],
            }
            self.items.append(stored)
            self.bytes_used += frame["bytes"]
            self.accepted.append(dict(stored))
            return "accepted"
        if self.policy == "discard_stale":
            self.dropped.append(dict(frame))
            return "discarded_stale"
        if self.policy == "visible_stop_with_gap":
            self.stopped = True
            self.gaps.append(dict(frame))
            return "stopped_with_gap"
        raise ValueError("simulate refused unsupported policy " + self.policy)

    def release_oldest(self) -> dict[str, Any]:
        require(bool(self.items), self.name + " released an empty queue")
        item = self.items.pop(0)
        self.bytes_used -= item["bytes"]
        return item


def _simulate(document: dict) -> dict[str, Any]:
    by_role = {queue["role"]: queue for queue in document["queues"]}
    queues = {
        role: _Queue(
            role,
            by_role[role]["frameCapacity"],
            by_role[role]["byteCapacity"],
            by_role[role]["overflowPolicy"],
        )
        for role in ROLES
    }
    outstanding = 0
    peak = 0

    def hold() -> None:
        nonlocal outstanding, peak
        outstanding += 1
        peak = max(peak, outstanding)

    def release_one(queue: _Queue) -> None:
        nonlocal outstanding
        queue.release_oldest()
        outstanding -= 1

    conditions: dict[str, Any] = {}
    for condition in document["conditions"]:
        blocked = condition["blockedConsumer"]
        writer_healthy = condition["sourceWriter"] == "healthy"
        for queue in queues.values():
            queue.items = []
            queue.bytes_used = 0
            queue.dropped = []
            queue.gaps = []
            queue.stopped = False
            queue.accepted = []
        outstanding = 0
        offered_tokens: list[str] = []
        for frame in condition["frames"]:
            payload = {
                "id": frame["id"],
                "timestampNs": frame["timestampNs"],
                "bytes": condition["frameBytes"],
            }
            offered_tokens.append(_frame_token(frame))
            for role in ROLES:
                status = queues[role].offer(payload)
                if status == "accepted":
                    hold()
                    drain = role != blocked and (role != "source" or writer_healthy)
                    if drain:
                        release_one(queues[role])
        source = queues["source"]
        inference = queues["inference"]
        retained = [_frame_token(item) for item in source.accepted]
        gap_tokens = [_frame_token(item) for item in source.gaps]
        hidden = retained != offered_tokens[: len(retained)] or any(
            item["timestampNs"] != source.accepted[index]["timestampNs"]
            for index, item in enumerate(source.items)
        )
        dropped = len(inference.dropped) + len(queues["preview"].dropped)
        conditions[condition["id"]] = {
            "monitoringFreshness": "reduced" if dropped else "unchanged",
            "captureStopped": source.stopped,
            "documentedStop": source.stopped and source.policy == "visible_stop_with_gap" and bool(gap_tokens),
            "sourceTimestamps": [item["timestampNs"] for item in source.accepted],
            "offeredTimestamps": [frame["timestampNs"] for frame in condition["frames"]],
            "retained": retained,
            "gaps": gap_tokens,
            "inferenceDropped": len(inference.dropped),
            "previewDropped": len(queues["preview"].dropped),
            "hiddenLoss": hidden or (bool(source.dropped) if hasattr(source, "dropped") else False),
            "blockedSeconds": condition["blockedSeconds"],
            "leasePeak": peak,
        }
        peak = 0
    lease_peak = max(item["leasePeak"] for item in conditions.values())
    return {
        "queues": list(ROLES),
        "leasePeak": lease_peak,
        "leaseLimit": document["budgets"]["leaseLimit"],
        "staticLeases": len(document["leases"]),
        "conditions": conditions,
    }


def unbounded_shared_accepts_all(frame_count: int) -> dict[str, Any]:
    """Behavior of the mutant: every frame is kept, with no stop and no gap.

    assess must reject a document that would behave this way. A test fails if
    that document is treated as policy_holds.
    """
    require(type(frame_count) is int and frame_count > 0, "frame_count must be a positive int")
    return {
        "accepted": frame_count,
        "stopped": False,
        "gaps": [],
        "shared": True,
        "bounded": False,
    }


def observe(document: dict) -> dict[str, Any]:
    """Simulate a structurally valid bounded policy. Refuses the mutant."""
    validate_policy(document)
    require(not _policy_faults(document), "observe requires the documented backpressure policies")
    return _simulate(document)


def _all_tokens(document: dict) -> list[str]:
    tokens: list[str] = []
    for condition in document["conditions"]:
        for frame in condition["frames"]:
            tokens.append(f"{condition['id']}:{_frame_token(frame)}")
    return tokens


def assess(document: dict) -> dict[str, Any]:
    """Judge the host fixture. The shared unbounded queue is rejected.

    A healthy blocked depth worker only reduces monitoring freshness. A stalled
    source writer stops capture and keeps gap evidence. Decision is never
    qualified or allowed.
    """
    require(isinstance(document, dict), "policy must be an object")
    if is_mutant(document):
        return _reject_mutant(document)
    validate_policy(document)
    preserved_all = _all_tokens(document)
    faults = _policy_faults(document)
    questions = ["host fixture only; physical S23 capture was not measured"]
    if faults:
        return _result(
            "rejected",
            [
                "declared overflow policy does not match source-stop versus preview-drop",
                "source frames were not overwritten by this rejection",
                ORACLE,
            ],
            faults,
            preserved_all,
            questions,
        )
    leases = document["leases"]
    lease_limit = document["budgets"]["leaseLimit"]
    lease_bytes = sum(item["bytes"] for item in leases)
    byte_budget = sum(document["budgets"][key] for key in ("sourceBytes", "previewBytes", "inferenceBytes"))
    if len(leases) > lease_limit or lease_bytes > byte_budget:
        return _result(
            "withheld",
            [
                "outstanding leases exceed the instrumented budget",
                "lease pressure is visible and does not discard the frame inventory",
            ],
            ["lease-budget-exceeded"],
            preserved_all,
            questions + ["outstanding leases are harness counts, not a device memory probe"],
        )
    observed = _simulate(document)
    first = observed["conditions"]["depth_blocked"]
    second = observed["conditions"]["source_stalled"]
    if observed["leasePeak"] > lease_limit:
        return _result(
            "withheld",
            [
                f"lease peak {observed['leasePeak']} exceeded limit {lease_limit}",
                "capture evidence already retained is kept",
            ],
            ["lease-budget-exceeded"],
            preserved_all,
            questions + ["outstanding leases are harness counts, not a device memory probe"],
        )
    oracle_ok = (
        first["monitoringFreshness"] == "reduced"
        and first["captureStopped"] is False
        and first["hiddenLoss"] is False
        and first["sourceTimestamps"] == first["offeredTimestamps"]
        and first["inferenceDropped"] > 0
        and second["captureStopped"] is True
        and second["documentedStop"] is True
        and second["hiddenLoss"] is False
        and bool(second["gaps"])
        and second["sourceTimestamps"] == second["offeredTimestamps"][: len(second["sourceTimestamps"])]
        and second["sourceTimestamps"] != second["offeredTimestamps"]
    )
    gap_claims = [f"gap:{token}" for token in second["gaps"]]
    retained = [f"depth_blocked:{token}" for token in first["retained"]]
    retained.extend(f"source_stalled:{token}" for token in second["retained"])
    if not oracle_ok:
        return _result(
            "withheld",
            [
                "fixture did not separate monitoring freshness from a documented source stop",
                ORACLE,
            ],
            gap_claims,
            preserved_all,
            questions,
        )
    reasons = [
        METHOD,
        (
            f"depth worker blocked for {first['blockedSeconds']}s while the source writer "
            f"stayed healthy; inference discarded {first['inferenceDropped']} stale frames"
        ),
        "monitoring freshness reduced; source timestamps were not altered; capture did not stop",
        (
            f"stalled source writer filled capacity and stopped with gap evidence "
            + ", ".join(gap_claims)
        ),
        f"outstanding leases peaked at {observed['leasePeak']} within limit {lease_limit}",
        ORACLE,
    ]
    return _result(
        "policy_holds",
        reasons,
        gap_claims,
        retained,
        questions + [
            "blocked depth worker reduced monitoring freshness without a capture stop",
            "outstanding leases are instrumented only inside this harness",
        ],
    )
