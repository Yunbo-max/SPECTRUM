"""Software fixtures only. Run on hn01; never scorer qualification or task data."""
import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import stage_entry as S
import native_wrapper as W


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.path=self.root/'runs/attempts/native-prepare/trial-a1-uuid/native-stage-context.json'
        self.path.parent.mkdir(parents=True)
        self.c={'kind':'research-native-stage-context','schema_version':1,
                'controller':{'task_id':'controller.task','run_id':'controller-run','owner':'native-worker','fence':7},
                'run_id':'native-prepare','trial_id':'trial','attempt_id':self.path.parent.name,
                'stage_id':'prepare','stage_kind':'prepare','native_stage_ref':{'path':'stage.json','sha256':'a'*64},
                'protocol_ref':{'path':'program.json','sha256':'b'*64},'plan_digest':'c'*64,
                'project_root':str(self.root),'workspace_root':str(self.path.parent/'workspace'),
                'scientific_verified':False,'dispatch_identity_sha256':'d'*64,'harness_context_ref':None}
        self.env={'RESEARCH_NATIVE_CONTROLLER_CONTEXT':json.dumps(self.c['controller']),
                  'RESEARCH_NATIVE_DISPATCH_SHA256':'d'*64}
        self.root_patch=patch.object(S,'ROOT',self.root); self.root_patch.start()
    def tearDown(self): self.root_patch.stop(); self.tmp.cleanup()
    def check(self): return S.context_identity(self.c,self.path,self.env)
    def test_actual_identity_fields(self):
        root,workspace=self.check()
        self.assertEqual(root,self.root); self.assertEqual(workspace,self.path.parent/'workspace')
        self.assertNotEqual(self.c['controller']['run_id'],self.c['run_id'])
    def test_missing_controller(self):
        self.env.pop('RESEARCH_NATIVE_CONTROLLER_CONTEXT')
        with self.assertRaises(W.ContractError): self.check()
    def test_forged_fence(self):
        self.c['controller']['fence']=8
        with self.assertRaises(W.ContractError): self.check()
    def test_boolean_fence(self):
        self.c['controller']['fence']=True
        with self.assertRaises(W.ContractError): self.check()
    def test_missing_dispatch(self):
        self.c['dispatch_identity_sha256']=None
        with self.assertRaises(W.ContractError): self.check()
    def test_forged_dispatch(self):
        self.env['RESEARCH_NATIVE_DISPATCH_SHA256']='e'*64
        with self.assertRaises(W.ContractError): self.check()
    def test_future_attempt_forbidden(self):
        self.c['attempt_id']='invented'
        with self.assertRaises(W.ContractError): self.check()
    def test_science_flag_rejected(self):
        self.c['scientific_verified']=True
        with self.assertRaises(W.ContractError): self.check()
    def test_workspace_escape(self):
        self.c['workspace_root']=str(self.root/'outside')
        with self.assertRaises(W.ContractError): self.check()
    def test_extra_admission_flag(self):
        self.c['admitted']=True
        with self.assertRaises(W.ContractError): self.check()


class PlanBindingTests(unittest.TestCase):
    def test_protocol_and_all_actual_fields(self):
        plan={'run_id':'native-run','protocol_ref':{'path':'program','sha256':'a'*64},
              'plan_digest':'b'*64,'provenance':{'native_stage_ref':{'path':'stage','sha256':'c'*64}}}
        stage={'job':{'trial_id':'trial'},'stage_id':'prepare','stage_kind':'prepare'}
        context={'run_id':'native-run','trial_id':'trial','stage_id':'prepare','stage_kind':'prepare',
                 'protocol_ref':plan['protocol_ref'],'native_stage_ref':plan['provenance']['native_stage_ref'],
                 'plan_digest':plan['plan_digest']}
        S.bind_context_plan(context,plan,stage)
        for key in context:
            bad=copy.deepcopy(context); bad[key]='forged'
            with self.subTest(field=key), self.assertRaises(W.ContractError):
                S.bind_context_plan(bad,plan,stage)


