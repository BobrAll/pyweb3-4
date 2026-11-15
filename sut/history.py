"""Research port of Deskhand trimmedHistory; see vendor/deskhand/provenance.json.

Measures this policy on synthetic messages, not the full macOS/LLM application.
Images are opaque payloads. Swift counts messages containing images, not images.
"""
TREE = 'Accessibility tree ('
DIFF = 'Changed after '
TREE_OMITTED = ('Accessibility tree omitted to keep the prompt small. Element numbers '
                'are stable, so the indices you already used still mean the same controls.')
DIFF_OMITTED = 'Changed after that: the details are superseded by a later action.\n'


def app_key(text):
    close = text.find(']')
    start = text.rfind('[', 0, close) if close >= 0 else -1
    return text[start + 1:close] if start >= 0 else text[:40]


def trim(messages, keep_trees=3, keep_screenshots=1):
    if keep_trees < 0 or keep_screenshots < 0:
        raise ValueError('Retention limits must be nonnegative')
    seen_images = diffs_kept = 0
    kept_apps, saw_tree, result = [], set(), []
    for message in reversed(messages):
        copy = {**message, 'images': list(message['images'])}
        if copy['images']:
            seen_images += 1
            if seen_images > keep_screenshots:
                copy['images'] = []
                if not copy['text']:
                    continue
        text = copy['text']
        if copy['role'] == 'tool' and DIFF in text:
            diffs_kept += 1
            if diffs_kept > 1:
                start = text.index(DIFF)
                tree = text.find(TREE, start)
                text = text[:start] + DIFF_OMITTED + (text[tree:] if tree >= 0 else '')
        if copy['role'] == 'tool' and TREE in text:
            app = app_key(text)
            newest = app not in saw_tree
            saw_tree.add(app)
            if newest and len(kept_apps) < keep_trees:
                kept_apps.append(app)
            else:
                text = text[:text.index(TREE)] + TREE_OMITTED
        copy['text'] = text
        result.append(copy)
    return result[::-1]


def apply(messages, policy, keep_trees=3, keep_screenshots=1):
    if policy == 'full':
        return messages
    if policy == 'bounded':
        return trim(messages, keep_trees, keep_screenshots)
    raise ValueError(f'Unknown policy: {policy}')
