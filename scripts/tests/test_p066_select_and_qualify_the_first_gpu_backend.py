"""Host checks for the P066 GPU backend decision. Not a physical S23 probe.

TC-P066-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p066_select_and_qualify_the_first_gpu_backend import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    MUTANT_PATH,
    ORACLE,
    assess,
    missing_extensions,
    route_unavailable,
    validate_document,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)


def load_document() -> dict:
    path = ROOT / "docs" / "P066_SELECT_AND_QUALIFY_THE_FIRST_GPU_BACKEND.json"
    return json.loads(path.read_text(encoding="utf-8"))


def capable(document: dict) -> dict:
    """A probed route with the high-precision format, one maintained backend."""
    raw = copy.deepcopy(document)
    probe = raw["probe"]
    probe["formatRenderable"] = True
    probe["presentExtensions"] = list(probe["requiredExtensions"])
    probe["surfaceCompatible"] = True
    probe["imageImportAvailable"] = True
    probe["apiVersionSupported"] = True
    probe["cpuReferenceRetained"] = True
    probe["silentPrecisionLowering"] = False
    for kernel in raw["kernels"]:
        kernel["gpuExecuted"] = True
        kernel["matchedReference"] = True
    for life in raw["lifetimes"]:
        life["completionObserved"] = True
        life["recycledAfterCompletion"] = True
    for backend in raw["backends"]:
        if backend["role"] == "candidate":
            backend["maintained"] = True
            backend["selected"] = True
        elif backend["role"] == "reference":
            backend["selected"] = True
        elif backend["role"] == "second":
            backend["selected"] = False
            backend["coverageBenefit"] = False
            backend["performanceBenefit"] = False
    return raw


class P066GpuBackendTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P066")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-gpu-backend-decision-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("EGL/OpenGL ES or Vulkan", METHOD)
        self.assertIn("reference kernels", METHOD)
        self.assertIn("resource-lifetime", METHOD)
        self.assertIn("second requires a demonstrated coverage or performance benefit", METHOD)
        self.assertEqual(
            FIXTURE,
            "A device supporting the API version but lacking a required renderable high-precision format.",
        )
        self.assertEqual(
            ORACLE,
            "The backend reports unavailable for that route and retains the CPU reference "
            "rather than silently lowering precision.",
        )
        self.assertEqual(
            MUTANT,
            "Assume an API version number guarantees every required texture and surface capability.",
        )

    def test_fixture_reports_unavailable_and_keeps_the_cpu_reference(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P066")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertIs(raw["probe"]["apiVersionSupported"], True)
        self.assertIs(raw["probe"]["formatRenderable"], False)
        self.assertEqual(missing_extensions(raw), ["GL_EXT_color_buffer_half_float"])
        self.assertIs(route_unavailable(raw), True)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "backend_selected", "rejected"})
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertNotIn(MUTANT, result["reasons"])
        self.assertIn("API version support was not treated as a capability guarantee", result["reasons"])
        self.assertIn("required format rgba16f is not renderable", result["reasons"])
        self.assertIn("missing extensions: GL_EXT_color_buffer_half_float", result["reasons"])
        self.assertIn("image import is unavailable", result["reasons"])
        self.assertIn("CPU reference retained rather than silently lowering precision", result["reasons"])
        self.assertIn("backend route gles-rgba16f is unavailable", result["reasons"])
        preserved = result["preservedResults"]
        self.assertIn("api-family:opengles", preserved)
        self.assertIn("api-version:3.2", preserved)
        self.assertIn("api-version-supported:true", preserved)
        self.assertIn("route:gles-rgba16f", preserved)
        self.assertIn("format:rgba16f", preserved)
        self.assertIn("format-renderable:false", preserved)
        self.assertIn("extension:GL_EXT_color_buffer_half_float:present=false", preserved)
        self.assertIn("surface-compatible:true", preserved)
        self.assertIn("image-import:false", preserved)
        self.assertIn("silent-precision:false", preserved)
        self.assertIn("cpu-reference:retained", preserved)
        self.assertIn("kernel:box-blur:reference=cpu:gpu-executed=false:matched=false", preserved)
        self.assertIn("kernel:luma-accumulate:reference=cpu:gpu-executed=false:matched=false", preserved)
        self.assertIn("lifetime:color-target:texture:completion=true:recycled-after=true", preserved)
        self.assertIn("lifetime:staging-buffer:buffer:completion=true:recycled-after=true", preserved)
        self.assertIn(
            "backend:gles:family=opengles:role=candidate:maintained=true:selected=false:coverage=false:performance=false",
            preserved,
        )
        self.assertIn(
            "backend:cpu-reference:family=cpu:role=reference:maintained=true:selected=true:coverage=false:performance=false",
            preserved,
        )
        self.assertIn(
            "backend:vulkan:family=vulkan:role=second:maintained=true:selected=false:coverage=false:performance=false",
            preserved,
        )

    def test_mutant_version_does_not_imply_texture_or_surface_capability(self) -> None:
        raw = load_document()
        honest = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(mutant)
        self.assertEqual(honest["decision"], "route_unavailable")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(
            mutant["rejectedClaims"],
            ["gles-rgba16f", "api-version-implies-capability"],
        )
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "backend_selected", "route_unavailable"})
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertIn("an API version number does not guarantee texture or surface capability", mutant["reasons"])
        self.assertIn("mutant API-version assumption was rejected", mutant["openQuestions"])
        self.assertIn("format-renderable:false", mutant["preservedResults"])
        self.assertIn("cpu-reference:retained", mutant["preservedResults"])
        self.assertIn("api-version-supported:true", mutant["preservedResults"])
        self.assertIn("extension:GL_EXT_color_buffer_half_float:present=false", mutant["preservedResults"])
        self.assertEqual(
            [item for item in honest["preservedResults"] if item.startswith("format")],
            [item for item in mutant["preservedResults"] if item.startswith("format")],
        )
        self.assertNotIn("format-renderable:true", mutant["preservedResults"])

    def test_mutant_does_not_select_a_backend_when_only_the_version_is_supported(self) -> None:
        raw = capable(load_document())
        raw["probe"]["formatRenderable"] = False
        for kernel in raw["kernels"]:
            kernel["gpuExecuted"] = False
            kernel["matchedReference"] = False
        for backend in raw["backends"]:
            if backend["role"] == "candidate":
                backend["selected"] = False
        typed = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assertEqual(typed["decision"], "route_unavailable")
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("api-version-implies-capability", mutant["rejectedClaims"])
        self.assertNotIn(mutant["decision"], {"backend_selected", "qualified", "allowed"})
        self.assertIn("format:rgba16f", mutant["preservedResults"])
        self.assertIn("cpu-reference:retained", mutant["preservedResults"])

    def test_capable_probe_selects_one_backend_and_mutant_still_rejects(self) -> None:
        raw = capable(load_document())
        self.assertIs(route_unavailable(raw), False)
        typed = assess(raw)
        mutant = assess(raw, path=MUTANT_PATH)
        self.assert_result(typed)
        self.assertEqual(typed["decision"], "backend_selected")
        self.assertEqual(typed["rejectedClaims"], [])
        self.assertNotIn(typed["decision"], {"qualified", "allowed"})
        self.assertIn("one maintained backend gles was recorded after the capability probe", typed["reasons"])
        self.assertIn("format-renderable:true", typed["preservedResults"])
        self.assertIn("extension:GL_EXT_color_buffer_half_float:present=true", typed["preservedResults"])
        self.assertIn("kernel:box-blur:reference=cpu:gpu-executed=true:matched=true", typed["preservedResults"])
        self.assertIn("cpu-reference:retained", typed["preservedResults"])
        self.assertEqual(mutant["decision"], "rejected")
        self.assertEqual(mutant["rejectedClaims"], ["api-version-implies-capability"])
        self.assertNotIn(mutant["decision"], {"backend_selected", "qualified", "allowed"})
        self.assertIn("format-renderable:true", mutant["preservedResults"])

    def test_silent_precision_drop_is_rejected_and_keeps_the_format(self) -> None:
        raw = load_document()
        raw["probe"]["silentPrecisionLowering"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f", "silent-precision-drop"])
        self.assertIn("silent precision lowering was rejected", result["reasons"])
        self.assertIn("format:rgba16f", result["preservedResults"])
        self.assertIn("format-renderable:false", result["preservedResults"])
        self.assertIn("cpu-reference:retained", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "route_unavailable", "backend_selected"})

    def test_missing_extension_and_incompatible_surface_repeat_the_unavailable_route(self) -> None:
        raw = load_document()
        raw["probe"]["formatRenderable"] = True
        raw["probe"]["imageImportAvailable"] = True
        raw["probe"]["surfaceCompatible"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f"])
        self.assertIn("missing extensions: GL_EXT_color_buffer_half_float", result["reasons"])
        self.assertIn("surface is incompatible", result["reasons"])
        self.assertIn("format-renderable:true", result["preservedResults"])
        self.assertIn("cpu-reference:retained", result["preservedResults"])
        self.assertNotIn("image import is unavailable", result["reasons"])

    def test_dropped_cpu_reference_does_not_erase_the_format(self) -> None:
        raw = load_document()
        raw["probe"]["cpuReferenceRetained"] = False
        for backend in raw["backends"]:
            if backend["role"] == "reference":
                backend["selected"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f", "cpu-reference-dropped"])
        self.assertIn("format:rgba16f", result["preservedResults"])
        self.assertIn("cpu-reference:dropped", result["preservedResults"])
        self.assertIn(
            "backend:cpu-reference:family=cpu:role=reference:maintained=true:selected=false:coverage=false:performance=false",
            result["preservedResults"],
        )

    def test_second_backend_without_benefit_is_rejected(self) -> None:
        raw = capable(load_document())
        for backend in raw["backends"]:
            if backend["role"] == "second":
                backend["selected"] = True
                backend["coverageBenefit"] = False
                backend["performanceBenefit"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unjustified-second-backend"])
        self.assertIn("kernel:box-blur:reference=cpu:gpu-executed=true:matched=true", result["preservedResults"])
        self.assertIn("cpu-reference:retained", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "backend_selected"})

    def test_second_backend_with_coverage_benefit_stays_a_host_record(self) -> None:
        raw = capable(load_document())
        for backend in raw["backends"]:
            if backend["role"] == "second":
                backend["selected"] = True
                backend["coverageBenefit"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "backend_selected")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("second backend vulkan was recorded only with a demonstrated benefit", result["reasons"])
        self.assertIn(
            "backend:vulkan:family=vulkan:role=second:maintained=true:selected=true:coverage=true:performance=false",
            result["preservedResults"],
        )

    def test_selecting_a_gpu_on_an_unavailable_route_keeps_the_inventory(self) -> None:
        raw = load_document()
        for backend in raw["backends"]:
            if backend["role"] == "candidate":
                backend["selected"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f", "selected-unavailable-route"])
        self.assertIn("format-renderable:false", result["preservedResults"])
        self.assertIn("cpu-reference:retained", result["preservedResults"])

    def test_early_recycle_and_unmeasured_kernel_match_are_rejected(self) -> None:
        raw = load_document()
        raw["kernels"][0]["matchedReference"] = True
        raw["lifetimes"][0]["completionObserved"] = False
        raw["lifetimes"][0]["recycledAfterCompletion"] = True
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["gles-rgba16f", "unmeasured-kernel-match:box-blur", "early-recycle:color-target"],
        )
        self.assertIn("kernel:box-blur:reference=cpu:gpu-executed=false:matched=true", result["preservedResults"])
        self.assertIn("lifetime:color-target:texture:completion=false:recycled-after=true", result["preservedResults"])
        self.assertIn("kernel:luma-accumulate:reference=cpu:gpu-executed=false:matched=false", result["preservedResults"])

    def test_kernel_mismatch_on_a_capable_route_is_not_a_selection(self) -> None:
        raw = capable(load_document())
        raw["kernels"][1]["matchedReference"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["kernel-mismatch:luma-accumulate"])
        self.assertIn("cpu-reference:retained", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "backend_selected"})

    def test_unselected_capable_route_is_withheld(self) -> None:
        raw = capable(load_document())
        for backend in raw["backends"]:
            if backend["role"] == "candidate":
                backend["selected"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("no maintained backend was selected on the probed route", result["reasons"])
        self.assertIn(
            "backend:gles:family=opengles:role=candidate:maintained=true:selected=false:coverage=false:performance=false",
            result["preservedResults"],
        )
        self.assertIn("format:rgba16f", result["preservedResults"])

    def test_unsupported_api_version_is_unavailable_even_with_the_format(self) -> None:
        raw = capable(load_document())
        raw["probe"]["apiVersionSupported"] = False
        for kernel in raw["kernels"]:
            kernel["gpuExecuted"] = False
            kernel["matchedReference"] = False
        for backend in raw["backends"]:
            if backend["role"] == "candidate":
                backend["selected"] = False
        result = assess(raw)
        self.assertEqual(result["decision"], "route_unavailable")
        self.assertEqual(result["rejectedClaims"], ["gles-rgba16f"])
        self.assertIn("API version 3.2 is not supported", result["reasons"])
        self.assertIn("format-renderable:true", result["preservedResults"])
        self.assertIn("api-version-supported:false", result["preservedResults"])

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P065"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        bad_version = copy.deepcopy(valid)
        bad_version["probe"]["apiVersion"] = "3.20"
        string_flag = copy.deepcopy(valid)
        string_flag["probe"]["formatRenderable"] = "false"
        extra_ext = copy.deepcopy(valid)
        extra_ext["probe"]["presentExtensions"] = ["GL_KHR_debug"]
        duplicate_ext = copy.deepcopy(valid)
        duplicate_ext["probe"]["requiredExtensions"] = [
            "GL_EXT_color_buffer_half_float",
            "GL_EXT_color_buffer_half_float",
        ]
        rgba8 = copy.deepcopy(valid)
        rgba8["probe"]["requiredFormat"] = "rgba8"
        bad_kernel = copy.deepcopy(valid)
        bad_kernel["kernels"][0]["reference"] = "gpu"
        early_bool = copy.deepcopy(valid)
        early_bool["lifetimes"][0]["completionObserved"] = 1
        drifted = copy.deepcopy(valid)
        drifted["backends"][1]["selected"] = False
        same_family = copy.deepcopy(valid)
        same_family["backends"][2]["family"] = "opengles"
        empty_kernels = copy.deepcopy(valid)
        empty_kernels["kernels"] = []
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            bad_phase,
            bad_revision,
            bad_version,
            string_flag,
            extra_ext,
            duplicate_ext,
            rgba8,
            bad_kernel,
            early_bool,
            drifted,
            same_family,
            empty_kernels,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            assess(valid, path="qualified")
        with self.assertRaises(ValueError):
            assess(valid, path="allowed")
        with self.assertRaises(ValueError):
            assess(valid, path="backend_selected")


if __name__ == "__main__":
    unittest.main()
