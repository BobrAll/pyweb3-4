import copy
import unittest
from load.dataset import trajectory
from sut.history import trim, TREE, DIFF, DIFF_OMITTED, app_key
from sut.worker import byte_count, verify


def msg(text='', images=None, role='tool'):
    return dict(role=role, text=text, images=images or [])


class HistoryTests(unittest.TestCase):
    def test_latest_per_app_and_stable_input(self):
        history = trajectory(7, 15, 20, 3, 100, 5)[-1]
        original = copy.deepcopy(history)
        output = trim(history)
        self.assertEqual(history, original)
        self.assertTrue(verify(history, output, 3, 1))
        self.assertEqual(sum(TREE in m['text'] for m in output), 3)
        self.assertEqual(sum(bool(m['images']) for m in output), 1)
        self.assertLess(byte_count(output), byte_count(history))

    def test_four_apps_eviction(self):
        history = trajectory(1, 4, 2, 4, 0, 1)[-1]
        output = trim(history)
        kept = [app_key(m['text']) for m in output if TREE in m['text']]
        self.assertEqual(kept, ['org.bench.app1', 'org.bench.app2', 'org.bench.app3'])

    def test_image_cap_counts_messages_not_images(self):
        out = trim([msg(images=['a']), msg(images=['b', 'c'])])
        self.assertEqual(out, [msg(images=['b', 'c'])])

    def test_diff_without_tree_and_role_guard(self):
        out = trim([msg('prefix Changed after click:\nold'), msg('Changed after click:\nnew'),
                    msg('Accessibility tree (user words)', role='user')])
        self.assertEqual(out[0]['text'], 'prefix ' + DIFF_OMITTED)
        self.assertIn('new', out[1]['text'])
        self.assertEqual(out[2]['role'], 'user')

    def test_zero_caps_and_empty(self):
        self.assertEqual(trim([]), [])
        self.assertEqual(trim([msg(images=['a'])], 0, 0), [])
        out = trim(trajectory(5, 3, 2, 1, 10, 0)[-1], 0, 0)
        self.assertFalse(any(TREE in m['text'] or m['images'] for m in out))

    def test_utf8_and_malformed_header(self):
        self.assertEqual(byte_count([msg('я')]), 2)
        self.assertEqual(app_key('plain header'), 'plain header')
        self.assertEqual(app_key('bad ] then [later'), 'bad ] then [later')
        self.assertEqual(app_key('Name [a] header'), 'a')

    def test_generator_is_reproducible(self):
        a = trajectory(22, 6, 10, 3, 10, 5)
        self.assertEqual(a, trajectory(22, 6, 10, 3, 10, 5))
        self.assertNotEqual(a, trajectory(23, 6, 10, 3, 10, 5))

    def test_full_history_must_remain_untrimmed_between_steps(self):
        # Upstream promptForStep trims a view, never writes it back to history.
        history = trajectory(13, 20, 10, 3, 100, 3)[-1]
        first = trim(history)
        self.assertEqual(first, trim(history))
        self.assertTrue(verify(history, first, 3, 1))


if __name__ == '__main__':
    unittest.main()
