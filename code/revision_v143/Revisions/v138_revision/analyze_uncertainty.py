"""Paired spatial uncertainty and explicit 2024 missing-status scenarios."""

import numpy as np
import pandas as pd
from analyze_revision import OUT, PRIVATE, SEED, MINUTES_PER_MILE, panel, points, hospitals, distance, gini, write_json


def main():
    d = panel()
    _, coords = points(d)
    z = np.load(PRIVATE / "distances.npz")
    w = d.POPULATION.to_numpy(dtype=float)
    codes, counties = pd.factorize(d.county_fips, sort=True)
    k = len(counties)
    sums = np.column_stack([np.bincount(codes, weights=w), np.bincount(codes, weights=w * d.within_2022), np.bincount(codes, weights=w * d.within_2024)])
    sorted_data = {}
    keys = ["primary_2022", "primary_2024", "all_hospitals_2022", "all_hospitals_2024"]
    for key in keys:
        x = z[key]
        ix = np.argsort(x)
        sorted_data[key] = (x[ix], w[ix], codes[ix])
    rng = np.random.default_rng(SEED)
    draws = []
    for _ in range(2000):
        freq = np.bincount(rng.integers(0, k, k), minlength=k)
        totals = freq @ sums
        gs = []
        for key in keys:
            x, weights, c = sorted_data[key]
            ww = weights * freq[c]
            a = np.r_[0., np.cumsum(ww) / ww.sum()]
            b = np.r_[0., np.cumsum(ww * x) / np.sum(ww * x)]
            gs.append(1 - 2 * np.trapezoid(b, a))
        draws.append([100 * totals[1] / totals[0], 100 * totals[2] / totals[0], 100 * (totals[2] - totals[1]) / totals[0], gs[0], gs[1], gs[1] - gs[0], gs[2], gs[3], gs[3] - gs[2]])
    names = ["coverage22", "coverage24", "coverage_change_pp", "gini22", "gini24", "gini_change", "all_gini22", "all_gini24", "all_gini_change"]
    low, high = np.quantile(draws, [.025, .975], axis=0)
    pd.DataFrame({"quantity": names, "lower95": low, "upper95": high, "bootstrap_mean": np.mean(draws, axis=0)}).to_csv(OUT / "paired_bootstrap_intervals.csv", index=False)
    print("Bootstrap completed", flush=True)
    h, a = hospitals(2024)
    # Scenario-only predictions for hospitals lacking every determinate item.
    # These do not replace observed data or resolve partial negative composites.
    base = h.ai_flag.eq(1).to_numpy()
    unknown = ~h.any_answer.to_numpy()
    size_stats = h.groupby("size", observed=True).agg(positive=("ai_flag", "sum"), answered=("any_answer", "sum"))
    prob = h["size"].map((size_stats.positive / size_stats.answered).to_dict()).astype(float).fillna(h.ai_flag.sum() / h.any_answer.sum()).to_numpy()
    assert np.isfinite(prob).all()
    cases = []
    for multiplier in [0., .5, 1., 1.5]:
        reps = 1 if multiplier == 0 else 100
        result = []
        for _ in range(reps):
            qualified = base | (unknown & (rng.random(len(h)) < np.clip(prob * multiplier, 0, 1)))
            x, _ = distance(coords, h[qualified])
            result.append([100 * w[x * MINUTES_PER_MILE <= 30].sum() / w.sum(), gini(x, w), qualified.sum()])
        result = np.asarray(result)
        lo, med, hi = np.quantile(result, [.025, .5, .975], axis=0)
        cases.append({"rate_multiplier": multiplier, "replicates": reps,
                      "coverage_median": med[0], "coverage_p025": lo[0], "coverage_p975": hi[0],
                      "gini_median": med[1], "gini_p025": lo[1], "gini_p975": hi[1], "qualifying_median": med[2]})
        pd.DataFrame(cases).to_csv(OUT / "nonresponse_scenarios.csv", index=False)
        print("Scenario completed", multiplier, flush=True)
    write_json("nonresponse_scenario_notes.json", {"year": 2024, "unknown_hospitals": int(unknown.sum()), "seed": SEED,
        "meaning": "Scenario multipliers applied to observed within-bed-stratum qualifying proportion among hospitals with any determinate item; nonpositive/missing bed counts use the pooled rate. Only hospitals with no determinate item receive simulated positive status. Observed positives and all other reports remain fixed. Probabilities capped at one. No assertion that missingness is random.",
        "interval": "2.5th-97.5th Monte Carlo percentiles conditional on fixed stratum rates; not confidence intervals, not statistical bounds, and not total uncertainty. Partial-item and upstream measurement errors are not addressed."})


if __name__ == "__main__":
    main()
