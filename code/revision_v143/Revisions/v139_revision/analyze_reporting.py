"""County-adjusted reporting diagnostics on the unchanged v138 hospital frame.

Only aggregate coefficients, diagnostics and public county context are written.
This is a reporting analysis, not imputation or a correction of spatial access.
"""
from pathlib import Path
import json
import sys
from zipfile import ZipFile

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy.stats import chi2

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
sys.path.insert(0, str(BASE))
from analyze_revision import hospitals, panel, sha, RUN
from analyze_context import context, ct_codes

OUT = HERE / "analysis"
BASE_TERMS = "C(size) + C(rurality)"
FULL_TERMS = BASE_TERMS + " + income_10k + log2_density + C(ownership) + general_medical + system_name_recorded"


def county_context():
    path = HERE / "private/2020_Gaz_counties_national.zip"
    with ZipFile(path) as z:
        names = [s for s in z.namelist() if s.endswith('.txt')]
        assert len(names) == 1
        with z.open(names[0]) as f:
            gaz = pd.read_csv(f, sep="\t", dtype={"GEOID": str})
    gaz.columns = gaz.columns.str.strip()
    assert gaz.GEOID.is_unique
    pop = panel().groupby("county_fips").POPULATION.sum()
    d = pd.DataFrame({"population2020": pop})
    d["land_sqmi2020"] = gaz.set_index("GEOID").ALAND_SQMI
    d["density2020"] = d.population2020 / d.land_sqmi2020
    assert len(d) == 3143 and d.notna().all().all() and d.density2020.gt(0).all()
    d.to_csv(OUT / "county_density_context.csv")
    return d


def ownership(value):
    if value.startswith("Nongovt."):return "Nonprofit"
    if value.startswith("Investor-owned"):return "For-profit"
    if value.startswith("Govt. (non federal)"):return "Nonfederal government"
    if value.startswith("Govt. (federal)") or value.startswith("Department of Defense"):return "Federal government"
    raise ValueError(f"Unmapped control category: {value}")


