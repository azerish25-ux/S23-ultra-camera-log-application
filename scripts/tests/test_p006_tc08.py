"""TC-P006-08 independent reproduction."""
import json
import sys
import unittest

sys.path.insert(0, '/workspace/s23/scripts/gates')

import p006_tc08

CASE_ID = 'TC-P006-08'
PHYSICAL = 'physical S23 qualification remains open'
EXACT_KEYS = {
    'caseId',
    'decision',
    'reasons',
    'rejectedClaims',
    'preservedResults',
    'openQuestions',
}


def payload(undocumented, manual, missing, phone, stated, temp_path=None, **extra):
    body = {
        'caseId': CASE_ID,
        'reproduction': {
            'undocumentedFiles': undocumented,
            'manualIntervention': manual,
            'missingPrerequisite': missing,
            'phoneConnected': phone,
        },
        'statedSoftwareResult': stated,
    }
    if temp_path is not None:
        body['tempPath'] = temp_path
    body.update(extra)
    return body


class IndependentReproductionTests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), EXACT_KEYS)
        self.assertEqual(result['caseId'], CASE_ID)
        self.assertIsInstance(result['decision'], str)
        self.assertNotIn(result['decision'], ('allowed', 'passed'))
        for key in ('reasons', 'rejectedClaims', 'preservedResults', 'openQuestions'):
            self.assertIsInstance(result[key], list)
            for item in result[key]:
                self.assertIsInstance(item, str)
        if result['decision'] != 'allowed':
            self.assertTrue(result['reasons'])

    def test_rejects_non_dict(self):
        for value in (None, [], CASE_ID, 8, 0.0):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p006_tc08.evaluate(value)

    def test_rejects_wrong_case_id(self):
        base = payload(False, False, None, False, 'host oracle')
        for case_id in (None, '', 'TC-P006-07', 'TC-P006-09', 'TC-P008-08', 'tc-p006-08'):
            body = json.loads(json.dumps(base))
            if case_id is None:
                body.pop('caseId')
            else:
                body['caseId'] = case_id
            with self.subTest(case_id=case_id):
                with self.assertRaises(ValueError):
                    p006_tc08.evaluate(body)

    def test_undocumented_files_remain_unverified(self):
        stated = 'phase oracle matched on the original machine'
        result = p006_tc08.evaluate(payload(
            True, False, None, False, stated))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'unverified')
        self.assertIn(stated, result['preservedResults'])
        self.assertNotIn(result['decision'], ('allowed', 'passed'))

    def test_manual_intervention_remains_unverified(self):
        stated = 'result after an unrecorded local tweak'
        result = p006_tc08.evaluate(payload(
            False, True, None, False, stated))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'unverified')
        self.assertIn(stated, result['preservedResults'])

    def test_missing_prerequisite_is_unverified_and_open(self):
        stated = 'software result claimed without the cache'
        missing = 'fresh dependencies'
        result = p006_tc08.evaluate(payload(
            False, False, missing, False, stated))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'unverified')
        self.assertIn(stated, result['preservedResults'])
        self.assertIn(missing, result['openQuestions'])
        self.assertNotIn(result['decision'], ('allowed', 'passed'))

    def test_blank_missing_prerequisite_is_not_reproduced(self):
        stated = 'blank prerequisite must not count as a clean run'
        for missing in ('', '   ', '\n'):
            with self.subTest(missing=missing):
                with self.assertRaises(ValueError):
                    p006_tc08.evaluate(payload(False, False, missing, False, stated))

    def test_combined_faults_stay_unverified(self):
        stated = 'attractive summary without a fresh run'
        missing = 'private notes'
        result = p006_tc08.evaluate(payload(
            True, True, missing, False, stated))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'unverified')
        self.assertIn(stated, result['preservedResults'])
        self.assertIn(missing, result['openQuestions'])

    def test_phone_does_not_upgrade_unverified(self):
        stated = 'host result still missing its prerequisite'
        missing = 'local caches'
        for undocumented, manual, prerequisite in (
            (True, False, None),
            (False, True, None),
            (False, False, missing),
            (True, True, missing),
        ):
            with self.subTest(undocumented=undocumented, manual=manual, prerequisite=prerequisite):
                result = p006_tc08.evaluate(payload(
                    undocumented, manual, prerequisite, True, stated,
                    decision='passed'))
                self.assert_contract(result)
                self.assertEqual(result['decision'], 'unverified')
                self.assertNotIn(result['decision'], (
                    'allowed', 'passed', 'qualified', 'physical'))
                self.assertIn(stated, result['preservedResults'])
                if prerequisite:
                    self.assertIn(prerequisite, result['openQuestions'])

    def test_clean_reproduction_leaves_physical_qualification_open(self):
        stated = 'stated software result from the phase artifacts'
        for phone in (False, True):
            with self.subTest(phone=phone):
                result = p006_tc08.evaluate(payload(
                    False, False, None, phone, stated))
                self.assert_contract(result)
                self.assertEqual(result['decision'], 'reproduced')
                self.assertIn(stated, result['preservedResults'])
                self.assertIn(PHYSICAL, result['openQuestions'])
                self.assertNotIn(result['decision'], (
                    'allowed', 'passed', 'qualified', 'physical'))

    def test_connected_phone_does_not_upgrade_clean_host_result(self):
        stated = 'clean host reproduction'
        disconnected = p006_tc08.evaluate(payload(
            False, False, None, False, stated))
        connected = p006_tc08.evaluate(payload(
            False, False, None, True, stated, decision='passed'))
        self.assertEqual(disconnected['decision'], 'reproduced')
        self.assertEqual(connected['decision'], 'reproduced')
        self.assertEqual(disconnected['decision'], connected['decision'])
        self.assertIn(PHYSICAL, disconnected['openQuestions'])
        self.assertIn(PHYSICAL, connected['openQuestions'])
        self.assertIn(stated, connected['preservedResults'])
        self.assertNotIn('physical qualification granted', '\n'.join(connected['reasons']))

    def test_temp_path_does_not_affect_decision(self):
        stated = 'reproduced with a fresh temporary directory'
        paths = (
            None,
            '/tmp/s23-repro-a',
            '/var/tmp/s23-repro-b',
            '/workspace/s23/build/tmp/other',
        )
        decisions = []
        preserved = []
        for path in paths:
            body = payload(False, False, None, False, stated)
            if path is not None:
                body['tempPath'] = path
            result = p006_tc08.evaluate(body)
            self.assert_contract(result)
            self.assertEqual(result['decision'], 'reproduced')
            self.assertIn(stated, result['preservedResults'])
            self.assertIn(PHYSICAL, result['openQuestions'])
            decisions.append(result['decision'])
            preserved.append(result['preservedResults'])
        self.assertEqual(len(set(decisions)), 1)
        self.assertEqual(preserved[0], preserved[1])
        self.assertEqual(preserved[1], preserved[2])

        dirty_a = p006_tc08.evaluate(payload(
            True, False, None, False, stated, temp_path='/tmp/one'))
        dirty_b = p006_tc08.evaluate(payload(
            True, False, None, False, stated, temp_path='/tmp/two'))
        self.assertEqual(dirty_a['decision'], 'unverified')
        self.assertEqual(dirty_b['decision'], 'unverified')

    def test_stated_result_is_not_promoted_to_a_pass(self):
        stated = 'narration that says the run passed and is allowed'
        clean = p006_tc08.evaluate(payload(False, False, None, True, stated))
        dirty = p006_tc08.evaluate(payload(False, True, None, True, stated))
        self.assertEqual(clean['decision'], 'reproduced')
        self.assertEqual(dirty['decision'], 'unverified')
        self.assertIn(stated, clean['preservedResults'])
        self.assertIn(stated, dirty['preservedResults'])
        self.assertNotIn(clean['decision'], ('allowed', 'passed'))
        self.assertNotIn(dirty['decision'], ('allowed', 'passed'))

    def test_does_not_mutate_payload(self):
        body = payload(False, False, 'gradle cache', True, 'kept', temp_path='/tmp/x')
        snapshot = json.dumps(body, sort_keys=True)
        result = p006_tc08.evaluate(body)
        self.assertEqual(json.dumps(body, sort_keys=True), snapshot)
        self.assertEqual(result['decision'], 'unverified')
        self.assertIn('gradle cache', result['openQuestions'])
        self.assertIn('kept', result['preservedResults'])


if __name__ == '__main__':
    unittest.main()
