import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("check_timing", Path(__file__).parents[1] / "check_timing.py")
timing = importlib.util.module_from_spec(spec); spec.loader.exec_module(timing)

class TimingChecks(unittest.TestCase):
    def test_known_event_offsets_and_drift(self):
        result = timing.evaluate([1, 4], [1.02, 4.02], [1, 4], 30, 1024)
        self.assertTrue(result["passed"]); self.assertFalse(result["physicalLipSyncVerified"])
    def test_independent_track_reset_is_detected(self):
        with self.assertRaises(ValueError): timing.evaluate([1, 4], [.875, 3.875], [1, 4], 30)
    def test_removed_audio_interval_is_detected(self):
        with self.assertRaises(ValueError): timing.evaluate([1, 4], [1.02, 3.82], [1, 4], 30)
    def test_duplicate_missing_and_shifted_events_fail(self):
        for v, a in [([1], [1, 4]), ([1, 4], [1]), ([1.2, 4.2], [1.2, 4.2]), ([1, 2, 4], [1, 4])]:
            with self.assertRaises(ValueError): timing.evaluate(v, a, [1, 4], 24)
    def test_unreported_priming_is_bounded_and_disclosed(self):
        result = timing.evaluate([1, 4], [1.04, 4.04], [1, 4], 30)
        self.assertFalse(result["primingKnown"]); self.assertAlmostEqual(2048/48000, result["primingAllowanceSeconds"])
        with self.assertRaises(ValueError): timing.evaluate([1, 4], [1.125, 4.125], [1, 4], 30)
    def test_nan_and_unreasonable_delay_rejected(self):
        with self.assertRaises(ValueError): timing.evaluate([1, 4], [float("nan"), 4], [1, 4], 30)
        with self.assertRaises(ValueError): timing.evaluate([1, 4], [1, 4], [1, 4], 30, 100000)
    def test_event_detection_requires_actual_transitions(self):
        self.assertEqual([1, 4], timing.starts([0,1,2,3,4,5], [False,True,True,False,True,False]))
        with self.assertRaises(ValueError): timing.starts([0, 1], [True])

if __name__ == "__main__": unittest.main()
