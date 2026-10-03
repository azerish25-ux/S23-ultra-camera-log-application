"""Host checks for the P038 capture-time calibration snapshot. Not a physical S23 probe.

TC-P038-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p038_snapshot_calibration_metadata_at_capture_time import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    COORDINATES,
    FIXTURE,
    MAP_ID,
    MATRICES,
    METHOD,
    MUTANT,
    ORACLE,
    apply_current_as_truth,
    assess,
    matrix_token,
    selected_forward,
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
    return json.loads(
        (ROOT / "docs" / "P038_SNAPSHOT_CALIBRATION_METADATA_AT_CAPTURE_TIME.json").read_text(
            encoding="utf-8"
        )
    )


class P038SnapshotTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P038")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P038")
        self.assertEqual(MAP_ID, "s23-capture-calibration-snapshot-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("explicit missing fields", METHOD)
        self.assertIn("firmware and route", METHOD)
        self.assertIn("coordinate and matrix conventions", METHOD)
        self.assertEqual(
            FIXTURE,
            "Two takes on different firmware versions with different forward matrices "
            "but the same physical handset.",
        )
        self.assertEqual(
            ORACLE,
            "The developer selects the matching snapshot and rejects a profile whose "
            "source identity does not match.",
        )
        self.assertEqual(
            MUTANT,
            "Look up current camera metadata while developing an older source and "
            "treat it as capture-time truth.",
        )
        self.assertIn("top-left", COORDINATES)
        self.assertIn("XYZ D50", MATRICES)
        self.assertIn("not a measured profile", MATRICES)

    def test_fixture_selects_matching_snapshots_and_keeps_missing_fields(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P038")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["sources"][0]["handsetId"], raw["sources"][1]["handsetId"])
        self.assertNotEqual(raw["sources"][0]["firmware"], raw["sources"][1]["firmware"])
        fw1 = raw["snapshots"][0]["forwardMatrix"]
        fw2 = raw["snapshots"][1]["forwardMatrix"]
        self.assertNotEqual(fw1, fw2)
        self.assertEqual(raw["currentMetadata"]["forwardMatrix"], fw2)
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "selected")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("snap-fw1:forward:" + ",".join(fw1), result["preservedResults"])
        self.assertIn("snap-fw2:forward:" + ",".join(fw2), result["preservedResults"])
        self.assertIn("missing:snap-fw1:calibrationMatrix", result["preservedResults"])
        self.assertIn("missing:snap-fw1:lensShading", result["preservedResults"])
        self.assertIn("missing:snap-fw2:lensShading", result["preservedResults"])
        self.assertTrue(any(item.startswith("take-fw1@") for item in result["preservedResults"]))
        self.assertTrue(any("not-capture-truth" in item for item in result["preservedResults"]))
        self.assertIn("snapshot is not a measured colour profile", result["openQuestions"])
        self.assertIn("physical S23 calibration unverified", result["openQuestions"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(
            "current device metadata was not treated as capture-time truth",
            result["reasons"],
        )
        self.assertEqual(selected_forward(raw, "take-fw1"), fw1)
        self.assertEqual(selected_forward(raw, "take-fw2"), fw2)

    def test_mutant_current_metadata_is_rejected_for_the_older_source(self) -> None:
        raw = load_document()
        fw1 = list(raw["snapshots"][0]["forwardMatrix"])
        fw2 = list(raw["snapshots"][1]["forwardMatrix"])
        mutant = apply_current_as_truth(raw, "take-fw1")
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "selected"})
        self.assertIn("current-metadata-as-capture-truth", mutant["rejectedClaims"])
        self.assertIn(MUTANT, mutant["reasons"])
        capture = [item for item in mutant["preservedResults"] if item.startswith("capture:")]
        self.assertEqual(capture, ["capture:" + "snap-fw1:forward:" + ",".join(fw1)])
        self.assertNotIn(",".join(fw2), capture[0])
        self.assertIn("take-fw1@", mutant["preservedResults"][0])

        forged = copy.deepcopy(raw)
        forged["currentMetadata"]["firmware"] = forged["sources"][0]["firmware"]
        forged["currentMetadata"]["forwardMatrix"] = ["9", "9", "9", "9", "9", "9", "9", "9", "9"]
        self.assertEqual(selected_forward(forged, "take-fw1"), fw1)
        forged_result = apply_current_as_truth(forged, "take-fw1")
        self.assertEqual(forged_result["decision"], "rejected")
        capture = [item for item in forged_result["preservedResults"] if item.startswith("capture:")]
        self.assertIn(",".join(fw1), capture[0])
        self.assertNotIn("9,9,9,9,9,9,9,9,9", capture[0])
        self.assertNotEqual(forged_result["decision"], "selected")

    def test_identity_mismatch_rejects_without_wiping_inventory(self) -> None:
        raw = load_document()
        raw["snapshots"][0]["firmware"] = "fw-other"
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("firmware-mismatch:take-fw1", result["rejectedClaims"])
        self.assertTrue(any(item.startswith("take-fw1@") for item in result["preservedResults"]))
        self.assertTrue(any(item.startswith("snap-fw2:forward:") for item in result["preservedResults"]))
        self.assertIn(matrix_token(raw["snapshots"][1]), result["preservedResults"])

    def test_missing_forward_is_not_backfilled(self) -> None:
        raw = load_document()
        raw["snapshots"][0]["forwardMatrix"] = None
        raw["snapshots"][0]["missingFields"] = [
            "forwardMatrix",
            "calibrationMatrix",
            "lensShading",
        ]
        result = assess(raw)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-forward:take-fw1", result["rejectedClaims"])
        self.assertIn("snap-fw1:forward:missing", result["preservedResults"])
        self.assertNotIn(
            "snap-fw1:forward:" + ",".join(raw["currentMetadata"]["forwardMatrix"]),
            result["preservedResults"],
        )
        self.assertTrue(any("not replaced from current metadata" in item for item in result["reasons"]))

    def test_invalid_document_raises(self) -> None:
        raw = load_document()
        cases = []
        broken = copy.deepcopy(raw)
        broken["schemaVersion"] = 2
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["phase"] = "P037"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        del broken["mutant"]
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["extra"] = True
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["snapshots"][0]["cfa"] = "XXXX"
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["snapshots"][1]["forwardMatrix"] = ["1.10"] * 9
        cases.append(broken)
        broken = copy.deepcopy(raw)
        broken["currentMetadata"]["id"] = "snap-fw2"
        cases.append(broken)
        for item in cases:
            with self.subTest(phase=item.get("phase"), keys=sorted(item)):
                with self.assertRaises(ValueError):
                    validate_document(item)


if __name__ == "__main__":
    unittest.main()