def main():
    OUT.mkdir(exist_ok=True)
    c = county_context()
    rucc, income = context()
    coef, diagnostics, exclusions, marginal, summary = [], [], [], [], []
    for year in (2022, 2024):
        h, a = hospitals(year)
        h["county_fips"] = h.county_fips.astype(str).str.zfill(5)
        h["county2023"] = ct_codes(h, "county_fips")
        h["rurality"] = pd.cut(h.county2023.map(rucc), [0, 3, 6, 9], labels=["Metro", "Nonmetro 4-6", "Nonmetro 7-9"])
        h["income_10k"] = h.county_fips.map(income) / 10000
        h["log2_density"] = np.log2(h.county_fips.map(c.density2020))
        h["ownership"] = pd.Categorical(h.cntrl.map(ownership), categories=["Nonprofit", "For-profit", "Nonfederal government", "Federal government"])
        h["general_medical"] = h.serv.eq("General medical and surgical").astype(int)
        h["system_name_recorded"] = h.sysname.fillna("").astype(str).str.strip().ne("").astype(int)
        h["answer"] = h.any_answer.astype(int)
        named = [x for x in a.columns if x not in ["aitiot", "clnoai"]]
        h["all_named"] = a[named].notna().all(axis=1).astype(int)
        required = ["size", "rurality", "income_10k", "log2_density", "ownership", "general_medical", "system_name_recorded"]
        complete = h.dropna(subset=required).copy()
        missing = h[required].isna()
        exclusions.append({"year": year, "frame": len(h), "included": len(complete), "excluded": int(missing.any(axis=1).sum()),
                           "missing_by_field_nonexclusive": missing.sum().astype(int).to_dict(),
                           "excluded_responders": int(h.loc[missing.any(axis=1), "answer"].sum()),
                           "ct_included": int(complete.county_fips.str.startswith("09").sum())})
        summary.append({"year": year, "frame":len(h), "any_answer":int(h.answer.sum()), "all_named":int(h.all_named.sum()),
                        "all_items":int(h.all_answer.sum()), "resolved":int(h.composite_resolved.sum())})
        specifications = [("base_same_sample", "answer", BASE_TERMS, complete),
                          ("extended", "answer", FULL_TERMS, complete),
                          ("extended_no_ct", "answer", FULL_TERMS, complete.loc[~complete.county_fips.str.startswith("09")])]
        if year == 2024:
            specifications.append(("named_completeness", "all_named", FULL_TERMS, complete))
        for name, outcome, rhs, sample in specifications:
            model = smf.glm(f"{outcome} ~ {rhs}", data=sample, family=sm.families.Binomial())
            assert np.linalg.matrix_rank(model.exog) == model.exog.shape[1]
            fit = model.fit(cov_type="cluster", cov_kwds={"groups":sample.county_fips, "use_correction":True}, maxiter=100)
            assert fit.converged and np.isfinite(fit.params).all() and np.isfinite(fit.bse).all()
            ci = fit.conf_int()
            pred = np.asarray(fit.predict(sample))
            assert ((pred > 0) & (pred < 1)).all()
            for term in fit.params.index:
                coef.append({"year":year,"model":name,"outcome":outcome,"n":len(sample),"counties":sample.county_fips.nunique(),"term":term,
                             "log_odds":fit.params[term],"cluster_se":fit.bse[term],"odds_ratio":np.exp(fit.params[term]),
                             "lower95":np.exp(ci.loc[term,0]),"upper95":np.exp(ci.loc[term,1]),"p_value":fit.pvalues[term]})
            geographic = [s for s in fit.params.index if "rurality" in s or s in ["income_10k","log2_density"]]
            if name == "base_same_sample":geographic=[s for s in fit.params.index if "rurality" in s]
            idx = [fit.params.index.get_loc(s) for s in geographic]
            b = np.asarray(fit.params)[idx]
            cov = np.asarray(fit.cov_params())[np.ix_(idx,idx)]
            wald = float(b @ np.linalg.solve(cov,b))
            diagnostics.append({"year":year,"model":name,"n":len(sample),"responses":int(sample[outcome].sum()),
                                "counties":sample.county_fips.nunique(),"parameters":len(fit.params),"converged":bool(fit.converged),
                                "minimum_probability":pred.min(),"p01_probability":np.quantile(pred,.01),"median_probability":np.median(pred),
                                "p99_probability":np.quantile(pred,.99),"maximum_probability":pred.max(),
                                "fraction_below_0_05":np.mean(pred<.05),"brier_in_sample":np.mean((sample[outcome].to_numpy()-pred)**2),
                                "joint_geography_wald":wald,"joint_geography_df":len(idx),"joint_geography_p":chi2.sf(wald,len(idx))})
            if name == "extended":
                for group in ["Metro","Nonmetro 4-6","Nonmetro 7-9"]:
                    simulated = sample.copy()
                    simulated["rurality"] = pd.Categorical([group]*len(sample),categories=h.rurality.cat.categories)
                    marginal.append({"year":year,"rurality":group,"standardized_response_pct":100*fit.predict(simulated).mean(),
                                     "interpretation":"model-standardized over hospital covariates; descriptive, not a causal intervention"})
            print(year,name,"n",len(sample),"joint geography p",chi2.sf(wald,len(idx)),flush=True)
    pd.DataFrame(coef).to_csv(OUT/"reporting_models_extended.csv",index=False)
    pd.DataFrame(diagnostics).to_csv(OUT/"reporting_model_diagnostics.csv",index=False)
    pd.DataFrame(marginal).to_csv(OUT/"reporting_standardized_probabilities.csv",index=False)
    pd.DataFrame(summary).to_csv(OUT/"reporting_definitions.csv",index=False)
    (OUT/"reporting_exclusions.json").write_text(json.dumps(exclusions,indent=2)+"\n")
    manifest={"analysis":"Exploratory response diagnostics; no IPW, Tobit, adoption imputation or spatial recalculation",
              "response":"At least one determinate AI-item answer; unknown is not a verified no",
              "named_completeness":"2024 all 12 named items determinate, excluding Other operational and Other clinical",
              "models":"Separate waves; binomial logit; small-sample-corrected county-cluster sandwich covariance; normal Wald 95% intervals",
              "controls":"Staffed-bed size group, RUCC group, fixed 2024-release CHR income per $10,000, log2 2020 county persons per land square mile, ownership, general medical/surgical service, presence of a recorded system name",
              "system_caution":"Recorded system name is a proxy; blank does not verify independent status",
              "ct":"Income, density and clustering use legacy counties; RUCC uses reconciled planning-region geography. Excluding Connecticut is a separate sensitivity.",
              "density":"Fixed 2020 Census block-group populations summed by legacy county / 2020 Gazetteer land square miles; no water area",
              "sources":[{"path":str(p),"sha256":sha(p)} for p in [HERE/"private/2020_Gaz_counties_national.zip",BASE/"private/chr2024.csv",BASE/"private/rucc2023.csv"] + [RUN/f"years/{y}/hospital_ai_robotics_enriched_{y}.parquet" for y in (2022,2024)]],
              "gazetteer_url":"https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_counties_national.zip",
              "diagnostics_caution":"Joint tests describe measured response differences, not a test of MAR or the presence/absence of bias. In-sample fit is not external validation. Analyses are not selected by statistical significance."}
    (OUT/"reporting_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")


if __name__=="__main__":main()
