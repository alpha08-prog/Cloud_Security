import unittest

from isolab.comparison import confusion, median_interval, split_runs, validate_predictions


class ComparisonTests(unittest.TestCase):
    def test_confusion(self):
        result = confusion([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual(result['f1'], .5)
        self.assertEqual(result['falsePositiveRate'], .5)

    def test_absent_denominator(self):
        self.assertIsNone(confusion([1], [0])['falsePositiveRate'])

    def test_split(self):
        split = split_runs(list(range(10)))
        self.assertEqual([list(split.values()).count(k) for k in ('train', 'validation', 'test')], [4, 3, 3])
        self.assertEqual(split, split_runs(list(range(10))))

    def test_interval(self):
        self.assertEqual(median_interval([2, 2, 2])['low'], 2)
        with self.assertRaises(ValueError):
            median_interval([float('nan'), 1])

    def test_leakage_and_alignment(self):
        row = dict(method='a', runId='r', timestamp=0, split='test', label=1, score=.8)
        validate_predictions([row, dict(row, method='b')])
        for extra in (dict(row, timestamp=1, split='train'), dict(row, method='b', label=0), row):
            with self.assertRaises(ValueError):
                validate_predictions([row, extra])
