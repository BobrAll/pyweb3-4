"""Compare two completed batches at step, run and source level."""
import json
from pathlib import Path


def load(batch):
    result = {}
    for p in (Path('results/raw') / batch).glob('*.json'):
        d = json.loads(p.read_text())
        if 'manifest' in d:
            result[d['manifest']['run_id']] = d
    return result


def main():
    a, b = load('main'), load('repeat')
    assert len(a) == len(b) == 130 and a.keys() == b.keys()
    for key in a:
        x, y = a[key], b[key]
        for field in ['config_sha256', 'source_sha256', 'dataset_sha256', 'input_sha256', 'params']:
            assert x['manifest'][field] == y['manifest'][field], (key, field)
        assert len(x['samples']) == len(y['samples'])
        for u, v in zip(x['samples'], y['samples']):
            for field in ['step', 'input_bytes', 'output_bytes', 'invariants_ok']:
                assert u[field] == v[field], (key, field)
    result = {'runs_compared': len(a), 'same_sources': True, 'same_inputs': True,
              'same_per_step_payloads': True, 'same_invariants': True,
              'timings_expected_to_differ': True}
    Path('results/repeatability.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
