#!/usr/bin/env python3
"""P143 Support release-specific and scene-specific looks.

Host reference only. This module does not probe a device, does not qualify a
physical S23, and does not run the TC-P143-01 through TC-P143-08 modules.

Looks are keyed by film_id, release_id, and optional scene_id. Two releases of
the same film stay distinct entries. Averaging their parameters into one look
(averaged true, or a single release_id "all") is rejected. Ambiguous releases
stay listed. A scene look must name its release and must not replace the
release-level look. A missing release_id is rejected. A missing edition stays
unknown; a theatrical print is not inferred from a screenshot.
"""

from __future__ import annotations

import copy
import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P143"
WORKSTREAM = 18
TITLE = "Support release-specific and scene-specific looks"
GOAL = "Avoid treating every distribution version of a film as one fixed color target."
METHOD = (
    "Record reference edition, format, display assumptions, and scene family when known. "
    "Permit several interpretations under one movie title. A missing edition remains unknown; "
    "the app must not infer a theatrical print response from an arbitrary screenshot."
)
FIXTURE = (
    "Two legally obtained references from different releases with visibly different "
    "contrast and color treatment."
)
ORACLE = "The database preserves separate recipe targets and identifies which reference supports each."
MUTANT = "Average all references into one supposedly definitive movie look."
DELIVERABLE = "Release-aware catalogue and ambiguity tests"
DEPENDENCIES = ("P142",)

EVIDENCE_ID = "p143-release-looks"
CLAIM = "release-specific-looks-host-reference"
FILM_ID = "reference-film"
RELEASE_THEATRICAL = "theatrical-35mm"
RELEASE_DIGITAL = "digital-sdr"
RELEASE_HDR = "hdr"
RELEASE_UNIDENTIFIED = "unidentified"
SCENE_NIGHT = "night-interior"
RELEASE_ALL = "all"

MISSING_RELEASE = "missing-release-id"
AVERAGED_LOOK = "averaged-into-one-look"
RELEASE_ID_ALL = "single-release-id-all"
RELEASES_COLLAPSED = "releases-collapsed"
DEFINITIVE_LOOK = "definitive-movie-look"
CONFLICTING_PARAMS = "conflicting-look-parameters"
AMBIGUOUS_DROPPED = "ambiguous-release-dropped"
AMBIGUITY_CONCEALED = "ambiguity-concealed"
SCREENSHOT_INFERENCE = "screenshot-inferred-theatrical"
SCENE_MISSING_RELEASE = "scene-look-missing-release"
SCENE_REPLACES_RELEASE = "scene-look-replaces-release-look"
AVERAGED_EDITIONS = "averaged-inconsistent-editions"

AVERAGING_FAULTS = frozenset({
    AVERAGED_LOOK,
    RELEASE_ID_ALL,
    RELEASES_COLLAPSED,
    DEFINITIVE_LOOK,
    AVERAGED_EDITIONS,
})
FAULT_ORDER = (
    MISSING_RELEASE,
    RELEASE_ID_ALL,
    AVERAGED_LOOK,
    RELEASES_COLLAPSED,
    DEFINITIVE_LOOK,
    AVERAGED_EDITIONS,
    CONFLICTING_PARAMS,
    AMBIGUOUS_DROPPED,
    AMBIGUITY_CONCEALED,
    SCREENSHOT_INFERENCE,
    SCENE_MISSING_RELEASE,
    SCENE_REPLACES_RELEASE,
    MUTANT,
)
FAULT_TEXT = {
    MISSING_RELEASE: "missing release_id is rejected",
    RELEASE_ID_ALL: 'release_id "all" is rejected',
    AVERAGED_LOOK: "averaging parameters into one look is rejected",
    RELEASES_COLLAPSED: "two releases of the same film must remain distinct entries",
    DEFINITIVE_LOOK: MUTANT,
    AVERAGED_EDITIONS: "averaging inconsistent editions into a historical fact must fail",
    CONFLICTING_PARAMS: "conflicting parameters on one look key are not averaged",
    AMBIGUOUS_DROPPED: "ambiguous releases stay listed",
    AMBIGUITY_CONCEALED: "an ambiguous release cannot be labelled unambiguous",
    SCREENSHOT_INFERENCE: (
        "a missing edition remains unknown; a theatrical print is not inferred from a screenshot"
    ),
    SCENE_MISSING_RELEASE: "a scene look must name its release",
    SCENE_REPLACES_RELEASE: "a scene look must not replace the release-level look",
    MUTANT: "mutant rejected: " + MUTANT,
}

