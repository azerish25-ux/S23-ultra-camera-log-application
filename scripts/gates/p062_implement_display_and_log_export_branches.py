#!/usr/bin/env python3
"""P062 display and Log export branches.

Branch from a declared working image. The clean Log export excludes film
grain, halation, virtual-lens rendering, and display tone mapping. The
rendered delivery keeps its own output transform and a reproducible recipe.
The two results stay separate.

The deliberate mutant — apply the display transform before both branches and
call one output clean Log — is rejected. The honest clean codes stay in the
inventory. This module does not probe a device, does not qualify a physical
S23, and does not execute TC-P062-01 through TC-P062-08.
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


PHASE = "P062"
CASE_ID = "P062"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-display-and-log-export-branches-fixture"
METHOD = (
    "Branch from a declared working image. The clean Log export excludes film grain, "
    "halation, virtual-lens rendering, and display tone mapping unless an explicitly "
    "named processed master is selected. The rendered delivery has its own output "
    "transform and reproducible recipe."
)
FIXTURE = (
    "A take exported once as a clean Log master and again with strong grain, "
    "halation, and virtual defocus."
)
ORACLE = (
    "The clean master remains unaffected while the rendered result records all "
    "processing stages."
)
MUTANT = "Apply the display transform before both branches and call one output clean Log."
HOST_LIMIT = (
    "host fixture does not qualify a physical S23, sensor-derived Log, ten-bit fidelity, "
    "film-stock fidelity, or cinema-camera equivalence"
)
DECLARED_PATH = "declared"
MUTANT_PATH = "display-before-both"
PATHS = (DECLARED_PATH, MUTANT_PATH)
SELECTION_CLEAN = "clean-log"
SELECTION_PROCESSED = "processed-master"
SELECTIONS = (SELECTION_CLEAN, SELECTION_PROCESSED)
CLEAN_NAME = "clean-log"
RENDERED_NAME = "rendered-delivery"
ENCODING = "declared-log-fixture"
OUTPUT_TRANSFORM = "display-film-transform"
RECIPE = "strong-grain+halation+virtual-defocus"
EXCLUDED = ("film-grain", "halation", "virtual-lens", "display-tone-map")
STAGES = ("film-grain", "halation", "virtual-defocus", "output-transform")
GRAIN = Decimal("0.05")
HALATION_RED = Decimal("0.1")
DEFOCUS_GREEN = Decimal("0.25")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
SIGNED = re.compile(r"-?(?:0|[1-9][0-9]*|0\.[0-9]*[1-9]|[1-9][0-9]*\.[0-9]*[1-9])")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "workingImage",
    "cleanLog",
    "rendered",
}
WORKING_KEYS = {"id", "rgb"}
CLEAN_KEYS = {"name", "encoding", "excluded"}
RENDERED_KEYS = {"name", "outputTransform", "recipe", "stages"}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "branches_separated", "processed_master_named"}


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


def canonical(value: Decimal) -> str:
    """Render a Decimal without exponent notation or trailing zeros."""
    if not value.is_finite():
        raise ValueError("nonfinite decimal")
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _decimal(value: object, label: str) -> str:
    require(
        isinstance(value, str) and SIGNED.fullmatch(value) is not None and value != "-0",
        label + " must be a canonical signed decimal",
    )
    return value


def _rgb(value: object, label: str) -> list[str]:
    require(type(value) is list and len(value) == 3, label + " must be three components")
    return [_decimal(item, label + " component") for item in value]


def _join(values: list[str] | tuple[str, ...]) -> str:
    return ",".join(values)


def _text(values: tuple[Decimal, Decimal, Decimal]) -> str:
    return ",".join(canonical(item) for item in values)


def declared_log(value: Decimal) -> Decimal:
    """Host code only. Not LogC3 and not a sensor-derived log.

    code = (2 * scene + 1) / 4. No clamp, grain, halation, or defocus.
    """
    return (value * 2 + 1) / 4


def display_transform(value: Decimal) -> Decimal:
    """Mutant display tone map: clamp each channel into 0..1."""
    return min(Decimal(1), max(Decimal(0), value))


def render_delivery(rgb: tuple[Decimal, Decimal, Decimal]) -> tuple[Decimal, Decimal, Decimal]:
    """Apply the fixture recipe, then the rendered output transform.

    Grain adds 0.05 on each channel. Halation adds 0.1 on red. Virtual
    defocus subtracts 0.25 from green. The output transform then clamps to
    0..1. These offsets are host constants, not a film stock or a lens.
    """
    red, green, blue = rgb
    red, green, blue = red + GRAIN, green + GRAIN, blue + GRAIN
    red = red + HALATION_RED
    green = green - DEFOCUS_GREEN
    clamped = tuple(min(Decimal(1), max(Decimal(0), channel)) for channel in (red, green, blue))
    return clamped[0], clamped[1], clamped[2]


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P062 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for key, items in (
        ("rejectedClaims", rejected),
        ("preservedResults", preserved),
        ("openQuestions", questions),
    ):
        require(all(isinstance(item, str) and item for item in items), key + " must be strings")
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


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P062 branch fixture shape."""
    exact_keys(document, DOCUMENT_KEYS, "export branches")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P062")
    require(document["mapId"] == MAP_ID, "mapId must be s23-display-and-log-export-branches-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "export branches need the P062 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    working = exact_keys(document["workingImage"], WORKING_KEYS, "workingImage")
    require(TOKEN.fullmatch(working["id"] or "") is not None, "working image id must be a token")
    _rgb(working["rgb"], "working rgb")
    clean = exact_keys(document["cleanLog"], CLEAN_KEYS, "cleanLog")
    require(clean["name"] == CLEAN_NAME, "clean log name must be clean-log")
    require(clean["encoding"] == ENCODING, "encoding must be the declared host fixture, not LogC3")
    require(type(clean["excluded"]) is list and tuple(clean["excluded"]) == EXCLUDED, "clean exclusions drifted")
    rendered = exact_keys(document["rendered"], RENDERED_KEYS, "rendered")
    require(rendered["name"] == RENDERED_NAME, "rendered name must be rendered-delivery")
    require(rendered["outputTransform"] == OUTPUT_TRANSFORM, "output transform drifted")
    require(rendered["recipe"] == RECIPE, "recipe drifted")
    require(type(rendered["stages"]) is list and tuple(rendered["stages"]) == STAGES, "rendered stages drifted")


def _as_tuple(components: list[str]) -> tuple[Decimal, Decimal, Decimal]:
    red, green, blue = (Decimal(item) for item in components)
    return red, green, blue


def _questions(document: dict, path: str, selection: str) -> list[str]:
    questions = [
        HOST_LIMIT,
        "clean Log encoding is a declared host fixture, not sensor-derived Log",
        "rendered recipe " + document["rendered"]["recipe"],
    ]
    if path == MUTANT_PATH:
        questions.append("display transform before both branches was rejected")
    if selection == SELECTION_PROCESSED:
        questions.append("processed master is explicitly named and is not a clean Log export")
    return questions


def _preserved(
    document: dict,
    honest_clean: str,
    honest_rendered: str,
    path: str,
    selection: str,
    display_text: str,
    contaminated_clean: str,
    contaminated_rendered: str,
) -> list[str]:
    working = document["workingImage"]
    rendered = document["rendered"]
    return [
        f"working:{working['id']}:{_join(working['rgb'])}",
        f"clean:{CLEAN_NAME}:{honest_clean}",
        "clean-excluded:" + ",".join(EXCLUDED),
        f"rendered:{RENDERED_NAME}:{honest_rendered}",
        "rendered-stages:" + ",".join(STAGES),
        f"recipe:{rendered['recipe']}",
        f"output-transform:{rendered['outputTransform']}",
        f"encoding:{ENCODING}",
        f"path:{path}",
        f"selection:{selection}",
        f"display-working:{display_text}",
        f"contaminated-clean:{contaminated_clean}",
        f"contaminated-rendered:{contaminated_rendered}",
    ]


def assess(document: dict, path: str = DECLARED_PATH, selection: str = SELECTION_CLEAN) -> dict:
    """Keep the clean Log master off the rendered recipe, or reject the mutant.

    ``path`` ``display-before-both`` applies the display clamp before both
    branches and still names one output clean Log. That decision is
    ``rejected``. ``preservedResults`` still contain the clean codes computed
    from the working image. The decision is never ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be declared or display-before-both")
    require(selection in SELECTIONS, "selection must be clean-log or processed-master")
    working = _as_tuple(document["workingImage"]["rgb"])
    honest_clean = tuple(declared_log(channel) for channel in working)
    honest_rendered = render_delivery(working)
    displayed = tuple(display_transform(channel) for channel in working)
    mutant_clean = tuple(declared_log(channel) for channel in displayed)
    mutant_rendered = render_delivery(displayed)
    honest_clean_text = _text(honest_clean)
    honest_rendered_text = _text(honest_rendered)
    questions = _questions(document, path, selection)
    reasons = [
        ORACLE,
        "clean log branched from the working image without grain, halation, virtual-lens, or display tone mapping",
        f"clean codes {honest_clean_text}",
        f"rendered codes {honest_rendered_text}",
        "rendered stages " + ", ".join(STAGES),
        HOST_LIMIT,
    ]
    if path == MUTANT_PATH:
        preserved = _preserved(
            document,
            honest_clean_text,
            honest_rendered_text,
            path,
            selection,
            _text(displayed),
            _text(mutant_clean),
            _text(mutant_rendered),
        )
        reasons.append(MUTANT)
        reasons.append("one output was still named clean-log after the shared display transform")
        reasons.append(f"contaminated clean codes {_text(mutant_clean)}")
        if mutant_clean != honest_clean:
            reasons.append("the shared display transform changed the clean master")
        return _result(
            "rejected",
            reasons,
            ["display-before-both", "false-clean-log"],
            preserved,
            questions,
        )
    preserved = _preserved(
        document,
        honest_clean_text,
        honest_rendered_text,
        path,
        selection,
        "not-applied",
        "not-applied",
        "not-applied",
    )
    if honest_clean == honest_rendered:
        reasons.append("rendered pixels did not diverge from the clean master on this working image")
        return _result("withheld", reasons, [], preserved, questions)
    if selection == SELECTION_PROCESSED:
        reasons.append(
            "processed master is explicitly named; grain, halation, virtual defocus, and its output transform stay off the clean log"
        )
        return _result("processed_master_named", reasons, [], preserved, questions)
    reasons.append("clean master was not display-tone-mapped and was not given the rendered recipe")
    return _result("branches_separated", reasons, [], preserved, questions)
