"""County maps aggregate frozen block-group populations, never hospital records."""
import os
from pathlib import Path
import sys
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/paper2-income-mpl")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable
import geopandas as gpd
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent/"v138_revision"
sys.path.insert(0, str(BASE))
from analyze_revision import SHAPES
OUT = HERE/"figures"
PRIVATE = HERE/"private"
DATA = HERE/"analysis"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "pdf.fonttype": 42,
                     "axes.titleweight": "bold", "axes.spines.top": False, "axes.spines.right": False})

LABELS = {"observed": "Observed reports", "central": "Income-aware reference scenario",
          "half_odds": "Missing-item odds x0.5", "double_odds": "Missing-item odds x2",
          "favor_poor": "Tilt toward poorer counties", "favor_rich": "Tilt toward richer counties",
          "independent_items": "Independent missing items", "no_income": "Model without income",
          "independent_waves": "Independent waves",
          "named_items_only": "Optional Other not imputed",
          "adverse_wave_odds": "2022 odds x2 / 2024 x0.5",
          "reverse_wave_odds": "2022 odds x0.5 / 2024 x2"}
ORDER = list(LABELS)


def save(fig, name):
    fig.savefig(OUT/f"{name}.png", dpi=250, facecolor="white")
    plt.close(fig)


def county_geometry():
    path = PRIVATE/"county_display.parquet"
    if path.exists():
        return gpd.read_parquet(path)
    c = gpd.read_file(SHAPES/"tl_2024_us_county.shp")
    c = c[c.STATEFP.isin([f"{i:02d}" for i in range(1,57)]) & ~c.STATEFP.isin(["02", "15", "09"])].to_crs(5070)
    c = c[["GEOID", "geometry"]].rename(columns={"GEOID": "county_fips"})
    # Use the original block-group boundary union only for legacy Connecticut.
    b = gpd.read_parquet(BASE/"private/display_geometry.parquet")
    b = b[b.GEOID.str.startswith("09")].copy()
    b["county_fips"] = b.GEOID.str[:5]
    ct = b[["county_fips", "geometry"]].dissolve(by="county_fips").reset_index()
    c = gpd.GeoDataFrame(pd.concat([c, ct], ignore_index=True), crs=5070)
    c.geometry = c.geometry.simplify(100, preserve_topology=True)
    assert c.county_fips.is_unique
    c.to_parquet(path)
    return c


def map_figure(c, specifications, filename, title, footer, subtitle=None, source=None):
    fig = plt.figure(figsize=(14, 10.2))
    fig.suptitle(title, x=.045, ha="left", y=.975, fontsize=20, fontweight="bold")
    fig.text(.045, .937, subtitle or "Population-weighted county summaries from 2020 census block groups | Contiguous United States", color="#4B5560", fontsize=11)
    grid = fig.add_gridspec(2, 2, left=.045, right=.98, bottom=.20, top=.885, hspace=.37, wspace=.12)
    bounds = c.total_bounds
    for index, (column, label, cmap, norm, unit) in enumerate(specifications):
        ax = fig.add_subplot(grid[index//2, index%2])
        c.plot(column=column, ax=ax, cmap=cmap, norm=norm, linewidth=0, rasterized=True,
               missing_kwds={"color": "#EEEEEE"})
        ax.set_xlim(bounds[0]-50000, bounds[2]+50000)
        ax.set_ylim(bounds[1]-50000, bounds[3]+50000)
        ax.set_axis_off()
        ax.set_title(f"{'ABCD'[index]}  {label}", loc="left", fontsize=13, pad=9)
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), ax=ax, orientation="horizontal",
                          fraction=.045, pad=.035, aspect=35)
        cb.set_label(unit, fontsize=10, labelpad=3)
        cb.ax.tick_params(labelsize=9)
        cb.outline.set_visible(False)
    fig.text(.045, .061, footer, fontsize=10, linespacing=1.5, color="#424A53")
    fig.text(.045, .025, source or "Source: frozen AHA reports, Census block-group populations and boundaries; authors' exploratory simulations. Not a corrected map of actual AI deployment.", fontsize=8.5, color="#606870")
    save(fig, filename)


