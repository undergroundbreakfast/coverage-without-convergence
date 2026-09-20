"""Summarize aggregate scenario results without drafting manuscript responses."""
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent
A = HERE / "analysis"


def main():
    s = pd.read_csv(A/"scenario_summary.csv")
    e = pd.read_csv(A/"exact_expected_coverage.csv")
    defs = pd.read_csv(A/"scenario_definitions.csv")
    observed = s[s.scenario.eq("observed")].set_index("group")
    old = pd.read_csv(HERE.parent/"v138_revision/analysis/spatial_metrics.csv")
    old = old[old.definition.eq("primary")].set_index("year")
    rows = []
    for name in ["observed"]+list(defs.scenario):
        if name == "observed":
            national = observed.loc["National"]
            row = {"scenario": name, "label": "Observed reports", "coverage22_pct": national.coverage_2022_pct,
                   "coverage24_pct": national.coverage_2024_pct, "change_pp": national.change_pp,
                   "outside_both_millions": national.outside_both_pct/100*331.449208,
                   "gini22": old.loc[2022,"gini"], "gini24": old.loc[2024,"gini"]}
            for prefix, short in [("RUCC 4-6", "rucc46"),("RUCC 7-9", "rucc79")]:
                row[f"{short}_q4_minus_q1_gain_pp"] = observed.loc[prefix+" Q4","change_pp"]-observed.loc[prefix+" Q1","change_pp"]
        else:
            ex = e[e.scenario.eq(name)].set_index("group")
            si = s[s.scenario.eq(name)].set_index("group")
            national = ex.loc["National"]
            row = {"scenario": name, "label": defs.set_index("scenario").loc[name,"label"],
                   "coverage22_pct": national.coverage_2022_pct, "coverage24_pct": national.coverage_2024_pct,
                   "change_pp": national.change_pp, "outside_both_millions": national.outside_both_pct/100*331.449208,
                   "gini22": si.loc["National","gini22_mean"], "gini24": si.loc["National","gini24_mean"]}
            for prefix, short in [("RUCC 4-6", "rucc46"),("RUCC 7-9", "rucc79")]:
                row[f"{short}_q4_minus_q1_gain_pp"] = ex.loc[prefix+" Q4","change_pp"]-ex.loc[prefix+" Q1","change_pp"]
                row[f"{short}_simulation_p025"] = si.loc[prefix+" Q4-Q1","change_pp_p025"]
                row[f"{short}_simulation_p975"] = si.loc[prefix+" Q4-Q1","change_pp_p975"]
        rows.append(row)
    key = pd.DataFrame(rows)
    key.to_csv(A/"key_results.csv", index=False)
    print(key.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
