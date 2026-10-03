#!/usr/bin/env python3
"""P046 illuminant adaptation on a host fixture.

Reference-white adaptation stays a declared von Kries scale. It is not a
rewrite of a camera spectral-sensitivity matrix. Every endpoint matrix and
neutral vector is labeled. Interpolation is accepted only between two
reference-white endpoints, only after convention and neutral-response checks,
and only when every sample in the unit-interval domain stays nonsingular and
inside the condition limit. Mixed daylight plus narrow-band LEDs keep a
mixed-light uncertainty label. One global neutral is not universal matching.

The deliberate mutant — interpolating arbitrary matrix elements without those
checks — is rejected. This module does not probe a device, does not qualify a
physical S23, and does not execute TC-P046-01 through TC-P046-08.
"""

from __future__ import annotations

import math
import re
from typing import Any


PHASE = "P046"
CASE_ID = "P046"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-illuminant-adaptation-fixture"
METHOD = (
    "Document the meaning of every endpoint matrix and neutral vector. Evaluate "
    "whether interpolation is valid for the available metadata, and test "
    "conditioning throughout the chosen domain. Mixed illumination remains a "
    "limitation; do not claim a single adaptation solves arbitrary spectra."
)
FIXTURE = (
    "A scene containing daylight and narrow-band colored LEDs with one global "
    "neutral measurement."
)
ORACLE = (
    "The pipeline applies only its declared adaptation and labels the mixed-light "
    "color uncertainty rather than claiming universal matching."
)
MUTANT = (
    "Interpolate arbitrary matrix elements without checking endpoint conventions "
    "or neutral response."
)
DECLARED = "von-kries-reference-white"
DECLARED_TEST = "declared-adaptation"
MUTANT_TEST = "unchecked-element-interpolation"
SOLE_TESTS = (DECLARED_TEST, MUTANT_TEST)
ROLES = ("reference-white", "spectral-sensitivity")
CONVENTIONS = (
    "row-camera-to-xyz",
    "column-xyz-to-camera",
    "transposed",
    "reversed",
)
ACCEPTED_CONVENTION = "row-camera-to-xyz"
SCOPES = ("global", "local", "region")
CONDITION_LIMIT = (20, 1)
DOMAIN = ((0, 1), (1, 4), (1, 2), (3, 4), (1, 1))
HOST_LIMIT = "a host estimate does not qualify a physical S23"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
CANONICAL_UINT = re.compile(r"0|[1-9][0-9]*")
CANONICAL_POSITIVE = re.compile(r"[1-9][0-9]*")
CANONICAL_INT = re.compile(r"0|-?[1-9][0-9]*")
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "endpoints",
    "neutralMeasurement",
    "scene",
    "declaredAdaptation",
    "interpolation",
}
ENDPOINT_KEYS = {"id", "role", "convention", "neutral", "matrix"}
NEUTRAL_KEYS = {"id", "scope", "channels", "patch"}
SCENE_KEYS = {"illuminants", "mixed"}
INTERPOLATION_KEYS = {
    "requested",
    "weightNumerator",
    "weightDenominator",
    "checkedConventions",
    "checkedNeutralResponse",
}
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "adaptation_limited", "adaptation_declared"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def exact_keys(value: object, required: set[str], context: str) -> dict:
    require(isinstance(value, dict), context + " must be an object")
    missing = required - set(value)
    extra = set(value) - required
    require(not missing, context + " missing fields: " + ", ".join(sorted(missing)))
    require(not extra, context + " has unexpected fields: " + ", ".join(sorted(extra)))
    return value


def _token(value: object, label: str) -> str:
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None,
            label + " must be a lowercase token")
    return value


def _uint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_UINT.fullmatch(value) is not None,
            label + " must be a canonical non-negative integer string")
    return value


def _positive(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_POSITIVE.fullmatch(value) is not None,
            label + " must be a canonical positive integer string")
    return value


def _sint(value: object, label: str) -> str:
    require(isinstance(value, str) and CANONICAL_INT.fullmatch(value) is not None,
            label + " must be a canonical integer string")
    return value


def _fraction(num: int, den: int) -> tuple[int, int]:
    require(den != 0, "fraction denominator must be non-zero")
    if den < 0:
        num, den = -num, -den
    g = abs(math.gcd(num, den))
    return num // g, den // g


def _fraction_text(pair: tuple[int, int]) -> str:
    return f"{pair[0]}/{pair[1]}"


