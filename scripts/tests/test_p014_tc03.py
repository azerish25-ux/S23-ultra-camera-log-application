"""TC-P014-03 incompatible simultaneous output combination."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p014_tc03", Path(__file__).resolve().parents[1] / "gates" / "p014_tc03.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_VARIANTS = ("mixed_preview", "raw_plus_encoder", "alternate_lens")
_COEXISTENCE = "independent support is not coexistence"


def _streams(variant):
    if variant == "mixed_preview":
        return [
            _output(id="preview", format="PRIVATE", width=1920, height=1080),
            _output(id="preview-sdr", format="YUV_420_888", width=1280, height=720),
        ]
    if variant == "raw_plus_encoder":
        return [
            _output(id="raw", format="RAW_SENSOR", width=4000, height=3000),
            _output(id="encoder", format="YUV_420_888", width=3840, height=2160),
        ]
    if variant == "alternate_lens":
        return [
            _output(id="wide-jpeg", format="JPEG", width=4000, height=3000),
            _output(id="tele-raw", format="RAW_SENSOR", width=2000, height=1500),
        ]
    raise AssertionError(variant)


def _output(**overrides):
    base = {
        "id": "preview",
        "format": "PRIVATE",
        "width": 1920,
        "height": 1080,
        "supportedAlone": True,
    }
    base.update(overrides)
    return base


def _token(item):
    return f"{item['width']}x{item['height']}:{item['format']}"


class TcP01403(unittest.TestCase):
    def test_module_encodes_the_case_text(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Provide individually supported outputs whose simultaneous combination "
            "violates the declared camera constraints.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Reject or replan the complete combination without pretending independent "
            "support proves coexistence.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Selecting every individually supported stream simultaneously must fail.",
        )

    def assertContract(self, result, decision):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P014-03")
        self.assertEqual(result["decision"], decision)
        self.assertNotIn(result["decision"], {"allowed", "qualified"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertEqual(result["openQuestions"], [])

    def test_each_variant_rejects_when_constraints_are_violated(self):
        for variant in _VARIANTS:
            with self.subTest(variant=variant):
                outputs = _streams(variant)
                result = evaluate(
                    {
                        "outputs": outputs,
                        "constraintsViolated": True,
                        "variant": variant,
                    }
                )
                self.assertContract(result, "rejected")
                self.assertEqual(result["reasons"], [_COEXISTENCE])
                self.assertEqual(result["rejectedClaims"], [item["id"] for item in outputs])
                self.assertEqual(result["preservedResults"], [_token(item) for item in outputs])
                self.assertNotIn(result["decision"], {"allowed", "qualified", "compatible"})

    def test_each_variant_is_compatible_when_constraints_hold(self):
        for variant in _VARIANTS:
            with self.subTest(variant=variant):
                outputs = _streams(variant)
                self.assertTrue(all(item["supportedAlone"] for item in outputs))
                result = evaluate(
                    {
                        "outputs": outputs,
                        "constraintsViolated": False,
                        "variant": variant,
                    }
                )
                self.assertContract(result, "compatible")
                self.assertEqual(
                    result["reasons"],
                    ["simultaneous combination is inside declared constraints"],
                )
                self.assertEqual(result["rejectedClaims"], [])
                self.assertEqual(result["preservedResults"], [_token(item) for item in outputs])
                self.assertNotIn(_COEXISTENCE, result["reasons"])

    def test_each_variant_rejects_when_any_output_is_unsupported_alone(self):
        for variant in _VARIANTS:
            with self.subTest(variant=variant):
                outputs = _streams(variant)
                outputs[0] = {**outputs[0], "supportedAlone": False}
                result = evaluate(
                    {
                        "outputs": outputs,
                        "constraintsViolated": False,
                        "variant": variant,
                    }
                )
                self.assertContract(result, "rejected")
                self.assertEqual(
                    result["reasons"],
                    ["individually unsupported output rejects the combination"],
                )
                self.assertEqual(result["rejectedClaims"], [outputs[0]["id"]])
                self.assertNotIn(outputs[1]["id"], result["rejectedClaims"])
                self.assertEqual(result["preservedResults"], [_token(item) for item in outputs])
                self.assertNotIn(result["decision"], {"allowed", "qualified", "compatible"})

    def test_constraint_violation_lists_every_id_even_if_one_is_unsupported(self):
        outputs = _streams("raw_plus_encoder")
        outputs[1] = {**outputs[1], "supportedAlone": False}
        result = evaluate(
            {
                "outputs": outputs,
                "constraintsViolated": True,
                "variant": "raw_plus_encoder",
            }
        )
        self.assertContract(result, "rejected")
        self.assertEqual(result["reasons"], [_COEXISTENCE])
        self.assertEqual(result["rejectedClaims"], ["raw", "encoder"])
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000:RAW_SENSOR", "3840x2160:YUV_420_888"],
        )

    def test_all_unsupported_alone_rejects_without_calling_it_coexistence(self):
        outputs = [
            {**item, "supportedAlone": False} for item in _streams("alternate_lens")
        ]
        result = evaluate(
            {
                "outputs": outputs,
                "constraintsViolated": False,
                "variant": "alternate_lens",
            }
        )
        self.assertContract(result, "rejected")
        self.assertEqual(result["rejectedClaims"], ["wide-jpeg", "tele-raw"])
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000:JPEG", "2000x1500:RAW_SENSOR"],
        )
        self.assertNotIn(_COEXISTENCE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = _streams("mixed_preview")
        first = valid[0]
        cases = [
            None,
            [],
            {},
            {"outputs": valid, "constraintsViolated": False},
            {"constraintsViolated": False, "variant": "mixed_preview"},
            {
                "outputs": valid,
                "constraintsViolated": False,
                "variant": "mixed_preview",
                "extra": True,
            },
            {"outputs": valid, "constraintsViolated": False, "variant": "mixed-preview"},
            {"outputs": valid, "constraintsViolated": False, "variant": "MIXED_PREVIEW"},
            {"outputs": valid, "constraintsViolated": 0, "variant": "mixed_preview"},
            {"outputs": valid, "constraintsViolated": "true", "variant": "raw_plus_encoder"},
            {"outputs": [], "constraintsViolated": False, "variant": "alternate_lens"},
            {"outputs": valid[0], "constraintsViolated": False, "variant": "mixed_preview"},
            {"outputs": [None], "constraintsViolated": True, "variant": "mixed_preview"},
            {"outputs": ["preview"], "constraintsViolated": False, "variant": "mixed_preview"},
            {
                "outputs": [{**first, "lens": "wide"}],
                "constraintsViolated": False,
                "variant": "alternate_lens",
            },
            {
                "outputs": [{key: value for key, value in first.items() if key != "format"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "id": ""}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "id": 1}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "format": ""}],
                "constraintsViolated": True,
                "variant": "raw_plus_encoder",
            },
            {
                "outputs": [{**first, "width": True}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "width": 0}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "height": -1}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "width": 1920.0}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "height": "1080"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "supportedAlone": 1}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**first, "supportedAlone": "true"}],
                "constraintsViolated": True,
                "variant": "alternate_lens",
            },
            {
                "outputs": [first, {**valid[1], "id": first["id"]}],
                "constraintsViolated": True,
                "variant": "mixed_preview",
            },
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
