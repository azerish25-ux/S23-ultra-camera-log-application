#!/usr/bin/env python3
"""P147 Secure media and profile import boundaries.

Host reference only. This module does not probe a device and does not qualify
a physical S23. External files, archives, LUTs, models, and profiles stay
hostile until kind, size, magic, header, and path checks all pass.

Import rule: an import declares kind (media, archive, lut, model, profile),
declared_size, actual_size, extension, and magic. Trusting the extension while
magic disagrees is rejected. Allocating from an unvalidated header
(header_validated false) is rejected. declared_size must match actual_size
within 0 or be rejected. Zip/archive path traversal ("../") is rejected. A
validated import with matching magic, size, and no traversal is recorded.
"""

from __future__ import annotations

import math
from typing import Any

BASE_REVISION = "db5593a4c7dae4d23363e70a27f0f93c3eb07b2b"
PHASE = "P147"
WORKSTREAM = 19
TITLE = "Secure media and profile import boundaries"
GOAL = "Treat external files, archives, LUTs, models, and profiles as hostile until validated."
METHOD = (
    "Bound lengths, dimensions, nesting, decompression, and allocation before use. "
    "Validate paths and hashes, restrict URI grants, and keep native parsers current. "
    "Reject nonfinite matrices and dangerous archive paths. Fuzz parsers with retained "
    "minimal reproducers."
)
FIXTURE = "A profile containing NaN, a huge declared image dimension, and an archive path attempting parent traversal."
ORACLE = "All inputs fail safely without excessive allocation, file escape, or source corruption."
MUTANT = "Trust extension names and allocate according to unvalidated headers."
DELIVERABLE = "Import threat model and parser fuzz corpus"
DEPENDENCIES = ("P146",)

IMPORT_RULE = (
    "An import declares kind (media, archive, lut, model, profile), declared_size, "
    "actual_size, extension, and magic. Trusting the extension while magic disagrees "
    "is rejected. Allocating from an unvalidated header (header_validated false) is "
    "rejected. declared_size must match actual_size within 0 or be rejected. "
    'Zip/archive path traversal ("../") is rejected. A validated import with matching '
    "magic, size, and no traversal is recorded."
)

OPEN_QUESTION = "physical S23 measurement was not run"
EVIDENCE_ID = "p147-secure-import"
CLAIM = "secure-media-and-profile-import-boundaries-host-reference"

IMPORT_KINDS = ("media", "archive", "lut", "model", "profile")
SIZE_TOLERANCE = 0
MAX_DIMENSION = 8192
MAX_LENGTH = 8_000_000
MAX_ALLOCATION = 8_000_000
MAX_NESTING = 8
MAX_DECOMPRESSION_RATIO = 100
HIGH_COVERAGE = 0.8

# Canonical signatures. magic == extension also agrees, so a declared token can
# match without pretending the extension string is itself a file signature.
EXTENSION_MAGIC = {
    "dng": "dng",
    "mov": "mov",
    "mp4": "mp4",
    "zip": "PK",
    "cube": "cube",
    "onnx": "onnx",
    "json": "json",
}
KIND_EXTENSIONS = {
    "media": frozenset({"dng", "mov", "mp4"}),
    "archive": frozenset({"zip"}),
    "lut": frozenset({"cube"}),
    "model": frozenset({"onnx"}),
    "profile": frozenset({"json"}),
}
NONFINITE_TOKENS = frozenset({
    "NaN",
    "nan",
    "Infinity",
    "+Infinity",
    "-Infinity",
    "inf",
    "-inf",
    "+inf",
})

TRUSTED_EXTENSION = "trusted-extension-magic-disagrees"
UNVALIDATED_HEADER = "unvalidated-header-allocation"
SIZE_MISMATCH = "declared-size-mismatch"
PATH_TRAVERSAL = "archive-path-traversal"
NONFINITE = "nonfinite-matrix"
EXCESSIVE_DIMENSION = "excessive-dimension"
EXCESSIVE_LENGTH = "excessive-length"
EXCESSIVE_ALLOCATION = "excessive-allocation"
EXCESSIVE_NESTING = "excessive-nesting"
DECOMPRESSION = "decompression-pressure"
URI_GRANT = "unrestricted-uri-grant"
HASH_INVALID = "hash-not-validated"
FILE_ESCAPE = "file-escape"
SOURCE_CORRUPTION = "source-corruption"
MALFORMED_LENGTH = "malformed-length"
KIND_EXTENSION = "kind-extension-mismatch"
KIND_GAP = "import-kind-missing"
FIXTURE_INCOMPLETE = "fixture-reproducers-missing"
CORPUS_NOT_HOSTILE = "corpus-reproducer-not-hostile"
CORPUS_UNSAFE = "corpus-failed-unsafely"