def _greater(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] * right[1] > right[0] * left[1]


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def _vector(value: object, label: str, positive: bool) -> list[int]:
    require(isinstance(value, list) and len(value) == 3, label + " must have three components")
    parsed: list[int] = []
    for index, item in enumerate(value):
        text = _positive(item, f"{label}[{index}]") if positive else _sint(item, f"{label}[{index}]")
        parsed.append(int(text))
    return parsed


def _matrix(value: object, label: str) -> list[list[int]]:
    require(isinstance(value, list) and len(value) == 3, label + " must have three rows")
    rows: list[list[int]] = []
    for r_index, row in enumerate(value):
        require(isinstance(row, list) and len(row) == 3, label + f" row {r_index} must have three columns")
        parsed: list[int] = []
        for c_index, item in enumerate(row):
            parsed.append(int(_sint(item, f"{label}[{r_index}][{c_index}]")))
        rows.append(parsed)
    return rows


def determinant(matrix: list[list[int]]) -> int:
    """Integer determinant of a 3x3 matrix."""
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def _adjugate(matrix: list[list[int]]) -> list[list[int]]:
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    return [
        [e * i - f * h, c * h - b * i, b * f - c * e],
        [f * g - d * i, a * i - c * g, c * d - a * f],
        [d * h - e * g, b * g - a * h, a * e - b * d],
    ]


def _inf_norm(matrix: list[list[int]]) -> int:
    return max(sum(abs(item) for item in row) for row in matrix)


def condition_fraction(matrix: list[list[int]]) -> tuple[int, int] | None:
    """Infinity-norm condition number, or None when the matrix is singular.

    cond(A) = ||A||_inf * ||adj(A)||_inf / |det(A)|. Scaling A does not change it.
    """
    det = determinant(matrix)
    if det == 0:
        return None
    numerator = _inf_norm(matrix) * _inf_norm(_adjugate(matrix))
    return _fraction(numerator, abs(det))


def multiply(matrix: list[list[int]], vector: list[int]) -> list[int]:
    return [sum(matrix[row][col] * vector[col] for col in range(3)) for row in range(3)]


def von_kries_gains(target: list[int], measured: list[int]) -> list[str]:
    """Diagonal reference-white gains as reduced target/measured fractions."""
    require(len(target) == 3 and len(measured) == 3, "von Kries vectors must have three channels")
    gains: list[str] = []
    for index, (wanted, seen) in enumerate(zip(target, measured)):
        require(seen > 0 and wanted > 0, f"von Kries channel {index} must be positive")
        gains.append(_fraction_text(_fraction(wanted, seen)))
    return gains


def endpoint_meaning(endpoint: dict) -> str:
    """State what one endpoint matrix and its neutral vector mean."""
    neutral = ",".join(str(item) for item in endpoint["neutral"])
    if endpoint["role"] == "reference-white":
        kind = "reference white vector, distinct from a camera spectral sensitivity model"
    else:
        kind = "camera spectral sensitivity neutral, distinct from reference-white adaptation"
    return (
        f"endpoint {endpoint['id']} matrix is {endpoint['role']} under {endpoint['convention']}; "
        f"neutral {neutral} is the {kind}"
    )


def _blend(left: list[list[int]], right: list[list[int]], num: int, den: int) -> list[list[int]]:
    return [
        [(den - num) * left[row][col] + num * right[row][col] for col in range(3)]
        for row in range(3)
    ]


def _blend_vector(left: list[int], right: list[int], num: int, den: int) -> list[int]:
    return [(den - num) * left[index] + num * right[index] for index in range(3)]


def element_lerp_token(left: list[list[int]], right: list[list[int]]) -> str:
    """Numerator identity of a 1/2 element interpolation. Not an adaptation."""
    parts: list[str] = []
    for row in range(3):
        for col in range(3):
            parts.append(_fraction_text(_fraction(left[row][col] + right[row][col], 2)))
    return "element-lerp:1/2:" + ",".join(parts)


def _endpoint(value: object, index: int, seen: set[str]) -> dict:
    item = exact_keys(value, ENDPOINT_KEYS, f"endpoint {index}")
    ident = _token(item["id"], f"endpoint {index} id")
    require(ident not in seen, "duplicate endpoint id: " + ident)
    seen.add(ident)
    role = _token(item["role"], f"endpoint {index} role")
    require(role in ROLES, f"endpoint {index} role is not reference-white or spectral-sensitivity")
    convention = _token(item["convention"], f"endpoint {index} convention")
    require(convention in CONVENTIONS, f"endpoint {index} convention is unknown")
    neutral = _vector(item["neutral"], f"endpoint {index} neutral", True)
    matrix = _matrix(item["matrix"], f"endpoint {index} matrix")
    return {
        "id": ident,
        "role": role,
        "convention": convention,
        "neutral": neutral,
        "matrix": matrix,
    }


