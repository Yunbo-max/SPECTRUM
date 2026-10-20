"""Start/resume CPU-safe SH02 preparation without starting model inference."""
import datetime
import fcntl
import json
import os
import pathlib
import subprocess
import sys
import time

STATE = pathlib.Path('/root/rivermind-data/spectrum-harness/project/research-state/sh02-migration-20261020')


def active_script(filename):
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            argv = (entry/'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if filename in argv:
            return int(entry.name), argv
    return None


def atomic_json(path, value):
    temp = path.with_name(path.name+'.tmp')
    temp.write_text(json.dumps(value, indent=2)+'\n')
    temp.replace(path)


def process_record(pid, command, log_path):
    return {
        'pid': pid,
        'boot_id': pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
        'proc_stat_at_launch': pathlib.Path(f'/proc/{pid}/stat').read_text(),
        'command': command,
        'log': str(log_path),
        'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }


def launch(label, script):
    log_path = STATE/f'{label}-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.log'
    command = [sys.executable, '-u', str(STATE/script)]
    with log_path.open('x') as log:
        process = subprocess.Popen(command, cwd=STATE, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, close_fds=True)
    time.sleep(0.1)
    atomic_json(STATE/f'{label}-process.json',
                process_record(process.pid, command, log_path))
    return process.pid


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    with (STATE/'preparation-start.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'gpu_scoring_started': False, 'actions': []}
        install_done = STATE/'installation-exit.json'
        install = active_script('install_environment.py')
        if install:
            result['actions'].append({'step': 'environment', 'status': 'already_running',
                                      'pid': install[0]})
        elif not (install_done.exists() and
                  json.loads(install_done.read_text()).get('returncode') == 0):
            if install_done.exists():
                archived = STATE/f'installation-exit-failed-{datetime.datetime.now(datetime.timezone.utc):%Y%m%dT%H%M%SZ}.json'
                install_done.replace(archived)
                result['archived_failed_install_marker'] = str(archived)
            result['actions'].append({'step': 'environment', 'status': 'started',
                                      'pid': launch('installation-resume', 'install_environment.py')})
        else:
            result['actions'].append({'step': 'environment', 'status': 'already_complete'})

        bootstrap = active_script('bootstrap_and_base.py')
        if bootstrap:
            result['actions'].append({'step': 'preparation', 'status': 'already_running',
                                      'pid': bootstrap[0]})
        elif (STATE/'preparation-completed.json').exists():
            result['actions'].append({'step': 'preparation', 'status': 'already_complete'})
        else:
            result['actions'].append({'step': 'preparation', 'status': 'started',
                                      'pid': launch('preparation', 'bootstrap_and_base.py')})
        atomic_json(STATE/'preparation-launch-observation.json', result)
        print(json.dumps(result, indent=2), flush=True)

        watcher = active_script('run_when_gpu_ready.py')
        if watcher:
            result['gpu_auto_runner'] = {'status': 'already_running', 'pid': watcher[0]}
        elif not (STATE/'base-stage-completed.json').exists():
            result['gpu_auto_runner'] = {
                'status': 'started',
                'pid': launch('gpu-auto-runner', 'run_when_gpu_ready.py'),
            }
        atomic_json(STATE/'preparation-launch-observation.json', result)
        print(json.dumps({'gpu_auto_runner': result['gpu_auto_runner']}, indent=2), flush=True)


if __name__ == '__main__':
    main()