def main():
    OUT.mkdir(exist_ok=True)
    data = pd.read_csv(DATA/"county_map_values.csv", dtype={"county_fips": str})
    c = county_geometry().merge(data, on="county_fips", validate="one_to_one", how="left")
    assert len(c) == 3108 and c.population.notna().all()
    assert c[c.county_fips.str.startswith("12")].shape[0] == 67
    c["coverage_uplift"] = c.central_coverage_2024_pct - c.observed_coverage_2024_pct
    scenario_cols = [f"{name}_coverage_2024_pct" for name in ["central", "half_odds", "double_odds", "favor_poor", "favor_rich", "independent_items"]]
    c["scenario_spread"] = c[scenario_cols].max(axis=1)-c[scenario_cols].min(axis=1)
    map_figure(c, [
        ("observed_coverage_2024_pct", "Reported destinations, 2024", "viridis", Normalize(0,100), "Residents within 30 proxy minutes (%)"),
        ("central_coverage_2024_pct", "Income-aware scenario, 2024", "viridis", Normalize(0,100), "Expected residents within 30 proxy minutes (%)"),
        ("coverage_uplift", "Potential coverage hidden by missing answers", "YlOrBr", Normalize(0,100), "Scenario minus reported coverage (percentage points)"),
        ("scenario_spread", "Sensitivity to missing-status assumptions", "magma_r", Normalize(0,100), "Highest minus lowest expected coverage (percentage points)"),
    ], "coverage_sensitivity_maps", "How much could missing AI reports change the access map?",
       "A uses observed qualifying reports only. B-C use the income-aware model with strongly positively dependent missing items.\nD spans six prespecified scenarios, including different missing-use odds, income tilts and item dependence. It is not a confidence interval.\nModels retain observed answers; 30 minutes is the manuscript's distance-based proxy. Alaska and Hawaii remain in national calculations.")
    c["modeled_unexcluded"] = c.observed_outside_both_pct-c.central_outside_both_pct
    c["temporal_difference"] = c.central_outside_both_pct-c.independent_waves_outside_both_pct
    map_figure(c, [
        ("observed_outside_both_pct", "Outside in both waves: reported destinations", "YlGnBu", Normalize(0,100), "Residents outside in both waves (%)"),
        ("central_outside_both_pct", "Outside in both waves: income-aware scenario", "YlGnBu", Normalize(0,100), "Expected outside-both population (%)"),
        ("modeled_unexcluded", "Difference associated with missing reports", "YlOrBr", Normalize(0,100), "Reported minus simulated outside-both share (pp)"),
        ("temporal_difference", "Dependence on persistence across waves", "YlOrBr", Normalize(0,25), "Shared minus independent wave expectation (percentage points)"),
    ], "persistent_exclusion_maps", "Persistent exclusion: geography versus missing information",
       "A is the reported-status transition profile. B-C show exact conditional expectations with shared latent draws across waves.\nD changes only temporal dependence; shared draws leave at least as many residents outside both waves as independent draws.\nMissing-status scenarios do not establish actual deployment, functional access or the clinical value of AI.")
    # A dot-range comparison makes the income contrast visible without map-area bias.
    sim = pd.read_csv(DATA/"scenario_summary.csv")
    exact = pd.read_csv(DATA/"exact_expected_coverage.csv")
    observed = sim[sim.scenario.eq("observed")].set_index("group")
    fig, axes = plt.subplots(1,2, figsize=(12.8,7.5), sharey=True)
    fig.subplots_adjust(left=.29, right=.97, top=.80, bottom=.19, wspace=.15)
    for ax, prefix, label in zip(axes, ["RUCC 4-6", "RUCC 7-9"], ["Nonmetropolitan: RUCC 4-6", "Nonmetropolitan: RUCC 7-9"]):
        for i, name in enumerate(ORDER):
            if name == "observed":
                val = observed.loc[prefix+" Q4", "change_pp"]-observed.loc[prefix+" Q1", "change_pp"]
                ax.scatter(val, i, marker="D", color="#242B33", s=45, zorder=4)
            else:
                s = sim[sim.scenario.eq(name) & sim.group.eq(prefix+" Q4-Q1")].iloc[0]
                e = exact[exact.scenario.eq(name)].set_index("group")
                val = e.loc[prefix+" Q4", "change_pp"]-e.loc[prefix+" Q1", "change_pp"]
                color = "#147D83" if name == "central" else ("#BE5543" if name == "favor_poor" else "#64748B")
                ax.hlines(i, s.change_pp_p025, s.change_pp_p975, color=color, linewidth=2.2)
                ax.scatter(val, i, color=color, s=38, zorder=4)
        ax.axvline(0, color="#626A72", linestyle="--", linewidth=1)
        ax.set_title(label, fontsize=12, pad=15)
        ax.grid(axis="x", color="#E3E7EA", linewidth=.7)
        ax.set_axisbelow(True)
        ax.set_xlabel("Q4 minus Q1 coverage gain (percentage points)", fontsize=10)
        ax.set_yticks(range(len(ORDER)), [LABELS[x] for x in ORDER])
        ax.tick_params(axis="y", length=0, labelsize=10)
        ax.spines["left"].set_visible(False)
    axes[0].invert_yaxis()
    lo = min(a.get_xlim()[0] for a in axes); hi = max(a.get_xlim()[1] for a in axes)
    for ax in axes: ax.set_xlim(lo, hi)
    fig.suptitle("Does the rural income gradient survive the reporting assumptions?", x=.04, y=.97, ha="left", fontsize=18, fontweight="bold")
    fig.text(.04,.895,"Positive values indicate larger 2022-2024 gains in the highest-income than lowest-income counties.",fontsize=11,color="#4B5560")
    fig.text(.04,.07,"Dots: exact expected coverage-gain contrasts. Lines: central 95% simulation ranges with fixed model coefficients, not confidence intervals.\nBlack diamonds: observed-report contrasts, with no uncertainty interval shown. Fixed county-income quartiles; Connecticut excluded from this comparison.", fontsize=9.5, linespacing=1.5)
    save(fig,"rural_income_sensitivity")
    c.drop(columns="geometry").to_csv(DATA/"contiguous_map_source_values.csv", index=False)
    print("Three figures saved; 3,108 counties, 67 Florida counties, no missing joins.", flush=True)


if __name__ == "__main__": main()
