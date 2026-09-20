"""Fixed-frame, item-level missing-status spatial scenarios. No database writes."""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import warnings

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/paper2-income-mpl")
import numpy as np
import pandas as pd
from scipy.special import expit, logit
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.neighbors import BallTree
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
PREVIOUS = HERE.parent / "v139_revision"
sys.path.insert(0, str(BASE))
from analyze_revision import (hospitals, panel, points, distance, gini, sha,
                              RUN, PANEL, RADIUS, MINUTES_PER_MILE)
from analyze_context import context, ct_codes
sys.path.insert(0, str(PREVIOUS))
from analyze_reporting import ownership

OUT = HERE / "analysis"
PRIVATE = HERE / "private"
SEED = 20260919
YEARS = (2022, 2024)
CAT = ["size", "rurality", "ownership", "general_medical", "system_recorded"]
NUM = ["income_10k", "log2_density"]
SCENARIOS = [
    ("central", "Income-aware; positively dependent items", "positive", 1., 0., True, True),
    ("independent_items", "Income-aware; independent missing items", "independent", 1., 0., True, True),
    ("half_odds", "Missing-item odds x0.5", "positive", .5, 0., True, True),
    ("double_odds", "Missing-item odds x2", "positive", 2., 0., True, True),
    ("favor_poor", "Missing-item odds tilted toward poorer counties", "positive", 1., -1., True, True),
    ("favor_rich", "Missing-item odds tilted toward richer counties", "positive", 1., 1., True, True),
    ("no_income", "Same predictors except income", "positive", 1., 0., False, True),
    ("independent_waves", "Central; independent wave draws", "positive", 1., 0., True, False),
    ("named_items_only", "No imputation of optional Other items", "positive", 1., 0., True, True),
    ("adverse_wave_odds", "Missing odds x2 in 2022, x0.5 in 2024", "positive", 1., 0., True, True),
    ("reverse_wave_odds", "Missing odds x0.5 in 2022, x2 in 2024", "positive", 1., 0., True, True),
]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=lambda x: x.item()) + "\n")


def predictor_frame(year):
    h, answers = hospitals(year)
    h = h.reset_index(drop=True)
    answers = answers.reset_index(drop=True)
    rucc, income = context()
    density = pd.read_csv(PREVIOUS / "analysis/county_density_context.csv",
                          dtype={"county_fips": str}).set_index("county_fips").density2020
    h["county_fips"] = h.county_fips.astype(str).str.zfill(5)
    h["county2023"] = ct_codes(h, "county_fips")
    h["rurality"] = pd.cut(h.county2023.map(rucc), [0, 3, 6, 9],
                           labels=["Metro", "Nonmetro 4-6", "Nonmetro 7-9"])
    h["income_10k"] = h.county_fips.map(income) / 10000
    h["log2_density"] = np.log2(h.county_fips.map(density))
    h["ownership"] = h.cntrl.map(ownership)
    h["general_medical"] = h.serv.eq("General medical and surgical").map({True: "Yes", False: "No"})
    h["system_recorded"] = h.sysname.fillna("").astype(str).str.strip().ne("").map({True: "Yes", False: "No"})
    for col in CAT:
        h[col] = h[col].astype("object").where(h[col].notna(), "Missing").astype(str)
    return h, answers


def estimator(include_income=True):
    num = NUM if include_income else ["log2_density"]
    numeric = Pipeline([("fill", SimpleImputer(strategy="median", add_indicator=True)),
                        ("scale", StandardScaler())])
    pre = ColumnTransformer([("num", numeric, num),
                             ("cat", OneHotEncoder(handle_unknown="ignore"), CAT)])
    return Pipeline([("pre", pre), ("logit", LogisticRegression(C=1., max_iter=2000, solver="lbfgs"))])


