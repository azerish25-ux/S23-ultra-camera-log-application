#!/usr/bin/env python3
"""P141 Manage reference media rights and attribution.

Host fixture only. This module does not probe a device and does not qualify a
physical S23. Each packaged asset carries asset_id, licence (a non-empty
string or null), attribution, and a redistribute bool. A public URL whose
licence is null is cited and is not redistributed. redistribute true without a
real licence is rejected. The string "public web page", and public-web
accessibility aliases, are not a licence. Attribution is required while
redistribute is true. Frames and other bytes that lack a licence stay out of
the distributable package. Model, profile, LUT, image, text, and frame rights
are judged independently.
"""

from __future__ import annotations

from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P141"
WORKSTREAM = 18
TITLE = "Manage reference media rights and attribution"
GOAL = "Avoid bundling copyrighted frames or proprietary look data without the required permission."
METHOD = (
    "Store links and factual citations separately from distributable assets. "
    "Use owned comparison footage and approved thumbnails. Track model, profile, LUT, image, "
    "and text rights independently. Unknown redistribution status blocks packaging that asset "
    "until reviewed."
)
FIXTURE = "A useful production still with an accessible public URL but no permission to bundle it in the app."
ORACLE = "The catalogue can retain a citation while excluding the image bytes from the distributable package."
MUTANT = "Treat public web accessibility as a redistribution licence."
DELIVERABLE = "Content rights manifest and package licence gate"
DEPENDENCIES = ("P140",)
LICENCE_RULE = (
    "A public URL with licence null must not be redistributed. "
    "redistribute true without a licence is rejected. "
    'Treating "public web page" as a licence is rejected. '
    "Required attribution missing while redistribute is true is rejected. "
    "Assets with a licence and attribution can be recorded. "
    "Frames that lack a licence are not bundled."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p141-reference-rights"
CLAIM = "content-rights-manifest-host-reference"
STILL_ID = "production-still-public"
STILL_URL = "https://example.invalid/production-still"
STILL_CITATION = "Production still cited from a public URL; no permission to bundle"
THUMB_ID = "owned-comparison-thumbnail"
THUMB_LICENCE = "owned-comparison"
THUMB_ATTRIBUTION = "S23 Cinema owned comparison footage"
THUMB_CITATION = "Owned comparison thumbnail approved for the package"

KINDS = frozenset({"model", "profile", "lut", "image", "text", "frame"})
ASSET_KEYS = (
    "asset_id",
    "kind",
    "licence",
    "attribution",
    "redistribute",
    "public_url",
    "citation",
    "bundled",
)
PSEUDO_LICENCES = frozenset(
    {
        "public web page",
        "public webpage",
        "public web accessibility",
        "publicly accessible",
        "public url",
        "public visibility",
        "web accessible",
        "public web",
        "accessible public url",
        "public accessibility",
        "web page",
    }
)

PUBLIC_WEB_NOT_LICENCE = "public-web-page-treated-as-licence"
REDISTRIBUTE_WITHOUT_LICENCE = "redistribute-without-licence"
PUBLIC_URL_NULL_LICENCE = "public-url-null-licence-redistributed"
ATTRIBUTION_MISSING = "attribution-missing-while-redistributing"
UNLICENSED_FRAME_BUNDLED = "unlicensed-frame-bundled"
UNLICENSED_BYTES_BUNDLED = "unlicensed-bytes-bundled"
UNKNOWN_REDISTRIBUTION = "unknown-redistribution-blocks-packaging"

DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "applyMutant",
    "assets",
}
EVALUATE_KEYS = {"caseId", "evidenceId", "repeat", "applyMutant", "assets"}
COMMON_KEYS = {"evidenceId", "repeat", "assets"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]

