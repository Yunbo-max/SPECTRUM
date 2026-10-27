"""Boundary rejection contracts. Real namespace acceptance uses the native CLI.

These tests are source-delivered and have not been executed in the Web session.
"""
from pathlib import Path

import pytest

from improving.native_sandbox import run_python


@pytest.fixture
def never_launch(monkeypatch):
    def prohibited(*args, **kwargs):
        raise AssertionError('Rejected input must not launch a process')
    monkeypatch.setattr('improving.native_sandbox.subprocess.Popen', prohibited)
    return {'protocol': 'test-rejection-only'}


@pytest.mark.parametrize('destination', ['/root/private', '/input/../../root', 'input/file', '/inputx/file'])
def test_host_path_and_traversal_mounts_rejected(tmp_path, never_launch, destination):
    source = tmp_path / 'source'
    source.write_text('data')
    with pytest.raises(ValueError, match='beneath /input'):
        run_python('pass', readonly={destination: source}, identity=never_launch)


def test_directory_mount_cannot_expose_parent_secrets(tmp_path, never_launch):
    (tmp_path / 'private').write_text('not for sandbox')
    with pytest.raises(ValueError, match='individual regular files'):
        run_python('pass', readonly={'/input/directory': tmp_path}, identity=never_launch)


def test_existing_output_directory_is_not_exposed_for_overwrite(tmp_path, never_launch):
    sentinel = tmp_path / 'existing-result'
    sentinel.write_text('preserve')
    with pytest.raises(ValueError, match='exist and be empty'):
        run_python('pass', output_dir=tmp_path, identity=never_launch)
    assert sentinel.read_text() == 'preserve'


def test_credentials_cannot_be_injected_into_worker_environment(never_launch):
    with pytest.raises(ValueError, match='environment variable'):
        run_python('pass', environment={'HF_TOKEN': 'test-only-placeholder'}, identity=never_launch)


def test_root_multiprocess_mode_requires_trusted_guarded_coordinator(monkeypatch, never_launch):
    monkeypatch.setattr('improving.native_sandbox.os.geteuid', lambda: 0)
    with pytest.raises(RuntimeError, match='non-root'):
        run_python('pass', allow_processes=True, identity=never_launch)
