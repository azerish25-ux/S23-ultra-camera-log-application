"""TC-P127-08 Shared bundle privacy and interpretation.

Host fixture. Personal paths and identifiers are redacted. A Log master
without its interpretation record is not self-describing. Technical hashes,
transfer, and the required non-claim stay in the share. Bundle rules apply.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

CASE_ID = "TC-P127-08"
NAME = "Shared bundle privacy and interpretation"
INTERVENTION = "Export a result with private paths or without necessary signal and recipe metadata."
EXPECTED = "Redact personal information while retaining the technical interpretation needed for correct use."
NEGATIVE = "A Log master without its required interpretation record must not be silently presented as universally self-describing."
REPEAT = "Repeat clean Log, rendered SDR, HDR-derived looks, and unverified partial exports."
NEGATIVE_TOKEN = "log-master-presented-as-self-describing"
KIND_TOKEN = "share-kind-disagrees-with-color-transfer"
VERIFIED_PARTIAL = "partial-export-marked-verified"
PARTIAL_EXPORT = "unverified-partial-exported-as-complete"
SUMMARY_TOKEN = "verification-summary-missing"
SHARE_KINDS = frozenset({"log-master", "rendered-sdr", "hdr-derived", "unverified-partial"})
KIND_TRANSFERS = {
    "log-master": frozenset({"logc3"}),
    "rendered-sdr": frozenset({"bt709"}),
    "hdr-derived": frozenset({"hlg"}),
    "unverified-partial": frozenset({"bt709", "hlg", "logc3", "pq", "unknown"}),
}
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
    "shareKind",
    "verificationSummaryPresent",
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


def evaluate(payload: dict) -> dict:
    if not isinstance(payload, dict) or set(payload) != set(PAYLOAD_KEYS):
        raise ValueError("invalid payload keys")
    evidence = _CORE.require_text(payload["evidenceId"], "evidenceId", stripped=True)
    repeat = _CORE.require_text(payload["repeat"], "repeat", stripped=True)
    kind = payload["shareKind"]
    if kind not in SHARE_KINDS:
        raise ValueError("shareKind is invalid")
    if type(payload["verificationSummaryPresent"]) is not bool:
        raise ValueError("verificationSummaryPresent must be a bool")
    bundle = _CORE.judge_bundle(payload)
    color = payload["manifest"]["color_transfer"]
    reasons = [f"{CASE_ID} {NAME} repeat {repeat}", EXPECTED, INTERVENTION, "shareKind=" + kind]
    reasons.extend(bundle["reasons"])
    rejected = list(bundle["rejectedClaims"])
    if color not in KIND_TRANSFERS[kind]:
        rejected.append(KIND_TOKEN)
        reasons.append("share kind disagrees with color_transfer")
    if kind == "log-master" and payload["interpretation"] is None and payload["selfDescribing"]:
        if NEGATIVE_TOKEN not in rejected:
            rejected.append(NEGATIVE_TOKEN)
        reasons.append(NEGATIVE)
    if kind == "unverified-partial":
        if payload["verificationSummaryPresent"]:
            rejected.append(VERIFIED_PARTIAL)
            reasons.append("unverified partial export was marked verified")
        if payload["export_allowed"]:
            rejected.append(PARTIAL_EXPORT)
            reasons.append("unverified partial export is not a complete share")
        else:
            reasons.append("unverified partial export kept out of the default verified share")
    elif payload["export_allowed"] and not payload["verificationSummaryPresent"]:
        rejected.append(SUMMARY_TOKEN)
        reasons.append("complete export requires a verification summary")
    elif kind != "log-master" or payload["interpretation"] is not None:
        reasons.append("technical interpretation retained for the share")
    preserved = [evidence]
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
