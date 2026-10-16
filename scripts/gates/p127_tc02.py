"""TC-P127-02 Mutable recipe during export.

Host fixture. The running export stays bound to the frozen recipe hash.
Later slider edits open a new recipe version. Reading live slider values
for frames of the running job is rejected. Bundle manifest rules still apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-02"
NAME = "Mutable recipe during export"
INTERVENTION = "Change UI parameters after a render has begun but before it finishes."
EXPECTED = "Keep the running job bound to its frozen recipe and create a new version for subsequent edits."
NEGATIVE = "Reading live slider values for successive output frames must fail."
REPEAT = "Repeat stock, focus, grain seed, output range, and source interpretation changes."
NEGATIVE_TOKEN = "live-slider-values-read-for-output-frames"
VERSION_TOKEN = "edit-without-new-recipe-version"
BINDING_TOKEN = "running-job-left-frozen-recipe"
REUSED_TOKEN = "new-version-reuses-frozen-recipe"
PAYLOAD_KEYS = (
    "evidenceId",
    "repeat",
    "filename",
    "labels",
    "manifest",
    "export_allowed",
    "grade_applied",
    "metadataTexts",
    "interpretation",
    "selfDescribing",
    "publishPrivatePaths",
    "personalIdentifiers",
    "frozenRecipeSha256",
    "frozenParameters",
    "liveParameters",
    "framesUsedLiveSliders",
    "newVersionCreated",
    "newVersionRecipeSha256",
)
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)

_SPEC = importlib.util.spec_from_file_location(
    "p127_export_interoperable_result_bundles",
    Path(__file__).resolve().parent / "p127_export_interoperable_result_bundles.py",
)
_CORE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_CORE)


def _parameters(value, label: str) -> dict:
    if not isinstance(value, dict) or not value:
        raise ValueError(f"{label} must be a non-empty object")
    parsed = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip() or key != key.strip():
            raise ValueError(f"{label} keys must be non-empty strings")
        parsed[key] = _CORE.require_text(item, f"{label}.{key}", stripped=False)
    return parsed


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    frozen_hash = _CORE.require_hash(payload["frozenRecipeSha256"], "frozenRecipeSha256")
    frozen = _parameters(payload["frozenParameters"], "frozenParameters")
    live = _parameters(payload["liveParameters"], "liveParameters")
    if type(payload["framesUsedLiveSliders"]) is not bool or type(payload["newVersionCreated"]) is not bool:
        raise ValueError("recipe flags must be bools")
    bundle = _CORE.judge_bundle(payload)
    recipe = payload["manifest"]["recipe_version_sha256"]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    if frozen_hash != recipe:
        rejected.append(BINDING_TOKEN)
        reasons.append("running job must stay bound to the frozen recipe hash")
    else:
        reasons.append("running job bound to frozen recipe " + frozen_hash)
    changed = frozen != live
    if payload["framesUsedLiveSliders"]:
        rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if changed and not payload["newVersionCreated"]:
        rejected.append(VERSION_TOKEN)
        reasons.append("subsequent edits require a new recipe version")
    if payload["newVersionCreated"]:
        new_hash = _CORE.require_hash(payload["newVersionRecipeSha256"], "newVersionRecipeSha256")
        if new_hash == frozen_hash:
            rejected.append(REUSED_TOKEN)
            reasons.append("new recipe version must not reuse the frozen hash")
        else:
            reasons.append("new recipe version " + new_hash)
    elif payload["newVersionRecipeSha256"] is not None:
        raise ValueError("newVersionRecipeSha256 must be null unless a new version is created")
    elif not changed and not payload["framesUsedLiveSliders"]:
        reasons.append("output frames stayed on the frozen parameters")
    preserved = [evidence, "frozenRecipeSha256=" + frozen_hash]
    preserved.extend(bundle["preservedResults"])
    result = _CORE.seal(
        CASE_ID,
        evidence,
        reasons,
        rejected,
        preserved,
        ["physical S23 measurement was not run", REPEAT],
    )
    if tuple(result) != RESULT_KEYS:
        raise ValueError("result keys drifted")
    return result