def fit_items(h, a, year, include_income=True):
    predictions = np.empty(a.shape)
    diagnostics, calibration, coefficients = [], [], []
    for j, item in enumerate(a):
        known = a[item].notna().to_numpy()
        y = a.loc[known, item].ge(1 if year == 2022 else 3).astype(int).to_numpy()
        sample = h.loc[known].reset_index(drop=True)
        assert 0 < y.sum() < len(y)
        model = estimator(include_income)
        model.fit(sample, y)
        assert model.named_steps["logit"].n_iter_[0] < 2000
        predictions[:, j] = model.predict_proba(h)[:, 1]
        oof = np.full(len(y), np.nan)
        for train, test in GroupKFold(5).split(sample, y, sample.county_fips):
            assert not set(sample.iloc[train].county_fips) & set(sample.iloc[test].county_fips)
            fit = estimator(include_income).fit(sample.iloc[train], y[train])
            assert fit.named_steps["logit"].n_iter_[0] < 2000
            oof[test] = fit.predict_proba(sample.iloc[test])[:, 1]
        assert np.isfinite(oof).all()
        missing = ~known
        row = {"year": year, "model": "income" if include_income else "no_income",
               "item": item, "known": int(known.sum()), "positive": int(y.sum()),
               "missing": int(missing.sum()), "cv_auc": roc_auc_score(y, oof),
               "cv_brier": brier_score_loss(y, oof), "cv_mean_prediction": oof.mean(),
               "known_positive_fraction": y.mean(),
               "missing_mean_prediction": predictions[missing, j].mean(),
               "missing_p01_prediction": np.quantile(predictions[missing, j], .01),
               "missing_p99_prediction": np.quantile(predictions[missing, j], .99)}
        diagnostics.append(row)
        bins = pd.qcut(oof, 5, labels=False, duplicates="drop")
        for b in np.unique(bins):
            ix = bins == b
            calibration.append({"year": year, "model": row["model"], "item": item,
                                "bin": int(b)+1, "n": int(ix.sum()),
                                "predicted": oof[ix].mean(), "observed": y[ix].mean()})
        for name, coefficient in zip(model.named_steps["pre"].get_feature_names_out(),
                                     model.named_steps["logit"].coef_[0]):
            coefficients.append({"year": year, "model": row["model"], "item": item,
                                 "term": name, "penalized_coefficient": coefficient})
        coefficients.append({"year": year, "model": row["model"], "item": item,
                             "term": "intercept", "penalized_coefficient": model.named_steps["logit"].intercept_[0]})
        print(f"Fitted {year} {row['model']} {item}: {len(y)} answers, CV AUC {row['cv_auc']:.3f}", flush=True)
    return predictions, diagnostics, calibration, coefficients


def probability(h, answers, item_p, dependence, odds, tilt, cut):
    # Income tilt affects only missing-item probabilities. No observed answers change.
    z = np.clip((h.income_10k.to_numpy()*10000 - cut[1]) / (cut[2]-cut[0]), -1, 1)
    z = np.nan_to_num(z, nan=0.)
    adjusted = expit(logit(np.clip(item_p, 1e-9, 1-1e-9)) + np.log(odds) + tilt*np.log(2)*z[:, None])
    unknown_p = np.where(answers.isna(), adjusted, 0.)
    if dependence == "positive":
        p = unknown_p.max(axis=1)
    else:
        p = 1 - np.prod(1-unknown_p, axis=1)
    p[h.ai_flag.eq(1)] = 1.
    assert np.all(p[h.ai_flag.eq(1)] == 1)
    assert np.all(p[h.all_answer & h.ai_flag.eq(0)] == 0)
    assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
    return p


def candidate_edges(coords, h, baseline, year):
    cache = PRIVATE / f"candidates_{year}.npz"
    if cache.exists():
        with np.load(cache) as z:
            return {key: z[key] for key in z.files}
    unknown = np.flatnonzero(~h.composite_resolved.to_numpy())
    tree = BallTree(np.deg2rad(h.loc[unknown, ["latitude", "longitude"]].to_numpy()), metric="haversine")
    indices, dist = tree.query_radius(coords, r=baseline/RADIUS+1e-12, return_distance=True)
    rows = np.repeat(np.arange(len(coords), dtype=np.int32), [len(x) for x in indices])
    cols = unknown[np.concatenate(indices)].astype(np.int32)
    miles = np.concatenate(dist)*RADIUS
    miles[miles == 0] = .1
    keep = miles < baseline[rows]
    result = {"rows": rows[keep], "cols": cols[keep], "miles": miles[keep]}
    np.savez_compressed(cache, **result)
    print(f"Exact spatial candidates {year}: {keep.sum():,} edges", flush=True)
    return result


