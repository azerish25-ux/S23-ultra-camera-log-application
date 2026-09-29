import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_colour import check_gpu, check_gate, check_timing_manifest, measure_luma, verify_archive


def gpu():
    return {"kind": "colour-gpu", "status": "passed", "physicalCameraCertified": False,
            "cameraYuvImportTested": False, "bt2020PatchMaximumError": .0005, "monitorMaximumError": .0005,
            "probe": {"status": "passed", "monitorIndependent": True, "referenceLogMaximumError": .0005,
                      "fp16ToRgb10": {"passed": True, "maximumError": .0005, "distinctLevels": 1024, "monotonic": True},
                      "negative8Bit": {"passed": False, "maximumError": .01, "distinctLevels": 256, "monotonic": True}}}


class ColourEvidenceChecks(unittest.TestCase):
    def test_pixel_evidence_passes(self):
        self.assertEqual("passed", check_gpu(gpu())["status"])

    def test_negative_control_is_mandatory(self):
        data = gpu(); data["probe"]["negative8Bit"]["passed"] = True
        with self.assertRaises(ValueError): check_gpu(data)

    def test_monitor_independence_cannot_be_omitted(self):
        data = gpu(); del data["probe"]["monitorIndependent"]
        with self.assertRaises(ValueError): check_gpu(data)

    def test_low_precision_is_rejected_despite_pass_flag(self):
        data = gpu(); data["probe"]["fp16ToRgb10"]["distinctLevels"] = 256
        with self.assertRaises(ValueError): check_gpu(data)

    def test_numeric_nan_cannot_pass(self):
        for value in (float("nan"), float("inf"), True, "0"):
            data = gpu(); data["probe"]["referenceLogMaximumError"] = value
            with self.assertRaises(ValueError): check_gpu(data)

    def test_synthetic_camera_certification_is_rejected(self):
        data = gpu(); data["physicalCameraCertified"] = True
        with self.assertRaises(ValueError): check_gpu(data)

    def test_unavailable_requires_reason_and_is_not_pass(self):
        data = {"kind": "colour-encoder", "status": "unavailable", "reason": "No HDR editing codec"}
        self.assertEqual("unavailable", check_gate(data, "colour-encoder", "encoded"))
        del data["reason"]
        with self.assertRaises(ValueError): check_gate(data, "colour-encoder", "encoded")

    def test_failed_hardware_cannot_be_renamed_passed(self):
        with self.assertRaises(ValueError): check_gate({"kind": "colour-encoder", "status": "passed"}, "colour-encoder", "encoded")

    def test_encoded_ramp_contract(self):
        row = [round(64 + 876 * x / 1023) for x in range(1024)]
        self.assertTrue(measure_luma(row * 128, 1024, 128)["passed"])
        for broken in ([0] * (1024 * 128), [512] * (1024 * 128), [round(x * 1023 / 1023) for x in range(1024)] * 128):
            with self.assertRaises(ValueError): measure_luma(broken, 1024, 128)

    def test_invalid_ramp_codes_and_dimensions(self):
        with self.assertRaises(ValueError): measure_luma([0], 1, 1)
        with self.assertRaises(ValueError): measure_luma([1024] * (1024 * 128), 1024, 128)

    def test_timing_fixtures_must_use_processor(self):
        manifest = {"fixtures": [{"fps": rate, "colourProcessor": "production_RGBA16F_HLG_identity", "monitorChangedDuringFixture": True} for rate in (24, 30)]}
        check_timing_manifest(manifest)
        del manifest["fixtures"][0]["colourProcessor"]
        with self.assertRaises(ValueError): check_timing_manifest(manifest)

    def test_archive_gates_are_independent_and_revision_bound(self):
        data = {"files/exports/colour/gpu.json": gpu(),
                "files/exports/colour/encoder.json": {"kind": "colour-encoder", "status": "unavailable", "reason": "No encoder"},
                "files/exports/colour/camera.json": {"kind": "colour-camera", "status": "unavailable", "reason": "No camera"},
                "files/exports/timing-fixtures/manifest.json": {"fixtures": [{"fps": n, "colourProcessor": "production_RGBA16F_HLG_identity", "monitorChangedDuringFixture": True} for n in (24, 30)]}}
        for value in data.values(): value["appCommit"] = "test-revision"
        def archive(path, contents):
            with tarfile.open(path, "w") as tar:
                for name, value in contents.items():
                    raw = json.dumps(value).encode(); entry = tarfile.TarInfo(name); entry.size = len(raw); tar.addfile(entry, io.BytesIO(raw))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "evidence.tar"; archive(path, data)
            result = verify_archive(path)
            self.assertIsNone(result["encodedPixelCheck"])
            self.assertFalse(result["physicalS23UltraCertified"])
            changed = copy.deepcopy(data); changed["files/exports/colour/camera.json"]["appCommit"] = "stale"
            archive(path, changed)
            with self.assertRaises(ValueError): verify_archive(path)
            del data["files/exports/colour/encoder.json"]; archive(path, data)
            with self.assertRaises(ValueError): verify_archive(path)
