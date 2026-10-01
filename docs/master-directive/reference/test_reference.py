"""Executable host contracts. These tests do not certify an Android device."""
import math
import tempfile
import unittest
from pathlib import Path
import cinema_reference as c


class LogEncodingTests(unittest.TestCase):
    def test_black_is_published_ei800_intercept(self):
        self.assertAlmostEqual(c.logc3_encode(0), 0.092809, places=12)

    def test_middle_grey_is_near_documented_value(self):
        self.assertAlmostEqual(c.logc3_encode(0.18), 0.3910068, places=6)

    def test_signed_values_round_trip(self):
        for x in (-0.01, -0.001, 0, 0.001, 0.01, 0.02, 0.18, 1, 4, 16):
            self.assertAlmostEqual(c.logc3_decode(c.logc3_encode(x)), x, places=9)

    def test_curve_is_monotonic_over_operating_domain(self):
        xs = [-0.01 + i * 0.001 for i in range(32000)]
        ys = [c.logc3_encode(x) for x in xs]
        self.assertTrue(all(a < b for a, b in zip(ys, ys[1:])))

    def test_nonfinite_values_are_rejected(self):
        for x in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError): c.logc3_encode(x)
            with self.assertRaises(ValueError): c.logc3_decode(x)

    def test_rounded_branch_coefficients_have_bounded_join(self):
        x = 0.010591
        self.assertLess(abs(c.logc3_encode(x) - c.logc3_encode(x + 1e-12)), 3e-7)


class NumericContractsTests(unittest.TestCase):
    def test_black_normalization_retains_negative_noise(self):
        self.assertLess(c.normalize_raw(60, 64, 1023), 0)

    def test_invalid_white_level_rejected(self):
        with self.assertRaises(ValueError): c.normalize_raw(64, 64, 64)

    def test_legal_luma_endpoints(self):
        self.assertEqual(c.quantize_luma10(0), 64)
        self.assertEqual(c.quantize_luma10(1), 940)

    def test_quantization_rejects_unconsented_clipping(self):
        with self.assertRaises(ValueError): c.quantize_luma10(1.1)
        self.assertEqual(c.quantize_luma10(1.1, allow_clip=True), 940)

    def test_p010_row_obeys_stride_and_bit_alignment(self):
        row = c.pack_p010_row([64, 512, 940], row_stride=10)
        self.assertEqual(len(row), 10)
        self.assertEqual(c.unpack_p010_row(row, 3), [64, 512, 940])
        self.assertEqual(row[6:], b'\0\0\0\0')
        self.assertTrue(all(int.from_bytes(row[i:i+2], 'little') & 63 == 0 for i in (0,2,4)))

    def test_p010_invalid_codes_and_stride_are_rejected(self):
        for codes, stride in (([1024], 2), ([-1], 2), ([1, 2], 3), ([True], 2)):
            with self.assertRaises(ValueError): c.pack_p010_row(codes, stride)

    def test_p010_unpack_rejects_low_bit_pollution(self):
        with self.assertRaises(ValueError): c.unpack_p010_row(b'\x01\x10', 1)

    def test_cfr_integer_arithmetic_avoids_accumulating_rounding(self):
        self.assertEqual(c.pts_us(24000, 24000, 1001), 1001000000)
        for i in range(24000):
            self.assertLessEqual(abs(c.pts_us(i, 24000, 1001) - i*1001*1e6/24000), 1)

    def test_cfr_invalid_values_rejected(self):
        for args in ((-1,24,1),(1,0,1),(1,24,0),(1.5,24,1)):
            with self.assertRaises(ValueError): c.pts_us(*args)

    def test_timestamp_pairing_is_exact_not_nearest(self):
        self.assertEqual(c.pair_exact([100,200], {200:'b',100:'a'}), ['a','b'])
        with self.assertRaises(ValueError): c.pair_exact([100], {101:'near'})

    def test_duplicate_sensor_timestamps_rejected(self):
        with self.assertRaises(ValueError): c.pair_exact([100,100], {100:'a'})


