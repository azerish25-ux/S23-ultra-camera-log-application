#!/usr/bin/env python3
"""P066 GPU backend decision record and capability probe.

Compare EGL/OpenGL ES or Vulkan paths with the same small reference kernels
and resource-lifetime tests. Record required extensions and formats. One
maintained backend is the start; a second needs a demonstrated coverage or
performance benefit.

The fixture supports an API version and lacks a required renderable
high-precision format. The honest probe reports that route unavailable and
keeps the CPU reference. It does not silently lower precision.

The deliberate mutant — an API version number guarantees every required
texture and surface capability — is rejected. Version support does not fill
in a missing format, extension, surface, or image import. This module does
not probe a device, does not qualify a physical S23, and does not execute
TC-P066-01 through TC-P066-08.
"""

from __future__ import annotations

import re
from typing import Any


PHASE = "P066"
CASE_ID = "P066"
BASE_REVISION = "d4deac8fc82832fd23396a01065c5f0bf9da6670"
MAP_ID = "s23-gpu-backend-decision-fixture"
METHOD = (
    "Compare available EGL/OpenGL ES or Vulkan paths using the same small reference kernels "
    "and resource-lifetime tests. Record required extensions and formats. Start with one "
    "maintained backend; a second requires a demonstrated coverage or performance benefit."
)
FIXTURE = "A device supporting the API version but lacking a required renderable high-precision format."
ORACLE = (
    "The backend reports unavailable for that route and retains the CPU reference "
    "rather than silently lowering precision."
)
MUTANT = "Assume an API version number guarantees every required texture and surface capability."
DECLARED_PATH = "capability-probe"
MUTANT_PATH = "version-implies-capability"
PATHS = (DECLARED_PATH, MUTANT_PATH)
HOST_LIMIT = "host fixture does not qualify a physical S23 or a measured GPU backend"
GPU_FAMILIES = ("opengles", "vulkan")
FAMILIES = ("opengles", "vulkan", "cpu")
FORMATS = ("rgba16f", "rgba32f")
ROLES = ("candidate", "reference", "second")
RESOURCES = ("texture", "buffer")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
TOKEN = re.compile(r"^[a-z0-9-]+$")
VERSION = re.compile(r"^(?:[1-9][0-9]*\.[1-9][0-9]*[1-9]|[1-9][0-9]*\.[1-9]|[1-9][0-9]*\.0)$")
EXTENSION = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
DOCUMENT_KEYS = {
    "schemaVersion",
    "phase",
    "mapId",
    "implementationBaseRevision",
    "method",
    "fixture",
    "oracle",
    "mutant",
    "probe",
    "kernels",
    "lifetimes",
    "backends",
}
PROBE_KEYS = {
    "apiFamily",
    "apiVersion",
    "apiVersionSupported",
    "routeId",
    "requiredFormat",
    "formatRenderable",
    "requiredExtensions",
    "presentExtensions",
    "surfaceCompatible",
    "imageImportAvailable",
    "cpuReferenceRetained",
    "silentPrecisionLowering",
}
KERNEL_KEYS = {"id", "reference", "gpuExecuted", "matchedReference"}
LIFETIME_KEYS = {"id", "resource", "completionObserved", "recycledAfterCompletion"}
BACKEND_KEYS = {
    "id",
    "family",
    "role",
    "maintained",
    "selected",
    "coverageBenefit",
    "performanceBenefit",
}
RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FORBIDDEN = {"qualified", "allowed"}
_DECISIONS = {"rejected", "withheld", "route_unavailable", "backend_selected"}


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
    require(isinstance(value, str) and TOKEN.fullmatch(value) is not None, label + " must be a token")
    return value


def _bool(value: object, label: str) -> bool:
    require(type(value) is bool, label + " must be a bool")
    return value


def _choice(value: object, allowed: tuple[str, ...], label: str) -> str:
    require(isinstance(value, str) and value in allowed, label + " is unsupported")
    return value


def _extensions(value: object, label: str) -> list[str]:
    require(type(value) is list, label + " must be a list")
    seen: set[str] = set()
    items: list[str] = []
    for item in value:
        require(isinstance(item, str) and EXTENSION.fullmatch(item) is not None, label + " has a bad extension")
        require(item not in seen, label + " has a duplicate")
        seen.add(item)
        items.append(item)
    return items


def _backend(nodes: list[dict], role: str) -> dict:
    matches = [item for item in nodes if item["role"] == role]
    require(len(matches) == 1, "backend role " + role + " must appear once")
    return matches[0]


