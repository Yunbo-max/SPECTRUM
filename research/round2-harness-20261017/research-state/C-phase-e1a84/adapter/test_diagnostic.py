"""Authored, unexecuted software checks; run only on hn01 after review.
Real pinned MBPP inputs are used for data adaptation, never invented eval programs.
"""
import copy
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

import diagnostic_driver as d

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((Path(__file__).parent/'config.json').read_text())


class DataAdapterTests(unittest.TestCase):
    def sources(self):
        return (d.read(d.checked(CONFIG['train_source_ref'], ROOT)),
                d.read(d.checked(CONFIG['test_source_ref'], ROOT)))

    def test_offline_adapter_matches_upstream_on_actual_rows(self):
        from improving.data import prepare_mbpp
        train, test = self.sources()
        actual, fields, manifest = d.adapt_sources(train, test, CONFIG['dataset_revision'])
        # Same released rows through upstream preparation; no model/scorer invocation.
        offline_dataset = {'train': train['raw_rows'], 'test': test}
        provider = types.ModuleType('datasets')
        provider.load_dataset = lambda *a, **k: offline_dataset
        with tempfile.TemporaryDirectory() as temp, patch.dict('sys.modules', {'datasets': provider}):
            expected = prepare_mbpp(temp,seed=42,calibration_size=50,validation_size=30,
                                    revision=CONFIG['dataset_revision'])
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual['calibration']), 50)
        self.assertEqual(len(actual['validation']), 30)
        self.assertEqual([r['original_task_id'] for r in actual['eval']], [r['task_id'] for r in test])
        self.assertEqual(len(actual['eval']), 500)
        original = {f"Mbpp/{r['task_id']}": r for r in train['raw_rows']+test}
        for row in fields:
            self.assertEqual(row['source_fields'],original[row['task_id']])
        self.assertEqual(sum(manifest['output_counts'].values()),len(fields))

    def test_refuse_wrong_container_and_duplicate_ids(self):
        train,test=self.sources()
        with self.assertRaises(ValueError): d.adapt_sources(train['raw_rows'],test,CONFIG['dataset_revision'])
        changed=copy.deepcopy(test); changed[-1]=changed[0]
        with self.assertRaises(ValueError): d.adapt_sources(train,changed,CONFIG['dataset_revision'])
        with self.assertRaises(ValueError): d.adapt_sources(train,test[:-1],CONFIG['dataset_revision'])


class ContractsTests(unittest.TestCase):
    def test_batches_express_n16_through_actual_group_rule(self):
        for size in [64,32,16,8,4,2,1]:
            settings=d.batch_settings(size)
            n=min(16,settings['batch_size'])
            tasks=min(settings['task_batch_size'],max(1,settings['sequence_batch_size']//n))
            self.assertEqual(n*tasks,size)
        with self.assertRaises(ValueError): d.batch_settings(3)

    def test_generation_seed_round_roles_and_missing_samples(self):
        # Metadata-only fixture; no completion/code/test/label or generated program.
        tasks=[{'task_id':'metadata/id'}]
        rows=[{'task_id':'metadata/id','sample_id':i,'seed':43,'round':1,'method':'F'} for i in range(16)]
        d.validate_generated(rows,tasks,43,'F')
        for field,value in [('seed',45),('round',0),('method','P')]:
            changed=copy.deepcopy(rows); changed[0][field]=value
            with self.assertRaises(ValueError): d.validate_generated(changed,tasks,43,'F')
        for changed in [rows[:-1],rows+rows[:1],list(reversed(rows))]:
            with self.assertRaises(ValueError): d.validate_generated(changed,tasks,43,'F')

    def test_hashes_and_completed_stage_readback(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'stages/generate-train'; out=p/'outputs'; out.mkdir(parents=True)
            (out/'predictions.jsonl').write_text('metadata-only\n')
            original=d.pin(out/'predictions.jsonl')
            d.write(Path(temp)/'identity.json',{'config_sha256':'metadata'})
            d.write(p/'request.json',{'config_sha256':'metadata','stage':'generate-train','stage_parameters':{}})
            d.write(p/'receipt.json',{'status':'completed','outputs':d.inventory(out)})
            restored,_=d.require_stage(temp,'generate-train')
            self.assertEqual(d.pin(restored/'predictions.jsonl'),original)
            (out/'predictions.jsonl').write_text('changed\n')
            with self.assertRaises(ValueError): d.require_stage(temp,'generate-train')
            with self.assertRaises(ValueError): d.checked(original)

    def test_unknown_attempt_is_not_dependency(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'stages/train-P'; p.mkdir(parents=True)
            d.write(Path(temp)/'identity.json',{'config_sha256':'metadata'})
            d.write(p/'request.json',{'config_sha256':'metadata','stage':'train-P','stage_parameters':{}})
            d.write(p/'receipt.json',{'status':'failed','error_class':'resource_oom'})
            with self.assertRaises(ValueError): d.require_stage(temp,'train-P')

    def test_error_types_do_not_turn_every_cuda_error_into_oom(self):
        self.assertEqual(d.classify_error(RuntimeError('CUDA illegal access')),'implementation_or_environment_error')
        self.assertEqual(d.classify_error(TimeoutError()),'timeout')
        self.assertEqual(d.classify_error(FileExistsError()),'attempt_conflict')
        self.assertEqual(d.classify_error(ValueError()),'contract_error')


if __name__=='__main__': unittest.main()
