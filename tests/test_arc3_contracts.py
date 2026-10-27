"""Software contracts only; these fixtures are not scientific ARC evaluation."""
import json
from types import SimpleNamespace

import pytest

from improving.arc3 import encode_frames, observation, parse_action, prompt_for
from improving.arc3_study import _reference_events, task_for


def native_observation(frames=None, state='NOT_FINISHED'):
    return SimpleNamespace(game_id='ab12-version', state=state, levels_completed=0,
                           win_levels=1, available_actions=[1, 6, 7],
                           frame=frames if frames is not None else [[[1, 1], [0, 2]]])


def test_every_animation_frame_round_trips_in_lossless_rle():
    frames = [[[1, 1, 1], [2, 0, 0]], [[15, 15, 0], [3, 3, 3]]]
    encoded = encode_frames(frames)
    decoded, active = [], None
    for line in encoded.splitlines():
        if line.startswith('frame='):
            active = []
            decoded.append(active)
        else:
            row = []
            for pair in line.split(','):
                color, count = pair.split(':')
                row.extend([int(color, 16)] * int(count))
            active.append(row)
    assert decoded == frames
    assert 'frame=0 width=3 height=2' in encoded
    assert 'frame=1 width=3 height=2' in encoded


@pytest.mark.parametrize('completion', [
    'ACTION1', '{"action":"ACTION2"}', '{"action":"RESET"}',
    '{"action":"ACTION6","x":64,"y":0}',
    '{"action":"ACTION6","x":true,"y":0}',
    '{"action":"ACTION1","x":0}',
    '{"action":"ACTION7","explanation":"undo"}',
    '```json\n{"action":"ACTION1"}\n```',
])
def test_invalid_outputs_are_rejected_without_fallback(completion):
    with pytest.raises((ValueError, TypeError)):
        parse_action(completion, observation(native_observation()))


def test_click_coordinates_and_game_over_reset_contract():
    current = observation(native_observation())
    assert parse_action('{"action":"ACTION6","x":63,"y":0}', current) == ('ACTION6', {'x': 63, 'y': 0})
    assert parse_action('{"action":"ACTION7"}', current) == ('ACTION7', {})
    over = observation(native_observation(state='GAME_OVER'))
    assert parse_action('{"action":"RESET"}', over) == ('RESET', {})
    with pytest.raises(ValueError):
        parse_action('{"action":"ACTION1"}', over)


def test_policy_observation_excludes_privileged_metadata():
    raw = native_observation()
    raw.baseline_actions = [2]
    raw.private_tags = ['hidden-rule']
    raw.source_code = 'private simulator source'
    visible = observation(raw)
    prompt = prompt_for(visible, [], 3)
    assert 'baseline_actions' not in visible
    assert 'hidden-rule' not in prompt and 'private simulator source' not in prompt


def test_evaluation_trajectory_preserves_its_split():
    config = {'history_steps': 3, 'chat_template_kwargs': {'enable_thinking': False}}
    task = task_for(config, 'ab12-version', 0, 0, observation(native_observation()), [], 'eval')
    assert task['split'] == 'eval'


def test_reference_cannot_use_eval_game():
    event = {'before': observation(native_observation())}
    with pytest.raises(ValueError, match='calibration game split'):
        _reference_events({}, {'splits': {'calibration': ['zz99-version']}}, [event], seed=0)


def test_reference_replay_rejects_changed_native_transition(monkeypatch):
    before = observation(native_observation())
    expected = observation(native_observation(frames=[[[4, 4], [4, 4]]], state='WIN'))
    actual = observation(native_observation(frames=[[[3, 3], [3, 3]]], state='WIN'))
    event = {'before': before, 'after': expected, 'action': 'ACTION1', 'action_data': {}}
    arcade = SimpleNamespace(create_scorecard=lambda **kwargs: 'fixture-card',
                             make=lambda *args, **kwargs: SimpleNamespace(observation_space=native_observation()))
    monkeypatch.setattr('improving.arc3_study.make_arcade', lambda *args: arcade)
    monkeypatch.setattr('improving.arc3_study._step', lambda *args: actual)
    config = {'data_dir': '.', 'history_steps': 3, 'chat_template_kwargs': {'enable_thinking': False}}
    with pytest.raises(ValueError, match='transition mismatch'):
        _reference_events(config, {'splits': {'calibration': ['ab12-version']}}, [event], seed=0)
