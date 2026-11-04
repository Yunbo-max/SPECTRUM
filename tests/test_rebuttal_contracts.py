"""Regression contracts for the rebuttal integration, never benchmark scores."""
from pathlib import Path
import pytest
from improving import pipeline


def test_baseline_resume_must_require_immediate_predecessor(tmp_path):
    for method in ("plain", "ssd", "spectral_soft", "spectral_learned"):
        expected = tmp_path / method / "round_1" / "model"
        with pytest.raises(ValueError, match="predecessor"):
            pipeline.require_predecessor(tmp_path, method, 2, None, trained=False)
        expected.mkdir(parents=True)
        pipeline.require_predecessor(tmp_path, method, 2, expected, trained=False)
        pipeline.require_predecessor(tmp_path, method, 2, None, trained=True)
        pipeline.require_predecessor(tmp_path, method, 1, None, trained=False)


def test_three_state_config_accepts_matched_four_arm_rebuttal():
    from tests.test_transfer_diagnostics import configuration
    from improving.transfer_diagnostics import transfer_settings
    cfg = configuration()
    cfg['methods'] = ['plain', 'ssd', 'spectral_soft', 'spectral_learned']
    assert transfer_settings(cfg)['samples'] == 64


def test_optional_diagnostic_validation_is_not_silently_ignored():
    cfg = {'model': {'name': 'fixture'}, 'output_dir': 'run', 'methods': ['plain'],
           'data': {s: s for s in ('train', 'calibration', 'validation', 'eval')},
           'diagnostics': {'transfer_gap': {'enabled': True}}}
    with pytest.raises(ValueError, match='transfer_gap'):
        pipeline.validate_config(cfg)
