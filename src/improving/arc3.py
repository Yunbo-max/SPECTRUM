"""ARC-AGI-3 native SDK boundary, lossless observations and strict actions.

No game engine or model is imported at module import time. Preparation and play
belong to the admitted native host. This module never executes model output.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re

from .utils import atomic_json, stable_hash

SDK_COMMIT = 'f12822c4d550121c35a275008d964afbbed47d2f'
ENGINE_COMMIT = 'b495c6acaf253c9681cd7b75c4299d352e9ce6f8'
PROTOCOL = 'arc3-lossless-rle-action-json-v1'


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def sdk_identity():
    result = {}
    for package, version, commit in [('arc-agi', '0.9.9', SDK_COMMIT),
                                     ('arcengine', '0.9.3', ENGINE_COMMIT)]:
        distribution = importlib.metadata.distribution(package)
        if distribution.version != version:
            raise ValueError(f'{package} must be {version}; reinstall the pinned source')
        direct = json.loads(distribution.read_text('direct_url.json') or '{}')
        if direct.get('vcs_info', {}).get('commit_id') != commit:
            raise ValueError(f'{package} must be installed from the pinned Git commit {commit}')
        source_files = {str(path): file_hash(distribution.locate_file(path))
                        for path in (distribution.files or []) if str(path).endswith('.py')}
        if not source_files:
            raise ValueError(f'{package} installation has no verifiable Python source files')
        result[package] = {'version': version, 'commit': commit,
                           'installed_python_sha256': stable_hash(source_files)}
    return result


def plain(value):
    if hasattr(value, 'model_dump'):
        return plain(value.model_dump())
    if hasattr(value, 'tolist'):
        return plain(value.tolist())
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items() if k != 'api_key'}
    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]
    if hasattr(value, 'value'):
        return plain(value.value)
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def observation(response):
    """Expose only the native observation, never source, tags or human actions."""
    if response is None:
        raise RuntimeError('ARC SDK returned no observation; preserve this failed attempt')
    state = getattr(response.state, 'name', str(response.state))
    frames = plain(response.frame)
    if not isinstance(frames, list) or not frames:
        raise ValueError('ARC response must contain all native animation frames')
    for frame in frames:
        if not frame or len(frame) > 64 or not frame[0] or len(frame[0]) > 64:
            raise ValueError('ARC frame shape is outside the native 1..64 grid')
        if any(len(row) != len(frame[0]) or any(type(c) is not int or not 0 <= c <= 15
                                               for c in row) for row in frame):
            raise ValueError('ARC frame must be a rectangular integer grid in 0..15')
    available = [int(getattr(a, 'value', a)) for a in response.available_actions]
    return {'game_id': response.game_id, 'state': state,
            'levels_completed': int(response.levels_completed),
            'win_levels': int(response.win_levels), 'available_actions': available,
            'frames': frames}


def encode_frames(frames):
    """Run-length encoding of every row of every frame; no crops or resampling."""
    out = []
    for index, frame in enumerate(frames):
        rows = []
        for row in frame:
            runs = []
            for value in row:
                if runs and runs[-1][0] == value:
                    runs[-1][1] += 1
                else:
                    runs.append([value, 1])
            rows.append(','.join(f'{color:x}:{count}' for color, count in runs))
        out.append(f'frame={index} width={len(frame[0])} height={len(frame)}\n' + '\n'.join(rows))
    return '\n'.join(out)


def prompt_for(obs, history, history_steps):
    preamble = (
        'Explore this unfamiliar interactive grid game and complete its levels. Infer the rules '
        'from observations. Return exactly one JSON object, no explanation or code fence. '
        'Use {"action":"ACTION1"} (or another available ACTION), '
        '{"action":"ACTION6","x":0,"y":0} for a click, or {"action":"RESET"} '
        'only after GAME_OVER. Coordinates are x=column, y=row, top-left (0,0), range 0..63. '
        'Actions 1..5 have game-dependent meanings; ACTION7 is undo. '
        'Frames are losslessly encoded row by row: hexadecimal color:repeat_count. '
        'All frames of each observation appear in chronological order.\n')
    parts = [preamble]
    for event in history[-history_steps:] if history_steps else []:
        parts.append('PREVIOUS OBSERVATION\n' + visible_text(event['before']))
        parts.append('PREVIOUS RESPONSE\n' + event['record']['completion'])
        parts.append('INTERFACE RESULT\n' + event.get('interface_error', 'action accepted'))
    parts.append('CURRENT OBSERVATION\n' + visible_text(obs))
    return '\n'.join(parts)


def visible_text(obs):
    metadata = {k: obs[k] for k in ('state', 'levels_completed', 'win_levels', 'available_actions')}
    return json.dumps(metadata, separators=(',', ':')) + '\n' + encode_frames(obs['frames'])


def parse_action(completion, obs):
    value = json.loads(completion)
    if not isinstance(value, dict) or not isinstance(value.get('action'), str):
        raise ValueError('Expected one JSON object with string action')
    action = value['action']
    if action == 'RESET':
        if set(value) != {'action'} or obs['state'] != 'GAME_OVER':
            raise ValueError('RESET is permitted only after GAME_OVER')
        return action, {}
    if not re.fullmatch(r'ACTION[1-7]', action):
        raise ValueError('Action must be ACTION1..ACTION7 or RESET')
    if obs['state'] == 'GAME_OVER' or int(action[-1]) not in obs['available_actions']:
        raise ValueError('Action is not currently available')
    if action == 'ACTION6':
        if set(value) != {'action', 'x', 'y'} or any(type(value.get(k)) is not int or
                                                   not 0 <= value[k] <= 63 for k in ('x', 'y')):
            raise ValueError('ACTION6 requires integer x,y in 0..63')
        return action, {k: value[k] for k in ('x', 'y')}
    if set(value) != {'action'}:
        raise ValueError('Simple actions accept no extra fields')
    return action, {}


def canonical_action(action_input):
    action = action_input['id']
    if type(action) is int:
        action = 'RESET' if action == 0 else f'ACTION{action}'
    data = action_input.get('data') or {}
    return json.dumps({'action': action, **({k: data[k] for k in ('x', 'y')}
                                           if action == 'ACTION6' else {})}, separators=(',', ':'))


def load_config(path):
    config = json.loads(Path(path).read_text())
    if config.get('protocol') != PROTOCOL or config.get('operation_mode') != 'OFFLINE':
        raise ValueError('This frozen study uses OFFLINE native SDK scorecards only')
    if config['train'].get('loss_scope') != 'completion':
        raise ValueError('ARC trajectory SFT must supervise action completions only')
    if config.get('rounds') != 5 or config.get('methods') != ['plain', 'ssd', 'spectral_soft']:
        raise ValueError('Change the explicit protocol version before changing the study matrix')
    return config


def prepare(config, split_file=None):
    """Acquire through the official SDK, then pin exact versions and local bytes.

    SDK make() initializes trusted native game code; execute this preparation on
    the admitted host. It never loads an LLM or chooses an action.
    """
    from arc_agi import Arcade, OperationMode, LocalEnvironmentWrapper
    identity = sdk_identity()
    root = Path(config['data_dir'])
    lock = root / 'assets.lock.json'
    if lock.exists():
        if split_file is not None:
            raise ValueError('An explicit new split requires a new data_dir; existing split is frozen')
        return verify_assets(config)
    split_request = json.loads(Path(split_file).read_text()) if split_file else config['games']
    if set(split_request) != {'train', 'calibration', 'eval'}:
        raise ValueError('Splits must be exactly train/calibration/eval; development reuses train')
    all_ids = [g for names in split_request.values() for g in names]
    if any(not names for names in split_request.values()) or len({g.split('-')[0] for g in all_ids}) != len(all_ids):
        raise ValueError('Game families must be nonempty and disjoint across all three splits')
    arc = Arcade(operation_mode=OperationMode.NORMAL,
                 environments_dir=str(root / 'environment_files'),
                 recordings_dir=str(root / 'preparation-recordings'))
    catalog = {e.game_id: e for e in arc.get_environments()}
    resolved = {}
    for requested in all_ids:
        matches = [name for name in catalog if name == requested or name.startswith(requested + '-')]
        if len(matches) != 1 or '-' not in matches[0]:
            raise ValueError(f'{requested}: need exactly one versioned official game; available matches {matches}')
        resolved[requested] = matches[0]
    card = arc.create_scorecard(tags=['spectrum-assets-only'])
    files, games = {}, {}
    try:
        for requested, full_id in resolved.items():
            env = arc.make(full_id, scorecard_id=card, save_recording=False)
            if not isinstance(env, LocalEnvironmentWrapper) or env.info.game_id != full_id:
                raise RuntimeError(f'{full_id}: local acquisition failed or game version changed')
            observation(env.observation_space)
            metadata = plain(env.info)
            if not metadata.get('baseline_actions') or any(type(x) is not int or x <= 0 for x in metadata['baseline_actions']):
                raise ValueError(f'{full_id}: official human baseline actions missing; native RHAE is unqualified')
            game_dir = Path(env.info.local_dir)
            local_files = sorted(p for p in game_dir.rglob('*') if p.is_file() and p.suffix in {'.json', '.py'})
            if not any(p.suffix == '.py' for p in local_files):
                raise ValueError(f'{full_id}: native game source is missing')
            for path in local_files:
                files[str(path.relative_to(root))] = {'sha256': file_hash(path), 'bytes': path.stat().st_size}
            games[full_id] = {'metadata': metadata, 'source_url': f'https://three.arcprize.org/api/games/{full_id}/source'}
    finally:
        arc.close_scorecard(card)
    manifest = {'format': 1, 'protocol': PROTOCOL, 'sdk': identity, 'games': games,
                'config_games': config['games'], 'requested_splits': split_request,
                'splits': {split: [resolved[g] for g in names] for split, names in split_request.items()},
                'development_split': 'train', 'files': files,
                'scope': 'frozen_public_game_holdout; not official hidden-test or leaderboard score'}
    atomic_json(lock, manifest)
    return manifest


def verify_assets(config):
    root = Path(config['data_dir'])
    manifest = json.loads((root / 'assets.lock.json').read_text())
    if manifest['sdk'] != sdk_identity() or manifest['protocol'] != PROTOCOL:
        raise ValueError('ARC SDK/protocol differs from the frozen assets')
    if manifest.get('config_games') != config['games']:
        raise ValueError('Configured game selection changed; use a new data_dir')
    groups = manifest['splits']
    ids = [game for games in groups.values() for game in games]
    if set(groups) != {'train', 'calibration', 'eval'} or any(not x for x in groups.values()) or len({x.split('-')[0] for x in ids}) != len(ids):
        raise ValueError('Frozen ARC split is not game-family disjoint')
    for relative, expected in manifest['files'].items():
        path = root / relative
        if path.resolve().is_relative_to(root.resolve()) is False or file_hash(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError(f'ARC asset identity changed: {relative}')
    return manifest


def make_arcade(config, recordings):
    from arc_agi import Arcade, OperationMode
    # Do not let an inherited environment variable change RESET semantics.
    if os.getenv('ONLY_RESET_LEVELS', '').lower() not in {'', 'false'}:
        raise ValueError('Unset ONLY_RESET_LEVELS for the frozen native RESET protocol')
    return Arcade(operation_mode=OperationMode.OFFLINE,
                  environments_dir=str(Path(config['data_dir']) / 'environment_files'),
                  recordings_dir=str(recordings))
