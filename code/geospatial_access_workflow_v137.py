#!/usr/bin/env python3
"""Public workflow utilities for the Nature Health v137 access manuscript.

This script documents and validates the public parts of the analysis for:

    Coverage without convergence: Geographic inequality in proximity to
    AI-reporting hospitals in the United States, 2022-2024

The full end-to-end workflow depends on licensed American Hospital Association
(AHA) source records and local geocoded hospital tables that cannot be
redistributed. This public script therefore focuses on reusable calculations
and on validating the releasable aggregate outputs included in this repository:

* proxy drive-time conversion from haversine miles;
* population-weighted quantiles;
* population-weighted Gini coefficients;
* threshold coverage summaries;
* presence and basic schema checks for the v137 public tables and figures.

Interpretation boundary: this repository supports proximity/access analyses.
It does not estimate causal effects of AI deployment on mortality.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Iterable

import numpy as np


EARTH_RADIUS_MILES = 3958.8
DEFAULT_SPEED_MPH = 40.0
DEFAULT_CIRCUITY = 1.3
DEFAULT_THRESHOLD_MINUTES = 30.0


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "results" / "nature_health_v137"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"


EXPECTED_FIGURES = [
    "2022_vs_2024_diffusion_v137.png",
    "manuscript_travel_distribution_ai_rucc.png",
    "2022_2024_delta_map_v137.png",
    "appendix_ai_flag_mode_sensitivity_2024_v137.png",
]


EXPECTED_TABLE_COLUMNS = {
    "table1_longitudinal_summary_v137.csv": [
        "metric",
        "year_2022",
        "year_2024",
        "change",
        "notes",
    ],
    "table2_blockgroup_summary_v137.csv": [
        "metric",
        "year_2022",
        "year_2024",
        "notes",
    ],
    "table3_transition_equity_profile_v137.csv": [
        "characteristic",
        "persistently_within_30_min",
        "newly_within_30_min",
        "improved_still_outside",
        "outside_no_improvement",
        "units_or_notes",
    ],
}


def haversine_miles(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
    radius_miles: float = EARTH_RADIUS_MILES,
) -> float:
    """Return great-circle distance between two latitude/longitude points."""

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = (
        math.sin(d_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2.0) ** 2
    )
    return 2.0 * radius_miles * math.asin(math.sqrt(a))


def _positive_finite(value: float, name: str) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be finite and positive")


def _weighted_observations(values, weights):
    """Validate inputs and discard observations with no population weight."""
    values_arr = np.asarray(list(values), dtype=float)
    weights_arr = np.asarray(list(weights), dtype=float)
    if values_arr.ndim != 1 or values_arr.shape != weights_arr.shape:
        raise ValueError("values and weights must be one-dimensional and equally sized")
    if not np.isfinite(values_arr).all() or not np.isfinite(weights_arr).all():
        raise ValueError("values and weights must be finite")
    if np.any(weights_arr < 0):
        raise ValueError("weights must be nonnegative")
    total = weights_arr.sum()
    if not np.isfinite(total) or total <= 0:
        raise ValueError("weights must sum to a finite positive value")
    keep = weights_arr > 0
    return values_arr[keep], weights_arr[keep]


def proxy_drive_minutes(
    haversine_distance_miles: np.ndarray | float,
    speed_mph: float = DEFAULT_SPEED_MPH,
    circuity: float = DEFAULT_CIRCUITY,
) -> np.ndarray | float:
    """Convert straight-line distance to proxy drive time in minutes."""

    _positive_finite(speed_mph, "speed_mph")
    _positive_finite(circuity, "circuity")
    miles = np.asarray(haversine_distance_miles, dtype=float)
    if not np.isfinite(miles).all() or np.any(miles < 0):
        raise ValueError("distances must be finite and nonnegative")
    return miles * circuity / speed_mph * 60.0


def effective_radius_miles(
    threshold_minutes: float = DEFAULT_THRESHOLD_MINUTES,
    speed_mph: float = DEFAULT_SPEED_MPH,
    circuity: float = DEFAULT_CIRCUITY,
) -> float:
    """Return straight-line radius corresponding to a drive-time threshold."""

    _positive_finite(speed_mph, "speed_mph")
    _positive_finite(circuity, "circuity")
    if not math.isfinite(threshold_minutes) or threshold_minutes < 0:
        raise ValueError("threshold_minutes must be finite and nonnegative")
    road_miles = speed_mph * threshold_minutes / 60.0
    return road_miles / circuity


def weighted_quantile(
    values: Iterable[float],
    weights: Iterable[float],
    quantile: float,
) -> float:
    """Interpolate at cumulative-weight midpoints, excluding zero weights.

    This legacy helper is not the revision's production quantile convention;
    revision analyses use statsmodels DescrStatsW.quantile instead.
    """

    if not 0 <= quantile <= 1:
        raise ValueError("quantile must be between 0 and 1")

    values_arr, weights_arr = _weighted_observations(values, weights)

    order = np.argsort(values_arr)
    values_sorted = values_arr[order]
    weights_sorted = weights_arr[order]
    midpoint_cumulative = (
        np.cumsum(weights_sorted) - 0.5 * weights_sorted
    ) / weights_sorted.sum()
    return float(np.interp(quantile, midpoint_cumulative, values_sorted))


def weighted_gini(values: Iterable[float], weights: Iterable[float]) -> float:
    """Compute weighted Gini; use zero for an all-zero distribution.

    Returning zero in that degenerate case is an explicit convention, not a
    claim that the usual relative-Gini formula has a nonzero denominator.
    """

    values_arr, weights_arr = _weighted_observations(values, weights)
    if np.any(values_arr < 0):
        raise ValueError("values must be nonnegative")
    if not np.any(values_arr):
        return 0.0

    order = np.argsort(values_arr)
    sorted_values = values_arr[order] / values_arr.max()
    sorted_weights = weights_arr[order] / weights_arr.sum()
    weighted_values = sorted_values * sorted_weights

    cum_weight = np.cumsum(sorted_weights)
    cum_value = np.cumsum(weighted_values)

    x = np.insert(cum_weight / cum_weight[-1], 0, 0.0)
    y = np.insert(cum_value / cum_value[-1], 0, 0.0)
    area = np.trapezoid(y, x)
    return float(1.0 - 2.0 * area)


def threshold_coverage(
    drive_minutes: Iterable[float],
    population: Iterable[float],
    threshold_minutes: float = DEFAULT_THRESHOLD_MINUTES,
) -> tuple[float, float]:
    """Return covered population and covered percentage under a threshold."""

    minutes_arr, population_arr = _weighted_observations(drive_minutes, population)
    if np.any(minutes_arr < 0):
        raise ValueError("drive_minutes must be nonnegative")
    if not math.isfinite(threshold_minutes) or threshold_minutes < 0:
        raise ValueError("threshold_minutes must be finite and nonnegative")

    covered = population_arr[minutes_arr <= threshold_minutes].sum()
    return float(covered), float(covered / population_arr.sum() * 100.0)


def read_csv_header(path: Path) -> list[str]:
    """Read the header row from a CSV file."""

    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        return next(reader)


def count_csv_rows(path: Path) -> int:
    """Return number of data rows in a CSV file."""

    with path.open(newline="") as handle:
        reader = csv.reader(handle)
        next(reader)
        return sum(1 for _ in reader)


def validate_public_outputs() -> None:
    """Validate that public v137 output files are present and well formed."""

    missing_figures = [name for name in EXPECTED_FIGURES if not (FIGURE_DIR / name).is_file()]
    if missing_figures:
        raise FileNotFoundError(f"Missing expected figures: {missing_figures}")

    for filename, expected_header in EXPECTED_TABLE_COLUMNS.items():
        path = TABLE_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing expected table: {filename}")
        observed_header = read_csv_header(path)
        if observed_header != expected_header:
            raise ValueError(
                f"Unexpected header for {filename}: {observed_header}; "
                f"expected {expected_header}"
            )
        if count_csv_rows(path) == 0:
            raise ValueError(f"Table has no data rows: {filename}")


def main() -> None:
    """Run public-output validation and print method constants."""

    validate_public_outputs()
    radius = effective_radius_miles()
    print("Archived v137 file presence and CSV schemas checked; numerical results not recomputed.")
    print(f"Default speed assumption: {DEFAULT_SPEED_MPH:.1f} mph")
    print(f"Default circuity factor: {DEFAULT_CIRCUITY:.1f}")
    print(f"30-minute effective straight-line radius: {radius:.2f} miles")


if __name__ == "__main__":
    main()