def validate_document(document: dict) -> None:
    """Raise ValueError unless document is the P066 backend decision fixture."""
    exact_keys(document, DOCUMENT_KEYS, "backend decision")
    require(type(document["schemaVersion"]) is int and document["schemaVersion"] == 1, "schemaVersion must be 1")
    require(document["phase"] == PHASE, "phase must be P066")
    require(document["mapId"] == MAP_ID, "mapId must be s23-gpu-backend-decision-fixture")
    revision = document["implementationBaseRevision"]
    require(
        revision == BASE_REVISION and HEX40.fullmatch(revision or "") is not None,
        "backend decision needs the P066 implementation base revision",
    )
    require(document["method"] == METHOD, "method text drifted")
    require(document["fixture"] == FIXTURE, "fixture text drifted")
    require(document["oracle"] == ORACLE, "oracle text drifted")
    require(document["mutant"] == MUTANT, "mutant text drifted")
    probe = exact_keys(document["probe"], PROBE_KEYS, "probe")
    family = _choice(probe["apiFamily"], GPU_FAMILIES, "probe apiFamily")
    require(isinstance(probe["apiVersion"], str) and VERSION.fullmatch(probe["apiVersion"]) is not None,
            "apiVersion must be a canonical version")
    _bool(probe["apiVersionSupported"], "apiVersionSupported")
    _token(probe["routeId"], "routeId")
    _choice(probe["requiredFormat"], FORMATS, "requiredFormat")
    for name in (
        "formatRenderable",
        "surfaceCompatible",
        "imageImportAvailable",
        "cpuReferenceRetained",
        "silentPrecisionLowering",
    ):
        _bool(probe[name], name)
    required = _extensions(probe["requiredExtensions"], "requiredExtensions")
    require(required, "requiredExtensions must be non-empty")
    present = _extensions(probe["presentExtensions"], "presentExtensions")
    require(set(present) <= set(required), "presentExtensions must be a subset of requiredExtensions")
    kernels = document["kernels"]
    require(type(kernels) is list and kernels, "kernels must be a non-empty list")
    seen: set[str] = set()
    for index, raw in enumerate(kernels):
        kernel = exact_keys(raw, KERNEL_KEYS, f"kernel {index}")
        kernel_id = _token(kernel["id"], f"kernel {index} id")
        require(kernel_id not in seen, "duplicate kernel id: " + kernel_id)
        seen.add(kernel_id)
        require(kernel["reference"] == "cpu", f"kernel {kernel_id} reference must be cpu")
        _bool(kernel["gpuExecuted"], f"kernel {kernel_id} gpuExecuted")
        _bool(kernel["matchedReference"], f"kernel {kernel_id} matchedReference")
    lifetimes = document["lifetimes"]
    require(type(lifetimes) is list and lifetimes, "lifetimes must be a non-empty list")
    seen_life: set[str] = set()
    for index, raw in enumerate(lifetimes):
        life = exact_keys(raw, LIFETIME_KEYS, f"lifetime {index}")
        life_id = _token(life["id"], f"lifetime {index} id")
        require(life_id not in seen_life, "duplicate lifetime id: " + life_id)
        seen_life.add(life_id)
        _choice(life["resource"], RESOURCES, f"lifetime {life_id} resource")
        _bool(life["completionObserved"], f"lifetime {life_id} completionObserved")
        _bool(life["recycledAfterCompletion"], f"lifetime {life_id} recycledAfterCompletion")
    backends = document["backends"]
    require(type(backends) is list and len(backends) == 3, "backends must list candidate, reference, and second")
    seen_ids: set[str] = set()
    for index, raw in enumerate(backends):
        backend = exact_keys(raw, BACKEND_KEYS, f"backend {index}")
        backend_id = _token(backend["id"], f"backend {index} id")
        require(backend_id not in seen_ids, "duplicate backend id: " + backend_id)
        seen_ids.add(backend_id)
        _choice(backend["family"], FAMILIES, f"backend {backend_id} family")
        _choice(backend["role"], ROLES, f"backend {backend_id} role")
        for name in ("maintained", "selected", "coverageBenefit", "performanceBenefit"):
            _bool(backend[name], f"backend {backend_id} {name}")
    candidate = _backend(backends, "candidate")
    reference = _backend(backends, "reference")
    second = _backend(backends, "second")
    require(candidate["family"] == family, "candidate family must match the probed API family")
    require(candidate["family"] in GPU_FAMILIES, "candidate must be a GPU family")
    require(reference["family"] == "cpu", "reference family must be cpu")
    require(reference["maintained"] is True, "CPU reference must stay maintained")
    require(reference["selected"] is probe["cpuReferenceRetained"], "CPU reference selection drifted from the probe")
    require(reference["coverageBenefit"] is False and reference["performanceBenefit"] is False,
            "CPU reference is not a second GPU backend benefit")
    require(second["family"] in GPU_FAMILIES and second["family"] != candidate["family"],
            "second backend must be the other GPU family")