ORACLE_BREACH = frozenset({EXCESSIVE_ALLOCATION, FILE_ESCAPE, SOURCE_CORRUPTION})
CRITICAL_CORPUS_IDS = (
    "nan-profile",
    "huge-dimension",
    "archive-traversal",
    "trust-extension-unvalidated-header",
)

RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DECISIONS = frozenset({"recorded", "rejected"})
NON_CLAIM_QUESTIONS = [
    OPEN_QUESTION,
    "sensor-derived Log was not established",
    "ten-bit fidelity was not established",
    "film-stock fidelity was not established",
    "cinema-camera equivalence was not established",
]
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "implementationBaseRevision",
    "evidenceId",
    "claim",
    "imports",
    "corpus",
}
CORE_KEYS = {"evidenceId", "claim", "imports", "corpus"}
CASE_COMMON_KEYS = CORE_KEYS | {"repeat"}
REQUIRED_IMPORT_KEYS = {
    "kind",
    "declared_size",
    "actual_size",
    "extension",
    "magic",
    "header_validated",
    "paths",
}
OPTIONAL_IMPORT_KEYS = {
    "id",
    "trust_extension",
    "allocated",
    "width",
    "height",
    "values",
    "nesting",
    "decompression_ratio",
    "uri",
    "hash_valid",
    "escaped",
    "source_corrupted",
}
RESULT_STATUSES = frozenset({"pass", "fail", "skip", "unavailable"})
SUMMARY_KEYS = ("pass", "fail", "skip", "unavailable")
FORBIDDEN_RELEASE_SCOPES = frozenset({"native-resolution", "camera-equivalence"})
FEATURE_STATES = frozenset({"implemented", "experimental", "physically-qualified"})
MIGRATIONS = frozenset({"explicit", "refused", "silent-uninstall", "none"})
PRIVATE_TRANSMISSIONS = frozenset({"frames", "depth", "audio", "metadata", "private-metadata"})
TRANSMISSION_KINDS = PRIVATE_TRANSMISSIONS | {"thumbnail", "none"}