class MappingTests(unittest.TestCase):
    def args(self,stage='prepare',**kw):
        return SimpleNamespace(driver_stage=stage,batch=kw.get('batch'),arm=kw.get('arm'),seed=kw.get('seed'))
    def descriptor(self,kind='prepare',role='prerequisite',group='prerequisite',seed=0):
        return {'stage_kind':kind,'job':{'arm_role':role,'group':group,'seed':seed}}
    def test_prepare(self):
        self.assertEqual(S.stage_parameters(self.args(),self.descriptor()),{})
    def test_wrong_stage(self):
        with self.assertRaises(W.ContractError): S.stage_parameters(self.args(),self.descriptor('train'))
    def test_prerequisite_not_baseline(self):
        with self.assertRaises(W.ContractError): S.stage_parameters(self.args(),self.descriptor(role='baseline'))
    def test_export_matrix(self):
        for arm,role in W.ROLES.items():
            for seed in (43,45):
                self.assertEqual(S.stage_parameters(self.args('generate-eval',arm=arm,seed=seed),
                    self.descriptor('export',role,'mbpp_full_test500',seed)),{'arm':arm,'seed':seed})
    def test_wrong_export_seed(self):
        with self.assertRaises(W.ContractError):
            S.stage_parameters(self.args('generate-eval',arm='P',seed=44),self.descriptor('export','treatment','mbpp_full_test500',44))
    def test_training_seed_separate(self):
        self.assertEqual(S.stage_parameters(self.args('train',arm='P'),self.descriptor('train',seed=44)),{'arm':'P'})
    def test_no_software_check_claim(self): self.assertNotIn('software_check',S.MAP)
    def test_output_namespace(self):
        paths=S.outputs('planned-run','prepare')
        self.assertTrue(all(p.startswith('runs/stage-outputs/planned-run/') for p in paths))
        self.assertIn('runs/stage-outputs/planned-run/eval.jsonl',paths)
        self.assertEqual(len(paths),len(set(paths)))
        with self.assertRaises(W.ContractError): S.outputs('../escape','prepare')
    def test_missing_predecessor(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(W.ContractError):
                S.check_predecessors(Path(tmp),{}, {'predecessor_receipt_refs':[], 'required_predecessor_ids':['prepare']})
    def test_failed_predecessor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); f=root/'failed.json'
            f.write_text(json.dumps({'controller':{'state':'failed','task':{'action':'native_harness'}}}))
            with self.assertRaises(W.ContractError):
                S.check_predecessors(root,{}, {'predecessor_receipt_refs':[{'path':f.name,'sha256':W.hash_file(f)}],
                                              'required_predecessor_ids':['prepare']})
    def test_unchanged_fpa_config(self):
        cfg=json.loads(Path(__file__).with_name('config.json').read_text())
        self.assertEqual(cfg['backend'],'none'); self.assertFalse(cfg['generated_code_execution_enabled'])
        self.assertEqual(cfg['generation']['samples'],16)
        self.assertEqual(cfg['evaluation_seeds'],[43,45]); self.assertEqual(cfg['training_seed'],44)
        self.assertEqual(cfg['train']['target_token_budget'],7200000)
        self.assertEqual(cfg['train']['loss_scope'],'all')


class PublicationTests(unittest.TestCase):
    def test_exclusive_stream_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); src=root/'origin'; dst=root/'workspace/output'
            src.write_bytes(b'raw retained output')
            S.copy_exclusive(src,dst)
            self.assertEqual(dst.read_bytes(),src.read_bytes())
            with self.assertRaises(FileExistsError): S.copy_exclusive(src,dst)
            self.assertEqual(dst.read_bytes(),src.read_bytes())
    def test_collect_workspace_only_no_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); workspace=root/'workspace'; run=root/'stable-run'
            folder=run/'stages/prepare'; out=folder/'outputs'; out.mkdir(parents=True)
            attempt=run/'attempt'; attempt.mkdir()
            for name in S.PREPARE: (out/name).write_text('{}\n')
            (folder/'receipt.json').write_text('{}\n'); (folder/'request.json').write_text('{}\n')
            for name in ('stdout.log','stderr.log','resource-observation.json'): (attempt/name).write_text('{}\n')
            spec={k:'fixture' for k in ('project_root','stable_code_root','run_root','config_ref','protocol_ref',
                                       'cd_evidence_ref','deployment_manifest_ref','goal_id','candidate_id')}
            spec['stage']='prepare'
            c={'run_id':'native-1','project_root':str(root),'attempt_id':'actual-attempt'}
            paths=S.outputs('native-1','prepare')
            S.collect(attempt,folder,run,workspace,c,{'job':{'output_paths':paths}},spec,[],0,0,None,{}, {})
            self.assertTrue(all((workspace/p).is_file() for p in paths))
            self.assertTrue(all(not (root/p).exists() for p in paths))
            summary=json.loads((workspace/paths[0]).read_text())
            self.assertEqual(summary['scoring_status'],'pending'); self.assertNotIn('score',summary)
            self.assertFalse(summary['scientific_verified'])
            with self.assertRaises(FileExistsError):
                S.collect(attempt,folder,run,workspace,c,{'job':{'output_paths':paths}},spec,[],0,0,None,{}, {})

if __name__=='__main__': unittest.main()
