"""Randomized paired experiment with immutable batches and raw per-run records."""
import argparse
import hashlib
import itertools
import json
import os
import platform
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from load.dataset import trajectory

ROOT = Path(__file__).resolve().parents[1]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='configs/experiment.json')
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    cfg_bytes = Path(args.config).read_bytes()
    cfg = json.loads(cfg_bytes)
    if cfg['repetitions'] < 5 or cfg['aa_repetitions'] != 10:
        raise ValueError('Require >=5 repetitions and 10 A/A runs')
    out = ROOT / 'results/raw' / args.batch
    out.mkdir(parents=True, exist_ok=False)
    env_path = ROOT / 'results/environment.json'
    environment = json.loads(env_path.read_text()) if env_path.exists() else {'mode': 'local-unrecorded'}
    source_files = sorted(p for folder in ['sut', 'load', 'runner', 'analysis', 'configs', 'vendor']
                          for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in str(p))
    source_hashes = {str(p.relative_to(ROOT)): sha(p.read_bytes()) for p in source_files}
    shared = {'config': cfg, 'config_sha256': sha(cfg_bytes), 'environment': environment,
              'source_sha256': source_hashes, 'python': sys.version,
              'container_platform': platform.platform(), 'cpu_count': os.cpu_count(),
              'upstream': json.loads((ROOT / 'vendor/deskhand/provenance.json').read_text())}
    dump(out / 'batch.json', shared)
    plan = []
    for steps, nodes, rep in itertools.product(cfg['steps'], cfg['nodes'], range(cfg['repetitions'])):
        seed = cfg['seed'] + steps * 100000 + nodes * 100 + rep
        for policy in cfg['policies']:
            plan.append(dict(kind='main', policy=policy, steps=steps, nodes=nodes, rep=rep, seed=seed))
    aa_groups = ['A'] * 5 + ['B'] * 5
    random.Random(cfg['seed'] + 1).shuffle(aa_groups)
    # A/A deliberately identical dataset/configuration: only timing may vary.
    for rep, group in enumerate(aa_groups):
        plan.append(dict(kind='aa', policy='bounded', steps=max(cfg['steps']), nodes=max(cfg['nodes']),
                         rep=rep, seed=cfg['seed'] + 999, group=group))
    random.Random(cfg['seed']).shuffle(plan)
    dump(out / 'plan.json', plan)
    for order, params in enumerate(plan):
        start = datetime.now(timezone.utc).isoformat()
        gen_cpu0, gen_wall0 = time.process_time_ns(), time.perf_counter_ns()
        snapshots = trajectory(params['seed'], params['steps'], params['nodes'], cfg['apps'],
                               cfg['image_chars'], cfg['diff_lines'])
        request = {**params, 'snapshots': snapshots,
                   **{k: cfg[k] for k in ['warmup_passes', 'keep_trees', 'keep_screenshots']}}
        payload = json.dumps(request, ensure_ascii=False).encode()
        generator_wall_ms = (time.perf_counter_ns() - gen_wall0) / 1e6
        generator_cpu_ms = (time.process_time_ns() - gen_cpu0) / 1e6
        # No online generator during measurement: materialize first, then start fresh SUT.
        wait_cpu0, wait_wall0 = time.process_time_ns(), time.perf_counter_ns()
        completed = subprocess.run([sys.executable, '-m', 'sut.worker'], input=payload,
                                   capture_output=True, check=True, timeout=cfg['timeout_seconds'], cwd=ROOT)
        wait_ms = (time.perf_counter_ns() - wait_wall0) / 1e6
        waiting_cpu_pct = 100 * ((time.process_time_ns() - wait_cpu0) / 1e6) / wait_ms
        result = json.loads(completed.stdout)
        run_id = f'{order:03d}-{params["kind"]}-{params["policy"]}-s{params["steps"]}-n{params["nodes"]}-r{params["rep"]}'
        run = {**result, 'manifest': {**shared, 'run_id': run_id, 'order': order, 'params': params,
               'started_at': start, 'finished_at': datetime.now(timezone.utc).isoformat(),
               'input_sha256': sha(payload), 'dataset_sha256': sha(json.dumps(snapshots, ensure_ascii=False).encode()), 'generator_wall_ms': generator_wall_ms,
               'generator_cpu_ms': generator_cpu_ms, 'generator_wait_cpu_pct': waiting_cpu_pct}}
        dump(out / f'{run_id}.json', run)
        print(f'[{order + 1}/{len(plan)}] {run_id}', flush=True)
    dump(out / 'COMPLETE.json', {'runs': len(plan)})


if __name__ == '__main__':
    main()