def missing_extensions(document: dict) -> list[str]:
    """Required extensions that the probe did not record as present."""
    probe = document["probe"]
    present = set(probe["presentExtensions"])
    return [item for item in probe["requiredExtensions"] if item not in present]


def route_unavailable(document: dict) -> bool:
    """True when version support still leaves a required capability missing.

    API version support is not consulted as a substitute for the format,
    extensions, surface, or image import. A supported version with a missing
    high-precision format stays unavailable.
    """
    probe = document["probe"]
    if not probe["apiVersionSupported"]:
        return True
    if not probe["formatRenderable"]:
        return True
    if missing_extensions(document):
        return True
    if not probe["surfaceCompatible"]:
        return True
    if not probe["imageImportAvailable"]:
        return True
    return False


def _gap_reasons(document: dict) -> list[str]:
    probe = document["probe"]
    reasons: list[str] = []
    if not probe["apiVersionSupported"]:
        reasons.append(f"API version {probe['apiVersion']} is not supported")
    if not probe["formatRenderable"]:
        reasons.append(f"required format {probe['requiredFormat']} is not renderable")
    missing = missing_extensions(document)
    if missing:
        reasons.append("missing extensions: " + ", ".join(missing))
    if not probe["surfaceCompatible"]:
        reasons.append("surface is incompatible")
    if not probe["imageImportAvailable"]:
        reasons.append("image import is unavailable")
    return reasons


def _inventory(document: dict) -> list[str]:
    probe = document["probe"]
    present = set(probe["presentExtensions"])
    preserved = [
        f"api-family:{probe['apiFamily']}",
        f"api-version:{probe['apiVersion']}",
        f"api-version-supported:{str(probe['apiVersionSupported']).lower()}",
        f"route:{probe['routeId']}",
        f"format:{probe['requiredFormat']}",
        f"format-renderable:{str(probe['formatRenderable']).lower()}",
        f"surface-compatible:{str(probe['surfaceCompatible']).lower()}",
        f"image-import:{str(probe['imageImportAvailable']).lower()}",
        f"silent-precision:{str(probe['silentPrecisionLowering']).lower()}",
        "cpu-reference:" + ("retained" if probe["cpuReferenceRetained"] else "dropped"),
    ]
    for name in probe["requiredExtensions"]:
        preserved.append(f"extension:{name}:present={str(name in present).lower()}")
    for kernel in document["kernels"]:
        preserved.append(
            f"kernel:{kernel['id']}:reference={kernel['reference']}:"
            f"gpu-executed={str(kernel['gpuExecuted']).lower()}:"
            f"matched={str(kernel['matchedReference']).lower()}"
        )
    for life in document["lifetimes"]:
        preserved.append(
            f"lifetime:{life['id']}:{life['resource']}:"
            f"completion={str(life['completionObserved']).lower()}:"
            f"recycled-after={str(life['recycledAfterCompletion']).lower()}"
        )
    for backend in document["backends"]:
        preserved.append(
            f"backend:{backend['id']}:family={backend['family']}:role={backend['role']}:"
            f"maintained={str(backend['maintained']).lower()}:selected={str(backend['selected']).lower()}:"
            f"coverage={str(backend['coverageBenefit']).lower()}:"
            f"performance={str(backend['performanceBenefit']).lower()}"
        )
    return preserved


def _result(
    decision: str,
    reasons: list[str],
    rejected: list[str],
    preserved: list[str],
    questions: list[str],
) -> dict[str, Any]:
    require(decision in _DECISIONS, "unexpected decision")
    require(decision not in _FORBIDDEN, "P066 must not decide qualified or allowed")
    require(
        bool(reasons) and all(isinstance(item, str) and item for item in reasons),
        "reasons must be a non-empty list of strings",
    )
    for items in (rejected, preserved, questions):
        require(all(isinstance(item, str) and item for item in items), "result lists must be non-empty strings")
    result = {
        "caseId": CASE_ID,
        "decision": decision,
        "reasons": reasons,
        "rejectedClaims": list(rejected),
        "preservedResults": list(preserved),
        "openQuestions": list(questions),
    }
    require(tuple(result) == RESULT_KEYS, "assessment keys drifted")
    return result


