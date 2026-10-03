"""TC-P073-06 unrequested beautification."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p073_tc06", Path(__file__).resolve().parents[1] / "gates" / "p073_tc06.py"
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


def payload(**overrides):
    base = {
        "subject": "people",
        "faceSmoothing": True,
        "geometryAlteration": False,
        "explicitOptional": False,
        "flattering": True,
        "texturePreserved": False,
    }
    base.update(overrides)
    return base


class TcP07306(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P073-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("face smoothing", _MODULE.INTERVENTION)
        self.assertIn("flattering result", _MODULE.NEGATIVE)
        self.assertIn("profile views", _MODULE.REPEAT)
        self.assertIn("moving faces", _MODULE.REPEAT)

    def test_hidden_smoothing_on_people_is_rejected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["hidden-alteration", "flattering-concealment"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("subject:people", result["preservedResults"])
        self.assertIn("texture:false", result["preservedResults"])
        self.assertIn("smoothing:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "optional_adjustment"})

    def test_skin_tone_geometry_without_consent_is_rejected(self):
        result = evaluate(
            payload(subject="skin-tone", faceSmoothing=False, geometryAlteration=True, flattering=False)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["hidden-alteration"])
        self.assertIn("subject:skin-tone", result["preservedResults"])
        self.assertIn("geometry:true", result["preservedResults"])

    def test_explicit_profile_view_adjustment_is_not_hidden(self):
        result = evaluate(
            payload(
                subject="profile-view",
                explicitOptional=True,
                flattering=True,
                texturePreserved=False,
                geometryAlteration=True,
            )
        )
        self.assertEqual(result["decision"], "optional_adjustment")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("subject:profile-view", result["preservedResults"])
        self.assertIn("explicit:true", result["preservedResults"])
        self.assertIn("texture:false", result["preservedResults"])

    def test_moving_face_without_alteration_preserves_texture(self):
        result = evaluate(
            payload(
                subject="moving-face",
                faceSmoothing=False,
                geometryAlteration=False,
                flattering=False,
                texturePreserved=True,
            )
        )
        self.assertEqual(result["decision"], "texture_preserved")
        self.assertIn("subject:moving-face", result["preservedResults"])
        self.assertIn("texture:true", result["preservedResults"])

    def test_texture_lost_without_an_explicit_adjustment_is_rejected(self):
        result = evaluate(
            payload(faceSmoothing=False, geometryAlteration=False, flattering=False, texturePreserved=False)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["texture-lost"])
        self.assertIn("subject:people", result["preservedResults"])
        self.assertIn("texture:false", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "subject"},
            {**valid, "extra": True},
            {**valid, "subject": "crowd"},
            {**valid, "faceSmoothing": "true"},
            {**valid, "explicitOptional": 1},
            {**valid, "texturePreserved": None},
            {**valid, "flattering": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
