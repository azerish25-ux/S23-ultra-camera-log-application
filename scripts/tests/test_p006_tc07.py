"""TC-P006-07 concurrent collaborator change."""
import json
import sys
import unittest

sys.path.insert(0, '/workspace/s23/scripts/gates')

import p006_tc07

CASE_ID = 'TC-P006-07'
EXACT_KEYS = {
    'caseId',
    'decision',
    'reasons',
    'rejectedClaims',
    'preservedResults',
    'openQuestions',
}


def payload(present, preserved, overlapping, remote_head_changed, content, revision,
            **extra):
    body = {
        'caseId': CASE_ID,
        'collaborator': {
            'present': present,
            'preserved': preserved,
            'overlapping': overlapping,
            'remoteHeadChanged': remote_head_changed,
            'content': content,
        },
        'integratedRevision': revision,
    }
    body.update(extra)
    return body


class CollaboratorChangeTests(unittest.TestCase):
    def assert_contract(self, result):
        self.assertIsInstance(result, dict)
        self.assertEqual(set(result), EXACT_KEYS)
        self.assertEqual(result['caseId'], CASE_ID)
        self.assertIsInstance(result['decision'], str)
        self.assertNotEqual(result['decision'], 'allowed')
        for key in ('reasons', 'rejectedClaims', 'preservedResults', 'openQuestions'):
            self.assertIsInstance(result[key], list)
            for item in result[key]:
                self.assertIsInstance(item, str)
        if result['decision'] != 'allowed':
            self.assertTrue(result['reasons'])

    def test_rejects_non_dict(self):
        for value in (None, [], 'TC-P006-07', 7, 1.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    p006_tc07.evaluate(value)

    def test_rejects_wrong_case_id(self):
        base = payload(False, False, False, False, 'note', 'rev-1')
        for case_id in (None, '', 'TC-P006-06', 'TC-P006-08', 'TC-P007-07', 'tc-p006-07'):
            body = dict(base)
            if case_id is None:
                body.pop('caseId')
            else:
                body['caseId'] = case_id
            with self.subTest(case_id=case_id):
                with self.assertRaises(ValueError):
                    p006_tc07.evaluate(body)

    def test_blocked_when_collaborator_work_not_preserved(self):
        content = 'collaborator edit on scripts/gates/risk_register.py'
        result = p006_tc07.evaluate(payload(
            True, False, False, False, content, 'rev-reset'))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'blocked')
        self.assertIn('collaborator work must not be overwritten', result['reasons'])
        self.assertIn('clean-demonstration-reset', result['rejectedClaims'])
        self.assertIn(content, result['preservedResults'])
        self.assertNotIn('allowed', result['decision'])

    def test_blocked_never_allowed_across_overlap_and_remote_head(self):
        content = 'must keep collaborator WIP'
        for overlapping in (False, True):
            for remote in (False, True):
                with self.subTest(overlapping=overlapping, remote=remote):
                    result = p006_tc07.evaluate(payload(
                        True, False, overlapping, remote, content, 'rev-clean-demo',
                        decision='allowed'))
                    self.assert_contract(result)
                    self.assertEqual(result['decision'], 'blocked')
                    self.assertIn('collaborator work must not be overwritten', result['reasons'])
                    self.assertIn('clean-demonstration-reset', result['rejectedClaims'])
                    self.assertIn(content, result['preservedResults'])

    def test_integrated_preserves_content_and_revision(self):
        content = 'handoff keeps collaborator paragraph'
        revision = 'int-100'
        result = p006_tc07.evaluate(payload(
            True, True, False, False, content, revision))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'integrated')
        self.assertIn(content, result['preservedResults'])
        self.assertIn(revision, result['preservedResults'])
        self.assertNotIn('clean-demonstration-reset', result['rejectedClaims'])

    def test_overlapping_files_re_evaluate_assumptions(self):
        content = 'overlapping file scripts/gates/p006_tc07.py collaborator assertion'
        revision = 'int-overlap'
        result = p006_tc07.evaluate(payload(
            True, True, True, False, content, revision))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'integrated')
        self.assertIn('overlapping assumptions were re-evaluated', result['reasons'])
        self.assertIn(content, result['preservedResults'])
        self.assertIn(revision, result['preservedResults'])
        self.assertNotEqual(result['preservedResults'].count(content), 0)

    def test_non_overlapping_files_are_preserved(self):
        content = 'separate file README.md collaborator note'
        revision = 'int-separate'
        result = p006_tc07.evaluate(payload(
            True, True, False, False, content, revision))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'integrated')
        self.assertIn(content, result['preservedResults'])
        self.assertIn(revision, result['preservedResults'])
        joined = '\n'.join(result['reasons'])
        self.assertNotIn('overlapping assumptions were re-evaluated', joined)
        self.assertNotIn('clean-demonstration-reset', result['rejectedClaims'])

    def test_remote_head_change_before_push(self):
        content = 'collaborator commit retained before push'
        revision = 'int-after-remote'
        result = p006_tc07.evaluate(payload(
            True, True, False, True, content, revision))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'integrated')
        self.assertTrue(any('remote head' in reason for reason in result['reasons']))
        self.assertIn(content, result['preservedResults'])
        self.assertIn(revision, result['preservedResults'])
        self.assertNotIn('overlapping assumptions were re-evaluated', result['reasons'])

    def test_overlapping_and_remote_head_together(self):
        content = 'overlapping gate file plus remote head move'
        revision = 'int-both'
        result = p006_tc07.evaluate(payload(
            True, True, True, True, content, revision))
        self.assert_contract(result)
        self.assertEqual(result['decision'], 'integrated')
        self.assertIn('overlapping assumptions were re-evaluated', result['reasons'])
        self.assertTrue(any('remote head' in reason for reason in result['reasons']))
        self.assertIn(content, result['preservedResults'])
        self.assertIn(revision, result['preservedResults'])

    def test_absent_collaborator_is_unchanged(self):
        content = 'stale content that is not present'
        revision = 'rev-steady'
        for preserved in (False, True):
            for overlapping in (False, True):
                for remote in (False, True):
                    with self.subTest(preserved=preserved, overlapping=overlapping, remote=remote):
                        result = p006_tc07.evaluate(payload(
                            False, preserved, overlapping, remote, content, revision))
                        self.assert_contract(result)
                        self.assertEqual(result['decision'], 'unchanged')
                        self.assertIn(revision, result['preservedResults'])
                        self.assertNotIn(content, result['preservedResults'])

    def test_does_not_mutate_payload_or_drop_content(self):
        content = 'exact collaborator bytes'
        body = payload(True, True, True, True, content, 'rev-keep')
        snapshot = json.dumps(body, sort_keys=True)
        result = p006_tc07.evaluate(body)
        self.assertEqual(json.dumps(body, sort_keys=True), snapshot)
        self.assertIn(content, result['preservedResults'])
        self.assertIn('rev-keep', result['preservedResults'])


if __name__ == '__main__':
    unittest.main()
