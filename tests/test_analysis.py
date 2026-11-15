import unittest
from analysis.analyze import nearest_rank, paired_signflip, holm


class AnalysisTests(unittest.TestCase):
    def test_percentile_nearest_rank(self):
        self.assertEqual(nearest_rank(list(range(1, 11)), .95), 10)

    def test_exact_signflip(self):
        self.assertEqual(paired_signflip([0] * 10), 1)
        self.assertEqual(paired_signflip([1] * 10), 2 / 1024)

    def test_holm_monotone(self):
        self.assertEqual(holm([.04, .001, .02]), [.04, .003, .04])
