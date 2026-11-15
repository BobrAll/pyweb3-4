"""One fresh subprocess per run. Timing excludes JSON input and output."""
import json
import math
import sys
import time
from sut.history import apply, TREE, DIFF_OMITTED, app_key


def byte_count(messages):
    # Payload bytes, not HTTP/JSON wire bytes, tokenizer output, or image tokens.
    return sum(len(m['text'].encode('utf-8')) + sum(len(i.encode('utf-8')) for i in m['images'])
               for m in messages)


def verify(original, output, keep_trees, keep_screenshots):
    latest = {}
    for m in reversed(original):
        if m['role'] == 'tool' and TREE in m['text']:
            key = app_key(m['text'])
            if key not in latest:
                latest[key] = m['text'].split(TREE, 1)[1]
    expected = list(latest.items())[:keep_trees]
    actual = {app_key(m['text']): m['text'].split(TREE, 1)[1]
              for m in output if m['role'] == 'tool' and TREE in m['text']}
    preserved = all(actual.get(key) == tree for key, tree in expected)
    plain_in = [m for m in original if m['role'] != 'tool' and not m['images']]
    plain_out = [m for m in output if m['role'] != 'tool' and not m['images']]
    expected_images = [m['images'] for m in original if m['images']][-keep_screenshots:] if keep_screenshots else []
    actual_images = [m['images'] for m in output if m['images']]
    latest_diff = next((m['text'].split('Changed after ', 1)[1].split(TREE, 1)[0]
                        for m in reversed(original) if m['role'] == 'tool' and 'Changed after ' in m['text']), None)
    output_diff = next((m['text'].split('Changed after ', 1)[1].split(TREE, 1)[0]
                        for m in reversed(output) if m['role'] == 'tool' and 'Changed after ' in m['text']), None)
    tree_count = sum(m['role'] == 'tool' and TREE in m['text'] for m in output)
    return (preserved and plain_in == plain_out and actual_images == expected_images
            and latest_diff == output_diff and tree_count == len(expected))


def run(request):
    samples = []
    policy = request['policy']
    trees, images = request['keep_trees'], request['keep_screenshots']
    snapshots = request['snapshots']
    # Warm-up is separate, discarded, and uses the same fixed input.
    for _ in range(request['warmup_passes']):
        for messages in snapshots:
            apply(messages, policy, trees, images)
    cpu0, wall0 = time.process_time_ns(), time.perf_counter_ns()
    for step, messages in enumerate(snapshots, 1):
        started = time.perf_counter_ns()
        output = apply(messages, policy, trees, images)
        elapsed = (time.perf_counter_ns() - started) / 1e6
        samples.append({'step': step, 'input_bytes': byte_count(messages),
                        'output_bytes': byte_count(output), 'policy_ms': elapsed,
                        'invariants_ok': verify(messages, output, trees, images) if policy == 'bounded' else True})
    return {'samples': samples, 'worker_cpu_ms': (time.process_time_ns() - cpu0) / 1e6,
            'worker_wall_ms': (time.perf_counter_ns() - wall0) / 1e6}


if __name__ == '__main__':
    print(json.dumps(run(json.load(sys.stdin))))
