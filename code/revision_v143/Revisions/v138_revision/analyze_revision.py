"""Reproduce the frozen spatial frame before calculating reviewer sensitivities.

Reads existing licensed hospital extracts in place; never copies them into the
submission package. Only aggregate outputs belong in analysis/. Public point
and detailed derived-distance caches stay under private/ and are not packaged.
"""

import argparse
import os
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from sklearn.neighbors import BallTree
from statsmodels.stats.weightstats import DescrStatsW

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "run_geo_multi_20260322_215110_7a831e"
PANEL = ROOT / "pr_inclusion_sensitivity_v128_exact/transition_detail_A_v128_50dc_bg_50dc_hosp.csv"
SHAPES = Path(os.environ.get("PAPER2_SHAPES_DIR", str(ROOT / "inputs/shapefiles")))
OUT = HERE / "analysis"
PRIVATE = HERE / "private"
ITEMS22 = ["wfaipsn", "wfaippd", "wfaiss", "wfaiart", "wfaioacw"]
OP = ["aiopef", "aipatd", "airevc", "aiscop", "aisswm", "aitiot"]
CLIN = ["clinai", "clnoai", "diagai", "papcai", "pcoeai", "pdmrai", "pophai", "surgai"]
SEED = 20260912
RADIUS = 3958.7613
MINUTES_PER_MILE = 1.95


def write_json(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, default=float) + "\n")


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for b in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def panel():
    d = pd.read_csv(PANEL, dtype={"GEOID": str, "county_fips": str, "state_fips": str})
    assert len(d) == 238433 and d.GEOID.is_unique
    assert d.POPULATION.sum() == 331449208
    return d


def hospitals(year):
    h = pd.read_parquet(RUN / f"years/{year}/hospital_ai_robotics_enriched_{year}.parquet")
    assert h.hospital_id.is_unique
    assert len(h) == {2022: 6095, 2024: 6076}[year]
    assert h.ai_flag.sum() == {2022: 1118, 2024: 1737}[year]
    items = ITEMS22 if year == 2022 else OP + CLIN
    if year == 2022:
        a = h[items].apply(lambda x: x.str.strip().str.lower().map({"yes": 1., "no": 0.}))
    else:
        a = h[[x + "_num" for x in items]].copy()
        a.columns = items
    h["any_answer"] = a.notna().any(axis=1)
    h["all_answer"] = a.notna().all(axis=1)
    h["composite_resolved"] = h.ai_flag.eq(1) | h.all_answer
    h["size"] = pd.cut(h.bsc, [0, 99, 299, np.inf], labels=["<100", "100-299", "300+"])
    return h, a


def points(d):
    cache = PRIVATE / "block_group_points.csv"
    if not cache.exists():
        print("Reading original block-group polygons", flush=True)
        bg = gpd.read_file(SHAPES / "USA_BlockGroups_2020Pop.geojson", columns=["GEOID", "population"])
        bg = bg.rename(columns={"population": "POPULATION"})
        bg.GEOID = bg.GEOID.astype(str).str.zfill(12)
        bg = bg.loc[bg.GEOID.isin(d.GEOID)].set_index("GEOID").loc[d.GEOID]
        assert np.array_equal(pd.to_numeric(bg.POPULATION), d.POPULATION)
        p = bg.to_crs(5070).geometry.representative_point().to_crs(4326)
        pd.DataFrame({"GEOID": d.GEOID.to_numpy(), "latitude": p.y.to_numpy(), "longitude": p.x.to_numpy()}).to_csv(cache, index=False)
    p = pd.read_csv(cache, dtype={"GEOID": str}).set_index("GEOID").loc[d.GEOID]
    return p, np.deg2rad(p[["latitude", "longitude"]].to_numpy())


def distance(coords, h):
    if h.empty:
        raise ValueError("No qualifying destinations")
    tree = BallTree(np.deg2rad(h[["latitude", "longitude"]].to_numpy()), metric="haversine")
    r, ix = tree.query(coords, k=1)
    miles = r[:, 0] * RADIUS
    # Match the production exact-zero convention, not a floor on all distances.
    miles[miles == 0] = .1
    return miles, ix[:, 0]


def gini(x, w):
    i = np.argsort(x)
    x, w = np.asarray(x)[i], np.asarray(w, dtype=float)[i]
    if np.sum(x * w) == 0:
        return 0.
    a = np.r_[0., np.cumsum(w) / w.sum()]
    b = np.r_[0., np.cumsum(x * w) / np.sum(x * w)]
    return float(1 - 2 * np.trapezoid(b, a))


