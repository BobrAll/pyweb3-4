"""Run-level paired inference; steps are never independent replicates."""
import argparse
import csv
import itertools
import json
import math
from pathlib import Path
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def quantile(values, q):
    return float(np.quantile(values, q))


def nearest_rank(values, q):
    return sorted(values)[max(0, math.ceil(q * len(values)) - 1)]


def ci(values, rng, resamples):
    a = np.asarray(values)
    medians = np.median(rng.choice(a, size=(resamples, len(a)), replace=True), axis=1)
    return [float(x) for x in np.quantile(medians, [0.025, 0.975])]


def paired_signflip(differences):
    d = np.asarray(differences)
    observed = abs(float(d.mean()))
    if len(d) > 16:
        raise ValueError('Exact sign-flip supports <=16 pairs')
    values = [abs(float(np.mean(d * signs))) for signs in itertools.product([-1, 1], repeat=len(d))]
    return sum(v >= observed - 1e-12 for v in values) / len(values)


def holm(pvalues):
    order = np.argsort(pvalues)
    adjusted, previous = [0.] * len(pvalues), 0.
    for rank, index in enumerate(order):
        previous = max(previous, min(1., pvalues[index] * (len(pvalues) - rank)))
        adjusted[index] = previous
    return adjusted


def read_runs(raw):
    if not (raw / 'COMPLETE.json').exists():
        raise ValueError('Incomplete batch: analysis refused')
    runs = []
    for path in sorted(raw.glob('*.json')):
        data = json.loads(path.read_text())
        if 'manifest' not in data:
            continue
        meta, samples = data['manifest'], data['samples']
        p = meta['params']
        runs.append({**p, 'order': meta['order'], 'run_id': meta['run_id'],
                     'total_bytes': sum(s['output_bytes'] for s in samples),
                     'last_bytes': samples[-1]['output_bytes'],
                     'p95_ms': nearest_rank([s['policy_ms'] for s in samples], .95),
                     'invariants_ok': all(s['invariants_ok'] for s in samples),
                     'generator_wait_cpu_pct': meta['generator_wait_cpu_pct']})
    expected = json.loads((raw / 'COMPLETE.json').read_text())['runs']
    if len(runs) != expected:
        raise ValueError('Run count mismatch')
    keys = [(r['kind'], r['policy'], r['steps'], r['nodes'], r['rep']) for r in runs]
    if len(keys) != len(set(keys)):
        raise ValueError('Duplicate run')
    return runs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', required=True)
    args = parser.parse_args()
    raw = Path('results/raw') / args.batch
    out = Path('results/processed') / args.batch
    out.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((raw / 'batch.json').read_text())['config']
    runs = read_runs(raw)
    rng = np.random.default_rng(cfg['seed'])
    rows = [r for r in runs if r['kind'] == 'main']
    summaries = []
    for steps, nodes in itertools.product(cfg['steps'], cfg['nodes']):
        group = [r for r in rows if (r['steps'], r['nodes']) == (steps, nodes)]
        full = sorted([r for r in group if r['policy'] == 'full'], key=lambda r: r['rep'])
        bounded = sorted([r for r in group if r['policy'] == 'bounded'], key=lambda r: r['rep'])
        if len(full) != cfg['repetitions'] or len(bounded) != len(full):
            raise ValueError('Incomplete pairs')
        assert [r['seed'] for r in full] == [r['seed'] for r in bounded]
        a, b = np.array([r['total_bytes'] for r in full]), np.array([r['total_bytes'] for r in bounded])
        reduction = 1 - b / a
        summaries.append({'steps': steps, 'nodes': nodes, 'n_pairs': len(a),
                          'full_median_bytes': float(np.median(a)), 'bounded_median_bytes': float(np.median(b)),
                          'reduction_median': float(np.median(reduction)),
                          'reduction_iqr': float(np.quantile(reduction, .75) - np.quantile(reduction, .25)),
                          'reduction_ci95': ci(reduction, rng, cfg['bootstrap_resamples']),
                          'p_signflip': paired_signflip(reduction),
                          'full_p95_median_ms': float(np.median([r['p95_ms'] for r in full])),
                          'bounded_p95_median_ms': float(np.median([r['p95_ms'] for r in bounded])),
                          'all_invariants_ok': all(r['invariants_ok'] for r in bounded)})
    for row, p in zip(summaries, holm([s['p_signflip'] for s in summaries])):
        row['p_holm'] = p
        row['practical_success'] = row['reduction_ci95'][0] >= cfg['practical_reduction'] and row['all_invariants_ok']
    aa = [r for r in runs if r['kind'] == 'aa']
    aa_a = [r['p95_ms'] for r in aa if r['group'] == 'A']
    aa_b = [r['p95_ms'] for r in aa if r['group'] == 'B']
    # Independent randomized groups; exhaustive label permutation handles ties.
    aa_values = np.array(aa_a + aa_b)
    obs = abs(float(np.median(aa_a) - np.median(aa_b)))
    differences = []
    for indices in itertools.combinations(range(10), 5):
        mask = np.zeros(10, dtype=bool); mask[list(indices)] = True
        differences.append(abs(float(np.median(aa_values[mask]) - np.median(aa_values[~mask]))))
    aa_p = sum(d >= obs - 1e-12 for d in differences) / len(differences)
    ordered_aa = sorted(aa, key=lambda r: r['order'])
    rho, trend_p = stats.spearmanr([r['order'] for r in ordered_aa], [r['p95_ms'] for r in ordered_aa])
    checks = {'aa_n': len(aa), 'aa_group_sizes': [len(aa_a), len(aa_b)],
              'aa_payload_identical': len(set(r['total_bytes'] for r in aa)) == 1,
              'aa_timing_permutation_p': aa_p, 'aa_timing_median_difference_ms': obs,
              'aa_timing_iqr_ms': quantile(aa_values, .75) - quantile(aa_values, .25),
              'aa_timing_median_ms': float(np.median(aa_values)),
              'aa_trend_spearman_rho': float(rho), 'aa_trend_p': float(trend_p),
              'generator_max_wait_cpu_pct': max(r['generator_wait_cpu_pct'] for r in runs),
              'invariants_ok': all(r['invariants_ok'] for r in runs),
              'note': 'A/A nonsignificance is not proof of equivalence; timing is secondary.'}
    (out / 'summary.json').write_text(json.dumps({'summary': summaries, 'checks': checks}, indent=2) + '\n')
    fields = sorted(set().union(*(r.keys() for r in runs)))
    with (out / 'runs.csv').open('w') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(runs)
    # Paired relative reductions: one point per independently seeded trajectory.
    labels, values = [], []
    for s in summaries:
        g = [r for r in rows if (r['steps'], r['nodes']) == (s['steps'], s['nodes'])]
        a = sorted([r for r in g if r['policy'] == 'full'], key=lambda r: r['rep'])
        b = sorted([r for r in g if r['policy'] == 'bounded'], key=lambda r: r['rep'])
        labels.append(f"{s['steps']} steps\n{s['nodes']} nodes")
        values.append([100 * (1 - y['total_bytes'] / x['total_bytes']) for x, y in zip(a, b)])
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.boxplot(values, tick_labels=labels)
    for i, v in enumerate(values, 1): ax.scatter(np.linspace(i-.08, i+.08, len(v)), v, color='#126e82', s=16)
    ax.axhline(30, color='#aa3939', linestyle='--', label='Practical threshold: 30%')
    ax.set(ylabel='Cumulative payload reduction (%)', title='Independent trajectories, paired full / bounded')
    ax.legend(); fig.tight_layout(); fig.savefig(out / 'reduction.png', dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    for policy in cfg['policies']:
        x = sorted(r['p95_ms'] for r in rows if r['policy'] == policy and r['steps'] == max(cfg['steps']) and r['nodes'] == max(cfg['nodes']))
        ax.step(x, np.arange(1, len(x)+1)/len(x), where='post', label=policy)
    ax.set(xlabel='Run-level p95 policy time (ms)', ylabel='ECDF', title='Largest configuration; policy CPU work only')
    ax.legend(); fig.tight_layout(); fig.savefig(out / 'latency-ecdf.png', dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot([r['order'] for r in ordered_aa], [r['p95_ms'] for r in ordered_aa], 'o-', color='#126e82')
    ax.set(xlabel='Global randomized run order', ylabel='Run-level p95 policy time (ms)', title='A/A timing stability, identical workload')
    fig.tight_layout(); fig.savefig(out / 'stability.png', dpi=180); plt.close(fig)
    text = ['| Steps | Nodes | n pairs | Full bytes | Bounded bytes | Reduction % [95% CI] | Holm p |',
            '|---|---|---|---|---|---|---|']
    for s in summaries:
        lo, hi = s['reduction_ci95']
        text.append(f"| {s['steps']} | {s['nodes']} | {s['n_pairs']} | {s['full_median_bytes']:.0f} | {s['bounded_median_bytes']:.0f} | {100*s['reduction_median']:.2f} [{100*lo:.2f}; {100*hi:.2f}] | {s['p_holm']:.5f} |")
    (out / 'table.md').write_text('\n'.join(text)+'\n')
    print(json.dumps({'summary': summaries, 'checks': checks}, indent=2))


if __name__ == '__main__':
    main()
