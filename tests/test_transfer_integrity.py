"""Sealed metric corruption must not become a rebuttal result."""
import json
import pytest
from tests.test_transfer_diagnostics import fake_summary
from improving.pipeline import file_sha
from improving.transfer_diagnostics import ROLES, collect_round_report
from improving.utils import atomic_json


def test_collect_round_report_rejects_tampered_sealed_metrics(tmp_path):
    data = fake_summary({'dev/a': 8})
    for role in ROLES:
        folder = tmp_path/role
        folder.mkdir()
        atomic_json(folder/'binding.json', {})
        (folder/'evaluation.jsonl').write_text('{}\n')
        (folder/'evaluation.verified.jsonl').write_text('{}\n')
        atomic_json(folder/'evaluation.metrics.json', data)
        atomic_json(folder/'complete.json', {'binding': {}, 'status':'complete',
            'files': {p.name: file_sha(p) for p in folder.iterdir()}})
    path=tmp_path/'pre_native'/'evaluation.metrics.json'
    edited=json.loads(path.read_text())
    edited['aggregate']['correct_count']+=1
    atomic_json(path,edited)
    with pytest.raises(ValueError, match='changed'):
        collect_round_report(tmp_path, {}, seed=1, bootstrap_samples=5)