UNKNOWN_TOKENS = frozenset({"unknown", "unidentified", "ambiguous"})
LOOK_FIELDS = frozenset({
    "film_id",
    "release_id",
    "scene_id",
    "reference_id",
    "edition",
    "format",
    "display_assumptions",
    "scene_family",
    "parameters",
    "averaged",
    "ambiguous",
    "inferred_from_screenshot",
    "definitive",
    "replaces_release_look",
    "collapsed_release_ids",
})
DOCUMENT_KEYS = frozenset({
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "looks",
    "dropAmbiguous",
})
EVALUATE_REQUIRED = frozenset({"evidenceId", "looks"})
EVALUATE_OPTIONAL = frozenset({
    "caseId",
    "claim",
    "applyMutant",
    "dropAmbiguous",
    "repeat",
})
COMMON_KEYS = frozenset({"evidenceId", "repeat", "looks", "dropAmbiguous"})
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
OPEN_QUESTIONS = (
    "physical S23 capture was not run",
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
)
OPEN_QUESTION = OPEN_QUESTIONS[0]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(value: object, label: str) -> str:
    require(
        isinstance(value, str) and bool(value.strip()) and value == value.strip(),
        label + " must be a non-empty string",
    )
    return value


def require_bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def require_number(value: object, label: str) -> float:
    require(
        isinstance(value, (int, float)) and not isinstance(value, bool),
        label + " must be a number",
    )
    number = float(value)
    require(math.isfinite(number), label + " must be finite")
    return number


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def order_faults(faults: list[str]) -> list[str]:
    present = set(faults)
    ordered = [token for token in FAULT_ORDER if token in present]
    ordered.extend(token for token in dedupe(faults) if token not in FAULT_ORDER)
    return ordered


def with_mutant(faults: list[str], apply_mutant: bool = False) -> list[str]:
    ordered = order_faults(faults)
    if apply_mutant or any(token in AVERAGING_FAULTS for token in ordered):
        if MUTANT not in ordered:
            ordered.append(MUTANT)
    return order_faults(ordered)


def _optional_bool(source: dict, key: str, default: bool = False) -> bool:
    if key not in source or source[key] is None:
        return default
    return require_bool(source[key], key)


def _optional_string(value: object, label: str) -> str | None:
    if value is None:
        return None
    return require_text(value, label)


def _is_unknown_token(value: str | None) -> bool:
    if value is None:
        return True
    return value.casefold() in UNKNOWN_TOKENS


def _is_all_release(release_id: str | None) -> bool:
    return isinstance(release_id, str) and release_id.casefold() == RELEASE_ALL


def look_key(film_id: str, release_id: str, scene_id: str | None) -> str:
    """Catalogue key: film, release, and optional scene. Releases are not merged."""
    scene = "" if scene_id is None else scene_id
    return film_id + "|" + release_id + "|" + scene


def _parse_parameters(value: object, label: str) -> dict[str, float]:
    if value is None:
        return {}
    require(isinstance(value, dict), label + " must be an object")
    parsed: dict[str, float] = {}
    for key, item in value.items():
        name = require_text(key, label + " key")
        parsed[name] = require_number(item, label + "." + name)
    return parsed


def _parse_collapsed(value: object, label: str) -> list[str] | None:
    if value is None:
        return None
    require(isinstance(value, list), label + " must be a list or null")
    names: list[str] = []
    for index, item in enumerate(value):
        names.append(require_text(item, f"{label}[{index}]"))
    return names


