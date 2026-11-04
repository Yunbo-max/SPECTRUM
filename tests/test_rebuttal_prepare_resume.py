"""A partial prepare must not rewrite a sealed model's download provenance."""
from tests.test_rebuttal_runner import runner


def test_prepare_reuses_verified_model_receipt_without_rewriting(tmp_path, monkeypatch):
    m = runner()
    m.initialize(tmp_path)
    (tmp_path/'assets').mkdir()
    (tmp_path/'assets/qwen7b.json').write_text('{"sealed": true}')
    checked = []
    monkeypatch.setattr(m.cf, 'verify_model', lambda manifest, alias: checked.append(alias))
    monkeypatch.setattr(m.cf, 'prepare', lambda args: {'prepared': True})

    def unexpected_download(args):
        raise AssertionError('Existing verified model receipt must not be downloaded or rewritten')

    monkeypatch.setattr(m.cf, 'download', unexpected_download)
    assert m.prepare(tmp_path, 'qwen7b', True) == {'prepared': True}
    assert checked == ['qwen7b']
    assert (tmp_path/'assets/qwen7b.json').read_text() == '{"sealed": true}'


def test_prepare_downloads_only_missing_models_and_does_not_hide_corruption(tmp_path, monkeypatch):
    m = runner()
    m.initialize(tmp_path)
    (tmp_path/'assets').mkdir()
    (tmp_path/'assets/qwen7b.json').write_text('{}')
    downloaded = []
    monkeypatch.setattr(m.cf, 'verify_model', lambda manifest, alias: None)
    monkeypatch.setattr(m.cf, 'download', lambda args: downloaded.append(args.model))
    monkeypatch.setattr(m.cf, 'prepare', lambda args: {'prepared': True})
    m.prepare(tmp_path, 'all', True)
    assert set(downloaded) == {'llama8b', 'deepseek6.7b'}
    import pytest
    def corrupt(*args):
        raise ValueError('Model checksum mismatch')
    monkeypatch.setattr(m.cf, 'verify_model', corrupt)
    with pytest.raises(ValueError, match='checksum'):
        m.prepare(tmp_path, 'qwen7b', True)
