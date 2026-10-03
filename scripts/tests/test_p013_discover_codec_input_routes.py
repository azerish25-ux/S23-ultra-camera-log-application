"""Host checks for the P013 codec-route database. Not a physical S23 probe.

TC-P013-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p013_discover_codec_input_routes import (  # noqa: E402
    BASE_REVISION,
    FIXTURE,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    candidate_status,
    inventory,
    oracle_holds,
    validate_database,
)


RESULT_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
FIXTURE_PATH = ROOT / "docs" / "P013_DISCOVER_CODEC_INPUT_ROUTES.json"


def load_db() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _available(preserved: list[str]) -> list[str]:
    return [
        item
        for item in preserved
        if not item.startswith("historical:") and not item.startswith("failure:")
    ]


class P013CodecRouteTests(unittest.TestCase):
    def test_module_encodes_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(
            METHOD,
            "Inventory codec names, profiles, levels, sizes, rates, surface support, "
            "and byte-buffer or Image formats. A P010 developer and an EGL surface "
            "encoder have different prerequisites. Store failures per candidate and "
            "re-query after relevant device software changes.",
        )
        self.assertEqual(
            FIXTURE,
            "A codec advertising Main10 with surface input but no usable P010 Image input.",
        )
        self.assertEqual(
            ORACLE,
            "The surface candidate remains available for testing while the CPU P010 "
            "developer is honestly unavailable.",
        )
        self.assertEqual(
            MUTANT,
            "Use the advertised Main10 profile as the sole P010 acceptance criterion.",
        )

    def test_fixture_validates_oracle_and_keeps_schema(self) -> None:
        raw = load_db()
        self.assertIsNone(validate_database(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P013")
        self.assertEqual(raw["databaseId"], "s23-codec-route-fixture")
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertTrue(oracle_holds(raw))
        rows = inventory(raw)
        self.assertEqual(len(rows), len(raw["candidates"]))
        surface = next(row for row in rows if row["candidateId"] == "hevc-main10-surface")
        p010 = next(row for row in rows if row["candidateId"] == "hevc-main10-p010-image")
        byte_buffer = next(row for row in rows if row["candidateId"] == "hevc-main10-byte-buffer")
        self.assertEqual(surface["status"], "available")
        self.assertEqual(surface["interface"], "surface")
        self.assertEqual(surface["profile"], "Main10")
        self.assertIsNone(surface["failure"])
        self.assertEqual(p010["status"], "unavailable")
        self.assertEqual(p010["inputFormat"], "P010")
        self.assertEqual(p010["failure"], "no usable P010 Image input")
        self.assertEqual(byte_buffer["status"], "unavailable")
        self.assertNotEqual(byte_buffer["failure"], p010["failure"])
        self.assertIn("hevc-main10-surface", [row["candidateId"] for row in rows])
        self.assertEqual(
            [row["candidateId"] for row in rows if row["failure"]],
            ["hevc-main10-p010-image", "hevc-main10-byte-buffer"],
        )

    def test_main10_profile_alone_does_not_accept_p010(self) -> None:
        unavailable = {
            "usable": False,
            "failure": "no usable P010 Image input",
            "profile": "Main10",
        }
        self.assertEqual(candidate_status(unavailable), "unavailable")
        self.assertNotEqual(candidate_status(unavailable), "available")
        surface = {"usable": True, "failure": None, "profile": "Main10"}
        self.assertEqual(candidate_status(surface), "available")
        other_profile = {"usable": True, "failure": None, "profile": "Main"}
        self.assertEqual(candidate_status(other_profile), "available")

    def test_honest_plan_keeps_surface_and_not_p010(self) -> None:
        raw = load_db()
        result = assess(raw)
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P013")
        self.assertEqual(result["decision"], "interface_specific")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("hevc-main10-surface", result["preservedResults"])
        self.assertIn("hevc-main10-surface", _available(result["preservedResults"]))
        self.assertNotIn("hevc-main10-p010-image", _available(result["preservedResults"]))
        self.assertIn("historical:hevc-main10-p010-image", result["preservedResults"])
        self.assertIn("failure:hevc-main10-p010-image", result["preservedResults"])
        self.assertIn("hevc-main10-p010-image", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertTrue(any("surface candidate remains available" in item for item in result["reasons"]))
        self.assertTrue(any("honestly unavailable" in item for item in result["reasons"]))
        self.assertTrue(any("different prerequisites" in item for item in result["reasons"]))
        self.assertTrue(result["reasons"])
        self.assertTrue(result["openQuestions"])
        joined = " ".join(result["reasons"] + result["rejectedClaims"])
        self.assertNotIn("qualified", joined)
        self.assertNotIn("allowed", joined)

    def test_mutant_sole_main10_criterion_is_rejected(self) -> None:
        raw = load_db()
        result = assess(raw, sole_main10_as_p010=True)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "interface_specific"})
        self.assertIn("main10-as-sole-p010-criterion", result["rejectedClaims"])
        self.assertIn("main10-implies-p010-image", result["rejectedClaims"])
        self.assertIn("hevc-main10-surface", _available(result["preservedResults"]))
        self.assertNotIn("hevc-main10-p010-image", _available(result["preservedResults"]))
        self.assertIn("failure:hevc-main10-p010-image", result["preservedResults"])
        self.assertTrue(any("not the sole P010 acceptance criterion" in item for item in result["reasons"]))
        promoted = assess(raw, sole_main10_as_p010=False)
        self.assertNotIn("hevc-main10-p010-image", _available(promoted["preservedResults"]))

    def test_software_change_requires_requery_without_dropping_surface(self) -> None:
        raw = load_db()
        current = {
            "buildFingerprint": raw["buildFingerprint"],
            "codecIdentity": "c2.android.hevc.encoder/changed",
            "probeProtocol": raw["probeProtocol"],
        }
        result = assess(raw, current_environment=current)
        self.assertEqual(result["decision"], "requalify")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("stale-environment", result["rejectedClaims"])
        self.assertIn("codecIdentity", result["rejectedClaims"])
        self.assertIn("hevc-main10-surface", result["preservedResults"])
        self.assertIn("historical:hevc-main10-p010-image", result["preservedResults"])
        self.assertTrue(any("marketing name" in item for item in result["reasons"]))
        same = {
            "buildFingerprint": raw["buildFingerprint"],
            "codecIdentity": raw["codecIdentity"],
            "probeProtocol": raw["probeProtocol"],
        }
        unchanged = assess(raw, current_environment=same)
        self.assertEqual(unchanged["decision"], "interface_specific")

    def test_marking_p010_usable_is_a_different_probe_not_the_oracle(self) -> None:
        raw = load_db()
        mutant_data = copy.deepcopy(raw)
        for candidate in mutant_data["candidates"]:
            if candidate["candidateId"] == "hevc-main10-p010-image":
                candidate["usable"] = True
                candidate["failure"] = None
        self.assertIsNone(validate_database(mutant_data))
        self.assertFalse(oracle_holds(mutant_data))
        rows = inventory(mutant_data)
        p010 = next(row for row in rows if row["candidateId"] == "hevc-main10-p010-image")
        self.assertEqual(p010["status"], "available")
        surface = next(row for row in rows if row["candidateId"] == "hevc-main10-surface")
        self.assertEqual(surface["status"], "available")

    def test_invalid_databases_raise(self) -> None:
        valid = load_db()
        extra = copy.deepcopy(valid)
        extra["note"] = "device probe"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        empty = copy.deepcopy(valid)
        empty["candidates"] = []
        numeric_fps = copy.deepcopy(valid)
        numeric_fps["candidates"][0]["minFps"] = 30
        bad_phase = copy.deepcopy(valid)
        bad_phase["phase"] = "P012"
        bad_revision = copy.deepcopy(valid)
        bad_revision["implementationBaseRevision"] = "abc"
        duplicate = copy.deepcopy(valid)
        duplicate["candidates"].append(copy.deepcopy(duplicate["candidates"][0]))
        usable_failure = copy.deepcopy(valid)
        usable_failure["candidates"][0]["failure"] = "should not be stored"
        missing_failure = copy.deepcopy(valid)
        missing_failure["candidates"][1]["failure"] = None
        bad_role = copy.deepcopy(valid)
        bad_role["candidates"][1]["role"] = "egl_surface_encoder"
        bad_interface = copy.deepcopy(valid)
        bad_interface["candidates"][0]["interface"] = "hdmi"
        schema = copy.deepcopy(valid)
        schema["schemaVersion"] = 2
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            empty,
            numeric_fps,
            bad_phase,
            bad_revision,
            duplicate,
            usable_failure,
            missing_failure,
            bad_role,
            bad_interface,
            schema,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_database(sample)
        with self.assertRaises(ValueError):
            assess(valid, sole_main10_as_p010="true")
        with self.assertRaises(ValueError):
            assess(valid, current_environment={"modelName": "Galaxy S23 Ultra"})


if __name__ == "__main__":
    unittest.main()