def parse_look(value: object, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    extra = set(value) - LOOK_FIELDS
    require(not extra, label + " has unexpected fields: " + ", ".join(sorted(extra)))
    require("film_id" in value, label + " missing film_id")
    film_id = require_text(value["film_id"], label + ".film_id")
    if "release_id" not in value or value["release_id"] is None:
        release_id = None
    else:
        require(isinstance(value["release_id"], str), label + ".release_id must be a string or null")
        stripped = value["release_id"].strip()
        release_id = stripped or None
    if "scene_id" not in value or value["scene_id"] is None:
        scene_id = None
    else:
        require(isinstance(value["scene_id"], str), label + ".scene_id must be a string or null")
        scene_text = value["scene_id"].strip()
        scene_id = scene_text or None
    edition_present = "edition" in value
    edition = _optional_string(value["edition"], label + ".edition") if edition_present else None
    reference_id = None
    if "reference_id" in value and value["reference_id"] is not None:
        reference_id = require_text(value["reference_id"], label + ".reference_id")
    fmt = _optional_string(value["format"], label + ".format") if "format" in value else None
    display = (
        _optional_string(value["display_assumptions"], label + ".display_assumptions")
        if "display_assumptions" in value
        else None
    )
    scene_family = (
        _optional_string(value["scene_family"], label + ".scene_family")
        if "scene_family" in value
        else None
    )
    parameters = _parse_parameters(value["parameters"], label + ".parameters") if "parameters" in value else {}
    averaged = _optional_bool(value, "averaged")
    definitive = _optional_bool(value, "definitive")
    replaces = _optional_bool(value, "replaces_release_look")
    inferred = _optional_bool(value, "inferred_from_screenshot")
    collapsed = _parse_collapsed(
        value["collapsed_release_ids"] if "collapsed_release_ids" in value else None,
        label + ".collapsed_release_ids",
    )
    explicit_ambiguous = value["ambiguous"] if "ambiguous" in value else None
    if explicit_ambiguous is not None:
        require_bool(explicit_ambiguous, label + ".ambiguous")
    auto_ambiguous = (edition_present and _is_unknown_token(edition)) or (
        isinstance(release_id, str) and release_id.casefold() in UNKNOWN_TOKENS
    )
    concealed = explicit_ambiguous is False and auto_ambiguous
    ambiguous = True if auto_ambiguous else bool(explicit_ambiguous)
    return {
        "film_id": film_id,
        "release_id": release_id,
        "scene_id": scene_id,
        "reference_id": reference_id,
        "edition": edition,
        "format": fmt,
        "display_assumptions": display,
        "scene_family": scene_family,
        "parameters": parameters,
        "averaged": averaged,
        "ambiguous": ambiguous,
        "ambiguity_concealed": concealed,
        "inferred_from_screenshot": inferred,
        "definitive": definitive,
        "replaces_release_look": replaces,
        "collapsed_release_ids": collapsed,
    }


def _same_parameters(left: dict[str, float], right: dict[str, float]) -> bool:
    if set(left) != set(right):
        return False
    return all(math.isclose(left[key], right[key], rel_tol=0.0, abs_tol=0.0) for key in left)


def _submitted(look: dict[str, Any]) -> dict[str, Any]:
    return {
        "film_id": look["film_id"],
        "release_id": look["release_id"],
        "scene_id": look["scene_id"],
        "reference_id": look["reference_id"] if look["reference_id"] is not None else "unknown",
        "edition": look["edition"] if look["edition"] is not None else "unknown",
        "parameters": dict(look["parameters"]),
        "averaged": look["averaged"],
        "ambiguous": look["ambiguous"],
        "collapsed_release_ids": list(look["collapsed_release_ids"] or []),
    }


def _entry_from(look: dict[str, Any]) -> dict[str, Any]:
    edition = look["edition"]
    fmt = look["format"]
    display = look["display_assumptions"]
    if look["inferred_from_screenshot"]:
        edition = "unknown"
        fmt = "unknown"
        display = "unknown"
    else:
        if edition is None:
            edition = "unknown"
        if fmt is None:
            fmt = "unknown"
        if display is None:
            display = "unknown"
    scene_id = look["scene_id"]
    return {
        "key": look_key(look["film_id"], look["release_id"], scene_id),
        "film_id": look["film_id"],
        "release_id": look["release_id"],
        "scene_id": scene_id,
        "reference_id": look["reference_id"] if look["reference_id"] is not None else "unknown",
        "edition": edition,
        "format": fmt,
        "display_assumptions": display,
        "scene_family": look["scene_family"],
        "parameters": dict(look["parameters"]),
        "ambiguous": look["ambiguous"],
        "scope": "scene" if scene_id is not None else "release",
    }


def analyze_looks(looks: list[dict[str, Any]], drop_ambiguous: bool) -> dict[str, Any]:
    """Index looks without averaging releases or letting a scene replace its release."""
    faults: list[str] = []
    submitted = [_submitted(look) for look in looks]
    grouped: dict[tuple[str, str, str | None], list[dict[str, Any]]] = {}
    for look in looks:
        release_id = look["release_id"]
        blocked = False
        if release_id is None:
            faults.append(MISSING_RELEASE)
            blocked = True
        if _is_all_release(release_id):
            faults.append(RELEASE_ID_ALL)
            blocked = True
        if look["averaged"]:
            faults.append(AVERAGED_LOOK)
            blocked = True
        collapsed = look["collapsed_release_ids"] or []
        if len(collapsed) >= 2:
            faults.append(RELEASES_COLLAPSED)
            blocked = True
        if look["definitive"]:
            faults.append(DEFINITIVE_LOOK)
        if look["inferred_from_screenshot"]:
            faults.append(SCREENSHOT_INFERENCE)
        if look["scene_id"] is not None and (release_id is None or _is_all_release(release_id)):
            faults.append(SCENE_MISSING_RELEASE)
        if look["ambiguity_concealed"]:
            faults.append(AMBIGUITY_CONCEALED)
        if blocked or release_id is None:
            continue
        key = (look["film_id"], release_id, look["scene_id"])
        grouped.setdefault(key, []).append(look)

    entries: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for key in sorted(grouped, key=lambda item: (item[0], item[1], item[2] or "")):
        group = grouped[key]
        if any(not _same_parameters(group[0]["parameters"], other["parameters"]) for other in group[1:]):
            faults.append(CONFLICTING_PARAMS)
            conflicts.append({
                "film_id": key[0],
                "release_id": key[1],
                "scene_id": key[2],
                "references": [
                    item["reference_id"] if item["reference_id"] is not None else "unknown"
                    for item in group
                ],
                "parameterSets": [dict(item["parameters"]) for item in group],
            })
            continue
        entries.append(_entry_from(group[0]))

    release_pairs = {
        (entry["film_id"], entry["release_id"])
        for entry in entries
        if entry["scene_id"] is None
    }
    for entry in entries:
        if entry["scene_id"] is None:
            continue
        matched = [
            look for look in looks
            if look["film_id"] == entry["film_id"]
            and look["release_id"] == entry["release_id"]
            and look["scene_id"] == entry["scene_id"]
        ]
        if any(look["replaces_release_look"] for look in matched):
            faults.append(SCENE_REPLACES_RELEASE)
        if (entry["film_id"], entry["release_id"]) not in release_pairs:
            faults.append(SCENE_REPLACES_RELEASE)

    distinct: dict[str, list[str]] = {}
    ambiguous: dict[str, list[str]] = {}
    for entry in entries:
        if entry["scene_id"] is not None:
            continue
        distinct.setdefault(entry["film_id"], [])
        if entry["release_id"] not in distinct[entry["film_id"]]:
            distinct[entry["film_id"]].append(entry["release_id"])
        if entry["ambiguous"] and entry["release_id"] not in ambiguous.setdefault(entry["film_id"], []):
            ambiguous[entry["film_id"]].append(entry["release_id"])
    for film in distinct:
        distinct[film] = sorted(distinct[film])
    for film in ambiguous:
        ambiguous[film] = sorted(ambiguous[film])

    submitted_ambiguous = any(item["ambiguous"] and item["release_id"] not in (None, RELEASE_ALL) for item in submitted)
    if drop_ambiguous and (ambiguous or submitted_ambiguous):
        faults.append(AMBIGUOUS_DROPPED)

    accepted_keys = [entry["key"] for entry in entries]
    reasons = _catalogue_reasons(entries, distinct, ambiguous, release_pairs)
    return {
        "entries": entries,
        "submitted": submitted,
        "conflicts": conflicts,
        "distinctReleaseIds": distinct,
        "ambiguousReleaseIds": ambiguous,
        "acceptedKeys": accepted_keys,
        "reasons": reasons,
        "faults": dedupe(faults),
    }


def _catalogue_reasons(
    entries: list[dict[str, Any]],
    distinct: dict[str, list[str]],
    ambiguous: dict[str, list[str]],
    release_pairs: set[tuple[str, str]],
) -> list[str]:
    reasons = ["looks are keyed by film_id, release_id, and optional scene_id"]
    if not distinct:
        reasons.append("no release-level look was accepted")
    for film in sorted(distinct):
        ids = distinct[film]
        if len(ids) >= 2:
            reasons.append(
                "two releases of the same film remain distinct entries for "
                + film
                + ": "
                + ", ".join(ids)
            )
        else:
            reasons.append("release entry retained for " + film + ": " + ids[0])
    listed = [
        film + ":" + release
        for film in sorted(ambiguous)
        for release in ambiguous[film]
    ]
    if listed:
        reasons.append("ambiguous releases stay listed: " + ", ".join(listed))
    else:
        reasons.append("ambiguous releases stay listed: none")
    for entry in entries:
        if entry["scene_id"] is None:
            continue
        if (entry["film_id"], entry["release_id"]) in release_pairs:
            reasons.append(
                "scene look "
                + entry["scene_id"]
                + " names release "
                + entry["release_id"]
                + " and does not replace the release-level look"
            )
    for entry in entries:
        reasons.append(
            "reference "
            + entry["reference_id"]
            + " supports "
            + entry["key"]
        )
    return reasons


def public_catalogue(info: dict[str, Any]) -> dict[str, Any]:
    return {
        "entries": info["entries"],
        "submitted": info["submitted"],
        "conflicts": info["conflicts"],
        "distinctReleaseIds": info["distinctReleaseIds"],
        "ambiguousReleaseIds": info["ambiguousReleaseIds"],
        "acceptedKeys": list(info["acceptedKeys"]),
    }


def _parse_looks(value: object, label: str = "looks") -> list[dict[str, Any]]:
    require(isinstance(value, list), label + " must be a list")
    require(len(value) >= 1, label + " must contain at least one look")
    return [parse_look(item, f"{label}[{index}]") for index, item in enumerate(value)]


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str] | tuple[str, ...],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": list(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "physical S23 was not noted")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    return result