def _neutral(value: object) -> dict:
    item = exact_keys(value, NEUTRAL_KEYS, "neutralMeasurement")
    ident = _token(item["id"], "neutralMeasurement id")
    scope = _token(item["scope"], "neutralMeasurement scope")
    require(scope in SCOPES, "neutralMeasurement scope must be global, local, or region")
    channels = _vector(item["channels"], "neutralMeasurement channels", True)
    patch = _token(item["patch"], "neutralMeasurement patch")
    return {"id": ident, "scope": scope, "channels": channels, "patch": patch}


def _scene(value: object) -> dict:
    item = exact_keys(value, SCENE_KEYS, "scene")
    require(type(item["mixed"]) is bool, "scene mixed must be a bool")
    illuminants = item["illuminants"]
    require(isinstance(illuminants, list) and illuminants, "scene illuminants must be a non-empty list")
    parsed = [_token(name, f"scene illuminants[{index}]") for index, name in enumerate(illuminants)]
    require(len(parsed) == len(set(parsed)), "scene illuminants must be unique")
    if item["mixed"]:
        require(len(parsed) >= 2, "mixed scene needs at least two illuminants")
    else:
        require(len(parsed) == 1, "a non-mixed scene needs exactly one illuminant")
    return {"illuminants": parsed, "mixed": item["mixed"]}


def _interpolation(value: object) -> dict:
    item = exact_keys(value, INTERPOLATION_KEYS, "interpolation")
    require(type(item["requested"]) is bool, "interpolation requested must be a bool")
    require(type(item["checkedConventions"]) is bool, "checkedConventions must be a bool")
    require(type(item["checkedNeutralResponse"]) is bool, "checkedNeutralResponse must be a bool")
    numerator = int(_uint(item["weightNumerator"], "weightNumerator"))
    denominator = int(_positive(item["weightDenominator"], "weightDenominator"))
    require(numerator <= denominator, "interpolation weight must be at most 1")
    require(math.gcd(numerator, denominator) == 1, "interpolation weight must be a reduced fraction")
    return {
        "requested": item["requested"],
        "weight": (numerator, denominator),
        "checkedConventions": item["checkedConventions"],
        "checkedNeutralResponse": item["checkedNeutralResponse"],
    }


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P046 illuminant fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "illuminant document")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1,
            "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P046")
    require(document["mapId"] == MAP_ID, "mapId must be s23-illuminant-adaptation-fixture")
    revision = document["implementationBaseRevision"]
    require(revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
            "illuminant document needs the P046 implementation base revision")
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    endpoints = document["endpoints"]
    require(isinstance(endpoints, list) and endpoints, "endpoints must be a non-empty list")
    seen: set[str] = set()
    for index, item in enumerate(endpoints):
        _endpoint(item, index, seen)
    _neutral(document["neutralMeasurement"])
    _scene(document["scene"])
    require(document["declaredAdaptation"] == DECLARED,
            "declaredAdaptation must be von-kries-reference-white")
    _interpolation(document["interpolation"])


def _load(document: dict) -> dict[str, Any]:
    seen: set[str] = set()
    endpoints = [_endpoint(item, index, seen) for index, item in enumerate(document["endpoints"])]
    return {
        "endpoints": endpoints,
        "neutral": _neutral(document["neutralMeasurement"]),
        "scene": _scene(document["scene"]),
        "interpolation": _interpolation(document["interpolation"]),
    }


def _matrix_text(matrix: list[list[int]]) -> str:
    return ",".join(str(item) for row in matrix for item in row)


def _cond_text(matrix: list[list[int]]) -> str:
    cond = condition_fraction(matrix)
    if cond is None:
        return "undefined"
    return _fraction_text(cond)


def _response_text(matrix: list[list[int]], neutral: list[int]) -> str:
    return ",".join(str(item) for item in multiply(matrix, neutral))


def _endpoint_token(endpoint: dict) -> str:
    neutral = ",".join(str(item) for item in endpoint["neutral"])
    return (
        f"endpoint:{endpoint['role']}:{endpoint['id']}:{endpoint['convention']}:"
        f"neutral={neutral}:matrix={_matrix_text(endpoint['matrix'])}:"
        f"cond={_cond_text(endpoint['matrix'])}:"
        f"response={_response_text(endpoint['matrix'], endpoint['neutral'])}"
    )


def _positive_response(matrix: list[list[int]], neutral: list[int]) -> bool:
    return all(item > 0 for item in multiply(matrix, neutral))


