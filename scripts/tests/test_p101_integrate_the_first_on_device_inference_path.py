"""Host checks for P101. Not a physical S23 probe."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_integrate_the_first_on_device_inference_path",
    Path(__file__).resolve().parents[1] / "gates" / "p101_integrate_the_first_on_device_inference_path.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
assess = _MODULE.assess
MUTANT = _MODULE.MUTANT
ORACLE = _MODULE.ORACLE

_DOC = Path(__file__).resolve().parents[2] / "docs" / "P101_INTEGRATE_THE_FIRST_ON_DEVICE_INFERENCE_PATH.json"
KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def document(**overrides):
    value = {
        "schemaVersion": 1,
        "phase": "P101",
        "implementationBaseRevision": "3fbad4bc0e0336e273d2723ec873f001e8865323",
        "evidenceId": "p101-offline-inference",
        "claim": "host-offline-inference-reference",
        "networkingEnabled": False,
        "blockCameraUntilCloud": False,
        "virtualBlurApplied": False,
        "model": {
            "filename": "depth-small.tflite",
            "content": "p101-approved-weights-v1",
            "precision": "fp16",
            "runtimeVersion": "tflite-2.16.1",
            "cachedFilename": "depth-small.tflite",
            "cachedContent": "p101-approved-weights-v1",
            "cachedPrecision": "fp16",
            "cachedRuntimeVersion": "tflite-2.16.1",
            "keepCachedDepth": True,
        },
        "geometry": {
            "sourceWidth": 4,
            "sourceHeight": 2,
            "tensorSize": 4,
            "channelOrder": "rgb",
            "recordedChannelOrder": "rgb",
            "preparation": "letterbox",
            "stretchRecorded": False,
        },
        "conversion": {
            "baseline": [0.10, 0.40, 0.70],
            "exported": [0.11, 0.39, 0.72],
            "tolerance": 0.05,
            "boundaryBaseline": [0.0, 1.0],
            "boundaryExported": [0.01, 0.99],
            "boundaryTolerance": 0.02,
            "loads": True,
            "experimental": False,
        },
        "offlineFailure": {
            "networkingEnabled": False,
            "assetPresent": False,
            "assetCorrupt": False,
            "missingCapability": "on-device-depth",
            "captureUsable": True,
            "blockCaptureUntilCloud": False,
            "sourceRetained": True,
        },
        "delegate": {
            "initFailed": True,
            "fallbackName": "",
            "fallbackQualified": False,
            "depthDisabled": True,
            "disableReason": "gpu-delegate-unavailable",
            "silentBackendChange": False,
            "uploadsFrames": False,
        },
        "depth": {
            "sourceTimestampNs": 1000000,
            "sourceCrop": [0, 0, 4, 2],
            "values": [0.25, 0.5, 0.75],
            "identity": {"timestampNs": 1000000, "crop": [0, 0, 4, 2]},
            "reprojected": False,
        },
        "confidence": {
            "scores": [0.33, 0.71],
            "label": "uncalibrated",
            "presentedAs": "uncalibrated-score",
            "renderingReliance": "reduced",
        },
        "load": {
            "modelLatencyMs": 12.5,
            "captureMs": 16.0,
            "renderMs": 4.0,
            "encodeMs": 6.0,
            "frameBudgetMs": 33.333,
            "operation": "deferred",
            "reportedAsFrameRateGuarantee": False,
            "workloadMeasured": True,
        },
    }
    value.update(overrides)
    return value


def _bound_identity(content: str, precision: str, runtime: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(content.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(precision.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(runtime.encode("utf-8"))
    return hasher.hexdigest()


class P101Tests(unittest.TestCase):
    def test_reference_is_recorded_not_qualified(self):
        result = assess(document())
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("p101-offline-inference", result["preservedResults"])
        self.assertIn(ORACLE, " ".join(result["reasons"]))
        text = " ".join(result["reasons"])
        identity = _bound_identity("p101-approved-weights-v1", "fp16", "tflite-2.16.1")
        self.assertIn(identity, text)
        self.assertIn("scale=1.000000 padX=0.000000 padY=1.000000 channelOrder=rgb", text)
        self.assertIn(
            "restoredCorners=(0.000000,0.000000);(3.000000,0.000000);(0.000000,1.000000);(3.000000,1.000000)",
            text,
        )
        self.assertIn("capture_usable=True", text)
        self.assertIn("missingCapability=on-device-depth", text)
        self.assertIn("is not a frame-rate guarantee", text)
        self.assertIn("chosenOperation=deferred", text)
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_checked_in_document_is_recorded(self):
        payload = json.loads(_DOC.read_text(encoding="utf-8"))
        result = assess(payload)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("p101-offline-inference", result["preservedResults"])

    def test_cloud_startup_block_is_rejected_and_evidence_remains(self):
        result = assess(document(blockCameraUntilCloud=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(MUTANT, result["rejectedClaims"])
        self.assertIn("p101-offline-inference", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p101-offline-inference-repeat"
        result = assess(document(evidenceId=evidence))
        self.assertEqual(result["decision"], "recorded")
        self.assertIn(evidence, result["preservedResults"])

    def test_filename_match_with_different_weights_rejects_cached_depth(self):
        payload = document()
        payload["model"] = dict(payload["model"])
        payload["model"]["content"] = "p101-other-weights"
        payload["model"]["keepCachedDepth"] = True
        result = assess(payload)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])
        self.assertIn("p101-offline-inference", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            assess({})
        with self.assertRaises(ValueError):
            assess(document(schemaVersion=2))

    def test_model_identity_binds_content_precision_and_runtime(self):
        base = _MODULE.model_identity(b"abc", "fp16", "rt-1")
        self.assertEqual(base, _bound_identity("abc", "fp16", "rt-1"))
        self.assertNotEqual(base, _MODULE.model_identity(b"abd", "fp16", "rt-1"))
        self.assertNotEqual(base, _MODULE.model_identity(b"abc", "fp32", "rt-1"))
        self.assertNotEqual(base, _MODULE.model_identity(b"abc", "fp16", "rt-2"))
        self.assertEqual(len(base), 64)

    def test_letterbox_restores_non_square_corners(self):
        geometry = _MODULE.letterbox_geometry(6, 2, 4)
        self.assertAlmostEqual(geometry["scale"], 4 / 6)
        self.assertAlmostEqual(geometry["padX"], 0.0)
        self.assertAlmostEqual(geometry["padY"], (4 - 2 * (4 / 6)) / 2)
        restored = _MODULE.restore_source_corners(6, 2, 4)
        expected = _MODULE.source_corners(6, 2)
        for (x_coord, y_coord), (restored_x, restored_y) in zip(expected, restored):
            self.assertAlmostEqual(x_coord, restored_x)
            self.assertAlmostEqual(y_coord, restored_y)
        self.assertEqual(_MODULE.choose_operation(38.5, 33.333), "deferred")
        self.assertEqual(_MODULE.choose_operation(10.0, 33.333), "live")
        self.assertAlmostEqual(_MODULE.max_abs_error([0.1, 0.4], [0.11, 0.39]), 0.01)

    def test_document_copy_does_not_alias_nested_mutation_check(self):
        payload = document()
        cloned = copy.deepcopy(payload)
        cloned["depth"] = dict(cloned["depth"])
        cloned["depth"]["identity"] = None
        result = assess(cloned)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])
