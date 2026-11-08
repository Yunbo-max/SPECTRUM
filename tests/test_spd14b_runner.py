import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('spd14b_runner',Path(__file__).resolve().parents[1]/'scripts/run_spd14b.py')
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class RunnerTests(unittest.TestCase):
    def test_fixed_settings(self):
        args=runner.parser().parse_args(['--domain','safety','--output-dir','out','--smoke'])
        settings=runner.study_settings(args)
        self.assertEqual(settings['rounds'],1)
        self.assertEqual(settings['train']['epochs'],2)
        self.assertEqual(settings['train']['batch_size'],2)
        self.assertEqual(settings['generation']['max_new_tokens'],4096)
        self.assertEqual(settings['generation']['sequence_batch_size'],2)
        self.assertEqual(settings['train']['max_length'],8192)

    def test_manifest_and_stage_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=runner.StageStore(root,{'identity':'one'},resume=False)
            target=root/'output.json'
            calls=[]
            store.execute('stage',lambda:(calls.append(1),target.write_text('original')),[target])
            store.execute('stage',lambda:calls.append(2),[target])
            self.assertEqual(calls,[1])
            target.write_text('tampered')
            with self.assertRaises(ValueError): store.is_done('stage')
            with self.assertRaises(ValueError): runner.StageStore(root,{'identity':'two'},resume=True)

    def test_failure_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=runner.StageStore(Path(tmp),{'identity':'one'},resume=False)
            def fail(): raise RuntimeError('failure retained')
            with self.assertRaises(RuntimeError): store.execute('bad',fail,[])
            self.assertFalse(store.is_done('bad'))
            self.assertIn('failure retained',next((Path(tmp)/'receipts').glob('bad.failure.*.json')).read_text())

    def test_span_union_preserves_selection(self):
        task={'calibration_spans':[{'start':2,'end':7,'text':'abcde'}, {'start':5,'end':9,'text':'defg'}]}
        self.assertEqual(runner.interval_tasks([task])[0]['calibration_spans'],[[2,9]])
        self.assertIsInstance(task['calibration_spans'][0],dict)

    def test_prune_requires_owned_checkpoint_and_successor(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=runner.StageStore(root,{'identity':'one'},resume=False)
            old=root/'round001'/'checkpoint'
            new=root/'round002'/'checkpoint'
            old.mkdir(parents=True); new.mkdir(parents=True)
            (old/'weights').write_text('old')
            with self.assertRaises(ValueError): runner.prune_checkpoints(store,2)
            self.assertTrue(old.exists())
            (old/'owner.json').write_text(json.dumps({'run_identity':store.identity}))
            marker=root/'evaluation.json'; marker.write_text('{}')
            store.execute('round002.evaluate',lambda:None,[marker])
            store.execute('round002.train',lambda:None,[new])
            runner.prune_checkpoints(store,2)
            self.assertFalse(old.exists())
            self.assertTrue(new.exists())

    def test_prepared_views_preserve_span_sources(self):
        from improving.data import validate_tasks
        for spans in [[], [{'start':0,'end':1,'text':'x'}]]:
            task={'task_id':'Safe/1','source':'SafeChain','split':'train',
                  'prompt':'prompt','reference':'x','calibration_spans':spans}
            clean=runner.task_views([task])
            validate_tasks(clean)
            self.assertNotIn('calibration_spans',clean[0])
            self.assertEqual(task['calibration_spans'],spans)

    def test_memory_admission_respects_other_processes(self):
        gib=2**30
        self.assertEqual(runner.memory_budget(96*gib,80*gib,12),68*gib)
        self.assertEqual(runner.memory_budget(96*gib,80*gib,12,40),40*gib)
        with self.assertRaises(ValueError): runner.memory_budget(96*gib,10*gib,12)
        with self.assertRaises(ValueError): runner.memory_budget(96*gib,80*gib,0)

    def test_smoke_orchestration_and_resume_with_cpu_stubs(self):
        from contextlib import ExitStack, contextmanager
        from unittest.mock import patch
        events=[]
        @contextmanager
        def folded(model,operators):
            events.append('fold')
            yield
            events.append('unfold')
        def load(settings,checkpoint=None):
            events.append('load-checkpoint' if checkpoint else 'load-initial')
            return object(),object()
        def generate(model,tokenizer,tasks,path,settings,**kwargs):
            self.assertTrue(all('calibration_spans' not in row for row in tasks))
            events.append(kwargs['stage'])
            rows=[{'task_id':task['task_id'],'sample_id':0,'completion':'raw','completion_ids':[1]} for task in tasks]
            runner.write_jsonl(path,rows)
            runner.atomic_json(path.with_suffix('.jsonl.budget.json'),{})
            return rows
        def annotate(model,tokenizer,tasks,path,**kwargs):
            events.append('annotate-initial')
            runner.atomic_json(path,{'raw':'preserved'})
            return [dict(row,calibration_spans=[{'start':0,'end':1,'text':'x'}]) for row in tasks]
        def calibrate(model,tokenizer,tasks,settings,path,**kwargs):
            events.append('calibrate')
            self.assertEqual(tasks[0]['calibration_spans'][0]['text'],'x')
            path.mkdir(parents=True,exist_ok=True)
            (path/'calibration.pt').write_bytes(b'operators')
            return {'module':'operator'}
        def train(model,tokenizer,tasks,records,settings,path,**kwargs):
            events.append('train')
            self.assertEqual(settings['epochs'],2)
            self.assertEqual(len(records),2)
            self.assertTrue(all('calibration_spans' not in row for row in tasks))
            path.mkdir(parents=True)
            (path/'model.safetensors').write_bytes(b'checkpoint')
            return model,{'epochs':2,'all_raw_records_retained':True}
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root=Path(tmp)
            model=root/'model'; model.mkdir(); (model/'model.safetensors').write_bytes(b'initial')
            prepared=root/'prepared'/'safety'; prepared.mkdir(parents=True)
            for split in ['train','calibration','validation','eval']:
                runner.write_jsonl(prepared/(split+'.jsonl'),[
                    {'task_id':f'Safe/{split}{i}','prompt':f'{split}{i}',
                     'original_prompt':f'{split}{i}','reference':'x','source':'SafeChain',
                     'split':split,'calibration_spans':[]} for i in range(2)])
            args=runner.parser().parse_args(['--domain','safety','--smoke','--output-dir',str(root/'out'),
                 '--model',str(model),'--prepared',str(root/'prepared')])
            replacements={
                'improving.modeling.load_model':load,
                'improving.generation.generate_to_file':generate,
                'improving.training.train_on_records':train,
                'improving.spectral.folded_operators':folded,
                'improving.spd_domains.calibrate_domains':calibrate,
                'improving.spd_safety.annotate_safety_tasks':annotate,
                'torch.cuda.is_available':lambda:True,
                'torch.cuda.mem_get_info':lambda:(80*2**30,96*2**30),
                'torch.cuda.set_per_process_memory_fraction':lambda *a:None,
                'torch.cuda.get_device_name':lambda:'CPU stub only',
                'torch.cuda.reset_peak_memory_stats':lambda:None,
                'torch.cuda.empty_cache':lambda:None}
            for name,value in replacements.items(): stack.enter_context(patch(name,value))
            stack.enter_context(patch.object(runner,'memory_receipt',lambda:{'stub_only':True}))
            runner.run_study(args)
            self.assertEqual(events,['load-initial','annotate-initial','baseline.eval_generation',
                 'calibrate','fold','round001.synthesis','unfold','train','round001.eval_generation'])
            metrics=json.loads((root/'out/round001/evaluation/metrics.json').read_text())
            self.assertIsNone(metrics['accuracy'])
            args.resume=True
            runner.run_study(args)
            self.assertEqual(events.count('annotate-initial'),1)
            self.assertEqual(events.count('train'),1)
            self.assertEqual(events[-1],'load-checkpoint')

            # Exercise the real runner boundary after checkpoint save and before
            # its train-stage seal, then recover through --resume.
            args.output_dir=str(root/'crash-out')
            args.resume=False
            real_atomic=runner.atomic_json
            failed=[False]
            def interrupt_train_seal(path,payload):
                if Path(path).name == 'round001.train.complete.json' and not failed[0]:
                    failed[0]=True
                    raise RuntimeError('injected crash before train seal')
                return real_atomic(path,payload)
            with patch.object(runner,'atomic_json',interrupt_train_seal):
                with self.assertRaisesRegex(RuntimeError,'before train seal'):
                    runner.run_study(args)
            self.assertTrue((root/'crash-out/round001/checkpoint/model.safetensors').is_file())
            self.assertFalse((root/'crash-out/receipts/round001.train.complete.json').exists())
            args.resume=True
            runner.run_study(args)
            self.assertTrue((root/'crash-out/complete.json').is_file())
            self.assertEqual(len(list((root/'crash-out/quarantine').glob('round001.*/checkpoint/model.safetensors'))),1)
            self.assertEqual(events.count('train'),3)

    def test_unsealed_checkpoint_is_quarantined_only_with_matching_intent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=runner.StageStore(root,{'identity':'one'},resume=False)
            checkpoint=root/'round001'/'checkpoint'
            records=[{'task_id':'Train/1','sample_id':0,'completion':'raw'}]
            config={'epochs':2}
            runner.prepare_training_attempt(store,'round001',checkpoint,'parent',records,config,43)
            checkpoint.mkdir(parents=True)
            (checkpoint/'weights.safetensors').write_bytes(b'saved-before-stage-seal')
            stats={'seed':43,'configured_epochs':2,'training_records_received':1}
            runner.atomic_json(checkpoint/'training_stats.json',stats)
            with self.assertRaises(ValueError):
                runner.prepare_training_attempt(store,'round001',checkpoint,'wrong-parent',records,config,43)
            self.assertTrue(checkpoint.exists())
            runner.prepare_training_attempt(store,'round001',checkpoint,'parent',records,config,43)
            self.assertFalse(checkpoint.exists())
            kept=list((root/'quarantine').glob('round001.*/checkpoint/weights.safetensors'))
            self.assertEqual(len(kept),1)
            self.assertEqual(kept[0].read_bytes(),b'saved-before-stage-seal')
            # No intent authorizes taking ownership of an unrelated checkpoint.
            unknown=root/'round002'/'checkpoint'
            unknown.mkdir(parents=True)
            with self.assertRaises(ValueError):
                runner.prepare_training_attempt(store,'round002',unknown,'parent',records,config,44)
            self.assertTrue(unknown.exists())

    def test_runtime_identity_binds_training_and_math_execution(self):
        from unittest.mock import patch
        with patch('improving.pipeline.training_runtime_identity',return_value={'torch':'v1'}), \
             patch('improving.pipeline.execution_runtime_identity',return_value={'backend':'bwrap','binary':'digest'}) as execution:
            before=runner.study_runtime_identity({'domain':'math','sandbox':{'backend':'bwrap'}})
            self.assertEqual(before['training'],{'torch':'v1'})
            self.assertEqual(before['evaluation']['binary'],'digest')
            execution.assert_called_once_with({'backend':'bwrap'})
        with patch('improving.pipeline.training_runtime_identity',return_value={'torch':'v2'}), \
             patch('improving.pipeline.execution_runtime_identity',return_value={'backend':'bwrap','binary':'digest'}):
            after=runner.study_runtime_identity({'domain':'math','sandbox':{'backend':'bwrap'}})
        self.assertNotEqual(before,after)

    def test_history_audit_checks_retained_artifacts_and_allows_sealed_pruning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            store=runner.StageStore(root,{'identity':'one'},resume=False)
            for number in (1,2):
                cp=root/f'round{number:03d}'/'checkpoint'
                cp.mkdir(parents=True)
                runner.atomic_json(cp/'owner.json',{'run_identity':store.identity})
                (cp/'weights').write_text(str(number))
                metric=root/f'round{number:03d}'/'metrics.json'
                metric.write_text('{}')
                store.execute(f'round{number:03d}.train',lambda:None,[cp])
                store.execute(f'round{number:03d}.evaluate',lambda:None,[metric])
            runner.prune_checkpoints(store,2)
            runner.audit_history(store)
            (root/'round001'/'metrics.json').write_text('changed')
            with self.assertRaises(ValueError): runner.audit_history(store)