FAULT_TEXT = {
    TRUSTED_EXTENSION: "trusting the extension while magic disagrees is rejected",
    UNVALIDATED_HEADER: "allocating from an unvalidated header (header_validated false) is rejected",
    SIZE_MISMATCH: "declared_size must match actual_size within 0 or be rejected",
    PATH_TRAVERSAL: 'zip/archive path traversal ("../") is rejected',
    NONFINITE: "a nonfinite profile matrix is rejected",
    EXCESSIVE_DIMENSION: "a huge declared image dimension is rejected before allocation",
    EXCESSIVE_LENGTH: "declared or actual length exceeds the bounded limit",
    EXCESSIVE_ALLOCATION: ORACLE,
    EXCESSIVE_NESTING: "archive nesting exceeds the bounded limit",
    DECOMPRESSION: "decompression pressure exceeds the bounded ratio",
    URI_GRANT: "URI grant is not a restricted local file grant",
    HASH_INVALID: "import hash was not validated",
    FILE_ESCAPE: "file escape is rejected",
    SOURCE_CORRUPTION: "source corruption is rejected",
    MALFORMED_LENGTH: "malformed length is rejected",
    KIND_EXTENSION: "extension is not valid for the declared kind",
    KIND_GAP: "validated imports must cover media, archive, lut, model, and profile",
    FIXTURE_INCOMPLETE: FIXTURE,
    CORPUS_NOT_HOSTILE: "a fuzz reproducer that is not hostile does not exercise the parser",
    CORPUS_UNSAFE: ORACLE,
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


def require_int(value: object, label: str) -> int:
    require(type(value) is int, label + " must be an int")
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


def identity_matrix() -> list[int]:
    return [1, 0, 0, 0, 1, 0, 0, 0, 1]


def magic_disagrees(extension: str, magic: str) -> bool:
    """True when the extension cannot be trusted because magic does not match it."""
    if magic == extension:
        return False
    expected = EXTENSION_MAGIC.get(extension)
    return expected is None or magic != expected


def sizes_match(declared_size: int, actual_size: int) -> bool:
    """declared_size must match actual_size within SIZE_TOLERANCE (0)."""
    return abs(declared_size - actual_size) <= SIZE_TOLERANCE


def path_traverses(path: str) -> bool:
    """Zip/archive parent traversal. The substring '../' is always rejected."""
    normalized = path.replace("\\", "/")
    if "../" in normalized:
        return True
    return ".." in normalized.split("/")


def _uri_allowed(uri: str) -> bool:
    if not uri.startswith("file://"):
        return False
    if path_traverses(uri):
        return False
    return True


def _matrix_nonfinite(values: list[Any]) -> bool:
    for value in values:
        if isinstance(value, str):
            return True
        if not math.isfinite(float(value)):
            return True
    return False


def classify_import(item: dict[str, Any]) -> list[str]:
    """Return stable fault tokens. An empty list means the import is recorded."""
    faults: list[str] = []
    extension = item["extension"]
    magic = item["magic"]
    disagrees = magic_disagrees(extension, magic)
    if extension not in KIND_EXTENSIONS.get(item["kind"], frozenset()):
        faults.append(KIND_EXTENSION)
    if disagrees:
        faults.append(TRUSTED_EXTENSION)
    if item["header_validated"] is False:
        faults.append(UNVALIDATED_HEADER)
    declared = item["declared_size"]
    actual = item["actual_size"]
    if declared <= 0 or actual <= 0:
        faults.append(MALFORMED_LENGTH)
    if not sizes_match(declared, actual):
        faults.append(SIZE_MISMATCH)
    if declared > MAX_LENGTH or actual > MAX_LENGTH:
        faults.append(EXCESSIVE_LENGTH)
    if any(path_traverses(path) for path in item["paths"]):
        faults.append(PATH_TRAVERSAL)
    if item["width"] <= 0 or item["height"] <= 0 or item["width"] > MAX_DIMENSION or item["height"] > MAX_DIMENSION:
        faults.append(EXCESSIVE_DIMENSION)
    if _matrix_nonfinite(item["values"]):
        faults.append(NONFINITE)
    if item["nesting"] > MAX_NESTING:
        faults.append(EXCESSIVE_NESTING)
    if item["decompression_ratio"] > MAX_DECOMPRESSION_RATIO:
        faults.append(DECOMPRESSION)
    if not _uri_allowed(item["uri"]):
        faults.append(URI_GRANT)
    if item["hash_valid"] is False:
        faults.append(HASH_INVALID)
    if item["allocated"] > MAX_ALLOCATION:
        faults.append(EXCESSIVE_ALLOCATION)
    if item["escaped"] is True:
        faults.append(FILE_ESCAPE)
    if item["source_corrupted"] is True:
        faults.append(SOURCE_CORRUPTION)
    return dedupe(faults)


def _parse_matrix(value: object, label: str) -> list[Any]:
    require(isinstance(value, list) and bool(value), label + " must be a non-empty list")
    parsed: list[Any] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if isinstance(item, str):
            require(item in NONFINITE_TOKENS, item_label + " is not a number or nonfinite token")
            parsed.append(item)
            continue
        require(type(item) in (int, float), item_label + " must be a number")
        parsed.append(item)
    return parsed


def _parse_paths(value: object, label: str) -> list[str]:
    require(isinstance(value, list) and bool(value), label + " must be a non-empty list")
    return [require_text(item, f"{label}[{index}]") for index, item in enumerate(value)]


def parse_import(value: object, label: str, required_extra: set[str] | None = None) -> dict[str, Any]:
    require(isinstance(value, dict), label + " must be an object")
    extra = set(required_extra or ())
    required = set(REQUIRED_IMPORT_KEYS) | extra
    allowed = required | set(OPTIONAL_IMPORT_KEYS)
    unknown = set(value) - allowed
    missing = required - set(value)
    require(not unknown, label + " has unexpected fields: " + ", ".join(sorted(unknown)))
    require(not missing, label + " missing fields: " + ", ".join(sorted(missing)))
    kind = require_text(value["kind"], label + ".kind")
    require(kind in IMPORT_KINDS, label + ".kind is not a supported import kind")
    extension = require_text(value["extension"], label + ".extension")
    magic = require_text(value["magic"], label + ".magic")
    declared = require_int(value["declared_size"], label + ".declared_size")
    actual = require_int(value["actual_size"], label + ".actual_size")
    header_validated = require_bool(value["header_validated"], label + ".header_validated")
    paths = _parse_paths(value["paths"], label + ".paths")
    if "id" in value:
        import_id = require_text(value["id"], label + ".id")
    else:
        import_id = ""
    trust_extension = require_bool(value["trust_extension"], label + ".trust_extension") if "trust_extension" in value else False
    allocated = require_int(value["allocated"], label + ".allocated") if "allocated" in value else 0
    require(allocated >= 0, label + ".allocated must be >= 0")
    width = require_int(value["width"], label + ".width") if "width" in value else 1
    height = require_int(value["height"], label + ".height") if "height" in value else 1
    if "values" in value:
        values = _parse_matrix(value["values"], label + ".values")
    else:
        values = [1]
    nesting = require_int(value["nesting"], label + ".nesting") if "nesting" in value else 1
    require(nesting >= 0, label + ".nesting must be >= 0")
    if "decompression_ratio" in value:
        ratio = require_int(value["decompression_ratio"], label + ".decompression_ratio")
    else:
        ratio = 1
    require(ratio >= 0, label + ".decompression_ratio must be >= 0")
    uri = require_text(value["uri"], label + ".uri") if "uri" in value else "file://imports/local"
    hash_valid = require_bool(value["hash_valid"], label + ".hash_valid") if "hash_valid" in value else True
    escaped = require_bool(value["escaped"], label + ".escaped") if "escaped" in value else False
    corrupted = (
        require_bool(value["source_corrupted"], label + ".source_corrupted")
        if "source_corrupted" in value
        else False
    )
    parsed: dict[str, Any] = {
        "id": import_id,
        "kind": kind,
        "declared_size": declared,
        "actual_size": actual,
        "extension": extension,
        "magic": magic,
        "header_validated": header_validated,
        "paths": paths,
        "trust_extension": trust_extension,
        "allocated": allocated,
        "width": width,
        "height": height,
        "values": values,
        "nesting": nesting,
        "decompression_ratio": ratio,
        "uri": uri,
        "hash_valid": hash_valid,
        "escaped": escaped,
        "source_corrupted": corrupted,
    }
    for key in extra:
        if key == "accepted":
            parsed["accepted"] = require_bool(value["accepted"], label + ".accepted")
        else:
            parsed[key] = value[key]
    parsed["faults"] = classify_import(parsed)
    parsed["decision"] = "rejected" if parsed["faults"] else "recorded"
    parsed["magic_disagrees"] = magic_disagrees(extension, magic)
    return parsed


def _parse_import_list(value: object, label: str) -> list[dict[str, Any]]:
    require(isinstance(value, list) and bool(value), label + " must be a non-empty list")
    rows = [parse_import(item, f"{label}[{index}]") for index, item in enumerate(value)]
    for index, row in enumerate(rows):
        if not row["id"]:
            row["id"] = f"{label}-{index}"
    ids = [row["id"] for row in rows]
    require(len(ids) == len(set(ids)), label + " ids must be unique")
    return rows


def _fixture_gaps(corpus: list[dict[str, Any]]) -> list[str]:
    groups = [set(item["faults"]) for item in corpus]
    gaps: list[str] = []
    if not any(NONFINITE in group for group in groups):
        gaps.append("nan-profile")
    if not any(EXCESSIVE_DIMENSION in group for group in groups):
        gaps.append("huge-dimension")
    if not any(PATH_TRAVERSAL in group for group in groups):
        gaps.append("archive-traversal")
    if not any(TRUSTED_EXTENSION in group and UNVALIDATED_HEADER in group for group in groups):
        gaps.append("unvalidated-extension-trust")
    return gaps


def analyze_computation(*, imports: list[dict[str, Any]], corpus: list[dict[str, Any]]) -> dict[str, Any]:
    faults: list[str] = []
    for item in imports:
        faults.extend(item["faults"])
    present = {item["kind"] for item in imports}
    if any(kind not in present for kind in IMPORT_KINDS):
        faults.append(KIND_GAP)
    rejected_corpus = 0
    for item in corpus:
        if not item["faults"]:
            faults.append(CORPUS_NOT_HOSTILE)
            continue
        rejected_corpus += 1
        breaches = [token for token in item["faults"] if token in ORACLE_BREACH]
        if breaches:
            faults.extend(breaches)
            faults.append(CORPUS_UNSAFE)
    if _fixture_gaps(corpus):
        faults.append(FIXTURE_INCOMPLETE)
    validated = sum(1 for item in imports if item["decision"] == "recorded")
    snapshot = {
        "sizeTolerance": SIZE_TOLERANCE,
        "importDecisions": {item["id"]: item["decision"] for item in imports},
        "importFaults": {item["id"]: list(item["faults"]) for item in imports},
        "corpusDecisions": {item["id"]: item["decision"] for item in corpus},
        "corpusFaults": {item["id"]: list(item["faults"]) for item in corpus},
        "validatedCount": validated,
        "rejectedCorpusCount": rejected_corpus,
    }
    extra_reasons = [
        "import rule: " + IMPORT_RULE,
        "size tolerance " + str(SIZE_TOLERANCE),
        "validated imports " + str(validated),
        "rejected corpus " + str(rejected_corpus),
    ]
    if validated == len(imports) and not faults:
        extra_reasons.append("validated import with matching magic, size, and no traversal is recorded")
    return {
        "faults": dedupe(faults),
        "snapshot": snapshot,
        "extraReasons": extra_reasons,
    }


def assemble(
    case_id: str,
    faults: list[str],
    reasons: list[str],
    preserved: list,
    open_questions: list[str],
    evidence: str,
) -> dict[str, Any]:
    ordered = dedupe(faults)
    decision = "rejected" if ordered else "recorded"
    require(decision in DECISIONS, "decision must be recorded or rejected")
    result = {
        "caseId": case_id,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": ordered,
        "preservedResults": preserved,
        "openQuestions": list(open_questions),
    }
    require(tuple(result) == RESULT_KEYS, "result keys drifted")
    require(evidence in result["preservedResults"], "evidence must be preserved")
    require(OPEN_QUESTION in result["openQuestions"], "open question missing")
    require(result["decision"] not in {"qualified", "allowed"}, "this phase must not qualify the fixture")
    require(bool(result["reasons"]), "reasons must be non-empty")
    return result


def _core_from_mapping(mapping: dict, label: str) -> dict[str, Any]:
    evidence = require_text(mapping["evidenceId"], "evidenceId")
    claim = require_text(mapping["claim"], "claim")
    imports = _parse_import_list(mapping["imports"], "imports")
    corpus = _parse_import_list(mapping["corpus"], "corpus")
    analysis = analyze_computation(imports=imports, corpus=corpus)
    analysis["evidence"] = evidence
    analysis["claim"] = claim
    analysis["label"] = label
    return analysis


def _reasons(analysis: dict[str, Any], lead: list[str], fault_text: dict[str, str] | None) -> list[str]:
    text = dict(FAULT_TEXT)
    if fault_text:
        text.update(fault_text)
    reasons = list(lead)
    reasons.extend(analysis["extraReasons"])
    for token in analysis["faults"]:
        reasons.append(text.get(token, token))
    if not analysis["faults"]:
        reasons.append("deliverable: " + DELIVERABLE)
        reasons.append("import threat model recorded; not a physical qualification")
    return reasons


def assess(document: dict) -> dict[str, Any]:
    """Record a validated import boundary and a rejected fuzz corpus, or reject it."""
    require(isinstance(document, dict), "document must be an object")
    missing = DOCUMENT_KEYS - set(document)
    extra = set(document) - DOCUMENT_KEYS
    require(not missing, "document missing fields: " + ", ".join(sorted(missing)))
    require(not extra, "document has unexpected fields: " + ", ".join(sorted(extra)))
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be " + PHASE)
    require(document["implementationBaseRevision"] == BASE_REVISION, "base revision mismatch")
    analysis = _core_from_mapping(document, "document")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "goal: " + GOAL,
            "method: " + METHOD,
            "fixture: " + FIXTURE,
            "oracle: " + ORACLE,
        ],
        None,
    )
    if TRUSTED_EXTENSION in analysis["faults"] or UNVALIDATED_HEADER in analysis["faults"]:
        reasons.append("mutant rejected: " + MUTANT)
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def evaluate(payload: dict) -> dict[str, Any]:
    """Evaluate a phase document or a core import-boundary payload."""
    require(isinstance(payload, dict), "payload must be an object")
    if "schemaVersion" in payload or "implementationBaseRevision" in payload or "phase" in payload:
        return assess(payload)
    require(set(payload) == CORE_KEYS, "invalid payload keys")
    analysis = _core_from_mapping(payload, "payload")
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            "fixture: " + FIXTURE,
        ],
        None,
    )
    preserved = [analysis["evidence"], analysis["snapshot"], analysis["claim"]]
    return assemble(PHASE, analysis["faults"], reasons, preserved, NON_CLAIM_QUESTIONS, analysis["evidence"])


