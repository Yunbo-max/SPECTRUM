import unittest
from improving.continual_data import replace_leaks
class ContinualDataTests(unittest.TestCase):
    def row(self, key, prompt, split):
        return {'task_id':key,'original_prompt':prompt,'prompt':prompt,'split':split,'answer':'unused'}
    def fixture(self):
        r=self.row
        return {'math':{'train':[r('m/a','\uff21  B','train'),r('m/b','keep','train')], 'calibration':[], 'validation':[], 'eval':[r('m/e','eval math','eval')]},'qa':{'train':[], 'calibration':[], 'validation':[], 'eval':[r('q/e','A\nB','eval')]}}
    def test_replaces_normalized_leak_preserves_counts_and_eval(self):
        data=self.fixture(); pool=[self.row('m/new','new','train')]
        result,audit=replace_leaks(data,pool,123)
        self.assertEqual(result['math']['train'][0]['task_id'],'m/new')
        self.assertEqual(result['math']['train'][1],data['math']['train'][1])
        self.assertEqual(result['qa']['eval'],data['qa']['eval'])
        self.assertEqual(result['math']['eval'],data['math']['eval'])
        self.assertEqual(len(result['math']['train']),2)
        self.assertEqual(len(audit),1)
        self.assertEqual((result,audit),replace_leaks(data,pool,123))
    def test_rejects_no_eligible_replacement(self):
        with self.assertRaises(ValueError):
            replace_leaks(self.fixture(),[self.row('m/e','eval math','train')],123)
    def test_prompt_duplicate_candidate_excluded(self):
        pool=[self.row('m/x','keep','train'),self.row('m/y','A B','train'),self.row('m/z','okay','train')]
        result,_=replace_leaks(self.fixture(),pool,7)
        self.assertEqual(result['math']['train'][0]['task_id'],'m/z')
    def test_hash_tamper_rejected(self):
        import tempfile
        import hashlib
        from pathlib import Path
        from improving.continual_data import verify_hashes
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'train.jsonl'
            path.write_bytes(b'original\n')
            hashes={'train.jsonl':hashlib.sha256(path.read_bytes()).hexdigest()}
            verify_hashes(directory,hashes)
            path.write_bytes(b'changed\n')
            with self.assertRaises(ValueError):
                verify_hashes(directory,hashes)
    def test_shared_evaluation_preserved(self):
        data=self.fixture()
        data['math']['eval'][0]['original_prompt']='A B'
        data['math']['eval'][0]['prompt']='A B'
        result,_=replace_leaks(data,[self.row('m/new','new','train')],0)
        self.assertEqual(result['math']['eval'],data['math']['eval'])
        self.assertEqual(result['qa']['eval'],data['qa']['eval'])