class OpticalContractsTests(unittest.TestCase):
    def test_focus_plane_is_sharp(self):
        self.assertEqual(c.coc_mm(50, 2, 2000, 2000), 0)

    def test_near_and_far_blur_have_opposite_signs(self):
        self.assertLess(c.coc_mm(50, 2, 2000, 1000), 0)
        self.assertGreater(c.coc_mm(50, 2, 2000, 4000), 0)

    def test_stopping_down_halves_diameter(self):
        self.assertAlmostEqual(c.coc_mm(50,4,2000,4000)*2, c.coc_mm(50,2,2000,4000))

    def test_infinity_limit_is_finite(self):
        self.assertAlmostEqual(c.coc_mm(50,2,2000,math.inf), 2500/(2*1950))

    def test_gate_conversion_is_explicit(self):
        self.assertAlmostEqual(c.coc_pixels(0.1, 50, 4000), 8)

    def test_invalid_optical_geometry_rejected(self):
        for args in ((50,0,2000,4000),(50,2,40,4000),(50,2,2000,40)):
            with self.assertRaises(ValueError): c.coc_mm(*args)

    def test_relative_depth_cannot_masquerade_as_metres(self):
        with self.assertRaises(ValueError): c.metric_distance(c.DepthSample(0.5, 'relative'))
        self.assertEqual(c.metric_distance(c.DepthSample(2.0, 'metres')), 2.0)

    def test_fov_lens_is_derived_from_gate_and_angle(self):
        self.assertAlmostEqual(c.focal_for_fov(36, 90), 18)

    def test_occlusion_disables_history_blending(self):
        self.assertEqual(c.temporal_depth(2, 100, 0.9, occluded=True), 2)

    def test_temporal_history_weight_is_bounded(self):
        self.assertAlmostEqual(c.temporal_depth(2,4,0.25), 2.5)
        with self.assertRaises(ValueError): c.temporal_depth(2,4,1.2)

    def test_shutter_angle_converts_to_seconds(self):
        self.assertAlmostEqual(c.exposure_seconds(180,24,1), 1/48)
        with self.assertRaises(ValueError): c.exposure_seconds(361,24,1)