def _decide(
    case_id: str,
    evidence: str,
    claim: str,
    looks: list[dict[str, Any]],
    drop_ambiguous: bool,
    apply_mutant: bool,
    repeat: str | None = None,
) -> dict[str, Any]:
    info = analyze_looks(looks, drop_ambiguous)
    faults = with_mutant(list(info["faults"]), apply_mutant)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    if repeat is not None:
        reasons.append("repeat " + repeat)
    reasons.extend(info["reasons"])
    for token in faults:
        reasons.append(FAULT_TEXT.get(token, token))
    if not faults:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("catalogue recorded; releases stay distinct; not a physical qualification")
    preserved = [evidence, public_catalogue(info), claim]
    return assemble(case_id, faults, reasons, preserved, OPEN_QUESTIONS, evidence)


def assess(document: dict) -> dict[str, Any]:
    """Record separate release and scene looks, or reject an averaged movie look."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    drop_ambiguous = require_bool(document["dropAmbiguous"], "dropAmbiguous")
    looks = _parse_looks(document["looks"])
    return _decide(PHASE, evidence, claim, looks, drop_ambiguous, apply_mutant)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a look catalogue. A full phase document is assessed as itself."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload:
        return assess(payload)
    missing = EVALUATE_REQUIRED - set(payload)
    extra = set(payload) - EVALUATE_REQUIRED - EVALUATE_OPTIONAL
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    evidence = require_text(payload["evidenceId"], "evidenceId")
    claim = require_text(payload["claim"], "claim") if "claim" in payload else CLAIM
    case_id = require_text(payload["caseId"], "caseId") if "caseId" in payload else PHASE
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant") if "applyMutant" in payload else False
    drop_ambiguous = (
        require_bool(payload["dropAmbiguous"], "dropAmbiguous") if "dropAmbiguous" in payload else False
    )
    repeat = require_text(payload["repeat"], "repeat") if "repeat" in payload else None
    looks = _parse_looks(payload["looks"])
    return _decide(case_id, evidence, claim, looks, drop_ambiguous, apply_mutant, repeat)


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    drop_ambiguous = require_bool(payload["dropAmbiguous"], "dropAmbiguous")
    looks = _parse_looks(payload["looks"])
    info = analyze_looks(looks, drop_ambiguous)
    return {
        "evidence": evidence,
        "repeat": repeat,
        "looks": looks,
        "info": info,
        "faults": list(info["faults"]),
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    ordered = with_mutant(faults, False)
    reasons = [
        "host reference only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(bundle["info"]["reasons"])
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append("case recorded; releases stay distinct; not a physical qualification")
    preserved = [bundle["evidence"], public_catalogue(bundle["info"]), *extra_preserved]
    questions = list(OPEN_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])


def make_look(**overrides: Any) -> dict[str, Any]:
    look: dict[str, Any] = {
        "film_id": FILM_ID,
        "release_id": RELEASE_THEATRICAL,
        "scene_id": None,
        "reference_id": "owned-theatrical-reference",
        "edition": "theatrical-print",
        "format": "35mm",
        "display_assumptions": "theatrical-projection",
        "scene_family": None,
        "parameters": {"contrast": 1.5, "red": 1.25, "green": 0.75, "blue": 0.5},
        "averaged": False,
        "ambiguous": False,
        "inferred_from_screenshot": False,
        "definitive": False,
        "replaces_release_look": False,
        "collapsed_release_ids": None,
    }
    look.update(overrides)
    return look


def digital_look(**overrides: Any) -> dict[str, Any]:
    look = make_look(
        release_id=RELEASE_DIGITAL,
        reference_id="owned-digital-reference",
        edition="digital-sdr",
        format="digital",
        display_assumptions="rec709",
        parameters={"contrast": 0.5, "red": 0.75, "green": 1.0, "blue": 1.25},
    )
    look.update(overrides)
    return look


def hdr_look(**overrides: Any) -> dict[str, Any]:
    look = make_look(
        release_id=RELEASE_HDR,
        reference_id="owned-hdr-reference",
        edition="hdr-release",
        format="digital-hdr",
        display_assumptions="hdr-pq",
        parameters={"contrast": 1.25, "red": 1.0, "green": 1.0, "blue": 1.25},
    )
    look.update(overrides)
    return look


def unidentified_look(**overrides: Any) -> dict[str, Any]:
    look = make_look(
        release_id=RELEASE_UNIDENTIFIED,
        reference_id="unidentified-reference",
        edition="unknown",
        format="unknown",
        display_assumptions="unknown",
        ambiguous=True,
        parameters={"contrast": 1.0, "red": 1.0, "green": 1.0, "blue": 1.0},
    )
    look.update(overrides)
    return look


def scene_look(**overrides: Any) -> dict[str, Any]:
    look = make_look(
        scene_id=SCENE_NIGHT,
        scene_family=SCENE_NIGHT,
        reference_id="owned-theatrical-scene-reference",
        parameters={"contrast": 1.75, "red": 0.5, "green": 0.75, "blue": 1.0},
    )
    look.update(overrides)
    return look


def fixture_looks() -> list[dict[str, Any]]:
    return [make_look(), digital_look()]


def edition_conflict_looks() -> list[dict[str, Any]]:
    return [make_look(), digital_look(), hdr_look(), unidentified_look()]


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "looks": fixture_looks(),
        "dropAmbiguous": False,
    }


def copy_document(**overrides: Any) -> dict[str, Any]:
    document = copy.deepcopy(fixture_document())
    document.update(overrides)
    return document
