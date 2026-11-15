"""Synthetic, seeded observations. No user data or real screenshots."""
import random


def trajectory(seed, steps, nodes, apps, image_chars, diff_lines):
    rng = random.Random(seed)
    messages = [{'role': 'user', 'text': 'Complete the synthetic workflow.', 'images': []}]
    snapshots = []
    for step in range(steps):
        app = step % apps
        tree = '\n'.join(f'{i} button label_{rng.randrange(1000000):06d} value_{step}_{i}'
                         for i in range(nodes))
        diff = '\n'.join(f'updated node {rng.randrange(nodes)} value {rng.randrange(1000000)}'
                         for _ in range(diff_lines))
        messages.append({'role': 'assistant', 'text': f'Inspect app {app}, step {step}.', 'images': []})
        messages.append({'role': 'tool', 'text': f'App{app} [org.bench.app{app}] - window "Synthetic"\n'
                         f'Changed after click:\n{diff}\nAccessibility tree ({nodes} nodes):\n{tree}',
                         'images': [chr(65 + step % 26) * image_chars] if image_chars else []})
        snapshots.append(list(messages))
    return snapshots
