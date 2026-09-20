"""Public county-context joins and descriptive models on frozen hospital inputs."""

import json
import numpy as np
import pandas as pd
import geopandas as gpd
import statsmodels.api as sm
import statsmodels.formula.api as smf

from analyze_revision import HERE, ROOT, RUN, OUT, PRIVATE, SHAPES, SEED, panel, points, hospitals, sha, write_json


def context():
    r = pd.read_csv(PRIVATE / "rucc2023.csv", encoding="latin1", dtype={"FIPS": str})
    r = r.loc[r.Attribute == "RUCC_2023", ["FIPS", "Value"]].rename(columns={"FIPS": "county2023", "Value": "rucc"})
    r.rucc = pd.to_numeric(r.rucc)
    assert r.county2023.is_unique
    c = pd.read_csv(PRIVATE / "chr2024.csv", skiprows=[1], dtype={"5-digit FIPS Code": str},
                    usecols=["5-digit FIPS Code", "Median Household Income raw value"])
    c = c.rename(columns={"5-digit FIPS Code": "county_fips", "Median Household Income raw value": "income"})
    return r.set_index("county2023").rucc, c.set_index("county_fips").income


def ct_codes(frame, county_field, latitude="latitude", longitude="longitude"):
    out = frame[county_field].copy()
    mask = out.str.startswith("09")
    ct = gpd.read_file(SHAPES / "tl_2024_us_county.shp", where="STATEFP = '09'").to_crs(4326)
    pts = gpd.GeoDataFrame(frame.loc[mask].copy(), geometry=gpd.points_from_xy(frame.loc[mask, longitude], frame.loc[mask, latitude]), crs=4326)
    joined = gpd.sjoin(pts, ct[["GEOID", "geometry"]].rename(columns={"GEOID": "new_county"}), predicate="within", how="left")
    assert joined.index.is_unique and joined.new_county.notna().all()
    out.loc[mask] = joined.new_county
    return out


def rates(group):
    w = group.POPULATION
    return {"population": int(w.sum()), "counties": group.county_fips.nunique(),
            "coverage_2022_pct": 100 * np.average(group.within_2022, weights=w),
            "coverage_2024_pct": 100 * np.average(group.within_2024, weights=w),
            "change_pp": 100 * np.average(group.within_2024 - group.within_2022, weights=w),
            "outside_both_pct": 100 * np.average((group.within_2022 == 0) & (group.within_2024 == 0), weights=w)}