def assess(document: dict, path: str = DECLARED_PATH) -> dict:
    """Report an unavailable high-precision route and reject the version mutant.

    ``path`` ``version-implies-capability`` is the deliberate mutant. It does
    not treat ``apiVersionSupported`` as proof of texture or surface
    capability, and it does not erase the CPU reference. The decision is never
    ``qualified`` or ``allowed``.
    """
    validate_document(document)
    require(path in PATHS, "path must be capability-probe or version-implies-capability")
    probe = document["probe"]
    candidate = _backend(document["backends"], "candidate")
    second = _backend(document["backends"], "second")
    unavailable = route_unavailable(document)
    rejected: list[str] = []
    if unavailable:
        rejected.append(probe["routeId"])
    if probe["silentPrecisionLowering"]:
        rejected.append("silent-precision-drop")
    if unavailable and not probe["cpuReferenceRetained"]:
        rejected.append("cpu-reference-dropped")
    for kernel in document["kernels"]:
        if unavailable:
            if kernel["gpuExecuted"]:
                rejected.append("kernel-ran-without-route:" + kernel["id"])
            if kernel["matchedReference"]:
                rejected.append("unmeasured-kernel-match:" + kernel["id"])
        elif not kernel["gpuExecuted"]:
            rejected.append("kernel-not-run:" + kernel["id"])
        elif not kernel["matchedReference"]:
            rejected.append("kernel-mismatch:" + kernel["id"])
    for life in document["lifetimes"]:
        if life["recycledAfterCompletion"] and not life["completionObserved"]:
            rejected.append("early-recycle:" + life["id"])
        elif not unavailable and not life["completionObserved"]:
            rejected.append("lifetime-unobserved:" + life["id"])
    if unavailable and candidate["selected"]:
        rejected.append("selected-unavailable-route")
    if candidate["selected"] and not candidate["maintained"]:
        rejected.append("unmaintained-backend")
    if unavailable and second["selected"]:
        rejected.append("second-selected-on-unavailable-route")
    if second["selected"] and not (second["coverageBenefit"] or second["performanceBenefit"]):
        rejected.append("unjustified-second-backend")
    if not unavailable and second["selected"] and not candidate["selected"]:
        rejected.append("primary-not-selected")
    mutant = path == MUTANT_PATH
    if mutant:
        rejected.append("api-version-implies-capability")
    only_route = rejected == [probe["routeId"]]
    if not rejected:
        if candidate["selected"] and candidate["maintained"]:
            decision = "backend_selected"
        else:
            decision = "withheld"
    elif only_route and probe["cpuReferenceRetained"] and not probe["silentPrecisionLowering"]:
        decision = "route_unavailable"
    else:
        decision = "rejected"
    reasons = [ORACLE, "required extensions and formats are recorded before a backend is kept"]
    reasons.extend(_gap_reasons(document))
    if probe["cpuReferenceRetained"]:
        reasons.append("CPU reference retained rather than silently lowering precision")
    if probe["silentPrecisionLowering"]:
        reasons.append("silent precision lowering was rejected")
    if mutant:
        reasons.append(MUTANT)
        reasons.append("an API version number does not guarantee texture or surface capability")
    else:
        reasons.append("API version support was not treated as a capability guarantee")
    if decision == "route_unavailable":
        reasons.append(f"backend route {probe['routeId']} is unavailable")
    elif decision == "backend_selected":
        reasons.append(f"one maintained backend {candidate['id']} was recorded after the capability probe")
        if second["selected"]:
            reasons.append(f"second backend {second['id']} was recorded only with a demonstrated benefit")
    elif decision == "withheld":
        reasons.append("no maintained backend was selected on the probed route")
    reasons.append(HOST_LIMIT)
    questions = [
        "host fixture is not a physical S23 measurement",
        HOST_LIMIT,
        "an API version does not imply every texture or surface capability",
        "a second backend requires a demonstrated coverage or performance benefit",
    ]
    if mutant:
        questions.append("mutant API-version assumption was rejected")
    return _result(decision, reasons, rejected, _inventory(document), questions)
