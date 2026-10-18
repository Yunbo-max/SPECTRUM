"""Unexecuted software-only numeric/metadata fixtures; no benchmark code or scorer."""
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from analysis import (PendingEvidence, indexed, paired_summary, effect_values,
                      get_metric, validate_rows, analyze, collect_inventory, calculate, validate_arm_identity, BASE_REVISION,
                      same_ref, digest)


class AnalysisContractTests(unittest.TestCase):
    def test_same_synthetic_file_identity_not_just_same_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic-metadata.txt'
            path.write_text('metadata only; no benchmark completion')
            other=Path(temp)/'other.txt'
            other.write_bytes(path.read_bytes())
            relative={'path':path.name,'sha256':digest(path)}
            absolute={'path':str(path),'sha256':digest(path)}
            self.assertTrue(same_ref(temp,relative,absolute))
            self.assertFalse(same_ref(temp,relative,{'path':other.name,'sha256':digest(other)}))

    def test_duplicate_and_missing(self):
        rows = [{'task_id':'metadata-only', 'sample_id':i} for i in range(16)]
        self.assertEqual(len(indexed(rows, ['metadata-only'])), 16)
        with self.assertRaises(ValueError):
            indexed(rows + [rows[0]], ['metadata-only'])
        with self.assertRaises(PendingEvidence):
            indexed(rows[:-1], ['metadata-only'])

    def test_scalar_bootstrap_and_empty(self):
        got = paired_summary({'a':1., 'b':1.}, ['a','b'], samples=10)
        self.assertEqual(got['mean'], 1.)
        self.assertEqual(got['ci'], [1.,1.])
        none = paired_summary({'a':None}, ['a'], samples=10)
        self.assertIsNone(none['mean'])
        self.assertEqual(none['empty_bootstraps'], 10)

    def test_denominator_not_silently_full(self):
        got = paired_summary({'a':2., 'b':None}, ['a','b'], samples=0)
        self.assertEqual(got['eligible_tasks'], 1)
        self.assertEqual(got['missing_task_ids'], ['b'])
        self.assertIsNone(got['all_task_mean'])

    def test_repeat_pairing_direction_and_intersection(self):
        def point(value, diversity):
            return {'pass_at_k':{'1':value}, 'implementation_proxy':{
                'coverage_at_k':{'16':2*value},
                'correct_matched_coverage_at_budgets':{'4':diversity}}}
        summaries = {('F',43):{'per_task':{'a':point(.2,2)}},
                     ('F',45):{'per_task':{'a':point(.3,2)}},
                     ('P',43):{'per_task':{'a':point(.4,3)}},
                     ('P',45):{'per_task':{'a':point(.7,None)}}}
        delta = effect_values(summaries, ['a'], 'P', 'F', 'pass@1')
        self.assertAlmostEqual(delta['a'], .3)
        self.assertIsNone(effect_values(summaries, ['a'], 'P', 'F', 'D4')['a'])
        self.assertAlmostEqual(get_metric(point(.2,2),'C16'), .4)

    def test_unscored_and_infrastructure_not_false(self):
        raw = [{'task_id':'metadata-only','sample_id':i,'seed':43,'round':1,
                'method':'F','completion':''} for i in range(16)]
        scored = [{**r,'status':'failed','correct':False,
                   'evaluation_provenance':{'provenance_version':2,'backend':'reviewed-native'}} for r in raw]
        outcomes = [{'task_id':r['task_id'],'sample_id':r['sample_id'],
                     'classification':'model_outcome'} for r in raw]
        outcomes[0]['classification']='infrastructure_error'
        with self.assertRaises(PendingEvidence):
            validate_rows(raw,scored,outcomes,['metadata-only'],43,'F')
        outcomes[0]['classification']='unscored'
        with self.assertRaises(PendingEvidence):
            validate_rows(raw,scored,outcomes,['metadata-only'],43,'F')

    def test_f_metadata_cannot_be_relabeled_p(self):
        frozen = {'arm':'F', 'seed':43, 'round':1, 'stage':'evaluation',
                  'model_identity':BASE_REVISION, 'checkpoint_receipt_ref':None}
        with self.assertRaises(ValueError):
            validate_arm_identity({'arm':'P','seed':43,'method':'F'}, frozen,
                                  {'method':'F','model_identity':BASE_REVISION})
        renamed = {**frozen, 'arm':'P'}
        with self.assertRaises(ValueError):
            validate_arm_identity({'arm':'P','seed':43,'method':'P'}, renamed,
                                  {'method':'P','model_identity':BASE_REVISION})

    def test_wrong_training_arm_refused(self):
        identity = {'arm':'P','seed':43,'round':1,'stage':'evaluation',
                    'model_identity':'metadata-hash','checkpoint_receipt_ref':{'sha256':'metadata-hash'}}
        training = {'status':'completed','stage':'train-P',
                    'result':{'arm':'A','training_seed':44,'base_revision':BASE_REVISION}}
        with self.assertRaises(ValueError):
            validate_arm_identity({'arm':'P','seed':43,'method':'P'}, identity,
                                  {'method':'P','model_identity':'metadata-hash'}, training)

    def test_protocol_mode_rejected_before_metric_import(self):
        with patch('analysis.read_json', return_value={'evidence_mode':'formal', 'cd_development':{}}):
            with self.assertRaises(ValueError):
                analyze('.', {'protocol_ref':{}})

    def test_inventory_retains_every_missing_sample(self):
        def json_reader(root, ref):
            if ref.get('path', '').endswith('hf-full-test-decoded.json'):
                return [{'task_id':11}]
            return {'status':'pending','per_sample_outcomes':[]}
        with patch('analysis.read_json', side_effect=json_reader), patch('analysis.read_rows', return_value=[]):
            failures, exclusions = collect_inventory('.', {'runs':[{'arm':'F','seed':43,
                'scoring_receipt_ref':{},'raw_ref':{},'scored_ref':{}}]})
        self.assertEqual(failures, [])
        self.assertEqual(sum(x['reason']=='missing' for x in exclusions), 48)
        self.assertTrue(any(x['reason']=='scoring_not_verified' for x in exclusions))

    def test_all_arms_repeat_sensitivity(self):
        def task(value):
            return {'pass_at_k':{'1':value}, 'implementation_proxy':{
                'coverage_at_k':{'16':value},
                'correct_matched_coverage_at_budgets':{'4':value,'8':value,'16':value}}}
        summaries = {(arm,seed):{'per_task':{'metadata-only':task((seed-43)/10)}}
                     for arm in ('F','P','A') for seed in (43,45)}
        result = calculate(summaries, ['metadata-only'])
        for arm in ('F','P','A'):
            self.assertAlmostEqual(result[f'{arm}45_minus_{arm}43']['pass@1']['paired']['mean'], .2)

    def test_cross_seed_rejected(self):
        raw = [{'task_id':'metadata-only','sample_id':i,'seed':45,'round':1,'method':'F'} for i in range(16)]
        with self.assertRaises(ValueError):
            validate_rows(raw,raw,[{**r,'classification':'model_outcome'} for r in raw],['metadata-only'],43,'F')


if __name__ == '__main__':
    unittest.main()