def main():
    r, income = context()
    d = panel()
    p, _ = points(d)
    d[["latitude", "longitude"]] = p[["latitude", "longitude"]].to_numpy()
    d["county2023"] = ct_codes(d, "county_fips")
    d["rucc"] = d.county2023.map(r)
    assert d.rucc.notna().all()
    d["rurality"] = pd.cut(d.rucc, [0, 3, 6, 9], labels=["Metro", "Nonmetro 4-6", "Nonmetro 7-9"])
    d["income"] = d.county_fips.map(income)
    d["is_ct"] = d.state_fips.eq("09")
    ct = d[d.is_ct].groupby(["county_fips", "county2023", "rucc"], observed=True).POPULATION.sum().reset_index()
    ct.to_csv(OUT / "connecticut_geography_crosswalk.csv", index=False)
    pd.DataFrame([{"rurality": str(k), **rates(g)} for k, g in d.groupby("rurality", observed=True)]).to_csv(OUT / "rurality_coverage.csv", index=False)
    # Primary income groups retain a common county geography; Connecticut income
    # estimates describe legacy counties, not the new planning-region units.
    nonmetro = d[d.rucc.gt(3) & ~d.is_ct].copy()
    counties = nonmetro[["county_fips", "income"]].drop_duplicates()
    assert counties.income.notna().all()
    cut = counties.income.quantile([.25, .5, .75]).to_numpy()
    nonmetro["quartile"] = np.searchsorted(cut, nonmetro.income, side="left") + 1
    rows = []
    for (rurality, q), g in nonmetro.groupby(["rurality", "quartile"], observed=True):
        rows.append({"rurality": str(rurality), "quartile": int(q), **rates(g)})
    pd.DataFrame(rows).to_csv(OUT / "rural_income_coverage.csv", index=False)
    # Paired county bootstrap keeps both waves together and cut points fixed.
    nonmetro["covered22"] = nonmetro.POPULATION * nonmetro.within_2022
    nonmetro["covered24"] = nonmetro.POPULATION * nonmetro.within_2024
    cc = nonmetro.groupby(["rurality", "quartile", "county_fips"], observed=True)[["POPULATION", "covered22", "covered24"]].sum().reset_index()
    rng = np.random.default_rng(SEED)
    cirows = []
    for rurality in ["Nonmetro 4-6", "Nonmetro 7-9"]:
        arrays = {q: cc[(cc.rurality == rurality) & (cc.quartile == q)][["POPULATION", "covered22", "covered24"]].to_numpy() for q in [1, 4]}
        draws = []
        for _ in range(2000):
            rates_q = {}
            for q, a in arrays.items():
                totals = a[rng.integers(0, len(a), len(a))].sum(axis=0)
                rates_q[q] = 100 * (totals[2] - totals[1]) / totals[0]
            draws.append(rates_q[4] - rates_q[1])
        lo, hi = np.quantile(draws, [.025, .975])
        rr = {x["quartile"]: x for x in rows if x["rurality"] == rurality}
        cirows.append({"rurality": rurality, "q4_minus_q1_change_pp": rr[4]["change_pp"] - rr[1]["change_pp"], "lower95": lo, "upper95": hi})
    pd.DataFrame(cirows).to_csv(OUT / "rural_income_gain_intervals.csv", index=False)
    # This revision-stage robustness check uses halves, not four categories.
    med = counties.income.median()
    nonmetro["income_half"] = np.where(nonmetro.income <= med, "Lower half", "Upper half")
    pd.DataFrame([{"rurality": str(k[0]), "income_half": k[1], **rates(g)} for k, g in nonmetro.groupby(["rurality", "income_half"], observed=True)]).to_csv(OUT / "rural_income_halves.csv", index=False)
    withct = d[d.rucc.gt(3)].copy()
    withct["quartile"] = np.searchsorted(cut, withct.income, side="left") + 1
    assert withct.income.notna().all()
    pd.DataFrame([{"rurality": str(k[0]), "quartile": int(k[1]), **rates(g)} for k, g in withct.groupby(["rurality", "quartile"], observed=True)]).to_csv(OUT / "rural_income_ct_legacy_context_sensitivity.csv", index=False)
    strata, models = [], []
    for y in [2022, 2024]:
        h, _ = hospitals(y)
        h.county_fips = h.county_fips.astype(str).str.zfill(5)
        h["county2023"] = ct_codes(h, "county_fips")
        h["rucc"] = h.county2023.map(r)
        h["rurality"] = pd.cut(h.rucc, [0, 3, 6, 9], labels=["Metro", "Nonmetro 4-6", "Nonmetro 7-9"])
        for grouping, cols in [("size", ["size"]), ("rurality", ["rurality"]), ("size_by_rurality", ["size", "rurality"])]:
            for key, g in h.groupby(cols, observed=True, dropna=False):
                if not isinstance(key, tuple):
                    key = (key,)
                strata.append({"year": y, "grouping": grouping, **dict(zip(cols, map(str, key))), "hospitals": len(g), "any_answer": int(g.any_answer.sum()), "composite_resolved": int(g.composite_resolved.sum()), "positive": int(g.ai_flag.sum())})
        h["answer"] = h.any_answer.astype(int)
        for name, subset, outcome in [("reporting_availability", h, "answer"), ("qualifying_among_resolved", h[h.composite_resolved], "ai_flag")]:
            subset = subset.dropna(subset=["size", "rurality"]).copy()
            fit = smf.glm(f"{outcome} ~ C(size) + C(rurality)", data=subset, family=sm.families.Binomial()).fit(cov_type="HC1")
            conf = fit.conf_int()
            for term in fit.params.index:
                models.append({"year": y, "model": name, "n": len(subset), "term": term, "odds_ratio": np.exp(fit.params[term]), "lower95": np.exp(conf.loc[term, 0]), "upper95": np.exp(conf.loc[term, 1])})
    pd.DataFrame(strata).to_csv(OUT / "hospital_strata_frozen.csv", index=False)
    pd.DataFrame(models).to_csv(OUT / "hospital_models.csv", index=False)
    d[["GEOID", "county_fips", "county2023", "rucc", "rurality", "income"]].to_csv(PRIVATE / "block_group_context.csv", index=False)
    write_json("context_manifest.json", {"quartile_cutpoints": cut.tolist(), "median_cutpoint": med, "income_counties": len(counties),
        "income_population_primary": int(nonmetro.POPULATION.sum()), "ct_population_national_retained": int(d.loc[d.is_ct, "POPULATION"].sum()),
        "ct_nonmetro_population": int(d.loc[d.is_ct & d.rucc.gt(3), "POPULATION"].sum()),
        "ct_method": "Assign original representative points to 2024 Census planning-region polygons and join 2023 RUCC; retain legacy counties for bootstrap and CHR income. Primary rural-income comparison excludes CT's nonmetro portion because its CHR income units differ. Separate sensitivity retains it using legacy-county income context and unchanged non-CT cutpoints.",
        "bootstrap": "2000 paired county resamples within rurality and fixed income quartile; 95% percentile intervals; seed 20260912; conditional spatial uncertainty",
        "sources": [{"path": str(p), "sha256": sha(p)} for p in [PRIVATE / "rucc2023.csv", PRIVATE / "chr2024.csv", SHAPES / "tl_2024_us_county.shp"]]})
    print(pd.DataFrame(cirows).to_string(index=False), flush=True)


if __name__ == "__main__":
    main()