FAULT_TEXT = {
    PUBLIC_WEB_NOT_LICENCE: 'Treating "public web page" as a licence is rejected',
    REDISTRIBUTE_WITHOUT_LICENCE: "redistribute true without a licence is rejected",
    PUBLIC_URL_NULL_LICENCE: "a public URL with licence null must not be redistributed",
    ATTRIBUTION_MISSING: "required attribution missing while redistribute is true is rejected",
    UNLICENSED_FRAME_BUNDLED: "frames that lack a licence are not bundled",
    UNLICENSED_BYTES_BUNDLED: "bytes that lack a licence are excluded from the distributable package",
    UNKNOWN_REDISTRIBUTION: (
        "unknown redistribution status blocks packaging that asset until reviewed"
    ),
}


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


def dedupe(items: list[str]) -> list[str]:
    seen: list[str] = []
    for item in items:
        if item not in seen:
            seen.append(item)
    return seen


def normalize_phrase(value: str) -> str:
    folded = value.casefold().replace("-", " ").replace("_", " ").replace("/", " ")
    return " ".join(folded.split())


def is_pseudo_licence(value: str) -> bool:
    """Public accessibility is not a redistribution licence."""
    if normalize_phrase(value) in PSEUDO_LICENCES:
        return True
    folded = value.casefold()
    return folded.startswith("http://") or folded.startswith("https://")


def parse_asset(value: Any, label: str) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    require(set(value) == set(ASSET_KEYS), label + " keys are invalid")
    asset_id = require_text(value["asset_id"], label + ".asset_id")
    kind = require_text(value["kind"], label + ".kind")
    require(kind in KINDS, label + ".kind is not a tracked rights kind")
    licence = value["licence"]
    if licence is not None:
        licence = require_text(licence, label + ".licence")
    attribution = value["attribution"]
    if attribution is not None:
        attribution = require_text(attribution, label + ".attribution")
    redistribute = require_bool(value["redistribute"], label + ".redistribute")
    public_url = value["public_url"]
    if public_url is not None:
        public_url = require_text(public_url, label + ".public_url")
    citation = value["citation"]
    if citation is not None:
        citation = require_text(citation, label + ".citation")
    bundled = require_bool(value["bundled"], label + ".bundled")
    return {
        "asset_id": asset_id,
        "kind": kind,
        "licence": licence,
        "attribution": attribution,
        "redistribute": redistribute,
        "public_url": public_url,
        "citation": citation,
        "bundled": bundled,
    }


def parse_assets(value: Any) -> list[dict[str, Any]]:
    require(isinstance(value, list) and len(value) >= 1, "assets must be a non-empty list")
    parsed: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(value):
        asset = parse_asset(item, f"assets[{index}]")
        require(asset["asset_id"] not in seen, "duplicate asset_id " + asset["asset_id"])
        seen.add(asset["asset_id"])
        parsed.append(asset)
    return parsed


def analyze_asset(asset: dict[str, Any]) -> dict[str, Any]:
    """Judge one asset. Sibling licences never transfer."""
    raw = asset["licence"]
    pseudo = isinstance(raw, str) and is_pseudo_licence(raw)
    real = raw if isinstance(raw, str) and not pseudo else None
    faults: list[str] = []
    if pseudo:
        faults.append(PUBLIC_WEB_NOT_LICENCE)
    if asset["redistribute"] and real is None:
        faults.append(REDISTRIBUTE_WITHOUT_LICENCE)
    if asset["public_url"] is not None and real is None and asset["redistribute"]:
        faults.append(PUBLIC_URL_NULL_LICENCE)
    if asset["redistribute"] and asset["attribution"] is None:
        faults.append(ATTRIBUTION_MISSING)
    if asset["bundled"] and real is None:
        if asset["kind"] == "frame":
            faults.append(UNLICENSED_FRAME_BUNDLED)
        faults.append(UNLICENSED_BYTES_BUNDLED)
    if real is None and (asset["bundled"] or asset["redistribute"]):
        faults.append(UNKNOWN_REDISTRIBUTION)
    ordered = dedupe(faults)
    return {
        "asset": asset,
        "realLicence": real,
        "pseudoLicence": pseudo,
        "faults": ordered,
        "redistributable": real is not None and asset["attribution"] is not None and asset["redistribute"] and not ordered,
        "packaged": asset["bundled"] and real is not None and not ordered,
    }