class EvidenceAndPersistenceTests(unittest.TestCase):
    def test_advertised_is_not_certified(self):
        e = c.ModeEvidence(True, True, True, True, False)
        self.assertFalse(e.certified)

    def test_all_evidence_required(self):
        self.assertTrue(c.ModeEvidence(True,True,True,True,True).certified)

    def test_source_lineage_disallows_raw_label_for_sdr(self):
        with self.assertRaises(ValueError): c.validate_lineage('SDR8', 'RAW_DERIVED_LOG', 10)
        c.validate_lineage('RAW_SENSOR', 'RAW_DERIVED_LOG', 10)

    def test_ten_bit_output_alone_does_not_upgrade_source(self):
        c.validate_lineage('SDR8', 'SDR_DERIVED_LOOK', 10)
        with self.assertRaises(ValueError): c.validate_lineage('HLG10', 'RAW_DERIVED_LOG', 10)

    def test_resume_key_covers_model_and_source(self):
        a = c.resume_key('a','m1','graph','v1')
        self.assertNotEqual(a, c.resume_key('a','m2','graph','v1'))
        self.assertNotEqual(a, c.resume_key('b','m1','graph','v1'))

    def test_canonical_manifest_is_order_independent(self):
        self.assertEqual(c.canonical_json({'a':1,'b':2}),c.canonical_json({'b':2,'a':1}))
        with self.assertRaises(ValueError): c.canonical_json({'x':math.nan})

    def test_atomic_write_preserves_unrelated_source(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'result.json'; source=Path(d)/'source.raw'
            source.write_bytes(b'unchanged')
            c.atomic_json_write(p, {'status':'partial'})
            c.atomic_json_write(p, {'status':'verified'})
            self.assertIn('verified', p.read_text())
            self.assertEqual(source.read_bytes(), b'unchanged')

    def test_corrupt_manifest_does_not_replace_valid_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json'; p.write_text('previous')
            with self.assertRaises(ValueError): c.atomic_json_write(p, {'bad': math.nan})
            self.assertEqual(p.read_text(), 'previous')

    def test_counter_noise_is_reproducible(self):
        self.assertEqual(c.grain_sample(123,4,5,6,0), c.grain_sample(123,4,5,6,0))
        self.assertNotEqual(c.grain_sample(123,4,5,6,0), c.grain_sample(123,5,5,6,0))

    def test_counter_noise_has_reasonable_synthetic_statistics(self):
        values=[c.grain_sample(991, i, 2,3,0) for i in range(5000)]
        mean=sum(values)/len(values)
        var=sum((v-mean)**2 for v in values)/len(values)
        self.assertLess(abs(mean), .06)
        self.assertLess(abs(var-1), .08)

    def test_film_density_responds_monotonically(self):
        ys=[c.toy_density(2**(i/10)) for i in range(-100,100)]
        self.assertTrue(all(a<b for a,b in zip(ys,ys[1:])))

    def test_density_to_transmission(self):
        self.assertAlmostEqual(c.transmittance(2), .01)

    def test_recipe_requires_evidence_for_documented_claims(self):
        with self.assertRaises(ValueError): c.validate_claim('documented', [])
        c.validate_claim('reconstructed', [])
        c.validate_claim('documented', ['source-1'])

    def test_no_claimed_movie_lens_from_null_fact(self):
        with self.assertRaises(ValueError): c.validate_claim('invented', ['source-1'])


class RecorderStateTests(unittest.TestCase):
    def test_recording_waits_for_every_selected_track(self):
        s = c.RecorderState()
        s = c.reduce_recorder(s, 'start', 1, expected=('video','audio'))
        s = c.reduce_recorder(s, 'sample', 1, track='video')
        self.assertEqual(s.phase, 'STARTING')
        s = c.reduce_recorder(s, 'sample', 1, track='audio')
        self.assertEqual(s.phase, 'RECORDING')

    def test_stop_cannot_be_undone_by_late_sample(self):
        s=c.reduce_recorder(c.RecorderState(), 'start', 1)
        s=c.reduce_recorder(s,'stop',1)
        self.assertEqual(c.reduce_recorder(s,'sample',1,track='video').phase,'STOPPING')

    def test_stale_generation_is_ignored(self):
        s=c.reduce_recorder(c.RecorderState(),'start',8)
        self.assertEqual(c.reduce_recorder(s,'sample',7,track='video'),s)

    def test_finalize_retains_recorded_status(self):
        s=c.reduce_recorder(c.RecorderState(),'start',1)
        s=c.reduce_recorder(s,'sample',1,track='video')
        s=c.reduce_recorder(s,'stop',1)
        s=c.reduce_recorder(s,'finalize',1)
        self.assertEqual(s.phase,'FINALIZED')
        self.assertEqual(s.seen, frozenset({'video'}))

    def test_unexpected_track_rejected(self):
        s=c.reduce_recorder(c.RecorderState(),'start',1)
        with self.assertRaises(ValueError): c.reduce_recorder(s,'sample',1,track='audio')

    def test_invalid_event_rejected(self):
        with self.assertRaises(ValueError): c.reduce_recorder(c.RecorderState(),'mystery',0)


class BoundaryHardeningTests(unittest.TestCase):
    def test_positive_log_overflow_is_rejected(self):
        with self.assertRaises(ValueError): c.logc3_encode(1e308)

    def test_negative_log_overflow_is_rejected(self):
        with self.assertRaises(ValueError): c.logc3_encode(-1e308)

    def test_raw_normalization_rejects_overflowed_intermediate(self):
        with self.assertRaises(ValueError): c.normalize_raw(1.0, -1e308, 1e308)

    def test_optical_overflow_is_rejected(self):
        with self.assertRaises(ValueError): c.coc_mm(1e200, 2.0, 2e200, 3e200)

    def test_evidence_fields_require_actual_booleans(self):
        with self.assertRaises(ValueError): c.ModeEvidence("false", True, True, True, True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
