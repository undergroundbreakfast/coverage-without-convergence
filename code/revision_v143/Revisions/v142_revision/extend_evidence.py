"""Aggregate existing fixed-frame scenarios and add targeted descriptive checks.

No database queries, model refits, or changes to previously reported estimates.
Only aggregate outputs are written to this revision directory.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
SCENARIO = HERE.parent / "income_spatial_sensitivity_20260919"
sys.path.insert(0, str(SCENARIO))
import analyze as inc

OUT = HERE / "analysis"
DATA = HERE / "Source_Data/revision_additions"


def save(frame, name):
    frame.to_csv(OUT / name, index=False)
    frame.to_csv(DATA / name, index=False)


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    d = inc.panel()
    context = pd.read_csv(BASE / "private/block_group_context.csv", dtype={"GEOID": str}).set_index("GEOID").loc[d.GEOID]
    weights = d.POPULATION.to_numpy(dtype=float)
    groups = {"Metro": context.rurality.eq("Metro").to_numpy(),
              "Nonmetro 4-6": context.rurality.eq("Nonmetro 4-6").to_numpy(),
              "Nonmetro 7-9": context.rurality.eq("Nonmetro 7-9").to_numpy()}
    groups["All nonmetro"] = groups["Nonmetro 4-6"] | groups["Nonmetro 7-9"]
    assert sum(int(weights[groups[k]].sum()) for k in list(groups)[:3]) == weights.sum()
    cut = np.asarray(json.loads((BASE / "analysis/context_manifest.json").read_text())["quartile_cutpoints"])
    hs, answers, predictions, edges = {}, {}, {}, {}
    source_files = [inc.PANEL, BASE / "private/block_group_context.csv"]
    baselines = {y: d[f"drive_{y}"].to_numpy() / inc.MINUTES_PER_MILE for y in inc.YEARS}
    for year in inc.YEARS:
        hs[year], answers[year] = inc.predictor_frame(year)
        for filename, target in [(f"item_predictions_{year}.npz", predictions), (f"candidates_{year}.npz", edges)]:
            path = SCENARIO / "private" / filename
            source_files.append(path)
            with np.load(path) as z:
                target[year] = {key: z[key] for key in z.files}
    expected_old = pd.read_csv(SCENARIO / "analysis/exact_expected_coverage.csv")
    old_rural = pd.read_csv(BASE / "analysis/rurality_coverage.csv")
    print(old_rural.to_string(index=False), flush=True)
    coverage = []
    cases = [("observed", "Observed reports", None, None, None, None, None)] + inc.SCENARIOS
    national_max_error = 0.
    for name, label, dependence, odds, tilt, income, shared in cases:
        expected = {}
        for year in inc.YEARS:
            if name == "observed":
                expected[year] = (baselines[year] * inc.MINUTES_PER_MILE <= 30).astype(float)
            else:
                a = answers[year]
                item_p = predictions[year]["income" if income else "no_income"]
                if name == "named_items_only" and year == 2024:
                    named = ~a.columns.isin(["aitiot", "clnoai"])
                    a, item_p = a.loc[:, named], item_p[:, named]
                effective = odds
                if name == "adverse_wave_odds":
                    effective = 2. if year == 2022 else .5
                elif name == "reverse_wave_odds":
                    effective = .5 if year == 2022 else 2.
                p = inc.probability(hs[year], a, item_p, dependence, effective, tilt, cut)
                expected[year] = inc.expected_coverage(baselines[year], edges[year], p)
                old = expected_old.loc[(expected_old.scenario == name) & (expected_old.group == "National"), f"coverage_{year}_pct"].item()
                error = abs(100 * np.average(expected[year], weights=weights) - old)
                national_max_error = max(error, national_max_error)
                assert error < 1e-9
        for group, mask in groups.items():
            row = {"scenario": name, "label": label, "group": group, "population": int(weights[mask].sum())}
            row.update({f"coverage_{year}_pct": 100 * np.average(expected[year][mask], weights=weights[mask]) for year in inc.YEARS})
            row["change_pp"] = row["coverage_2024_pct"] - row["coverage_2022_pct"]
            coverage.append(row)
        print(f"Scenario {name} reaggregated; national expectation reproduced", flush=True)
    coverage = pd.DataFrame(coverage)
    for year in inc.YEARS:
        metro = coverage[coverage.group.eq("Metro")].set_index("scenario")[f"coverage_{year}_pct"]
        coverage[f"metro_gap_{year}_pp"] = coverage.scenario.map(metro) - coverage[f"coverage_{year}_pct"]
    coverage["gap_change_pp"] = coverage.metro_gap_2024_pp - coverage.metro_gap_2022_pp
    save(coverage, "scenario_rurality_coverage.csv")
    for row in old_rural.itertuples():
        result = coverage[(coverage.scenario == "observed") & (coverage.group == row.rurality)].iloc[0]
        assert abs(result.coverage_2022_pct - row.coverage_2022_pct) < 1e-9
        assert abs(result.coverage_2024_pct - row.coverage_2024_pct) < 1e-9

    h, a = hs[2024], answers[2024]
    small, rural = h["size"].eq("<100"), h.rurality.eq("Nonmetro 7-9")
    hgroups = {"All hospitals": np.ones(len(h), dtype=bool), "Fewer than 100 beds": small,
               "RUCC 7-9": rural, "Fewer than 100 beds and RUCC 7-9": small & rural}
    rows = []
    for group, mask in hgroups.items():
        for item in a:
            values = a.loc[mask, item]
            n, known, positive = len(values), int(values.notna().sum()), int(values.ge(3).sum())
            rows.append({"group": group, "item": item, "hospitals": n, "determinate_answers": known,
                         "qualifying_reports": positive, "unknown": n-known,
                         "reported_share_of_frame_pct": 100*positive/n,
                         "qualifying_share_of_answers_pct": 100*positive/known if known else np.nan})
    application = pd.DataFrame(rows)
    save(application, "application_size_rurality.csv")
    prior = pd.read_csv(BASE / "analysis/application_spatial_metrics.csv")
    print("Application columns", list(prior), flush=True)
    for row in prior.itertuples():
        if row.item in a:
            assert application[(application.group == "All hospitals") & (application.item == row.item)].qualifying_reports.item() == row.qualifying

    codes, counties = pd.factorize(d.county_fips, sort=True)
    distances = np.load(BASE / "private/distances.npz")
    outside = ~d.within_2022.to_numpy(dtype=bool) & ~d.within_2024.to_numpy(dtype=bool)
    near_any = distances["all_hospitals_2024"] * inc.MINUTES_PER_MILE <= 30
    indicators = {"coverage22": d.within_2022, "coverage24": d.within_2024,
                  "outside_both": outside, "outside_both_near_any": outside & near_any,
                  "outside_both_far_any": outside & ~near_any}
    county = np.column_stack([np.bincount(codes, weights=weights)] +
                            [np.bincount(codes, weights=weights*np.asarray(v)) for v in indicators.values()])
    rng = np.random.default_rng(20260912)
    draws = []
    for _ in range(2000):
        freq = np.bincount(rng.integers(0, len(counties), len(counties)), minlength=len(counties))
        totals = freq @ county
        draws.append(totals[1:] / totals[0])
    draws = np.asarray(draws)
    ci = []
    for j, (name, values) in enumerate(indicators.items()):
        point = np.average(values, weights=weights)
        lo, hi = np.quantile(draws[:, j], [.025, .975])
        ci.append({"quantity": name, "estimate_pct": 100*point, "lower95_pct": 100*lo, "upper95_pct": 100*hi,
                   "estimate_millions": point*weights.sum()/1e6,
                   "lower95_standardized_millions": lo*weights.sum()/1e6,
                   "upper95_standardized_millions": hi*weights.sum()/1e6})
    ci = pd.DataFrame(ci)
    old_ci = pd.read_csv(BASE / "analysis/paired_bootstrap_intervals.csv").set_index("quantity")
    for key in ["coverage22", "coverage24"]:
        row = ci[ci.quantity == key].iloc[0]
        assert np.allclose([row.lower95_pct, row.upper95_pct], old_ci.loc[key, ["lower95", "upper95"]].to_numpy(float), atol=1e-10, rtol=0)
    save(ci, "population_conditional_intervals.csv")
    source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    report = {"frozen_frame": {"block_groups": len(d), "population": int(weights.sum())},
              "exact_expectations_reproduced_max_error_pp": national_max_error,
              "rurality_observed_values_reproduced": True, "coverage_bootstrap_reproduced": True,
              "models_refitted": False, "database_modified": False, "source_hashes": source_hashes,
              "metro_gap_ranges_2024_pp": coverage[coverage.scenario != "observed"].groupby("group").metro_gap_2024_pp.agg(["min", "max"]).to_dict(),
              "bootstrap": "2000 paired legacy-county resamples, seed 20260912; totals standardized to fixed population; conditional spatial variability only"}
    (OUT / "extension_verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(ci.to_string(index=False), flush=True)
    print(coverage.groupby("group").metro_gap_2024_pp.agg(["min", "max"]).to_string(), flush=True)


if __name__ == "__main__":
    main()