def _preserved(loaded: dict[str, Any], adaptation: str, interpolation: str) -> list[str]:
    scene = loaded["scene"]
    neutral = loaded["neutral"]
    preserved = [
        "scene:" + "+".join(scene["illuminants"]) + f":mixed={'true' if scene['mixed'] else 'false'}",
        (
            f"neutral:{neutral['id']}:{neutral['scope']}:"
            + ",".join(str(item) for item in neutral["channels"])
            + f":patch={neutral['patch']}"
        ),
    ]
    preserved.extend(_endpoint_token(item) for item in loaded["endpoints"])
    preserved.append(adaptation)
    preserved.extend(
        f"spectral-sensitivity:{item['id']}:unchanged"
        for item in loaded["endpoints"]
        if item["role"] == "spectral-sensitivity"
    )
    preserved.append(interpolation)
    return preserved


def _questions(loaded: dict[str, Any], extra: list[str]) -> list[str]:
    items = list(extra)
    if loaded["scene"]["mixed"]:
        items.append("mixed illumination is not solved by one global neutral")
    items.append("host fixture is not a physical S23 measurement")
    return _dedupe(items)


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS and decision not in _FORBIDDEN,
            "P046 must not decide qualified or allowed")
    require(bool(reasons) and all(isinstance(item, str) and item for item in reasons),
            "reasons must be a non-empty list of strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": list(reasons),
        "rejectedClaims": _dedupe(rejected),
        "preservedResults": list(preserved),
        "openQuestions": _dedupe(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def _reference_whites(endpoints: list[dict]) -> list[dict]:
    return [item for item in endpoints if item["role"] == "reference-white"]


def _adaptation_token(loaded: dict[str, Any]) -> str:
    whites = _reference_whites(loaded["endpoints"])
    if not whites:
        return "adaptation:unavailable"
    gains = von_kries_gains(whites[0]["neutral"], loaded["neutral"]["channels"])
    return "adaptation:" + DECLARED + ":" + ",".join(gains)


def _domain_problem(left: dict, right: dict) -> str | None:
    for num, den in DOMAIN:
        blended = _blend(left["matrix"], right["matrix"], num, den)
        label = _fraction_text(_fraction(num, den))
        if determinant(blended) == 0:
            return "singular-domain:" + label
        cond = condition_fraction(blended)
        if cond is None or _greater(cond, CONDITION_LIMIT):
            return "ill-conditioned-domain:" + label
        neutral = _blend_vector(left["neutral"], right["neutral"], num, den)
        if not _positive_response(blended, neutral):
            return "neutral-response-domain:" + label
    return None


def _endpoint_problem(endpoint: dict) -> str | None:
    if endpoint["convention"] != ACCEPTED_CONVENTION:
        return f"convention:{endpoint['id']}:{endpoint['convention']}"
    if determinant(endpoint["matrix"]) == 0:
        return "singular:" + endpoint["id"]
    cond = condition_fraction(endpoint["matrix"])
    if cond is None or _greater(cond, CONDITION_LIMIT):
        return "ill-conditioned:" + endpoint["id"]
    if not _positive_response(endpoint["matrix"], endpoint["neutral"]):
        return "neutral-response:" + endpoint["id"]
    return None


def _interpolation_status(loaded: dict[str, Any]) -> tuple[str, str | None]:
    """Return the interpolation inventory token and an optional rejection claim."""
    request = loaded["interpolation"]
    if not request["requested"]:
        return "interpolation:not-requested", None
    if not request["checkedConventions"] or not request["checkedNeutralResponse"]:
        return "interpolation:invalid:unchecked", "unchecked-element-interpolation"
    whites = _reference_whites(loaded["endpoints"])
    if len(whites) != 2:
        return "interpolation:invalid:endpoint-count", "interpolation-endpoint-count"
    if loaded["scene"]["mixed"]:
        return "interpolation:invalid:mixed-illumination", None
    problem = _domain_problem(whites[0], whites[1])
    if problem is not None:
        return "interpolation:invalid:" + problem.split(":", 1)[0], problem
    weights = ",".join(_fraction_text(_fraction(num, den)) for num, den in DOMAIN)
    return "interpolation:valid:" + weights, None


def _base_reasons(loaded: dict[str, Any], adaptation: str) -> list[str]:
    reasons = [ORACLE]
    reasons.extend(endpoint_meaning(item) for item in loaded["endpoints"])
    parts = [f"{item['id']} {_cond_text(item['matrix'])}" for item in loaded["endpoints"]]
    reasons.append("conditioning " + ", ".join(parts))
    if adaptation == "adaptation:unavailable":
        reasons.append("declared adaptation is unavailable without a reference-white endpoint")
    else:
        reasons.append(
            "declared adaptation " + adaptation.split(":", 1)[1] + " leaves spectral sensitivity unchanged"
        )
    if loaded["scene"]["mixed"]:
        reasons.append(
            "mixed-light color uncertainty remains; one global neutral does not solve arbitrary spectra"
        )
    else:
        reasons.append("single-illuminant metadata still does not measure a camera spectral sensitivity")
    return reasons


def _shared_claims(loaded: dict[str, Any]) -> list[str]:
    claims = ["universal-matching"]
    if any(item["role"] == "spectral-sensitivity" for item in loaded["endpoints"]):
        claims.append("spectral-sensitivity-rewrite")
    return claims


def assess(document: dict, sole_test: str = DECLARED_TEST) -> dict:
    """Apply only the declared adaptation. Reject unchecked element interpolation.

    sole_test "unchecked-element-interpolation" is the mutant. It is rejected
    even when endpoint numbers are finite. Spectral-sensitivity matrices stay
    in preservedResults unchanged, and the element lerp is not installed.
    """
    validate_document(document)
    require(sole_test in SOLE_TESTS,
            "sole_test must be declared-adaptation or unchecked-element-interpolation")
    loaded = _load(document)
    adaptation = _adaptation_token(loaded)
    interpolation, interpolation_claim = _interpolation_status(loaded)
    preserved = _preserved(loaded, adaptation, interpolation)
    reasons = _base_reasons(loaded, adaptation)
    rejected = _shared_claims(loaded)
    questions_extra: list[str] = []

    endpoint_claims = [claim for item in loaded["endpoints"] if (claim := _endpoint_problem(item))]
    decision: str | None = None
    if endpoint_claims:
        decision = "rejected"
        rejected = endpoint_claims + rejected
        reasons.append("endpoint convention, singularity, conditioning, or neutral response failed")
        questions_extra.append(endpoint_claims[0])
        interpolation = "interpolation:invalid:endpoint"
        preserved = _preserved(loaded, adaptation, interpolation)
    elif interpolation_claim == "unchecked-element-interpolation":
        decision = "rejected"
        unchecked = ["unchecked-element-interpolation"]
        request = loaded["interpolation"]
        if not request["checkedConventions"]:
            unchecked.append("endpoint-convention-not-checked")
        if not request["checkedNeutralResponse"]:
            unchecked.append("neutral-response-not-checked")
        rejected = unchecked + rejected
        reasons.append(MUTANT)
        reasons.append("interpolation request did not check endpoint conventions or neutral response")
        questions_extra.append("unchecked element interpolation was rejected")
    elif interpolation_claim is not None:
        decision = "rejected"
        rejected = [interpolation_claim] + rejected
        reasons.append("interpolation " + interpolation + " was not applied")
        questions_extra.append(interpolation_claim)
    elif not _reference_whites(loaded["endpoints"]):
        decision = "withheld"
        rejected = ["missing-reference-white"] + rejected
        questions_extra.append("no reference-white endpoint")
    elif loaded["neutral"]["scope"] != "global":
        decision = "withheld"
        rejected = ["non-global-neutral"] + rejected
        questions_extra.append("neutral scope is not a single global measurement")
    elif loaded["scene"]["mixed"]:
        decision = "adaptation_limited"
        reasons.append("interpolation was not applied" if interpolation == "interpolation:not-requested"
                       else "interpolation is not valid for mixed illumination")
    else:
        decision = "adaptation_declared"
        if interpolation.startswith("interpolation:valid:"):
            reasons.append(
                "interpolation is valid only between reference-white endpoints and was not "
                "substituted for the declared adaptation"
            )
        else:
            reasons.append("interpolation was not applied")
        questions_extra.append("declared adaptation is not a camera spectral-sensitivity measurement")

    if sole_test == MUTANT_TEST:
        decision = "rejected"
        pair = loaded["endpoints"]
        mutant_claims = [
            "unchecked-element-interpolation",
            "endpoint-convention-not-checked",
            "neutral-response-not-checked",
        ]
        if len(pair) >= 2:
            mutant_claims.append(element_lerp_token(pair[0]["matrix"], pair[1]["matrix"]))
        else:
            mutant_claims.append("element-lerp:unavailable")
        rejected = mutant_claims + rejected
        if MUTANT not in reasons:
            reasons.append(MUTANT)
        reasons.append("element interpolation was not installed as the adaptation")
        questions_extra.insert(0, "unchecked element interpolation was rejected")

    reasons.append(HOST_LIMIT)
    return _result(decision, reasons, rejected, preserved, _questions(loaded, questions_extra))
