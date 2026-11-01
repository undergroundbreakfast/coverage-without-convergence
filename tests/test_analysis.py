"""Data-free checks of the production calculations and scenario constraints."""

from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "code"))
from analyze_access import distance, gini, metrics, MINUTES_PER_MILE
from implementation_stages import counts
from sensitivity_analysis import (
    probability,
    update_distance,
    expected_coverage,
    expected_outside_both,
)


class AccessCalculations(unittest.TestCase):
    def test_gini_known_distribution(self):
        self.assertEqual(gini(np.array([0.0, 2.0]), np.array([1.0, 1.0])), 0.5)

    def test_gini_matches_pairwise_definition(self):
        x, w = np.array([1.0, 4.0, 8.0]), np.array([2.0, 3.0, 1.0])
        expected = np.sum(w[:, None] * w[None, :] * abs(x[:, None] - x[None, :])) / (
            2 * w.sum() * np.sum(w * x)
        )
        self.assertAlmostEqual(gini(x, w), expected)

    def test_gini_zero_and_equal(self):
        for x in [np.array([0.0, 0.0]), np.array([2.0, 2.0])]:
            self.assertAlmostEqual(gini(x, np.array([1.0, 3.0])), 0.0)

    def test_gini_scale_and_order_invariance(self):
        x, w = np.array([1.0, 4.0, 8.0]), np.array([2.0, 3.0, 1.0])
        self.assertAlmostEqual(gini(x, w), gini(x[::-1] * 100, w[::-1] * 10))

    def test_threshold_includes_boundary(self):
        result = metrics(
            np.array([10.0, 30.0, 40.0]) / MINUTES_PER_MILE, np.array([2.0, 3.0, 5.0])
        )
        self.assertEqual(result["coverage30_pct"], 50.0)

    def test_production_weighted_quantiles(self):
        result = metrics(np.array([1.0, 2.0, 3.0]), np.array([1.0, 1.0, 1.0]))
        self.assertEqual(result["median_miles"], 2.0)
        self.assertEqual(result["p10_miles"], 1.0)
        self.assertEqual(result["p90_miles"], 3.0)

    def test_exact_zero_distance_convention(self):
        h = pd.DataFrame({"latitude": [0.0], "longitude": [0.0]})
        d, _ = distance(np.deg2rad([[0.0, 0.0], [0.0, 0.00001]]), h)
        self.assertEqual(d[0], 0.1)
        self.assertGreater(d[1], 0.0)
        self.assertLess(d[1], 0.1)

    def test_fewer_destinations_cannot_reduce_distance(self):
        h = pd.DataFrame({"latitude": [0.0, 0.0], "longitude": [0.0, 1.0]})
        points = np.deg2rad([[0.0, 0.25], [0.0, 0.75]])
        broad, _ = distance(points, h)
        strict, _ = distance(points, h.iloc[:1])
        np.testing.assert_array_less(broad - 1e-12, strict)

    def test_empty_destinations_raise(self):
        with self.assertRaises(ValueError):
            distance(np.zeros((1, 2)), pd.DataFrame(columns=["latitude", "longitude"]))

    def test_implementation_unknown_is_separate(self):
        result = counts(pd.Series([0.0, 1.0, 2.0, 3.0, 4.0, np.nan]))
        self.assertEqual(result["determinate"], 5)
        self.assertEqual(result["unknown"], 1)
        self.assertEqual(result["advanced_n"], 2)
        self.assertEqual(result["pct_answers_4"], 20.0)

    def test_all_unknown_stage_counts(self):
        result = counts(pd.Series([np.nan, np.nan]))
        self.assertEqual(result["unknown"], 2)
        self.assertIsNone(result["advanced_pct_answers"])


class MissingStatusScenarios(unittest.TestCase):
    def setUp(self):
        self.h = pd.DataFrame(
            {
                "income_10k": [4.0, 6.0, 8.0],
                "ai_flag": [1, 0, 0],
                "all_answer": [False, True, False],
            }
        )
        self.a = pd.DataFrame({"one": [3.0, 0.0, np.nan], "two": [np.nan, 0.0, np.nan]})
        self.p = np.array([[0.2, 0.3], [0.2, 0.3], [0.2, 0.3]])

    def test_observed_answers_are_preserved(self):
        for dependence in ["positive", "independent"]:
            for odds in [0.5, 1.0, 2.0]:
                for tilt in [-1.0, 0.0, 1.0]:
                    result = probability(
                        self.h,
                        self.a,
                        self.p,
                        dependence,
                        odds,
                        tilt,
                        np.array([40000.0, 60000.0, 80000.0]),
                    )
                    self.assertEqual(result[0], 1.0)
                    self.assertEqual(result[1], 0.0)
                    self.assertTrue(np.all((result >= 0) & (result <= 1)))

    def test_item_dependence_changes_only_missing_probability(self):
        positive = probability(
            self.h,
            self.a,
            self.p,
            "positive",
            1.0,
            0.0,
            np.array([40000.0, 60000.0, 80000.0]),
        )
        independent = probability(
            self.h,
            self.a,
            self.p,
            "independent",
            1.0,
            0.0,
            np.array([40000.0, 60000.0, 80000.0]),
        )
        self.assertAlmostEqual(positive[2], 0.3)
        self.assertAlmostEqual(independent[2], 1 - 0.8 * 0.7)

    def test_distance_update_preserves_baseline(self):
        base = np.array([20.0, 30.0])
        edges = {
            "rows": np.array([0, 0, 1]),
            "cols": np.array([0, 1, 0]),
            "miles": np.array([5.0, 10.0, 15.0]),
        }
        result = update_distance(base, edges, np.array([False, True]))
        np.testing.assert_array_equal(result, [10.0, 30.0])
        np.testing.assert_array_equal(base, [20.0, 30.0])

    def test_exact_expected_coverage(self):
        base = np.array([20.0, 10.0, 30.0])
        edges = {
            "rows": np.array([0, 0]),
            "cols": np.array([0, 1]),
            "miles": np.array([5.0, 10.0]),
        }
        result = expected_coverage(base, edges, np.array([0.2, 0.3]))
        np.testing.assert_allclose(result, [1 - 0.8 * 0.7, 1.0, 0.0])

    def test_shared_hospital_is_not_counted_twice_across_years(self):
        base = {y: np.array([20.0]) for y in [2022, 2024]}
        edges = {
            y: {"rows": np.array([0]), "cols": np.array([0]), "miles": np.array([10.0])}
            for y in base
        }
        p = {2022: np.array([0.2]), 2024: np.array([0.4])}
        ids = {y: np.array([0]) for y in base}
        expected = {y: expected_coverage(base[y], edges[y], p[y]) for y in base}
        shared = expected_outside_both(base, edges, p, ids, True, expected)
        independent = expected_outside_both(base, edges, p, ids, False, expected)
        np.testing.assert_allclose(shared, [0.6])
        np.testing.assert_allclose(independent, [0.8 * 0.6])


if __name__ == "__main__":
    unittest.main()