def begin_case(payload: dict, extra_keys: set[str]) -> dict[str, Any]:
    require(isinstance(payload, dict), "payload must be an object")
    require(set(payload) == set(CASE_COMMON_KEYS) | set(extra_keys), "invalid payload keys")
    repeat = require_text(payload["repeat"], "repeat")
    analysis = _core_from_mapping(payload, "case")
    return {
        "evidence": analysis["evidence"],
        "claim": analysis["claim"],
        "repeat": repeat,
        "faults": list(analysis["faults"]),
        "analysis": analysis,
        "snapshot": analysis["snapshot"],
    }


def finish_case(
    case: dict,
    bundle: dict,
    faults: list[str],
    extra_preserved: list,
    fault_text: dict | None = None,
) -> dict[str, Any]:
    analysis = dict(bundle["analysis"])
    analysis["faults"] = dedupe(list(faults))
    reasons = _reasons(
        analysis,
        [
            "host reference only; not a physical S23 measurement",
            "physical S23 was not run",
            "oracle: " + ORACLE,
            case["expected"],
            "repeat " + bundle["repeat"],
        ],
        fault_text,
    )
    preserved = [bundle["evidence"], bundle["snapshot"], bundle["claim"], *extra_preserved]
    questions = list(NON_CLAIM_QUESTIONS) + [case["repeat"]]
    return assemble(case["id"], analysis["faults"], reasons, preserved, questions, bundle["evidence"])