def update_distance(baseline, edges, selected):
    result = baseline.copy()
    keep = selected[edges["cols"]]
    np.minimum.at(result, edges["rows"][keep], edges["miles"][keep])
    return result


def expected_coverage(baseline, edges, p):
    inside = edges["miles"]*MINUTES_PER_MILE <= 30
    sums = np.bincount(edges["rows"][inside],
                       weights=np.log1p(-np.minimum(p[edges["cols"][inside]], 1-1e-15)),
                       minlength=len(baseline))
    value = -np.expm1(sums)
    value[baseline*MINUTES_PER_MILE <= 30] = 1.
    return value


def expected_outside_both(baselines, edges, p, ids, shared, expected):
    if not shared:
        return (1-expected[2022])*(1-expected[2024])
    row_parts, id_parts, probability_parts = [], [], []
    for year in YEARS:
        edge = edges[year]
        keep = edge['miles']*MINUTES_PER_MILE <= 30
        row_parts.append(edge['rows'][keep])
        id_parts.append(ids[year][edge['cols'][keep]])
        probability_parts.append(p[year][edge['cols'][keep]])
    rows = np.concatenate(row_parts)
    destinations = np.concatenate(id_parts)
    values = np.concatenate(probability_parts)
    order = np.lexsort((destinations, rows))
    rows, destinations, values = rows[order], destinations[order], values[order]
    starts = np.r_[0, np.flatnonzero((np.diff(rows) != 0) | (np.diff(destinations) != 0))+1]
    # A shared latent uniform selects a destination in either wave at max(p22,p24).
    union = np.maximum.reduceat(values, starts)
    sums = np.bincount(rows[starts], weights=np.log1p(-np.minimum(union,1-1e-15)),
                       minlength=len(baselines[2022]))
    result = np.exp(sums)
    observed_inside = ((baselines[2022]*MINUTES_PER_MILE <= 30)
                       | (baselines[2024]*MINUTES_PER_MILE <= 30))
    result[observed_inside] = 0.
    assert np.all(result+1e-12 >= (1-expected[2022])*(1-expected[2024]))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=300)
    parser.add_argument("--fit-only", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    PRIVATE.mkdir(exist_ok=True)
    source_files = [PANEL, BASE/"private/block_group_points.csv", BASE/"private/block_group_context.csv",
                    BASE/"private/chr2024.csv", BASE/"private/rucc2023.csv", PREVIOUS/"analysis/county_density_context.csv",
]
    source_files += [RUN/f"years/{y}/hospital_ai_robotics_enriched_{y}.parquet" for y in YEARS]
    sources = [{"path": str(p), "sha256": sha(p)} for p in source_files]
    d = panel()
    _, coords = points(d)
    ctx = pd.read_csv(BASE/"private/block_group_context.csv", dtype={"GEOID": str, "county_fips": str}).set_index("GEOID").loc[d.GEOID]
    cut = np.asarray(json.loads((BASE/"analysis/context_manifest.json").read_text())["quartile_cutpoints"])
    w = d.POPULATION.to_numpy(dtype=float)
    county_codes, county_names = pd.factorize(d.county_fips, sort=True)
    county_pop = np.bincount(county_codes, weights=w)
    hs, aa, probs, edges, baselines = {}, {}, {}, {}, {}
    diagnostics, calibration, coefficients, fills, checks = [], [], [], [], {}
    for year in YEARS:
        h, a = predictor_frame(year)
        hs[year], aa[year] = h, a
        fills.append({"year": year, "hospitals": len(h), "any_answer": int(h.any_answer.sum()),
                      "resolved": int(h.composite_resolved.sum()), "positive": int(h.ai_flag.sum()),
                      "unknown_composite": int((~h.composite_resolved).sum()),
                      "missing_income": int(h.income_10k.isna().sum()),
                      "missing_density": int(h.log2_density.isna().sum()),
                      "missing_size": int(h['size'].eq('Missing').sum()),
                      "missing_rurality": int(h.rurality.eq('Missing').sum())})
        cache = PRIVATE/f"item_predictions_{year}.npz"
        if cache.exists():
            z = np.load(cache)
            probs[year] = {key: z[key] for key in z.files}
            saved = json.loads((PRIVATE/f"model_metadata_{year}.json").read_text())
            diagnostics.extend(saved["diagnostics"])
            calibration.extend(saved["calibration"])
            coefficients.extend(saved["coefficients"])
        else:
            probs[year] = {}
            saved = {"diagnostics": [], "calibration": [], "coefficients": []}
            for use_income in (True, False):
                label = "income" if use_income else "no_income"
                p, diag, cal, coef = fit_items(h, a, year, use_income)
                probs[year][label] = p
                diagnostics.extend(diag); calibration.extend(cal); coefficients.extend(coef)
                saved["diagnostics"].extend(diag)
                saved["calibration"].extend(cal)
                saved["coefficients"].extend(coef)
            np.savez_compressed(cache, **probs[year])
            write_json(PRIVATE/f"model_metadata_{year}.json", saved)
        baselines[year] = d[f"drive_{year}"].to_numpy()/MINUTES_PER_MILE
        direct, _ = distance(coords, h[h.ai_flag.eq(1)])
        assert np.max(np.abs(direct-baselines[year])) < 1e-7
        edges[year] = candidate_edges(coords, h, baselines[year], year)
        test_choice = h.ai_flag.eq(1).to_numpy() | ((~h.composite_resolved) & (np.random.default_rng(SEED).random(len(h)) < .5))
        sparse = update_distance(baselines[year], edges[year], np.asarray(test_choice))
        fresh, _ = distance(coords, h[test_choice])
        checks[f"sparse_max_distance_difference_{year}"] = float(np.max(np.abs(sparse-fresh)))
        assert checks[f"sparse_max_distance_difference_{year}"] < 1e-7
        all_distance, _ = distance(coords, h)
        checks[f"all_hospital_coverage_{year}"] = float(100*np.average(all_distance*MINUTES_PER_MILE <= 30, weights=w))
    if diagnostics:
        pd.DataFrame(diagnostics).to_csv(OUT/"item_model_diagnostics.csv", index=False)
        pd.DataFrame(calibration).to_csv(OUT/"item_model_calibration.csv", index=False)
        pd.DataFrame(coefficients).to_csv(OUT/"item_model_coefficients.csv", index=False)
    pd.DataFrame(fills).to_csv(OUT/"frame_and_missingness.csv", index=False)
    if args.fit_only:
        return
    groups = {"National": np.ones(len(d), dtype=bool),
              "Contiguous US": ~d.state_fips.isin(["02", "15"]).to_numpy()}
    q = np.searchsorted(cut, ctx.income, side="left")+1
    for rurality, prefix in [("Nonmetro 4-6", "RUCC 4-6"), ("Nonmetro 7-9", "RUCC 7-9")]:
        for quartile in range(1, 5):
            groups[f"{prefix} Q{quartile}"] = (ctx.rurality.eq(rurality).to_numpy() & (q == quartile)
                                               & ~d.state_fips.eq("09").to_numpy())
    group_weights = {name: (ix, w[ix], w[ix].sum()) for name, ix in groups.items()}
    def summarize(c22, c24, outside):
        return {name: {"population": int(total),
                        "coverage_2022_pct": 100*np.sum(c22[ix]*ww)/total,
                        "coverage_2024_pct": 100*np.sum(c24[ix]*ww)/total,
                        "change_pp": 100*np.sum((c24[ix]-c22[ix])*ww)/total,
                        "outside_both_pct": 100*np.sum(outside[ix]*ww)/total}
                for name, (ix, ww, total) in group_weights.items()}
    observed22 = (baselines[2022]*MINUTES_PER_MILE <= 30).astype(float)
    observed24 = (baselines[2024]*MINUTES_PER_MILE <= 30).astype(float)
    observed = summarize(observed22, observed24, (1-observed22)*(1-observed24))
    previous = pd.read_csv(BASE/"analysis/rural_income_coverage.csv")
    for row in previous.itertuples():
        name = f"{row.rurality.replace('Nonmetro', 'RUCC')} Q{row.quartile}"
        assert abs(observed[name]["change_pp"]-row.change_pp) < 1e-9
        assert observed[name]["population"] == row.population
    summary_rows = [{"scenario": "observed", "group": name, **vals} for name, vals in observed.items()]
    exact_rows = []
    draw_rows = []
    county = pd.DataFrame({"county_fips": county_names, "population": county_pop.astype(int)})
    def county_mean(value):
        return np.bincount(county_codes, weights=value*w, minlength=len(county_names))/county_pop
    county["observed_coverage_2022_pct"] = 100*county_mean(observed22)
    county["observed_coverage_2024_pct"] = 100*county_mean(observed24)
    county["observed_outside_both_pct"] = 100*county_mean((1-observed22)*(1-observed24))
    all_ids = sorted(set(hs[2022].hospital_id.astype(str)) | set(hs[2024].hospital_id.astype(str)))
    idmap = {name: i for i, name in enumerate(all_ids)}
    indices = {y: hs[y].hospital_id.astype(str).map(idmap).to_numpy() for y in YEARS}
    grid = []
    for name, label, dep, odds, tilt, income, shared in SCENARIOS:
        p = {}
        for y in YEARS:
            item_p = probs[y]["income" if income else "no_income"]
            answers = aa[y]
            if name == "named_items_only" and y == 2024:
                named = ~answers.columns.isin(["aitiot", "clnoai"])
                answers = answers.loc[:, named]
                item_p = item_p[:, named]
            effective_odds = odds
            if name == "adverse_wave_odds": effective_odds = 2. if y == 2022 else .5
            if name == "reverse_wave_odds": effective_odds = .5 if y == 2022 else 2.
            p[y] = probability(hs[y], answers, item_p, dep, effective_odds, tilt, cut)
        expected = {y: expected_coverage(baselines[y], edges[y], p[y]) for y in YEARS}
        outside_expected = expected_outside_both(baselines, edges, p, indices, shared, expected)
        exact = summarize(expected[2022], expected[2024], outside_expected)
        for group, vals in exact.items():
            exact_rows.append({"scenario": name, "group": group, **vals})
        for year in YEARS:
            county[f"{name}_coverage_{year}_pct"] = 100*county_mean(expected[year])
        if name == "central":
            np.savez_compressed(PRIVATE/"central_expected_blockgroups.npz", expected22=expected[2022], expected24=expected[2024])
        grid.append({"scenario": name, "label": label, "dependence": dep, "odds_multiplier": odds,
                     "income_tilt": tilt, "income_predictor": income, "shared_wave_uniform": shared,
                     "missing_odds_2022": 2. if name == "adverse_wave_odds" else (.5 if name == "reverse_wave_odds" else odds),
                     "missing_odds_2024": .5 if name == "adverse_wave_odds" else (2. if name == "reverse_wave_odds" else odds),
                     "impute_optional_other": name != "named_items_only",
                     "expected_destinations22": p[2022].sum(), "expected_destinations24": p[2024].sum()})
        rng = np.random.default_rng(SEED)
        outside_sum = np.zeros(len(d))
        local = []
        start = time.monotonic()
        for rep in range(args.draws):
            u = rng.random(len(all_ids))
            draws = {}
            selected = {}
            for year in YEARS:
                uy = u[indices[year]] if shared or year == 2022 else rng.random(len(hs[year]))
                selected[year] = uy < p[year]
                draws[year] = update_distance(baselines[year], edges[year], selected[year])
                assert np.all(draws[year] <= baselines[year]+1e-10)
            c22 = (draws[2022]*MINUTES_PER_MILE <= 30).astype(float)
            c24 = (draws[2024]*MINUTES_PER_MILE <= 30).astype(float)
            outside = (1-c22)*(1-c24)
            outside_sum += outside
            stats = summarize(c22, c24, outside)
            for group, vals in stats.items():
                row = {"scenario": name, "replicate": rep, "group": group, **vals}
                if group == "National":
                    row.update({"gini22": gini(draws[2022], w), "gini24": gini(draws[2024], w),
                                "destinations22": int(selected[2022].sum()), "destinations24": int(selected[2024].sum())})
                    row["gini_change"] = row["gini24"]-row["gini22"]
                local.append(row)
            for prefix in ("RUCC 4-6", "RUCC 7-9"):
                local.append({"scenario": name, "replicate": rep, "group": f"{prefix} Q4-Q1",
                              "change_pp": stats[f"{prefix} Q4"]["change_pp"]-stats[f"{prefix} Q1"]["change_pp"]})
            if (rep+1) % 100 == 0:
                print(f"{name}: {rep+1}/{args.draws} networks, {time.monotonic()-start:.1f}s", flush=True)
        county[f"{name}_outside_both_pct"] = 100*county_mean(outside_expected)
        draw_rows.extend(local)
        local = pd.DataFrame(local)
        for group, frame in local.groupby("group", sort=False):
            entry = {"scenario": name, "group": group}
            for metric in ["coverage_2022_pct", "coverage_2024_pct", "change_pp", "outside_both_pct", "gini22", "gini24", "gini_change", "destinations22", "destinations24"]:
                if frame[metric].notna().any():
                    val = frame[metric].dropna().to_numpy()
                    entry.update({metric+"_mean": val.mean(), metric+"_p025": np.quantile(val, .025),
                                  metric+"_p975": np.quantile(val, .975), metric+"_mcse": val.std(ddof=1)/np.sqrt(len(val))})
                    if (metric.startswith("coverage_") or metric == "outside_both_pct") and group in exact:
                        error = abs(val.mean()-exact[group][metric])
                        assert error < max(6*val.std(ddof=1)/np.sqrt(len(val)), .03)
            summary_rows.append(entry)
        pd.DataFrame(draw_rows).to_csv(OUT/"simulation_draws.csv", index=False)
        pd.DataFrame(summary_rows).to_csv(OUT/"scenario_summary.csv", index=False)
        pd.DataFrame(exact_rows).to_csv(OUT/"exact_expected_coverage.csv", index=False)
        county.to_csv(OUT/"county_map_values.csv", index=False)
        print(name, "national exact coverage", round(exact["National"]["coverage_2022_pct"], 2),
              round(exact["National"]["coverage_2024_pct"], 2), flush=True)
    pd.DataFrame(grid).to_csv(OUT/"scenario_definitions.csv", index=False)
    checks["sources_unchanged"] = all(sha(Path(s["path"])) == s["sha256"] for s in sources)
    assert checks["sources_unchanged"]
    checks.update({"original_income_contrasts_reproduced": True, "observed_statuses_preserved": True,
                   "exact_expectation_checks_passed": True, "county_disjoint_validation": True,
                   "block_groups": len(d), "population": int(w.sum()), "draws_per_scenario": args.draws,
                   "scenario_count": len(SCENARIOS)})
    write_json(OUT/"verification.json", checks)
    import sklearn, statsmodels, geopandas
    write_json(OUT/"manifest.json", {"seed": SEED, "draws": args.draws, "sources": sources,
               "database": "Read-only MCP connection verified 2026-09-19; no live database records substituted for frozen inputs",
               "cutpoints": cut.tolist(), "point_method": "Original EPSG5070 representative points transformed to EPSG4326",
               "minutes_per_mile": MINUTES_PER_MILE, "earth_radius_miles": RADIUS,
               "model": "Per-item L2 binomial logit, C=1; 5-fold county-grouped validation, fixed coefficients for simulations",
               "interval": "Conditional 2.5-97.5 simulation percentiles, not confidence intervals",
               "versions": {"numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
                            "statsmodels": statsmodels.__version__, "geopandas": geopandas.__version__}})
    print("All spatial sensitivity checks passed.", flush=True)


if __name__ == "__main__":
    main()
