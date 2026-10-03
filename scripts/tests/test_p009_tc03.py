"""TC-P009-03 incompatible output combination."""

from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p009_tc03", Path(__file__).resolve().parents[1] / "gates" / "p009_tc03.py"
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


def output(**overrides):
    base = {
        "id": "preview-main",
        "routeLogicalId": "rear",
        "routePhysicalId": "tele-sensor",
        "kind": "preview",
        "supportedAlone": True,
    }
    base.update(overrides)
    return base


def _texts(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)


class TcP00903(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P009-03")
        self.assertIn(result["decision"], {"rejected", "compatible"})
        self.assertNotIn(result["decision"], {"allowed", "qualified"})
        self.assertIsInstance(result["reasons"], list)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))
        for key in ("rejectedClaims", "preservedResults", "openQuestions"):
            self.assertIsInstance(result[key], list)
            self.assertTrue(all(isinstance(item, str) for item in result[key]))
        self.assertEqual(result["openQuestions"], ["focal unknown"])

    def assertLogicalOwner(self, result):
        self.assertIn("tele-sensor addressed via rear", result["reasons"])
        self.assertNotIn("tele-sensor", result["preservedResults"])
        self.assertNotIn("tele-sensor", result["rejectedClaims"])

    def assertNoInventedLens(self, result):
        blob = json.dumps({key: value for key, value in result.items() if key != "caseId"})
        self.assertNotIn("mm", blob.lower())
        self.assertNotIn("lens", blob.lower())
        for text in _texts(result):
            if text == result["caseId"]:
                continue
            self.assertNotRegex(text, r"\d")

    def test_variants_reject_individually_supported_combination(self):
        fixtures = {
            "mixed_preview": [
                output(id="preview-log", kind="preview"),
                output(id="preview-hdr", kind="preview"),
            ],
            "raw_plus_encoder": [
                output(id="raw-main", kind="raw"),
                output(id="encoder-main", kind="encoder"),
            ],
            "alternate_lens": [
                output(id="wide-preview", routeLogicalId="wide", routePhysicalId="wide-sensor", kind="preview"),
                output(id="tele-preview", kind="preview"),
            ],
        }
        for variant in _VARIANTS:
            outputs = fixtures[variant]
            result = evaluate(
                {
                    "outputs": outputs,
                    "constraintsViolated": True,
                    "variant": variant,
                }
            )
            with self.subTest(variant=variant):
                self.assertContract(result)
                self.assertEqual(result["decision"], "rejected")
                self.assertNotIn(result["decision"], {"allowed", "qualified"})
                self.assertEqual(result["reasons"][0], _COEXISTENCE)
                self.assertEqual(result["rejectedClaims"], [item["id"] for item in outputs])
                preserved = []
                for item in outputs:
                    if item["routeLogicalId"] not in preserved:
                        preserved.append(item["routeLogicalId"])
                self.assertEqual(result["preservedResults"], preserved)
                self.assertNoInventedLens(result)
        wide = evaluate(
            {
                "outputs": fixtures["alternate_lens"],
                "constraintsViolated": True,
                "variant": "alternate_lens",
            }
        )
        self.assertEqual(wide["preservedResults"], ["wide", "rear"])
        self.assertIn("wide-sensor addressed via wide", wide["reasons"])
        self.assertIn("tele-sensor addressed via rear", wide["reasons"])
        self.assertNotIn("wide-sensor", wide["preservedResults"])
        self.assertNotIn("tele-sensor", wide["preservedResults"])

    def test_constraints_respected_when_each_output_is_supported_alone(self):
        for variant in _VARIANTS:
            result = evaluate(
                {
                    "outputs": [
                        output(id="preview-main", kind="preview"),
                        output(id="raw-main", routeLogicalId="rear", kind="raw"),
                    ],
                    "constraintsViolated": False,
                    "variant": variant,
                }
            )
            with self.subTest(variant=variant):
                self.assertContract(result)
                self.assertEqual(result["decision"], "compatible")
                self.assertEqual(result["rejectedClaims"], [])
                self.assertEqual(result["preservedResults"], ["rear"])
                self.assertNotIn(_COEXISTENCE, result["reasons"])
                self.assertLogicalOwner(result)
                self.assertNoInventedLens(result)

    def test_unsupported_output_is_rejected_for_every_variant(self):
        for variant in _VARIANTS:
            result = evaluate(
                {
                    "outputs": [
                        output(id="preview-main", supportedAlone=True),
                        output(id="encoder-main", kind="encoder", supportedAlone=False),
                    ],
                    "constraintsViolated": False,
                    "variant": variant,
                }
            )
            with self.subTest(variant=variant):
                self.assertContract(result)
                self.assertEqual(result["decision"], "rejected")
                self.assertEqual(result["rejectedClaims"], ["encoder-main"])
                self.assertNotIn("preview-main", result["rejectedClaims"])
                self.assertEqual(result["preservedResults"], ["rear"])
                self.assertEqual(
                    result["reasons"],
                    [
                        "output encoder-main is not supported alone",
                        "tele-sensor addressed via rear",
                    ],
                )
                self.assertNoInventedLens(result)

    def test_unique_logical_ids_keep_first_seen_order(self):
        result = evaluate(
            {
                "outputs": [
                    output(id="front-preview", routeLogicalId="front", routePhysicalId="front", kind="preview"),
                    output(id="rear-raw", routeLogicalId="rear", routePhysicalId="tele-sensor", kind="raw"),
                    output(id="front-encoder", routeLogicalId="front", routePhysicalId="front", kind="encoder"),
                ],
                "constraintsViolated": True,
                "variant": "raw_plus_encoder",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["front-preview", "rear-raw", "front-encoder"])
        self.assertEqual(result["preservedResults"], ["front", "rear"])
        self.assertNotIn("addressed via front", " ".join(result["reasons"]))
        self.assertIn("tele-sensor addressed via rear", result["reasons"])

    def test_public_physical_id_needs_no_owner_bridge(self):
        result = evaluate(
            {
                "outputs": [
                    output(routePhysicalId="rear", supportedAlone=True),
                ],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            }
        )
        self.assertEqual(result["decision"], "compatible")
        self.assertEqual(result["reasons"], ["output combination is compatible"])
        self.assertEqual(result["preservedResults"], ["rear"])
        self.assertFalse(any("addressed via" in item for item in result["reasons"]))

    def test_missing_physical_member_is_not_opened_as_a_camera(self):
        result = evaluate(
            {
                "outputs": [
                    output(id="raw-main", routePhysicalId=None, kind="raw", supportedAlone=True),
                    output(id="encoder-main", routePhysicalId=None, kind="encoder", supportedAlone=True),
                ],
                "constraintsViolated": True,
                "variant": "raw_plus_encoder",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["reasons"], [_COEXISTENCE])
        self.assertEqual(result["rejectedClaims"], ["raw-main", "encoder-main"])
        self.assertEqual(result["preservedResults"], ["rear"])

    def test_constraint_violation_with_an_unsupported_output_rejects_that_id(self):
        result = evaluate(
            {
                "outputs": [
                    output(id="preview-main", supportedAlone=True),
                    output(id="raw-main", kind="raw", supportedAlone=False),
                    output(
                        id="wide-encoder",
                        routeLogicalId="wide",
                        routePhysicalId="wide",
                        kind="encoder",
                        supportedAlone=False,
                    ),
                ],
                "constraintsViolated": True,
                "variant": "alternate_lens",
            }
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"allowed", "qualified", "compatible"})
        self.assertEqual(result["rejectedClaims"], ["raw-main", "wide-encoder"])
        self.assertEqual(result["preservedResults"], ["rear", "wide"])
        self.assertEqual(
            result["reasons"],
            [
                "output raw-main is not supported alone",
                "output wide-encoder is not supported alone",
                "tele-sensor addressed via rear",
            ],
        )

    def test_variant_label_does_not_override_constraints(self):
        outputs = [
            output(id="preview-a", kind="preview"),
            output(id="preview-b", kind="preview"),
        ]
        rejected = evaluate(
            {"outputs": outputs, "constraintsViolated": True, "variant": "alternate_lens"}
        )
        compatible = evaluate(
            {"outputs": outputs, "constraintsViolated": False, "variant": "mixed_preview"}
        )
        self.assertEqual(rejected["decision"], "rejected")
        self.assertEqual(compatible["decision"], "compatible")
        self.assertEqual(rejected["rejectedClaims"], ["preview-a", "preview-b"])

    def test_invalid_payload_raises(self):
        valid = output()
        cases = [
            None,
            [],
            {},
            {"outputs": [valid], "constraintsViolated": True},
            {"constraintsViolated": True, "variant": "mixed_preview"},
            {
                "outputs": [valid],
                "constraintsViolated": True,
                "variant": "mixed_preview",
                "modelName": "SM-S918U",
            },
            {"outputs": [valid], "constraintsViolated": True, "variant": "mixed-preview"},
            {"outputs": [valid], "constraintsViolated": True, "variant": "MIXED_PREVIEW"},
            {"outputs": [valid], "constraintsViolated": "true", "variant": "mixed_preview"},
            {"outputs": [valid], "constraintsViolated": 1, "variant": "raw_plus_encoder"},
            {"outputs": valid, "constraintsViolated": False, "variant": "alternate_lens"},
            {"outputs": [], "constraintsViolated": True, "variant": "mixed_preview"},
            {"outputs": [None], "constraintsViolated": False, "variant": "mixed_preview"},
            {"outputs": ["preview"], "constraintsViolated": False, "variant": "mixed_preview"},
            {
                "outputs": [{**valid, "lens": "invented"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{key: value for key, value in valid.items() if key != "kind"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "id": ""}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "id": "   "}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "routeLogicalId": ""}],
                "constraintsViolated": True,
                "variant": "alternate_lens",
            },
            {
                "outputs": [{**valid, "routePhysicalId": ""}],
                "constraintsViolated": True,
                "variant": "alternate_lens",
            },
            {
                "outputs": [{**valid, "routePhysicalId": 2}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "kind": "still"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "kind": "RAW"}],
                "constraintsViolated": False,
                "variant": "raw_plus_encoder",
            },
            {
                "outputs": [{**valid, "supportedAlone": "true"}],
                "constraintsViolated": False,
                "variant": "mixed_preview",
            },
            {
                "outputs": [{**valid, "supportedAlone": 1}],
                "constraintsViolated": True,
                "variant": "mixed_preview",
            },
            {
                "outputs": [valid, {**valid, "id": "preview-main", "kind": "raw"}],
                "constraintsViolated": True,
                "variant": "raw_plus_encoder",
            },
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    evaluate(payload)


if __name__ == "__main__":
    unittest.main()