def judge_assets(assets: Any, *, apply_mutant: bool) -> dict[str, Any]:
    parsed = parse_assets(assets)
    judged = [analyze_asset(asset) for asset in parsed]
    faults: list[str] = []
    for item in judged:
        faults.extend(item["faults"])
    if apply_mutant and PUBLIC_WEB_NOT_LICENCE not in faults:
        faults.append(PUBLIC_WEB_NOT_LICENCE)
    return {"assets": judged, "faults": dedupe(faults)}


def rights_reasons(info: dict[str, Any]) -> list[str]:
    reasons = ["licence rule: " + LICENCE_RULE]
    for item in info["assets"]:
        asset = item["asset"]
        licence = "null" if item["realLicence"] is None else item["realLicence"]
        reasons.append(
            "asset "
            + asset["asset_id"]
            + " kind="
            + asset["kind"]
            + " licence="
            + licence
            + " redistribute="
            + ("true" if asset["redistribute"] else "false")
            + " bundled="
            + ("true" if asset["bundled"] else "false")
        )
        if asset["public_url"] is not None and item["realLicence"] is None and not asset["redistribute"]:
            reasons.append("public URL with licence null is not redistributed: " + asset["asset_id"])
        if asset["citation"] is not None and not item["packaged"]:
            reasons.append("citation retained for " + asset["asset_id"])
        if item["realLicence"] is None and not item["packaged"]:
            reasons.append("image bytes excluded from the distributable package: " + asset["asset_id"])
        if asset["kind"] == "frame" and item["realLicence"] is None and not item["packaged"]:
            reasons.append("frame lacking a licence is not bundled: " + asset["asset_id"])
        if item["redistributable"]:
            reasons.append("licensed asset with attribution recorded: " + asset["asset_id"])
    packaged = [item["asset"]["asset_id"] for item in info["assets"] if item["packaged"]]
    reasons.append("packaged assets: " + (",".join(packaged) if packaged else "none"))
    return reasons


def public_rights(info: dict[str, Any]) -> dict[str, Any]:
    citations = []
    packaged: list[str] = []
    excluded: list[str] = []
    redistributable: list[str] = []
    rejected: list[str] = []
    for item in info["assets"]:
        asset = item["asset"]
        citations.append(
            {
                "asset_id": asset["asset_id"],
                "kind": asset["kind"],
                "citation": asset["citation"],
                "public_url": asset["public_url"],
                "licence": item["realLicence"],
                "attribution": asset["attribution"],
            }
        )
        if item["packaged"]:
            packaged.append(asset["asset_id"])
        else:
            excluded.append(asset["asset_id"])
        if item["redistributable"]:
            redistributable.append(asset["asset_id"])
        if item["faults"]:
            rejected.append(asset["asset_id"])
    return {
        "citations": citations,
        "packagedAssetIds": packaged,
        "excludedAssetIds": excluded,
        "redistributableAssetIds": redistributable,
        "rejectedAssetIds": rejected,
    }


def production_still(**overrides: Any) -> dict[str, Any]:
    asset = {
        "asset_id": STILL_ID,
        "kind": "image",
        "licence": None,
        "attribution": None,
        "redistribute": False,
        "public_url": STILL_URL,
        "citation": STILL_CITATION,
        "bundled": False,
    }
    asset.update(overrides)
    return asset


def owned_thumbnail(**overrides: Any) -> dict[str, Any]:
    asset = {
        "asset_id": THUMB_ID,
        "kind": "image",
        "licence": THUMB_LICENCE,
        "attribution": THUMB_ATTRIBUTION,
        "redistribute": True,
        "public_url": None,
        "citation": THUMB_CITATION,
        "bundled": True,
    }
    asset.update(overrides)
    return asset