def make_import(
    import_id: str,
    kind: str,
    extension: str,
    magic: str,
    **overrides: Any,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": import_id,
        "kind": kind,
        "declared_size": 1024,
        "actual_size": 1024,
        "extension": extension,
        "magic": magic,
        "header_validated": True,
        "paths": [f"imports/{import_id}.{extension}"],
        "trust_extension": False,
        "allocated": 1024,
        "width": 1920,
        "height": 1080,
        "values": identity_matrix(),
        "nesting": 1,
        "decompression_ratio": 1,
        "uri": f"file://imports/{import_id}.{extension}",
        "hash_valid": True,
        "escaped": False,
        "source_corrupted": False,
    }
    payload.update(overrides)
    return payload


def fixture_imports() -> list[dict[str, Any]]:
    return [
        make_import("media-dng", "media", "dng", "dng"),
        make_import(
            "archive-zip",
            "archive",
            "zip",
            "PK",
            paths=["imports/archive-zip.zip", "luts/stock.cube"],
        ),
        make_import("lut-cube", "lut", "cube", "cube"),
        make_import("model-onnx", "model", "onnx", "onnx"),
        make_import("profile-json", "profile", "json", "json"),
    ]


def fixture_corpus() -> list[dict[str, Any]]:
    """Hostile reproducers that must fail safely. None of these are accepted imports."""
    nan_values = identity_matrix()
    nan_values[4] = "NaN"
    return [
        make_import(
            "nan-profile",
            "profile",
            "json",
            "json",
            values=nan_values,
            allocated=0,
        ),
        make_import(
            "huge-dimension",
            "media",
            "dng",
            "dng",
            width=MAX_DIMENSION + 1,
            height=MAX_DIMENSION + 1,
            allocated=0,
        ),
        make_import(
            "archive-traversal",
            "archive",
            "zip",
            "PK",
            paths=["../escape"],
            allocated=0,
        ),
        make_import(
            "trust-extension-unvalidated-header",
            "lut",
            "cube",
            "PK",
            trust_extension=True,
            header_validated=False,
            declared_size=MAX_LENGTH + 1,
            actual_size=64,
            allocated=0,
        ),
    ]


def core_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "evidenceId": EVIDENCE_ID,
        "claim": CLAIM,
        "imports": fixture_imports(),
        "corpus": fixture_corpus(),
    }
    payload.update(overrides)
    return payload


def fixture_document() -> dict[str, Any]:
    core = core_payload()
    return {
        "schemaVersion": 1,
        "phase": PHASE,
        "implementationBaseRevision": BASE_REVISION,
        "evidenceId": core["evidenceId"],
        "claim": core["claim"],
        "imports": core["imports"],
        "corpus": core["corpus"],
    }
