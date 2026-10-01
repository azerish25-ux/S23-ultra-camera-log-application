import copy
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_raw_development import verify


class RawDevelopmentEvidenceTest(unittest.TestCase):
    def reports(self):
        common = {"appCommit": "fixture-commit", "physicalCameraCertified": False}
        return {"native-ui": {**common, "status": "passed", "sourceCrcChecked": True, "profileImported": True,
                              "activityRecreated": True, "sourceHashUnchanged": True},
                "android-math": {**common, "status": "passed", "distinctMathLevels": 1024,
                                 "referenceGreyMatched": True, "corruptionRejected": True, "sourceRetained": True},
                "p010-codec": {**common, "status": "unavailable", "encodedPixelsTested": False,
                               "reason": "No advertised P010 encoder on this fixture"}}

    def check(self, reports, duplicate=False):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"evidence.tar"
            with tarfile.open(path, "w") as archive:
                for name, report in list(reports.items()) + ([next(iter(reports.items()))] if duplicate else []):
                    data = json.dumps(report).encode()
                    info = tarfile.TarInfo(f"files/exports/raw-development/{name}.json")
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            return verify(path)

    def test_unavailable_is_not_a_codec_pass(self):
        result = self.check(self.reports())
        self.assertEqual(result["codecRoute"], "unavailable")
        self.assertFalse(result["encodedPixelsTested"])

    def test_positive_and_negative_and_full_decode_required(self):
        reports = self.reports()
        reports["p010-codec"].update(status="passed", encodedPixelsTested=True,
            qualification={"positive": {"passed": True}, "eightBitNegative": {"passed": False}},
            verification={"fullDecodeVerified": True, "decodedFrames": 8, "lumaBitDepth": 10, "chromaBitDepth": 10,
                          "colorPrimariesCode": 2, "transferCharacteristicsCode": 2, "matrixCoefficientsCode": 1})
        self.assertEqual(self.check(reports)["codecRoute"], "passed")
        for kind in ("negative", "count", "depth", "transfer"):
            broken = copy.deepcopy(reports)
            c = broken["p010-codec"]
            if kind == "negative": c["qualification"]["eightBitNegative"]["passed"] = True
            if kind == "count": c["verification"]["decodedFrames"] = 7
            if kind == "depth": c["verification"]["lumaBitDepth"] = 8
            if kind == "transfer": c["verification"]["transferCharacteristicsCode"] = 18
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.check(broken)

    def test_ui_math_and_provenance_are_mandatory(self):
        for name, key, value in (("native-ui", "sourceHashUnchanged", False),
                                 ("android-math", "distinctMathLevels", 256),
                                 ("p010-codec", "physicalCameraCertified", True),
                                 ("p010-codec", "encodedPixelsTested", True),
                                 ("p010-codec", "appCommit", "")):
            reports = self.reports(); reports[name][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): self.check(reports)

    def test_missing_and_duplicate_evidence_rejected(self):
        reports = self.reports(); del reports["native-ui"]
        with self.assertRaises(ValueError): self.check(reports)
        with self.assertRaises(ValueError): self.check(self.reports(), duplicate=True)
