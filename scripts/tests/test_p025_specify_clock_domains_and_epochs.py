"""Host checks for the P025 clock-domain fixture. Not a physical S23 probe.

TC-P025-01..08 are specified in separate modules and are not executed here.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p025_specify_clock_domains_and_epochs import (  # noqa: E402
    BASE_REVISION,
    CASE_ID,
    FIXTURE,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    assess,
    present,
    subtract,
    token,
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
PRESERVED = [
    "video-0@video:sensor:ns:1000000000:sensor-boot",
    "audio-0@audio:audio_hardware:ns:1000000000:audio-boot",
    "mono-0@video:monotonic_system:ns:1000000000:boottime",
    "pres-0@video:encoded_presentation:ns:1000000000:container-zero",
    "codec-0@video:codec:ns:0:codec-start",
]
PATHS = [
    "sensor->audio_hardware unverified",
    "sensor->monotonic_system unverified",
    "sensor->codec unverified",
    "sensor->encoded_presentation unverified",
    "monotonic_system->audio_hardware unverified",
    "audio_hardware->codec unverified",
    "codec->encoded_presentation unverified",
    "monotonic_system->encoded_presentation unverified",
]


def load_document() -> dict:
    return json.loads(
        (ROOT / "docs" / "P025_SPECIFY_CLOCK_DOMAINS_AND_EPOCHS.json").read_text(encoding="utf-8")
    )


def clock(**overrides) -> dict:
    value = {
        "id": "sensor-a",
        "streamId": "video",
        "domain": "sensor",
        "units": "ns",
        "value": "5000",
        "origin": "sensor-boot",
    }
    value.update(overrides)
    return value


def link(**overrides) -> dict:
    value = {
        "id": "map-1",
        "fromDomain": "sensor",
        "toDomain": "audio_hardware",
        "method": "measured_offset",
        "units": "ns",
        "retainedSampleIds": ["sensor-a", "audio-a"],
        "offset": "250",
    }
    value.update(overrides)
    return value


class P025ClockDomainTests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P025")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(CASE_ID, "P025")
        self.assertEqual(MAP_ID, "s23-clock-domain-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("domain and units", METHOD)
        self.assertIn("retained samples", METHOD)
        self.assertIn("original sensor times", METHOD)
        self.assertEqual(
            FIXTURE,
            "Audio and video streams whose timestamps look similar numerically but originate "
            "from different clock domains.",
        )
        self.assertEqual(
            ORACLE,
            "The synchronizer refuses to assume equivalence without a measured or documented mapping.",
        )
        self.assertEqual(
            MUTANT,
            "Subtract timestamps from unrelated domains because both are expressed in nanoseconds.",
        )

    def test_fixture_rejects_numeric_lookalikes_and_keeps_sensor_time(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P025")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["mappings"], [])
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["numeric-unit-equivalence"])
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertIn("1000000000", result["preservedResults"][0])
        self.assertIn("sensor", result["preservedResults"][0])
        self.assertEqual(
            result["openQuestions"],
            PATHS + ["timing unverified", "shared take epoch not applied"],
        )
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn("original sensor times are preserved", result["reasons"])
        self.assertIn("subtracting unrelated nanosecond timestamps is rejected", result["reasons"])
        self.assertNotIn("0", result["preservedResults"])

    def test_mutant_nanosecond_subtraction_is_rejected(self) -> None:
        left = clock()
        right = clock(
            id="audio-a",
            streamId="audio",
            domain="audio_hardware",
            value="3000",
            origin="audio-boot",
        )
        bare = subtract(left, right, None)
        self.assert_result(bare)
        self.assertEqual(bare["decision"], "rejected")
        self.assertNotIn(bare["decision"], {"qualified", "allowed", "mapped", "same_domain"})
        self.assertIn("numeric-unit-equivalence", bare["rejectedClaims"])
        self.assertIn("subtract-unrelated-nanoseconds", bare["rejectedClaims"])
        self.assertEqual(bare["preservedResults"], [token(left), token(right)])
        self.assertNotIn("2000", bare["preservedResults"])
        self.assertFalse(any("delta" in item for item in bare["preservedResults"]))
        self.assertIn("matching nanosecond units are not a shared epoch", bare["reasons"])

        mutant = subtract(
            left,
            right,
            link(method="subtract_unrelated_nanoseconds", offset="0"),
        )
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertIn("subtract-unrelated-nanoseconds", mutant["rejectedClaims"])
        self.assertEqual(mutant["preservedResults"], [token(left), token(right)])
        self.assertNotIn("2000", "".join(mutant["preservedResults"]))
        self.assertNotIn("5000", "".join(mutant["rejectedClaims"]))

    def test_mutant_mapping_on_the_fixture_does_not_erase_timestamps(self) -> None:
        raw = load_document()
        raw["mappings"] = [
            {
                "id": "mutant",
                "fromDomain": "sensor",
                "toDomain": "audio_hardware",
                "method": "subtract_unrelated_nanoseconds",
                "units": "ns",
                "retainedSampleIds": ["video-0", "audio-0"],
                "offset": "0",
            }
        ]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["subtract-unrelated-nanoseconds", "numeric-unit-equivalence"],
        )
        self.assertEqual(result["preservedResults"], PRESERVED)
        self.assertNotIn("0", result["preservedResults"])
        self.assertIn(MUTANT, result["reasons"])

    def test_identified_mapping_preserves_sensor_time_without_qualifying(self) -> None:
        raw = load_document()
        raw["timestamps"] = raw["timestamps"][:2]
        raw["unsupportedPaths"] = []
        raw["mappings"] = [
            {
                "id": "map-sensor-audio",
                "fromDomain": "sensor",
                "toDomain": "audio_hardware",
                "method": "measured_offset",
                "units": "ns",
                "retainedSampleIds": ["video-0", "audio-0"],
                "offset": "250",
            }
        ]
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "mapped")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"], PRESERVED[:2])
        self.assertIn("1000000000", result["preservedResults"][0])
        self.assertNotIn("250", "".join(result["preservedResults"]))
        self.assertEqual(result["openQuestions"], ["physical synchronization unverified"])
        self.assertTrue(any("not physical synchronization" in item for item in result["reasons"]))

        left = clock(id="video-0", value="5000")
        right = clock(
            id="audio-0",
            streamId="audio",
            domain="audio_hardware",
            value="3000",
            origin="audio-boot",
        )
        paired = subtract(
            left,
            right,
            link(
                fromDomain="sensor",
                toDomain="audio_hardware",
                retainedSampleIds=["video-0", "audio-0"],
                offset="250",
            ),
        )
        self.assertEqual(paired["decision"], "mapped")
        self.assertEqual(paired["preservedResults"], [token(left), token(right)])
        self.assertNotIn("2000", paired["preservedResults"])
        self.assertNotIn(paired["decision"], {"qualified", "allowed"})

    def test_presentation_keeps_the_sensor_token(self) -> None:
        stamp = clock(id="video-0", value="5000")
        epoch = {
            "id": "take-1",
            "domain": "monotonic_system",
            "units": "ns",
            "origin": "take-start",
        }
        missing = present(stamp, epoch, None)
        self.assertEqual(missing["decision"], "withheld")
        self.assertEqual(missing["preservedResults"], [token(stamp)])
        self.assertIn("missing-mapping", missing["rejectedClaims"])
        self.assertFalse(any(item.startswith("presentation:") for item in missing["preservedResults"]))

        shown = present(
            stamp,
            epoch,
            link(
                fromDomain="sensor",
                toDomain="monotonic_system",
                method="documented_epoch",
                retainedSampleIds=["video-0", "mono-0"],
                offset="250",
            ),
        )
        self.assertEqual(shown["decision"], "presented")
        self.assertEqual(shown["preservedResults"][0], token(stamp))
        self.assertIn("5000", shown["preservedResults"][0])
        self.assertEqual(shown["preservedResults"][1], "presentation:take-1:250ns")
        self.assertNotIn(shown["decision"], {"qualified", "allowed"})

        blocked = present(
            stamp,
            epoch,
            link(
                fromDomain="sensor",
                toDomain="monotonic_system",
                method="subtract_unrelated_nanoseconds",
                retainedSampleIds=["video-0", "mono-0"],
                offset="0",
            ),
        )
        self.assertEqual(blocked["decision"], "rejected")
        self.assertEqual(blocked["preservedResults"], [token(stamp)])
        self.assertIn("subtract-unrelated-nanoseconds", blocked["rejectedClaims"])

    def test_same_domain_difference_is_not_cross_domain_equivalence(self) -> None:
        left = clock(value="5000", origin="boottime", domain="monotonic_system", id="mono-a")
        right = clock(value="3000", origin="boottime", domain="monotonic_system", id="mono-b")
        result = subtract(left, right, None)
        self.assertEqual(result["decision"], "same_domain")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["preservedResults"], [token(left), token(right)])
        self.assertTrue(any("same-domain difference 2000ns" in item for item in result["reasons"]))

        shifted = subtract(left, clock(**{**right, "origin": "other-boot"}), None)
        self.assertEqual(shifted["decision"], "withheld")
        self.assertIn("origin-changed", shifted["rejectedClaims"])
        self.assertNotIn("2000", "".join(shifted["preservedResults"]))

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mappings"]
        wrong_phase = copy.deepcopy(valid)
        wrong_phase["phase"] = "P024"
        wrong_revision = copy.deepcopy(valid)
        wrong_revision["implementationBaseRevision"] = "abc"
        numeric = copy.deepcopy(valid)
        numeric["timestamps"][0]["value"] = 1000000000
        equivalent = copy.deepcopy(valid)
        equivalent["unsupportedPaths"][0]["status"] = "equivalent"
        empty = copy.deepcopy(valid)
        empty["timestamps"] = []
        duplicate = copy.deepcopy(valid)
        duplicate["timestamps"].append(copy.deepcopy(duplicate["timestamps"][0]))
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            wrong_phase,
            wrong_revision,
            numeric,
            equivalent,
            empty,
            duplicate,
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)


if __name__ == "__main__":
    unittest.main()
