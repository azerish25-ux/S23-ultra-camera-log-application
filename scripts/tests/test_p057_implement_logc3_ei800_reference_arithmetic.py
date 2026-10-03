"""Host checks for the P057 LogC3 EI800 reference. Not a physical S23 probe.

TC-P057-01..08 are specified elsewhere and are not executed by this module.
"""

from __future__ import annotations

import copy
import json
import sys
import unittest
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "gates"))

from p057_implement_logc3_ei800_reference_arithmetic import (  # noqa: E402
    BASE_REVISION,
    EI200_EXPOSURE_BLACK,
    EXPOSURE_COEFFICIENTS,
    FIXTURE,
    HOST_LIMIT,
    MAP_ID,
    METHOD,
    MUTANT,
    ORACLE,
    SENSOR_COEFFICIENTS,
    SOURCE,
    TOLERANCE,
    apply_sensor_signal_coefficients,
    assess,
    branch_discontinuity,
    decode,
    encode,
    encode_with,
    exposure_oracle_failures,
    independent_encode,
    select_by_phone_iso,
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
FIXTURE_PATH = ROOT / "docs" / "P057_IMPLEMENT_LOGC3_EI800_REFERENCE_ARITHMETIC.json"


def load_document() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def published_exposure_encode(exposure: str) -> str:
    """Independent EI800 exposure formula. It does not call the gate."""
    coeff = {key: Decimal(value) for key, value in EXPOSURE_COEFFICIENTS.items()}
    number = Decimal(exposure)
    if number > coeff["cut"]:
        argument = coeff["a"] * number + coeff["b"]
        with localcontext() as ctx:
            ctx.prec = 50
            encoded = coeff["c"] * argument.ln() / Decimal(10).ln() + coeff["d"]
    else:
        encoded = coeff["e"] * number + coeff["f"]
    quantized = encoded.quantize(Decimal("1e-15"), rounding=ROUND_HALF_EVEN)
    text = format(quantized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


class P057LogC3Tests(unittest.TestCase):
    def assert_result(self, result) -> None:
        self.assertEqual(tuple(result), RESULT_KEYS)
        self.assertEqual(result["caseId"], "P057")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) and item for item in result[key]))

    def test_constants_encode_method_fixture_oracle_and_mutant(self) -> None:
        self.assertEqual(MAP_ID, "s23-logc3-ei800-reference-fixture")
        self.assertEqual(BASE_REVISION, "d4deac8fc82832fd23396a01065c5f0bf9da6670")
        self.assertIn("published EI800 exposure-domain coefficients", METHOD)
        self.assertIn("signed linear branch", METHOD)
        self.assertIn("phone ISO", METHOD)
        self.assertEqual(
            FIXTURE,
            "Signed exposures around zero, values bracketing the branch cut, middle grey, "
            "and highlights well above scene-linear one.",
        )
        self.assertEqual(
            ORACLE,
            "The independent numerical reference agrees within declared arithmetic tolerances "
            "without clipping valid intermediate values.",
        )
        self.assertEqual(MUTANT, "Use the sensor-signal coefficient table for exposure-domain input.")
        self.assertEqual(EXPOSURE_COEFFICIENTS["f"], "0.092809")
        self.assertEqual(SENSOR_COEFFICIENTS["a"], "200")
        self.assertNotEqual(EXPOSURE_COEFFICIENTS, SENSOR_COEFFICIENTS)
        self.assertEqual(SOURCE, "ARRI, ALEXA Log C Curve: Usage in VFX, 2017-03")

    def test_fixture_agrees_without_clipping(self) -> None:
        raw = load_document()
        self.assertIsNone(validate_document(raw))
        self.assertEqual(raw["schemaVersion"], 1)
        self.assertEqual(raw["phase"], "P057")
        self.assertEqual(raw["mapId"], MAP_ID)
        self.assertEqual(raw["implementationBaseRevision"], BASE_REVISION)
        self.assertEqual(raw["method"], METHOD)
        self.assertEqual(raw["fixture"], FIXTURE)
        self.assertEqual(raw["oracle"], ORACLE)
        self.assertEqual(raw["mutant"], MUTANT)
        self.assertEqual(raw["encodingEi"], "800")
        self.assertEqual(raw["phoneIso"], "200")
        self.assertNotEqual(raw["encodingEi"], raw["phoneIso"])
        self.assertEqual(raw["convention"], "exposure-domain")
        result = assess(raw)
        self.assert_result(result)
        self.assertEqual(result["decision"], "reference_agreed")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:" + SOURCE, result["preservedResults"])
        self.assertIn("encoding-ei:800", result["preservedResults"])
        self.assertIn("phone-iso:200", result["preservedResults"])
        self.assertIn("black:0.092809", result["preservedResults"])
        self.assertIn("mid-grey:0.391006832034084", result["preservedResults"])
        self.assertIn("sample:neg-001:signed-negative:-0.01->0.03913245", result["preservedResults"])
        self.assertIn("sample:black:black:0->0.092809", result["preservedResults"])
        self.assertIn("sample:grey:middle-grey:0.18->0.391006832034084", result["preservedResults"])
        self.assertIn("sample:hi-16:highlight:16->0.867335728158507", result["preservedResults"])
        self.assertIn("sample:cut:branch-cut:0.010591->0.149657834105", result["preservedResults"])
        self.assertIn("unclipped:signed-and-highlight", result["preservedResults"])
        self.assertIn(ORACLE, result["reasons"])
        self.assertIn(HOST_LIMIT, result["reasons"])
        self.assertTrue(any("phone ISO 200" in item for item in result["reasons"]))
        self.assertTrue(any("not a physical S23" in item for item in result["openQuestions"]))
        self.assertNotIn(MUTANT, result["reasons"])
        joined = " ".join(result["preservedResults"])
        self.assertNotIn("->-0.662201", joined)
        self.assertNotIn("0.768042684906148", joined)

    def test_published_anchors_round_trip_and_stay_monotonic(self) -> None:
        self.assertEqual(encode("0"), "0.092809")
        self.assertEqual(encode("0"), published_exposure_encode("0"))
        self.assertEqual(encode("0.18"), "0.391006832034084")
        self.assertEqual(encode("0.18"), published_exposure_encode("0.18"))
        self.assertEqual(encode("-0.01"), published_exposure_encode("-0.01"))
        self.assertEqual(encode("16"), published_exposure_encode("16"))
        self.assertEqual(encode("16"), "0.867335728158507")
        self.assertNotEqual(encode("16"), encode("1"))
        self.assertLess(Decimal(encode("-0.01")), Decimal(encode("0")))
        self.assertGreater(Decimal(encode("16")), Decimal(encode("1")))
        previous = None
        for exposure in ("-0.02", "-0.01", "0", "0.001", "0.010591", "0.010592", "0.18", "1", "4", "16"):
            encoded = Decimal(encode(exposure))
            self.assertEqual(encode(exposure), independent_encode(exposure))
            self.assertLessEqual(abs(Decimal(decode(encode(exposure))) - Decimal(exposure)), Decimal(TOLERANCE["roundTrip"]))
            if previous is not None:
                self.assertGreater(encoded, previous)
            previous = encoded
        gap = Decimal(branch_discontinuity())
        self.assertLessEqual(gap, Decimal(TOLERANCE["branchGap"]))
        self.assertGreater(gap, 0)
        self.assertEqual(exposure_oracle_failures("exposure-domain"), [])

    def test_sensor_signal_mutant_is_rejected_and_keeps_the_inventory(self) -> None:
        raw = load_document()
        honest = assess(raw)
        self.assertNotEqual(encode_with("0", "sensor-signal"), "0.092809")
        self.assertEqual(encode_with("0", "sensor-signal"), "-0.662201")
        self.assertNotEqual(encode_with("0.18", "sensor-signal"), published_exposure_encode("0.18"))
        self.assertEqual(
            exposure_oracle_failures("sensor-signal"),
            ["black", "middle-grey", "branch", "inverse"],
        )
        mutant = apply_sensor_signal_coefficients(raw)
        self.assert_result(mutant)
        self.assertEqual(mutant["decision"], "rejected")
        self.assertNotIn(mutant["decision"], {"qualified", "allowed", "reference_agreed"})
        self.assertEqual(
            mutant["rejectedClaims"],
            ["sensor-signal-on-exposure-domain", "black", "middle-grey", "branch", "inverse"],
        )
        self.assertEqual(mutant["preservedResults"], honest["preservedResults"])
        self.assertIn("sample:hi-16:highlight:16->0.867335728158507", mutant["preservedResults"])
        self.assertIn("sample:neg-002:signed-negative:-0.02->-0.0145441", mutant["preservedResults"])
        self.assertIn(MUTANT, mutant["reasons"])
        self.assertTrue(any("different input convention" in item for item in mutant["openQuestions"]))
        self.assertNotIn("sensor-signal-on-exposure-domain", honest["rejectedClaims"])

    def test_phone_iso_does_not_select_the_encoding(self) -> None:
        raw = load_document()
        honest = assess(raw)
        rejected = select_by_phone_iso(raw)
        self.assertEqual(rejected["decision"], "rejected")
        self.assertEqual(rejected["rejectedClaims"], ["phone-iso-is-not-encoding-ei"])
        self.assertEqual(rejected["preservedResults"], honest["preservedResults"])
        self.assertNotEqual(encode("0"), EI200_EXPOSURE_BLACK)
        self.assertIn("ei200-exposure-black-not-used:" + EI200_EXPOSURE_BLACK, rejected["preservedResults"])
        self.assertNotIn(rejected["decision"], {"qualified", "allowed", "reference_agreed"})

    def test_invalid_documents_raise(self) -> None:
        valid = load_document()
        clipped = copy.deepcopy(valid)
        clipped["samples"][1]["exposure"] = "0"
        swapped = copy.deepcopy(valid)
        swapped["coefficients"]["exposure-domain"] = dict(SENSOR_COEFFICIENTS)
        phone = copy.deepcopy(valid)
        phone["phoneIso"] = "800"
        sensor_fixture = copy.deepcopy(valid)
        sensor_fixture["convention"] = "sensor-signal"
        extra = copy.deepcopy(valid)
        extra["note"] = "device"
        missing = copy.deepcopy(valid)
        del missing["mutant"]
        loose = copy.deepcopy(valid)
        loose["tolerance"]["branchGap"] = "1"
        no_highlight = copy.deepcopy(valid)
        no_highlight["samples"] = [item for item in no_highlight["samples"] if item["role"] != "highlight"]
        cases = (
            None,
            [],
            {},
            extra,
            missing,
            clipped,
            swapped,
            phone,
            sensor_fixture,
            loose,
            no_highlight,
            {**valid, "schemaVersion": 2},
            {**valid, "phase": "P056"},
            {**valid, "mapId": "other"},
            {**valid, "implementationBaseRevision": "abc"},
            {**valid, "coefficientSelector": "phone-iso"},
            {**valid, "encodingEi": "200"},
        )
        for sample in cases:
            with self.subTest(sample=type(sample).__name__):
                with self.assertRaises(ValueError):
                    validate_document(sample)
        with self.assertRaises(ValueError):
            encode("0.180")
        with self.assertRaises(ValueError):
            encode("inf")
        with self.assertRaises(ValueError):
            encode_with("0.18", "sensor")


if __name__ == "__main__":
    unittest.main()