def make_asset(**overrides: Any) -> dict[str, Any]:
    asset = {
        "asset_id": "licensed-asset",
        "kind": "image",
        "licence": "cc-by-4.0",
        "attribution": "Example Archive",
        "redistribute": True,
        "public_url": None,
        "citation": "Example Archive comparison",
        "bundled": True,
    }
    asset.update(overrides)
    return asset


def fixture_assets() -> list[dict[str, Any]]:
    return [production_still(), owned_thumbnail()]


def fixture_document() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "applyMutant": False,
        "assets": fixture_assets(),
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    decision = "rejected" if faults else "recorded"
    require(decision in {"recorded", "rejected"}, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": dedupe(faults),
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be present")
    return result


def _identity(document: dict) -> tuple[str, str, bool]:
    evidence = require_text(document["evidenceId"], "evidenceId")
    claim = require_text(document["claim"], "claim")
    apply_mutant = require_bool(document["applyMutant"], "applyMutant")
    return evidence, claim, apply_mutant


def _reasons(info: dict[str, Any], faults: list[str]) -> list[str]:
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "goal: " + GOAL,
        "method: " + METHOD,
        "fixture: " + FIXTURE,
        "oracle: " + ORACLE,
    ]
    reasons.extend(rights_reasons(info))
    for token in faults:
        reasons.append(FAULT_TEXT[token])
    if PUBLIC_WEB_NOT_LICENCE in faults:
        reasons.append("mutant rejected: " + MUTANT)
    if not faults:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append(
            "rights recorded; citation kept separate from unlicensed bytes; not a physical qualification"
        )
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a rights manifest or reject an unlicensed redistribution."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    evidence, claim, apply_mutant = _identity(document)
    info = judge_assets(document["assets"], apply_mutant=apply_mutant)
    faults = list(info["faults"])
    preserved = [evidence, public_rights(info), claim]
    return assemble(PHASE, faults, _reasons(info, faults), preserved, NON_CLAIM_QUESTIONS, evidence)


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate one rights payload. Invalid shapes raise ValueError."""
    require(isinstance(payload, dict), "payload must be an object")
    missing = EVALUATE_KEYS - set(payload)
    extra = set(payload) - EVALUATE_KEYS
    require(not missing, "payload missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "payload has unexpected fields: " + ", ".join(sorted(extra)))
    case_id = require_text(payload["caseId"], "caseId")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    apply_mutant = require_bool(payload["applyMutant"], "applyMutant")
    info = judge_assets(payload["assets"], apply_mutant=apply_mutant)
    faults = list(info["faults"])
    reasons = _reasons(info, faults)
    reasons.append("repeat " + repeat)
    preserved = [evidence, public_rights(info), repeat]
    questions = list(NON_CLAIM_QUESTIONS) + [repeat]
    return assemble(case_id, faults, reasons, preserved, questions, evidence)


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    evidence = require_text(payload["evidenceId"], "evidenceId")
    repeat = require_text(payload["repeat"], "repeat")
    info = judge_assets(payload["assets"], apply_mutant=False)
    return {
        "evidence": evidence,
        "repeat": repeat,
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
    reasons = [
        "host fixture only; not a physical S23 measurement",
        "oracle: " + ORACLE,
        "licence rule: " + LICENCE_RULE,
        case["expected"],
        "repeat " + bundle["repeat"],
    ]
    reasons.extend(rights_reasons(bundle["info"]))
    ordered = dedupe(faults)
    for token in ordered:
        reasons.append(text.get(token, token))
    if not ordered:
        reasons.append(
            "rights recorded; citation kept separate from unlicensed bytes; not a physical qualification"
        )
    preserved = [bundle["evidence"], public_rights(bundle["info"]), *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], ordered, reasons, preserved, questions, bundle["evidence"])
