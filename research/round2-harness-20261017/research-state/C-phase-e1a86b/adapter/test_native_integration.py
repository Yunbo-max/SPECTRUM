"""Generated, unexecuted software-interface checks; run only on admitted hn01.

These metadata/byte-transport fixtures contain no benchmark examples, generated
programs, scientific predictions, or scorer qualification evidence.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import diagnostic_driver as driver
import native_wrapper as wrapper


def put(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True))
    return {'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class ExperimentPinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.evidence = {'kind': 'research-cd-experiment', 'schema_version': 1,
                         'flow_profile': 'work-harness-cd-v1', 'stage': 'diagnosis',
                         'goal_id': 'software-fixture-goal', 'candidate_id': 'software-fixture-candidate'}

    def bind(self, value=None):
        ref = put(self.root, 'experiment.json', value or self.evidence)
        protocol = {'evidence_mode': 'developmental', 'cd_development': {
            'flow_profile': 'work-harness-cd-v1', 'stage': 'diagnosis', 'cd_evidence_ref': ref}}
        return ref, protocol

    def validate(self, ref, protocol):
        return driver.validate_cd_evidence(ref, self.root, protocol,
                                           'software-fixture-goal', 'software-fixture-candidate')

    def test_correct_real_metadata_and_exact_pin(self):
        ref, protocol = self.bind()
        self.assertEqual(self.validate(ref, protocol), self.evidence)

    def test_design_is_not_experiment_even_with_matching_hash(self):
        wrong = dict(self.evidence, kind='research-cd-diagnostic-design')
        ref, protocol = self.bind(wrong)
        with self.assertRaises(ValueError):
            self.validate(ref, protocol)

    def test_each_identity_component_is_mandatory(self):
        for key, wrong in [('schema_version', 2), ('schema_version', True),
                           ('stage', 'development'), ('flow_profile', 'legacy'),
                           ('goal_id', 'other-goal'), ('candidate_id', 'other-candidate')]:
            with self.subTest(key=key, wrong=wrong):
                ref, protocol = self.bind(dict(self.evidence, **{key: wrong}))
                with self.assertRaises(ValueError):
                    self.validate(ref, protocol)

    def test_protocol_cannot_substitute_design_or_add_unreviewed_fields(self):
        ref, protocol = self.bind()
        for field, value in [('cd_evidence_ref', {'path': 'design.json', 'sha256': '0'*64}),
                             ('stage', 'development'), ('extra', True)]:
            changed = copy.deepcopy(protocol)
            changed['cd_development'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.validate(ref, changed)

    def test_content_mutation_absolute_traversal_and_symlink_rejected(self):
        ref, protocol = self.bind()
        (self.root / 'experiment.json').write_text('{}')
        with self.assertRaises(ValueError):
            self.validate(ref, protocol)
        ref, protocol = self.bind()
        for bad_path in [str(self.root/'experiment.json'), '../experiment.json', './experiment.json']:
            bad = dict(ref, path=bad_path)
            with self.subTest(path=bad_path), self.assertRaises(ValueError):
                driver.project_pin(bad, self.root)
        (self.root/'link.json').symlink_to(self.root/'experiment.json')
        with self.assertRaises(ValueError):
            driver.project_pin(dict(ref, path='link.json'), self.root)

    def test_deployment_requires_all_python_files_and_config(self):
        code = self.root/'code'
        code.mkdir()
        first = put(self.root, 'code/driver.py', {'software_fixture': 1})
        second = put(self.root, 'code/source/helper.py', {'software_fixture': 2})
        cfg = put(self.root, 'code/config.json', {'software_fixture': True})
        manifest = {'kind': 'b02-stable-deployment', 'schema_version': 1,
                    'files': [first, second, cfg]}
        ref = put(self.root, 'deployment.json', manifest)
        self.assertEqual(driver.validate_deployment(ref, self.root, code, code/'config.json'), manifest['files'])
        for omitted in (first, second, cfg):
            broken = dict(manifest, files=[r for r in manifest['files'] if r != omitted])
            ref = put(self.root, 'deployment.json', broken)
            with self.subTest(omitted=omitted['path']), self.assertRaises(ValueError):
                driver.validate_deployment(ref, self.root, code, code/'config.json')

    def test_upstream_manifest_requires_init_and_transitive_python_files(self):
        source = self.root/'upstream'
        init = put(source, 'src/improving/__init__.py', {'fixture': 'init'})
        module = put(source, 'src/improving/data.py', {'fixture': 'data'})
        cfg = {'source_root': str(source), 'source_hashes': {module['path']: module['sha256']}}
        manifest = {'upstream_files': [init, module]}
        self.assertEqual(driver.validate_upstream_deployment(manifest, cfg), [init, module])
        with self.assertRaises(ValueError):
            driver.validate_upstream_deployment({'upstream_files': [module]}, cfg)
        put(source, 'src/improving/new_dependency.py', {'fixture': 'new'})
        with self.assertRaises(ValueError):
            driver.validate_upstream_deployment(manifest, cfg)

    def test_deployment_detects_new_dependency_and_symlink(self):
        code = self.root/'code'
        code.mkdir()
        cfg = put(self.root, 'code/config.json', {})
        src = put(self.root, 'code/driver.py', {})
        ref = put(self.root, 'deployment.json', {'kind': 'b02-stable-deployment',
                    'schema_version': 1, 'files': [cfg, src]})
        put(self.root, 'code/new_dependency.py', {})
        with self.assertRaises(ValueError):
            driver.validate_deployment(ref, self.root, code, code/'config.json')
        (code/'new_dependency.py').unlink()
        (code/'alias.py').symlink_to(code/'driver.py')
        with self.assertRaises(ValueError):
            driver.validate_deployment(ref, self.root, code, code/'config.json')


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root/'origin.log'
        self.source.write_bytes(b'software-only partial stderr\n')
        self.identity = {'task_id': 'fixture', 'attempt_id': 'attempt1',
                         'protocol_ref': {'path': 'protocol.json', 'sha256': '0'*64},
                         'arm_role': None, 'group': None, 'seed': None}

    def test_streamed_mirror_exact_bytes_and_same_producer_reuse(self):
        dest = self.root/'mirror'
        first = wrapper.mirror_file(self.source, dest, 'logs/stderr.log', self.identity)
        second = wrapper.mirror_file(self.source, dest, 'logs/stderr.log', self.identity)
        self.assertFalse(first['reused'])
        self.assertTrue(second['reused'])
        self.assertEqual((dest/'logs/stderr.log').read_bytes(), self.source.read_bytes())
        self.assertEqual(first['origin']['path'], str(self.source))

    def test_equal_bytes_with_different_origin_or_attempt_are_not_reusable(self):
        dest = self.root/'mirror'
        wrapper.mirror_file(self.source, dest, 'stderr.log', self.identity)
        unrelated = self.root/'unrelated.log'
        unrelated.write_bytes(self.source.read_bytes())
        with self.assertRaises(wrapper.PackagingError):
            wrapper.mirror_file(unrelated, dest, 'stderr.log', self.identity)
        for field, wrong in [('attempt_id', 'attempt2'), ('arm_role', 'treatment'),
                             ('seed', 45), ('protocol_ref', {'path': 'other.json', 'sha256': '0'*64})]:
            with self.subTest(field=field), self.assertRaises(wrapper.PackagingError):
                wrapper.mirror_file(self.source, dest, 'stderr.log', dict(self.identity, **{field: wrong}))

    def test_conflict_preserves_existing_bytes_and_original(self):
        dest = self.root/'mirror'
        wrapper.mirror_file(self.source, dest, 'stderr.log', self.identity)
        (dest/'stderr.log').write_bytes(b'conflicting output')
        before = self.source.read_bytes()
        with self.assertRaises(wrapper.PackagingError):
            wrapper.mirror_file(self.source, dest, 'stderr.log', self.identity)
        self.assertEqual((dest/'stderr.log').read_bytes(), b'conflicting output')
        self.assertEqual(self.source.read_bytes(), before)

    def test_path_escape_and_symlink_rejected(self):
        for path in ('../escape', '/absolute/escape'):
            with self.subTest(path=path), self.assertRaises(wrapper.ContractError):
                wrapper.safe_path(self.root, path)
        (self.root/'link').symlink_to(self.source)
        with self.assertRaises(wrapper.ContractError):
            wrapper.mirror_file(self.root/'link', self.root/'mirror', 'stderr.log', self.identity)
        (self.root/'linked-dir').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(wrapper.ContractError):
            wrapper.safe_path(self.root, 'linked-dir/stderr.log')

    def test_archive_fixed_slots_and_exact_reconstruction(self):
        from unittest.mock import patch
        # Shrink only software transport blocks; real constants remain 8 x 256MiB.
        self.assertEqual(wrapper.PART_COUNT, 8)
        self.assertEqual(wrapper.PART_BYTES, 256*1024*1024)
        other = self.root/'second.log'
        other.write_bytes(b'metadata-only')
        with patch.object(wrapper, 'PART_BYTES', 16):
            index = wrapper.archive_members([self.source, other], self.root/'parts')
        self.assertEqual(len(index['parts']), 8)
        for entry in index['members']:
            reconstructed = bytearray()
            for span in entry['spans']:
                self.assertEqual(span['member_offset'], len(reconstructed))
                part = self.root/'parts'/f'archive-{span["part"]:02d}.bin'
                with part.open('rb') as stream:
                    stream.seek(span['offset'])
                    reconstructed.extend(stream.read(span['length']))
            self.assertEqual(bytes(reconstructed), Path(entry['path']).read_bytes())
            self.assertEqual(hashlib.sha256(reconstructed).hexdigest(), entry['sha256'])
        for part in index['parts']:
            self.assertLessEqual(part['size'], 16)
            if part['unused']:
                self.assertEqual(Path(part['path']).read_bytes(), b'')

    def test_archive_overflow_keeps_partial_log_without_truncating(self):
        from unittest.mock import patch
        original = self.source.read_bytes()
        with patch.object(wrapper, 'PART_BYTES', 1), self.assertRaises(wrapper.PackagingError):
            wrapper.archive_members([self.source], self.root/'too-small')
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse((self.root/'too-small/archive-index.json').exists())


class StageInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.spec = {'project_root': str(self.root), 'stable_code_root': str(self.root/'code'),
                     'run_root': str(self.root/'run'), 'export_root': str(self.root/'exports'),
                     'stage': 'generate-eval', 'parameters': {'arm': 'F', 'seed': 43},
                     'task_id': 'software-task', 'run_id': 'software-run', 'attempt_id': 'software-attempt',
                     'arm_role': 'baseline', 'group': 'mbpp_full_test500',
                     'kind': 'b02-native-stage', 'schema_version': 1,
                     'timeout_seconds': 1, 'estimated_new_original_bytes': 0,
                     'estimated_core_bytes': 0, 'disk_margin_bytes': 0,
                     'protocol_ref': {'path': 'protocol.json', 'sha256': '0'*64},
                     'cd_evidence_ref': {'path': 'experiment.json', 'sha256': '1'*64}}

    def test_timeouts_and_disk_estimates_must_be_finite_and_nonnegative(self):
        self.assertIsNone(wrapper.validate_numbers(self.spec))
        for timeout in (float('nan'), float('inf'), float('-inf'), -1, 0, True, '1', None):
            with self.subTest(timeout=timeout), self.assertRaises(wrapper.ContractError):
                wrapper.validate_numbers(dict(self.spec, timeout_seconds=timeout))
        for field in ('estimated_new_original_bytes', 'estimated_core_bytes', 'disk_margin_bytes'):
            for value in (-1, float('nan'), float('inf'), 0.5, True, '0', None):
                with self.subTest(field=field, value=value), self.assertRaises(wrapper.ContractError):
                    wrapper.validate_numbers(dict(self.spec, **{field: value}))

    def test_six_exports_individually_declare_predictions_and_fixed_slots(self):
        predictions = []
        for arm in ('F', 'P', 'A'):
            for seed in (43, 45):
                spec = dict(self.spec, parameters={'arm': arm, 'seed': seed})
                paths = wrapper.declared_outputs(spec)
                raw = [p for p in paths if p.endswith('/predictions.jsonl')]
                self.assertEqual(len(raw), 1)
                predictions.extend(raw)
                self.assertEqual(len([p for p in paths if p.endswith('.bin')]), 8)
                self.assertEqual(len(paths), len(set(paths)))
                self.assertTrue(any(p.endswith('/driver-receipt.json') for p in paths))
                self.assertFalse(any('score' in Path(p).name for p in paths))
        self.assertEqual(len(set(predictions)), 6)
        prep = dict(self.spec, stage='prepare', parameters={}, arm_role=None, group=None)
        self.assertFalse(any(p.endswith('/predictions.jsonl') for p in wrapper.declared_outputs(prep)))

    def test_wrong_role_seed_group_and_unenumerated_stage_reject_before_launch(self):
        for changes in ({'arm_role': 'treatment'}, {'group': 'another-population'},
                        {'parameters': {'arm': 'F', 'seed': 99}}, {'stage': 'shell'},
                        {'parameters': {'arm': 'F', 'seed': 43, 'command': 'arbitrary'}}):
            spec = dict(self.spec, **changes)
            with self.subTest(changes=changes), self.assertRaises(wrapper.ContractError):
                wrapper.validate_spec(spec, self.root, self.root/'code', self.root/'run', self.root/'exports',
                                      'software-task', 'software-run', 'software-attempt')

    def test_stable_identity_ignores_workspace_but_not_source_or_experiment(self):
        spec = dict(self.spec, config_ref={'path': 'config.json', 'sha256': '2'*64},
                    deployment_manifest_ref={'path': 'deployment.json', 'sha256': '3'*64},
                    goal_id='fixture-goal', candidate_id='fixture-candidate')
        first = wrapper.stable_identity(dict(spec, workspace_root='/workspace/one'))
        second = wrapper.stable_identity(dict(spec, workspace_root='/workspace/two',
                                              attempt_id='second-attempt'))
        self.assertEqual(first, second)
        self.assertNotEqual(first, wrapper.stable_identity(dict(spec, stable_code_root='/changed/code')))
        self.assertNotEqual(first, wrapper.stable_identity(dict(spec,
            cd_evidence_ref={'path': 'other-experiment.json', 'sha256': '1'*64})))

    def test_failed_launch_seals_metadata_without_scores_and_refuses_retry(self):
        from contextlib import ExitStack
        from types import SimpleNamespace
        from unittest.mock import patch
        # This test never launches any process: the process factory raises before launch.
        spec = dict(self.spec, stage='prepare', parameters={}, arm_role=None, group=None,
            config_ref={'path': 'config.json', 'sha256': '2'*64},
            deployment_manifest_ref={'path': 'deployment.json', 'sha256': '3'*64},
            goal_id='fixture-goal', candidate_id='fixture-candidate',
            interpreter='/software-fixture-venv/bin/python',
            estimated_new_original_bytes=0, estimated_core_bytes=0, disk_margin_bytes=0,
            timeout_seconds=1, input_refs=[], predecessor_refs=[],
            resource_observation_ref={'path': 'resource.json', 'sha256': '4'*64})
        spec['output_paths'] = wrapper.declared_outputs(spec)
        cfg = {'source_root': str(self.root/'upstream')}
        identity = (spec['task_id'], spec['run_id'], spec['attempt_id'])
        with ExitStack() as stack:
            stack.enter_context(patch.object(wrapper, 'validate_spec', return_value=({}, cfg)))
            stack.enter_context(patch.object(wrapper, 'build_argv', return_value=['never-launched']))
            stack.enter_context(patch.object(wrapper.sys, 'platform', 'linux'))
            stack.enter_context(patch.object(wrapper.sys, 'executable', spec['interpreter']))
            stack.enter_context(patch.object(wrapper.sys, 'prefix', '/software-fixture-venv'))
            stack.enter_context(patch.object(wrapper.shutil, 'disk_usage', return_value=SimpleNamespace(free=64*1024**3)))
            popen = stack.enter_context(patch.object(wrapper.subprocess, 'Popen', side_effect=OSError('software-fixture launch failure')))
            result = wrapper.run_stage(spec, {'path': 'spec.json', 'sha256': '5'*64},
                                       self.root/'workspace', identity)
            self.assertEqual(result['exit_code'], 3)
            self.assertEqual(result['scoring_status'], 'pending')
            self.assertFalse(result['science_accepted'])
            attempt = Path(result['attempt_path'])
            summary = json.loads((attempt/'seal/stage-summary.json').read_text())
            self.assertEqual(summary['status'], 'failed')
            self.assertIn('software-fixture launch failure', summary['failure'])
            self.assertFalse(summary['checkpoint_downloaded'])
            self.assertNotIn('score', summary)
            self.assertNotIn('metrics', summary)
            self.assertTrue(json.loads((attempt/'seal/inventory.json').read_text())['partial'])
            self.assertTrue((attempt/'sealed.json').is_file())
            self.assertEqual(len(list((attempt/'seal').glob('archive-*.bin'))), 8)
            with self.assertRaises(wrapper.ContractError):
                wrapper.run_stage(spec, {'path': 'spec.json', 'sha256': '5'*64},
                                  self.root/'other-workspace', identity)
            self.assertEqual(popen.call_count, 1)

    def test_driver_receipt_rejects_wrong_protocol_pid_or_origin_identity(self):
        protocol = self.root/'protocol.json'
        protocol.write_text('{}')
        self.spec['protocol_ref'] = put(self.root, 'protocol.json', {'software_metadata': True})
        self.spec['config_ref'] = put(self.root, 'config.json', {'software_metadata': True})
        self.spec['deployment_manifest_ref'] = put(self.root, 'deployment.json', {'files': []})
        refs = {'protocol_ref': protocol, 'config_ref': self.root/'config.json',
                'deployment_manifest_ref': self.root/'deployment.json'}
        expected = {'path': str(protocol), 'sha256': self.spec['protocol_ref']['sha256']}
        folder = self.root/'run/stages/generate-eval-F-43'
        execution_identity = {key: self.spec[key] for key in ('task_id', 'run_id', 'attempt_id')}
        request = {'stage': 'generate-eval-F-43',
                   'stage_parameters': {'batch': None, 'arm': 'F', 'seed': 43, 'execution_identity': execution_identity},
                   'cd_evidence_ref': self.spec['cd_evidence_ref'],
                   'deployment_manifest_ref': self.spec['deployment_manifest_ref'], 'deployment_code_refs': []}
        receipt = {'stage': 'generate-eval-F-43', 'pid': 123, 'started_at_unix': 10,
                   'protocol_ref': expected, 'status': 'failed', 'execution_identity': execution_identity,
                   'config_ref': {'path': str(refs['config_ref']), 'sha256': self.spec['config_ref']['sha256']},
                   'cd_evidence_ref': self.spec['cd_evidence_ref'],
                   'deployment_manifest_ref': self.spec['deployment_manifest_ref'], 'partial_outputs': []}
        put(folder, 'request.json', request)
        put(folder, 'receipt.json', receipt)
        self.assertEqual(wrapper.verify_driver(self.spec, refs, 123, 9), receipt)
        for changes in ({'pid': 124}, {'protocol_ref': {'path': '/wrong', 'sha256': '0'*64}},
                        {'started_at_unix': 8}, {'stage': 'generate-eval-P-43'}):
            put(folder, 'receipt.json', dict(receipt, **changes))
            with self.subTest(changes=changes), self.assertRaises(wrapper.ContractError):
                wrapper.verify_driver(self.spec, refs, 123, 9)
        put(folder, 'receipt.json', dict(receipt, status='completed'))
        # Metadata is sufficient to reject; no fake benchmark prediction rows are created.
        for changes in ({'arm': 'P'}, {'seed': 45}, {'stage': 'training'},
                        {'protocol_ref': {'path': '/wrong', 'sha256': '0'*64}}):
            ident = dict({'arm': 'F', 'seed': 43, 'stage': 'evaluation', 'protocol_ref': expected}, **changes)
            ident_ref = put(folder, 'outputs/identity.json', ident)
            identity_path = folder/'outputs/identity.json'
            put(folder, 'receipt.json', dict(receipt, status='completed', outputs=[{
                'path': 'identity.json', 'sha256': ident_ref['sha256'], 'bytes': identity_path.stat().st_size}]))
            with self.subTest(changes=changes), self.assertRaises(wrapper.ContractError):
                wrapper.verify_driver(self.spec, refs, 123, 9)


class PredecessorContractTests(unittest.TestCase):
    """Software-only receipt chains, not evidence of any actual experiment."""
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.spec = {'project_root': str(self.root), 'stable_code_root': str(self.root/'code'),
                     'run_root': str(self.root/'run'), 'export_root': str(self.root/'exports'),
                     'stage': 'calibrate-inference', 'parameters': {'batch': 32},
                     'goal_id': 'fixture-goal', 'candidate_id': 'fixture-candidate',
                     'input_refs': [], 'predecessor_refs': []}
        for key, name in [('config_ref', 'config.json'), ('protocol_ref', 'protocol.json'),
                          ('cd_evidence_ref', 'experiment.json'), ('deployment_manifest_ref', 'deployment.json')]:
            self.spec[key] = put(self.root, name, {'files': []} if key == 'deployment_manifest_ref' else {'software_only': key})
        self.refs = {key: self.root/self.spec[key]['path'] for key in
                     ('config_ref', 'protocol_ref', 'cd_evidence_ref', 'deployment_manifest_ref')}
        protocol = {'path': str(self.refs['protocol_ref']), 'sha256': self.spec['protocol_ref']['sha256']}
        run_identity = {'config_sha256': self.spec['config_ref']['sha256'], 'deployment_code_refs': [],
                        'protocol_ref': protocol, **{key: self.spec[key] for key in
                        ('cd_evidence_ref', 'deployment_manifest_ref', 'goal_id', 'candidate_id')}}
        put(self.root, 'run/identity.json', run_identity)
        for stage, status in [('prepare', 'completed'), ('calibrate-inference-64', 'failed')]:
            execution = {'task_id': 'fixture-'+stage, 'run_id': 'fixture-run', 'attempt_id': 'fixture-'+stage}
            request = dict(run_identity, stage=stage, stage_parameters={'execution_identity': execution})
            put(self.root, f'run/stages/{stage}/request.json', request)
            receipt = {'stage': stage, 'status': status, 'execution_identity': execution,
                       'protocol_ref': protocol, 'config_ref': {'path': str(self.refs['config_ref']),
                       'sha256': self.spec['config_ref']['sha256']},
                       'cd_evidence_ref': self.spec['cd_evidence_ref'],
                       'deployment_manifest_ref': self.spec['deployment_manifest_ref']}
            if status == 'failed':
                receipt.update(error_class='resource_oom', partial_outputs=[])
            else:
                receipt['outputs'] = []
            receipt_ref = put(self.root, f'run/stages/{stage}/receipt.json', receipt)
            self.spec['predecessor_refs'].append(receipt_ref)
            wrapper_request = dict(wrapper.stable_identity(self.spec), **execution, stage=stage)
            attempt = f'run/wrapper-attempts/{execution["attempt_id"]}'
            put(self.root, attempt+'/request.json', wrapper_request)
            summary_ref = put(self.root, attempt+'/seal/stage-summary.json', {
                'identity': wrapper_request, 'driver_receipt': receipt, 'driver_receipt_ref': receipt_ref,
                'status': status})
            summary_path = self.root/summary_ref['path']
            seal_ref = put(self.root, attempt+'/sealed.json', {'status': status, 'summary': {
                'path': str(summary_path), 'sha256': summary_ref['sha256'], 'size': summary_path.stat().st_size}})
            self.spec['input_refs'].append(seal_ref)

    def test_sealed_same_run_immediate_oom_permits_next_lower_batch(self):
        self.assertEqual(wrapper.required_predecessors(self.spec), {'prepare', 'calibrate-inference-64'})
        self.assertIsNone(wrapper.validate_predecessors(self.spec, self.refs))

    def test_unsealed_or_missing_dependency_rejected(self):
        for changed in (dict(self.spec, input_refs=self.spec['input_refs'][:1]),
                        dict(self.spec, predecessor_refs=self.spec['predecessor_refs'][:1])):
            with self.assertRaises(wrapper.ContractError):
                wrapper.validate_predecessors(changed, self.refs)

    def test_same_bytes_foreign_run_receipt_rejected(self):
        original = self.root/self.spec['predecessor_refs'][1]['path']
        foreign = put(self.root, 'foreign/stages/calibrate-inference-64/receipt.json', json.loads(original.read_text()))
        self.assertEqual(foreign['sha256'], self.spec['predecessor_refs'][1]['sha256'])
        changed = dict(self.spec, predecessor_refs=[self.spec['predecessor_refs'][0], foreign])
        with self.assertRaises(wrapper.ContractError):
            wrapper.validate_predecessors(changed, self.refs)

    def test_non_oom_failure_not_eligible_for_descent(self):
        ref = self.spec['predecessor_refs'][1]
        receipt = json.loads((self.root/ref['path']).read_text())
        receipt['error_class'] = 'implementation_or_environment_error'
        changed_ref = put(self.root, ref['path'], receipt)
        changed = dict(self.spec, predecessor_refs=[self.spec['predecessor_refs'][0], changed_ref])
        with self.assertRaises(wrapper.ContractError):
            wrapper.validate_predecessors(changed, self.refs)

    def test_mismatched_request_attempt_and_run_config_rejected(self):
        name = 'run/stages/calibrate-inference-64/request.json'
        original = json.loads((self.root/name).read_text())
        for changed in (dict(original, config_sha256='0'*64),
                        dict(original, stage_parameters={'execution_identity': {
                            'task_id': 'foreign', 'run_id': 'foreign', 'attempt_id': 'foreign'}})):
            put(self.root, name, changed)
            with self.assertRaises(wrapper.ContractError):
                wrapper.validate_predecessors(self.spec, self.refs)


if __name__ == '__main__':
    unittest.main()