def metrics(x, w):
    q = DescrStatsW(x, weights=w).quantile([.1, .5, .9], return_pandas=False)
    mu = np.average(x, weights=w)
    z = x / mu
    return {"population": int(w.sum()), "coverage30_pct": 100 * np.sum(w[x * MINUTES_PER_MILE <= 30]) / w.sum(),
            "gini": gini(x, w), "p10_miles": q[0], "median_miles": q[1], "p90_miles": q[2], "p90_p10_miles": q[2] - q[0],
            "atkinson_epsilon_0_5": 1 - np.average(np.sqrt(x), weights=w)**2 / mu,
            "theil": np.average(np.where(z > 0, z * np.log(np.maximum(z, 1e-300)), 0), weights=w)}


def main():
    OUT.mkdir(exist_ok=True)
    PRIVATE.mkdir(exist_ok=True)
    d = panel()
    p, coords = points(d)
    hs = {y: hospitals(y) for y in (2022, 2024)}
    audit, basic, itemrows = [], [], []
    distances = {}
    for year, (h, a) in hs.items():
        x, _ = distance(coords, h[h.ai_flag == 1])
        delta = np.abs(x * MINUTES_PER_MILE - d[f"drive_{year}"].to_numpy())
        audit.append({"year": year, "hospitals_geocoded": len(h), "qualifying_geocoded": int(h.ai_flag.sum()),
                      "any_determinate": int(h.any_answer.sum()), "all_determinate": int(h.all_answer.sum()),
                      "composite_resolved": int(h.composite_resolved.sum()), "max_minutes_difference": delta.max(),
                      "threshold_disagreements": int(np.sum((x * MINUTES_PER_MILE <= 30) != d[f"within_{year}"].to_numpy()))})
        print("Frame audit", audit[-1], flush=True)
        write_json("frame_audit.json", audit)
        assert delta.max() < 1e-7, "Reconstructed distances do not match the frozen submission; stop"
        distances[f"primary_{year}"] = x
        for tech, subset in [("primary", h[h.ai_flag == 1]), ("all_hospitals", h), ("robotic_surgery_comparator", h[h.robo_flag == 1])]:
            miles, _ = distance(coords, subset)
            distances[f"{tech}_{year}"] = miles
            basic.append({"year": year, "definition": tech, "hospitals": len(subset), **metrics(miles, d.POPULATION.to_numpy())})
        if year == 2024:
            for item in OP + CLIN:
                sub = h[a[item].ge(3)]
                miles, _ = distance(coords, sub)
                itemrows.append({"item": item, "known": int(a[item].notna().sum()), "qualifying": len(sub), **metrics(miles, d.POPULATION.to_numpy())})
    pd.DataFrame(basic).to_csv(OUT / "spatial_metrics.csv", index=False)
    pd.DataFrame(itemrows).to_csv(OUT / "application_spatial_metrics.csv", index=False)
    h22, a22 = hs[2022]
    h24, a24 = hs[2024]
    ids = set(h22.loc[h22.any_answer, "hospital_id"]) & set(h24.loc[h24.any_answer, "hospital_id"])
    balanced = []
    for year, label, select in [(2022, "primary", h22.ai_flag.eq(1)), (2024, "primary", h24.ai_flag.eq(1)),
                                (2024, "operational", a24[OP].ge(3).any(axis=1))]:
        h = hs[year][0]
        sub = h[select & h.hospital_id.isin(ids)]
        x, _ = distance(coords, sub)
        distances[f"balanced_{label}_{year}"] = x
        balanced.append({"year": year, "definition": label, "balanced_hospitals": len(ids), "qualifying": len(sub), **metrics(x, d.POPULATION.to_numpy())})
    pd.DataFrame(balanced).to_csv(OUT / "balanced_spatial_metrics.csv", index=False)
    outside = (d.within_2022 == 0) & (d.within_2024 == 0)
    near_all = distances["all_hospitals_2024"] * MINUTES_PER_MILE <= 30
    split = {"outside_both": int(d.loc[outside, "POPULATION"].sum()),
             "outside_both_near_any_hospital": int(d.loc[outside & near_all, "POPULATION"].sum()),
             "outside_both_far_any_hospital": int(d.loc[outside & ~near_all, "POPULATION"].sum())}
    write_json("all_hospital_split.json", split)
    np.savez_compressed(PRIVATE / "distances.npz", **distances)
    files = [PANEL, SHAPES / "USA_BlockGroups_2020Pop.geojson"] + [RUN / f"years/{y}/hospital_ai_robotics_enriched_{y}.parquet" for y in (2022, 2024)]
    write_json("input_manifest.json", {"earth_radius_miles": RADIUS, "minutes_per_mile": MINUTES_PER_MILE,
               "point_method": "EPSG:5070 polygon representative_point transformed to EPSG:4326",
               "weighted_quantile": "statsmodels DescrStatsW quantile; production convention",
               "files": [{"path": str(f), "sha256": sha(f), "bytes": f.stat().st_size} for f in files]})
    print("Completed primary reproduction, same-reporters spatial sensitivity and 14 application comparisons", flush=True)


if __name__ == "__main__":
    main()
