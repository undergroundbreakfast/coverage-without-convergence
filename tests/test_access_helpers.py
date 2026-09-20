"""Synthetic, data-free tests; no manuscript estimates are recomputed."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("access", ROOT / "code/geospatial_access_workflow_v137.py")
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


class AccessHelpers(unittest.TestCase):
    def test_zero_weight_quantile_is_invariant(self):
        self.assertEqual(access.weighted_quantile([0, 10, 100], [1, 0, 1], .5), 50)
        self.assertEqual(access.weighted_quantile([0, 100], [1, 1], .5), 50)

    def test_quantile_endpoints(self):
        self.assertEqual(access.weighted_quantile([3, 1, 9], [1, 2, 3], 0), 1)
        self.assertEqual(access.weighted_quantile([3, 1, 9], [1, 2, 3], 1), 9)

    def test_quantile_scale_and_order(self):
        a = access.weighted_quantile([1, 4, 10], [3, 2, 1], .7)
        b = access.weighted_quantile([10, 1, 4], [10, 30, 20], .7)
        self.assertAlmostEqual(a, b)

    def test_quantile_rejects_invalid_probability(self):
        for q in [-.1, 1.1, float("nan")]:
            with self.subTest(q=q), self.assertRaises(ValueError):
                access.weighted_quantile([1, 2], [1, 1], q)

    def test_gini_zero_convention(self):
        self.assertEqual(access.weighted_gini([0, 0], [1, 3]), 0)

    def test_gini_equal_and_single(self):
        self.assertAlmostEqual(access.weighted_gini([2, 2], [1, 3]), 0)
        self.assertAlmostEqual(access.weighted_gini([9], [100]), 0)

    def test_gini_known_answer(self):
        self.assertAlmostEqual(access.weighted_gini([0, 2], [1, 1]), .5)

    def test_gini_matches_pairwise_definition(self):
        x = np.array([1., 4., 8.])
        w = np.array([2., 3., 1.])
        expected = np.sum(w[:, None] * w[None, :] * abs(x[:, None] - x[None, :]))
        expected /= 2 * w.sum() * np.sum(w * x)
        self.assertAlmostEqual(access.weighted_gini(x, w), expected)

    def test_gini_scale_and_zero_weight(self):
        original = access.weighted_gini([1, 3], [1, 2])
        self.assertAlmostEqual(original, access.weighted_gini([100, 300, 900], [5, 10, 0]))

    def test_gini_rejects_negative_values(self):
        with self.assertRaises(ValueError):
            access.weighted_gini([-1, 2], [1, 1])

    def test_invalid_weighted_inputs(self):
        pairs = [([], []), ([1], [0]), ([1, 2], [1, -1]), ([1], [1, 2]),
                 ([1, np.nan], [1, 2]), ([1, 2], [1, np.inf]), ([[1, 2]], [[1, 1]])]
        for values, weights in pairs:
            for fn, extra in [(access.weighted_gini, ()), (access.weighted_quantile, (.5,)),
                              (access.threshold_coverage, ())]:
                with self.subTest(fn=fn.__name__, values=values), self.assertRaises(ValueError):
                    fn(values, weights, *extra)

    def test_threshold_includes_boundary(self):
        self.assertEqual(access.threshold_coverage([10, 30, 40], [2, 3, 5]), (5., 50.))

    def test_threshold_negative_time(self):
        with self.assertRaises(ValueError):
            access.threshold_coverage([-1, 2], [1, 1])

    def test_threshold_and_conversion_inputs(self):
        for value in [-1, float("inf"), float("nan")]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                access.threshold_coverage([1], [1], value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                access.proxy_drive_minutes(value)
        with self.assertRaises(ValueError):
            access.proxy_drive_minutes(1, speed_mph=0)
        with self.assertRaises(ValueError):
            access.effective_radius_miles(circuity=0)

    def test_radius_conversion_roundtrip(self):
        self.assertAlmostEqual(float(access.proxy_drive_minutes(access.effective_radius_miles())), 30)

    def test_haversine_symmetric_and_zero(self):
        self.assertAlmostEqual(access.haversine_miles(0, 0, 0, 0), 0)
        self.assertAlmostEqual(access.haversine_miles(0, 0, 0, 1), access.haversine_miles(0, 1, 0, 0))

    def test_archived_file_schema_check(self):
        access.validate_public_outputs()


if __name__ == "__main__":
    unittest.main()
