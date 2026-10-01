import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_live_log import validate


class LiveEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.gpu = dict(appCommit="abc", status="passed", bayerReductionCases=12, maximumLogRgbError=.0003,
                        maximumP010CodeError=1, sensorPrecisionMeasured=False)
        self.backend = dict(appCommit="abc", status="unavailable", sensorPrecisionMeasured=False, routes=[], selectedCodec=None)
        self.screen = dict(appCommit="abc", status="passed", implicitRecording=False)

    def test_unavailable_does_not_become_pass(self):
        result = validate(self.gpu, self.backend, self.screen)
        self.assertEqual(result["backend"], "unavailable")
        self.assertFalse(result["liveCameraTested"])

    def test_mixed_revision_rejected(self):
        self.screen["appCommit"] = "other"
        with self.assertRaises(ValueError): validate(self.gpu, self.backend, self.screen)

    def test_qualified_without_pixels_rejected(self):
        self.backend["status"] = "qualified"
        with self.assertRaises(ValueError): validate(self.gpu, self.backend, self.screen)

    def test_gpu_error_rejected(self):
        self.gpu["maximumP010CodeError"] = 4
        with self.assertRaises(ValueError): validate(self.gpu, self.backend, self.screen)

    def test_sensor_claim_rejected(self):
        self.gpu["sensorPrecisionMeasured"] = True
        with self.assertRaises(ValueError): validate(self.gpu, self.backend, self.screen)

    def test_available_route_contradiction_rejected(self):
        self.backend["routes"] = [{"status": "qualified"}]
        with self.assertRaises(ValueError): validate(self.gpu, self.backend, self.screen)
