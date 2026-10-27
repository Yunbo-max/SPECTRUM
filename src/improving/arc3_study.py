"""Finite, resumable native ARC-AGI-3 trajectories and recursive action SFT."""
from __future__ import annotations

from contextlib import nullcontext
import json
import fcntl
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

from .arc3 import (PROTOCOL, canonical_action, file_hash, load_config, make_arcade,
                   observation, parse_action, plain, prompt_for, verify_assets)
from .data import read_jsonl, write_jsonl
from .utils import atomic_json, stable_hash


def private_seed(config):
    value = json.loads(Path(config['seed_file']).read_text())
    seed = value.get('seed')
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('Private seed file must contain one integer seed in [0,2**31)')
    return seed


def source_identity():
    paths = sorted(Path(__file__).parent.glob('*.py'))
    return {p.name: file_hash(p) for p in paths}


def bind(config, assets, root, *, resume):
    from huggingface_hub import snapshot_download
    from .pipeline import checkpoint_fingerprint, training_runtime_identity
    snapshot = Path(snapshot_download(repo_id=config['model']['name'],
                                     revision=config['model']['revision'], local_files_only=True))
    indices = list(snapshot.glob('*.safetensors.index.json'))
    if not indices:
        raise ValueError('ARC original model needs the complete pinned sharded HF snapshot')
    for index in indices:
        names = set(json.loads(index.read_text())['weight_map'].values())
        if any(not (snapshot / name).is_file() for name in names):
            raise ValueError('ARC original model is missing a referenced weight shard')
    identity = {'protocol': PROTOCOL, 'config': config, 'assets': stable_hash(assets),
                'seed_file_sha256': file_hash(config['seed_file']),
                'sources': source_identity(), 'runtime': training_runtime_identity(),
                'base_checkpoint_identity': checkpoint_fingerprint(snapshot)}
    # Freeze all methods, development baselines and reference collection against
    # one study. References are deliberately not part of assets.lock: they are
    # acquired after baseline qualification and separately bound to SPECTRUM.
    study_root = Path(config['output_dir'])
    study_root.mkdir(parents=True, exist_ok=True)
    with (study_root / '.study.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        study_path = study_root / 'study_manifest.json'
        if study_path.exists():
            if json.loads(study_path.read_text()) != identity:
                raise ValueError('ARC methods/baselines/reference collection must share identical source/config/assets/model bytes/runtime; use a new output_dir')
        else:
            atomic_json(study_path, identity)
    destination = Path(root) / 'manifest.json'
    if destination.exists():
        if not resume or json.loads(destination.read_text()) != identity:
            raise ValueError('ARC run exists or source/config/assets/runtime changed; use matching --resume or a new output_dir')
    else:
        if Path(root).exists() and any(Path(root).iterdir()):
            raise ValueError('ARC output directory is nonempty without a manifest')
        atomic_json(destination, identity)
    return stable_hash(identity)


def task_for(config, game_id, episode, decision, before, history, split):
    return {'task_id': f'ARC3/{game_id}/episode-{episode}/decision-{decision}',
            'prompt': prompt_for(before, history, config['history_steps']),
            'source': 'arcprize/ARC-AGI-3', 'split': split,
            'chat_template_kwargs': config['chat_template_kwargs']}


def _step(env, name, data):
    from arcengine import GameAction
    return observation(env.step(GameAction[name], data=data))


def rollout(model, tokenizer, config, game_id, directory, *, seed, identity,
            method, round_index, episode, generation, resume, split):
    """Replay a partial local episode, then continue; invalid outputs consume a decision.

    Every raw model completion is saved and becomes an SFT record. Invalid JSON
    or unavailable actions do not cause a hidden retry or fabricated environment
    action. They receive explicit interface feedback within the fixed decision cap.
    """
    from .generation import generate_to_file
    directory = Path(directory)
    signature = {'model': identity, 'game': game_id, 'method': method, 'round': round_index,
                 'episode': episode, 'generation': generation, 'seed': seed,
                 'split': split,
                 'protocol': PROTOCOL, 'history_steps': config['history_steps'],
                 'caps': config['budgets']}
    progress_path = directory / 'progress.json'
    complete = directory / 'complete.json'
    progress = {'signature': signature, 'events': [], 'elapsed_seconds': 0.0}
    if progress_path.exists():
        if not resume:
            raise FileExistsError(f'Use --resume for {directory}')
        progress = json.loads(progress_path.read_text())
        if progress['signature'] != signature:
            raise ValueError('ARC episode identity changed')
    elif directory.exists() and any(directory.iterdir()):
        raise ValueError('ARC episode files exist without progress identity')
    if complete.exists():
        result = json.loads(complete.read_text())
        if result['progress_sha256'] != file_hash(progress_path) or result['scorecard_sha256'] != file_hash(directory / 'scorecard.json'):
            raise ValueError('Completed ARC episode artifacts changed')
        return progress['events'], result
    atomic_json(progress_path, progress)
    arc = make_arcade(config, directory / 'native_recordings')
    card = arc.create_scorecard(tags=['spectrum', method, f'round-{round_index}'])
    env = arc.make(game_id, seed=seed, scorecard_id=card, save_recording=True,
                   include_frame_data=True)
    if env is None:
        raise RuntimeError(f'Could not initialize frozen game {game_id}')
    current = observation(env.observation_space)  # make() already RESETs once.
    successful_actions = 0
    for event in progress['events']:
        if stable_hash(current) != stable_hash(event['before']):
            raise ValueError('Native ARC replay disagrees before a saved action')
        if event['action'] is not None:
            current = _step(env, event['action'], event['action_data'])
            successful_actions += 1
        if stable_hash(current) != stable_hash(event['after']):
            raise ValueError('Native ARC replay disagrees after a saved action')
    started = time.monotonic()
    previous_elapsed = progress['elapsed_seconds']
    status = 'decision_budget'
    try:
        while len(progress['events']) < config['budgets']['max_decisions']:
            if current['state'] == 'WIN':
                status = 'win'
                break
            if successful_actions >= config['budgets']['max_actions']:
                status = 'action_budget'
                break
            if previous_elapsed + time.monotonic() - started >= config['budgets']['max_seconds_per_episode']:
                status = 'wall_budget'
                break
            index = len(progress['events'])
            task = task_for(config, game_id, episode, index, current, progress['events'], split)
            rows = generate_to_file(model, tokenizer, [task],
                                    directory / f'decision-{index:05d}' / 'raw.jsonl',
                                    {**generation, 'samples': 1, 'batch_size': 1,
                                     'task_batch_size': 1, 'sequence_batch_size': 1},
                                    seed=seed, model_identity=identity, method=method,
                                    round_index=round_index, stage='arc_action', resume=resume)
            record = rows[0]
            before, action, action_data, error = current, None, {}, None
            try:
                action, action_data = parse_action(record['completion'], before)
            except (ValueError, TypeError, KeyError) as exc:
                error = str(exc)
            if action is not None:
                current = _step(env, action, action_data)
                successful_actions += 1
            event = {'task': task, 'record': record, 'before': before, 'after': current,
                     'action': action, 'action_data': action_data}
            if error:
                event['interface_error'] = error
            progress['events'].append(event)
            progress['elapsed_seconds'] = previous_elapsed + time.monotonic() - started
            atomic_json(progress_path, progress)
        if current['state'] == 'WIN':
            status = 'win'
        scorecard = arc.close_scorecard(card)
        if scorecard is None:
            raise RuntimeError('Native ARC scorecard is missing; no substitute score is calculated')
        scorecard = plain(scorecard)
        if not isinstance(scorecard.get('score'), (float, int)):
            raise ValueError('Native ARC scorecard did not supply a numerical score')
        atomic_json(directory / 'scorecard.json', scorecard)
        write_jsonl(directory / 'tasks.jsonl', [e['task'] for e in progress['events']])
        write_jsonl(directory / 'raw.jsonl', [e['record'] for e in progress['events']])
        valid_actions = [json.dumps(e['action'], sort_keys=True, ensure_ascii=False)
                         for e in progress['events'] if e['action'] is not None]
        result = {'status': status, 'game_id': game_id, 'episode': episode,
                  'native_score': scorecard['score'], 'levels_completed': current['levels_completed'],
                  'win_levels': current['win_levels'], 'environment_actions': successful_actions,
                  'model_decisions': len(progress['events']),
                  'invalid_outputs': sum(e['action'] is None for e in progress['events']),
                  'valid_actions': valid_actions,
                  'prompt_tokens': sum(e['record']['prompt_tokens'] for e in progress['events']),
                  'generation_tokens': sum(e['record']['generation_tokens'] for e in progress['events']),
                  'elapsed_seconds': progress['elapsed_seconds'],
                  'progress_sha256': file_hash(progress_path),
                  'scorecard_sha256': file_hash(directory / 'scorecard.json'),
                  'score_scope': 'single frozen public game, native SDK RHAE; not leaderboard'}
        atomic_json(complete, result)
        return progress['events'], result
    except BaseException as exc:
        atomic_json(directory / 'failure.json', {'error_type': type(exc).__name__,
                                               'error': str(exc), 'complete': False})
        raise


def evaluate(model, tokenizer, config, assets, root, *, identity, method, round_index,
             seed, split, episodes, generation, resume):
    results, all_tasks, all_records = [], [], []
    for game_id in assets['splits'][split]:
        for episode in range(episodes):
            # One private randomization, matching native game seed across methods.
            game_seed = int(stable_hash([seed, game_id, episode, split])[:8], 16)
            events, result = rollout(model, tokenizer, config, game_id,
                                    Path(root) / game_id / f'episode-{episode}', seed=game_seed,
                                    identity=identity, method=method, round_index=round_index,
                                    episode=episode, generation=generation, resume=resume, split=split)
            results.append(result)
            all_tasks.extend(e['task'] for e in events)
            all_records.extend(e['record'] for e in events)
    expected = len(assets['splits'][split]) * episodes
    if len(results) != expected:
        raise ValueError('Incomplete native ARC denominator')
    # Action-sequence diversity: per-episode valid-action trajectories, distinct
    # action types, and the realized sequence length. Action keys use a canonical
    # JSON representation so distinct coordinates/arguments remain distinguishable.
    action_sequences, distinct_actions, action_lengths = [], set(), []
    for r in results:
        episode_actions = r.get('valid_actions', [])
        action_sequences.append(episode_actions)
        distinct_actions.update(episode_actions)
        action_lengths.append(len(episode_actions))
    summary = {'split': split, 'games': assets['splits'][split], 'episodes': expected,
               'mean_native_score': sum(r['native_score'] for r in results) / expected,
               'wins': sum(r['status'] == 'win' for r in results),
               'results': results, 'missing': [],
               'action_diversity': {
                   'distinct_action_types': len(distinct_actions),
                   'mean_actions_per_episode': sum(action_lengths) / expected if expected else 0.0,
                   'total_valid_actions': sum(action_lengths),
                   'definition': 'distinct canonical actions across all episodes; sequence-level variety of valid native actions'},
               'score_scope': 'public game holdout; each episode uses its own native scorecard'}
    atomic_json(Path(root) / 'summary.json', summary)
    return all_tasks, all_records, summary


def verify_evaluation_evidence(directory):
    """A summary file alone is not a complete native episode receipt."""
    directory = Path(directory)
    summary = json.loads((directory / 'summary.json').read_text())
    if len(summary['results']) != summary['episodes'] or summary.get('missing'):
        raise ValueError('ARC evaluation denominator is incomplete')
    for result in summary['results']:
        episode = directory / result['game_id'] / f"episode-{result['episode']}"
        if (file_hash(episode / 'progress.json') != result['progress_sha256'] or
                file_hash(episode / 'scorecard.json') != result['scorecard_sha256'] or
                json.loads((episode / 'complete.json').read_text()) != result):
            raise ValueError('ARC native episode evidence changed beneath its summary')


def _reference_events(config, assets, events, *, seed):
    """Independently replay a complete calibration-game win before accepting labels."""
    if not events:
        raise ValueError('Reference trajectory is empty')
    game_id = events[0]['before']['game_id']
    if game_id not in assets['splits']['calibration']:
        raise ValueError('Reference trajectory must belong to the frozen calibration game split')
    arc = make_arcade(config, Path(config['data_dir']) / 'reference-replay-recordings')
    card = arc.create_scorecard(tags=['spectrum-reference-validation'])
    env = arc.make(game_id, seed=seed, scorecard_id=card, save_recording=True, include_frame_data=True)
    if env is None:
        raise RuntimeError('Cannot replay reference game')
    current = observation(env.observation_space)
    history, tasks = [], []
    for index, event in enumerate(events):
        if stable_hash(current) != stable_hash(event['before']):
            raise ValueError('Reference replay observation mismatch')
        # A reference has to be a real native action, with no malformed outputs.
        completion = json.dumps({'action': event['action'], **event['action_data']}, separators=(',', ':'))
        action, data = parse_action(completion, current)
        task = task_for(config, game_id, 0, index, current, history, 'calibration')
        task.update(task_id=f'ARC3-reference/{game_id}/{index}', split='calibration',
                    reference=completion, reference_origin='native_replayed_successful_trajectory')
        next_obs = _step(env, action, data)
        if stable_hash(next_obs) != stable_hash(event['after']):
            raise ValueError('Reference replay transition mismatch')
        tasks.append(task)
        # Use the same canonical JSON history during calibration and replay.
        history.append({**event, 'record': {'completion': completion}})
        current = next_obs
    if current['state'] != 'WIN':
        raise ValueError('Reference must finish a complete native game; no optimality is inferred')
    score = plain(arc.close_scorecard(card))
    if not score or 'score' not in score:
        raise ValueError('Native reference replay scorecard missing')
    return tasks, score


def save_reference(config, assets, events, *, seed, origin):
    root = Path(config['data_dir'])
    destination = root / 'calibration.jsonl'
    if destination.exists() or (root / 'calibration.lock.json').exists():
        raise FileExistsError('Fixed calibration reference exists; use a new data_dir to replace it')
    tasks, score = _reference_events(config, assets, events, seed=seed)
    write_jsonl(destination, tasks)
    atomic_json(root / 'calibration.lock.json', {
        'assets_sha256': stable_hash(assets), 'protocol': PROTOCOL,
        'chat_template_kwargs': config['chat_template_kwargs'], 'history_steps': config['history_steps'],
        'reference_sha256': file_hash(destination), 'tasks': len(tasks), 'origin': origin,
        'native_replay_scorecard': score, 'seed': seed,
        'label_claim': 'actions in a complete successful native replay; not optimal actions',
        'synthetic_training_filtering': False})


def collect_reference(config, *, resume=False):
    from .modeling import load_model
    assets = verify_assets(config)
    root = Path(config['output_dir']) / 'reference-collection'
    identity = bind(config, assets, root, resume=resume)
    model, tokenizer = load_model(config['model'])
    seed = private_seed(config)
    # A single bounded attempt per frozen calibration game. No eval-derived search.
    for game_id in assets['splits']['calibration']:
        game_seed = int(stable_hash([seed, game_id, 0, 'calibration'])[:8], 16)
        events, result = rollout(model, tokenizer, config, game_id, root / game_id,
                                seed=game_seed, identity=identity, method='base', round_index=0,
                                episode=0, generation=config['generation'], resume=resume, split='calibration')
        if result['status'] == 'win' and result['invalid_outputs'] == 0:
            save_reference(config, assets, events, seed=game_seed,
                           origin={'kind': 'base_calibration_play', 'progress_sha256': result['progress_sha256']})
            return
    raise RuntimeError('No complete valid calibration-game win. Raw attempts are retained. '
                       'Provide a human successful recording with import-reference; do not use eval games.')


def import_reference(config, recording, *, game_seed):
    assets = verify_assets(config)
    rows = read_jsonl(recording)
    if len(rows) < 2:
        raise ValueError('Official recording needs initial RESET plus action transitions')
    observations = []
    for row in rows:
        data = row['data']
        observations.append(observation(SimpleNamespace(**data)))
    first_action = canonical_action(rows[0]['data']['action_input'])
    if json.loads(first_action)['action'] != 'RESET':
        raise ValueError('Official recording must begin with RESET')
    events = []
    for index, row in enumerate(rows[1:]):
        completion = canonical_action(row['data']['action_input'])
        action, data = parse_action(completion, observations[index])
        events.append({'before': observations[index], 'after': observations[index + 1],
                       'action': action, 'action_data': data, 'record': {'completion': completion}})
    save_reference(config, assets, events, seed=game_seed,
                   origin={'kind': 'external_official_sdk_recording', 'sha256': file_hash(recording)})


def calibration_tasks(config, assets):
    root = Path(config['data_dir'])
    lock = json.loads((root / 'calibration.lock.json').read_text())
    if (lock['assets_sha256'] != stable_hash(assets) or
            lock['reference_sha256'] != file_hash(root / 'calibration.jsonl') or
            lock['protocol'] != PROTOCOL or lock['history_steps'] != config['history_steps'] or
            lock['chat_template_kwargs'] != config['chat_template_kwargs']):
        raise ValueError('Frozen calibration reference or rendering protocol changed')
    tasks = read_jsonl(root / 'calibration.jsonl')
    if len(tasks) != lock['tasks'] or any(t.get('split') != 'calibration' or
                                         t.get('reference_origin') != 'native_replayed_successful_trajectory'
                                         for t in tasks):
        raise ValueError('Invalid calibration reference records')
    return tasks


def run(config, *, method, resume=False, baseline_split='train'):
    from .modeling import load_model
    from .pipeline import _calibrate, checkpoint_fingerprint
    from .spectral import folded_operators, make_operator
    from .training import train_on_records
    assets = verify_assets(config)
    if method not in ['base', *config['methods']]:
        raise ValueError('Unknown ARC method')
    root = Path(config['output_dir']) / (f'baseline-{baseline_split}' if method == 'base' else method)
    run_identity = bind(config, assets, root, resume=resume)
    seed = private_seed(config)
    references = calibration_tasks(config, assets) if method == 'spectral_soft' else None
    if references is not None:
        reference_lock = {'sha256': file_hash(Path(config['data_dir']) / 'calibration.lock.json')}
        path = root / 'reference-binding.json'
        if path.exists() and json.loads(path.read_text()) != reference_lock:
            raise ValueError('ARC calibration reference changed after run creation')
        atomic_json(path, reference_lock)
    identity = stable_hash([run_identity, config['model']])
    if method == 'base':
        model, tokenizer = load_model(config['model'])
        return evaluate(model, tokenizer, config, assets, root / 'evaluation', identity=identity,
                        method='base', round_index=0, seed=seed, split=baseline_split, episodes=1,
                        generation=config['generation'], resume=resume)[2]
    # Completed old rounds remain auditable after explicitly recorded checkpoint
    # pruning. Resume from the latest sealed round, never regenerate an old round.
    start_round, start_checkpoint = 1, None
    for index in range(1, config['rounds'] + 1):
        directory = root / f'round-{index}'
        seal_path = directory / 'complete.json'
        if not seal_path.exists():
            break
        seal = json.loads(seal_path.read_text())
        receipt = json.loads((directory / 'trained.json').read_text())
        if (receipt['parent_identity'] != identity or
                seal['trained_sha256'] != file_hash(directory / 'trained.json') or
                seal['evaluation_sha256'] != file_hash(directory / 'evaluation' / 'summary.json') or
                seal['tasks_sha256'] != file_hash(directory / 'synthesis-tasks.jsonl') or
                seal['raw_sha256'] != file_hash(directory / 'synthesis-raw.jsonl')):
            raise ValueError('Sealed ARC round lineage or raw evidence changed')
        verify_evaluation_evidence(directory / 'evaluation')
        if not (directory / 'model').exists():
            prune_path = directory / 'pruned.json'
            descendant_seal = root / f'round-{index + 1}' / 'complete.json'
            if not prune_path.exists() or not descendant_seal.exists():
                raise ValueError('Missing ARC checkpoint has no sealed pruning record')
            prune = json.loads(prune_path.read_text())
            if (prune['checkpoint'] != receipt['checkpoint'] or
                    prune['replaced_by_round'] != index + 1 or
                    prune['replacement_seal'] != stable_hash(json.loads(descendant_seal.read_text()))):
                raise ValueError('ARC checkpoint pruning record does not match its sealed descendant')
        identity = receipt['next_identity']
        start_round, start_checkpoint = index + 1, directory / 'model'
    if start_checkpoint is not None:
        receipt = json.loads((start_checkpoint.parent / 'trained.json').read_text())
        if receipt['checkpoint'] != checkpoint_fingerprint(start_checkpoint):
            raise ValueError('Latest ARC checkpoint is missing or changed')
    if start_round > config['rounds']:
        result = {'status': 'complete', 'method': method, 'rounds': config['rounds'],
                  'run_identity': run_identity}
        atomic_json(root / 'complete.json', result)
        return result
    model, tokenizer = load_model(config['model'], checkpoint=start_checkpoint)
    if start_round == 1:
        evaluate(model, tokenizer, config, assets, root / 'round-0' / 'evaluation', identity=identity,
                 method=method, round_index=0, seed=seed, split='eval', episodes=1,
                 generation=config['generation'], resume=resume)
    for round_index in range(start_round, config['rounds'] + 1):
        current = root / f'round-{round_index}'
        checkpoint = current / 'model'
        trained = current / 'trained.json'
        if trained.exists():
            receipt = json.loads(trained.read_text())
            if receipt['parent_identity'] != identity or receipt['checkpoint'] != checkpoint_fingerprint(checkpoint):
                raise ValueError('ARC checkpoint parent/content changed')
            del model
            import gc
            import torch
            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            model, tokenizer = load_model(config['model'], checkpoint=checkpoint)
            identity = receipt['next_identity']
        else:
            if checkpoint.exists():
                raise ValueError('Unsealed ARC checkpoint exists; retain it for interrupted-save diagnosis')
            operators = {}
            if method == 'spectral_soft':
                moments = _calibrate(model, tokenizer, references, config['calibration'],
                                     current / 'calibration.pt', identity)
                operators = {name: make_operator(value['covariance'], kind='spectral_soft',
                                                 tau=config['spectral']['tau'])
                             for name, value in moments.items()}
            generation = config['ssd_generation'] if method == 'ssd' else config['generation']
            with folded_operators(model, operators) if operators else nullcontext():
                tasks, records, _ = evaluate(model, tokenizer, config, assets,
                                             current / 'synthesis', identity=identity, method=method,
                                             round_index=round_index, seed=seed, split='train',
                                             episodes=config['train_episodes_per_game'],
                                             generation=generation, resume=resume)
            if not tasks or len(tasks) != len(records):
                raise ValueError('No complete ARC action corpus; nothing was filtered')
            write_jsonl(current / 'synthesis-tasks.jsonl', tasks)
            write_jsonl(current / 'synthesis-raw.jsonl', records)
            # Every generated action attempt, including invalid JSON, is retained.
            model, stats = train_on_records(model, tokenizer, tasks, records,
                                             config['train'], checkpoint, seed=seed)
            fingerprint = checkpoint_fingerprint(checkpoint)
            next_identity = stable_hash([run_identity, method, round_index, fingerprint])
            atomic_json(trained, {'parent_identity': identity, 'next_identity': next_identity,
                                 'checkpoint': fingerprint, 'raw_record_count': len(records),
                                 'training_stats': stats, 'quality_filtering': False})
            identity = next_identity
        evaluate(model, tokenizer, config, assets, current / 'evaluation', identity=identity,
                 method=method, round_index=round_index, seed=seed, split='eval', episodes=1,
                 generation=config['generation'], resume=resume)
        seal = {'trained_sha256': file_hash(trained),
                'evaluation_sha256': file_hash(current / 'evaluation' / 'summary.json'),
                'tasks_sha256': file_hash(current / 'synthesis-tasks.jsonl'),
                'raw_sha256': file_hash(current / 'synthesis-raw.jsonl')}
        atomic_json(current / 'complete.json', seal)
        if config.get('checkpoint_retention') == 'latest' and round_index > 1:
            previous = root / f'round-{round_index - 1}'
            old_model = previous / 'model'
            if old_model.exists():
                old_receipt = json.loads((previous / 'trained.json').read_text())
                if not (previous / 'complete.json').exists() or checkpoint_fingerprint(old_model) != old_receipt['checkpoint']:
                    raise ValueError('Refusing to prune an unsealed or changed checkpoint')
                atomic_json(previous / 'pruned.json', {'checkpoint': old_receipt['checkpoint'],
                            'replaced_by_round': round_index, 'replacement_seal': stable_hash(seal),
                            'policy': 'latest; raw trajectories, calibration and metrics retained'})
                shutil.rmtree(old_model)
    atomic_json(root / 'complete.json', {'status': 'complete', 'method': method,
                                       'rounds': config['rounds'], 'run_identity': run_identity})


def status(config):
    root = Path(config['output_dir'])
    return {'scope': 'stored artifacts, not process liveness',
            'reference_ready': (Path(config['data_dir']) / 'calibration.lock.json').exists(),
            'methods': {m: {'complete': (root / m / 'complete.json').exists(),
                            'rounds': {str(r): (root / m / f'round-{r}' / 'evaluation' / 'summary.json').exists()
                                       for r in range(config['rounds'] + 1)}} for m in config['methods']}}
