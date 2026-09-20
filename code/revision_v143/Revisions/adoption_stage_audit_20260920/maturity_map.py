"""Exploratory rurality-by-proximity-to-implementation-stage map.

Reads the frozen study frame. No imputation, model fitting, manuscript changes,
or publishing. Detailed derived values stay in a local private directory.
"""
import os
os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/paper2-maturity-map")
os.environ.setdefault("XDG_CACHE_HOME", "/private/tmp/paper2-maturity-cache")
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, to_rgb
from matplotlib.patches import Rectangle
import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
PAPER = HERE.parents[1]
sys.path.insert(0, str(BASE))
from analyze_revision import panel, hospitals, points, distance, RUN, PANEL

RURAL = ["Metro", "Nonmetro 4-6", "Nonmetro 7-9"]
CATEGORIES = ["Fully integrated within 30", "Expanding within 30; no fully integrated report within 30",
              "No expanding or fully integrated report within 30"]
# Rows encode observed proximity category; columns encode county rurality.
COLORS = ["#D4ECE6", "#76B7A9", "#216E66",
          "#F9E2B6", "#DFAC51", "#986219",
          "#EAD2E2", "#B677A5", "#77345E"]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    protected = []
    before = {}
    sources = [PANEL, RUN / "years/2024/hospital_ai_robotics_enriched_2024.parquet",
               BASE / "private/block_group_context.csv", BASE / "private/display_geometry.parquet"]
    source_hashes = {str(p): sha(p) for p in sources}
    d = panel()
    h, a = hospitals(2024)
    _, coords = points(d)
    flags = {"expanding_or_integrated": a.ge(3).any(axis=1),
             "fully_integrated": a.eq(4).any(axis=1)}
    assert flags["expanding_or_integrated"].equals(h.ai_flag.eq(1))
    for name, flag in flags.items():
        miles, _ = distance(coords, h.loc[flag])
        d[f"minutes_{name}"] = miles * 1.95
    error = float(np.max(abs(d.minutes_expanding_or_integrated-d.drive_2024)))
    assert error < 1e-7
    assert (d.minutes_fully_integrated + 1e-8 >= d.minutes_expanding_or_integrated).all()
    ctx = pd.read_csv(BASE / "private/block_group_context.csv", dtype={"GEOID": str}).set_index("GEOID")
    d["rurality"] = d.GEOID.map(ctx.rurality)
    assert d.rurality.isin(RURAL).all()
    d["rurality_class"] = d.rurality.map(dict(zip(RURAL, range(3))))
    d["proximity_class"] = np.select([d.minutes_fully_integrated <= 30,
                                       d.minutes_expanding_or_integrated <= 30], [0, 1], default=2)
    d["map_class"] = d.proximity_class*3+d.rurality_class
    contiguous = ~d.state_fips.isin(["02", "15"])
    rows = []
    for frame, mask in [("50 states and DC", pd.Series(True, index=d.index)),
                        ("Contiguous US", contiguous)]:
        for group in ["All"]+RURAL:
            dd = d.loc[mask & (d.rurality.eq(group) if group != "All" else True)]
            population = int(dd.POPULATION.sum())
            row = {"frame": frame, "rurality": group, "population": population,
                   "block_groups": len(dd)}
            for c in range(3):
                pop = int(dd.loc[dd.proximity_class.eq(c), "POPULATION"].sum())
                row[f"population_class_{c}"] = pop
                row[f"percent_class_{c}"] = 100*pop/population
            assert sum(row[f"population_class_{c}"] for c in range(3)) == population
            rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(HERE / "maturity_proximity_rurality_summary.csv", index=False)
    private = HERE / "private"
    private.mkdir(exist_ok=True)
    d[["GEOID", "POPULATION", "rurality", "minutes_expanding_or_integrated", "minutes_fully_integrated",
       "proximity_class", "map_class"]].to_csv(private / "maturity_map_block_group_values.csv", index=False)
    mapped = d.loc[contiguous].copy()
    b = gpd.read_parquet(BASE / "private/display_geometry.parquet").merge(mapped, on="GEOID", validate="one_to_one")
    assert len(b) == 236879 and b.POPULATION.sum() == mapped.POPULATION.sum()
    bounds = b.total_bounds
    cmap = ListedColormap(COLORS)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "pdf.fonttype": 42,
                         "axes.spines.top": False, "axes.spines.right": False})
    fig = plt.figure(figsize=(16.6, 11.2), facecolor="white")
    ax = fig.add_axes([.018, .315, .728, .64])
    def plot_map(axes, frame):
        frame.plot(column="map_class", cmap=cmap, vmin=-.5, vmax=8.5,
                   ax=axes, linewidth=0, rasterized=True)
        axes.set_axis_off()
    plot_map(ax, b)
    ax.set_xlim(bounds[0]-35000, bounds[2]+35000)
    ax.set_ylim(bounds[1]-35000, bounds[3]+35000)
    ax.text(.012, .98, "a", transform=ax.transAxes, fontsize=16, fontweight="bold", va="top")
    trans = Transformer.from_crs(4326, 5070, always_xy=True)
    regions = [("b", "Appalachia", (-86.5, 34, -77.5, 39.8), [.77, .642, .218, .29]),
               ("c", "Lower Mississippi", (-93.5, 31, -88.5, 36.5), [.77, .323, .218, .274])]
    for letter, label, (west, south, east, north), pos in regions:
        xx, yy = trans.transform([west, west, east, east], [south, north, south, north])
        box = [min(xx), min(yy), max(xx), max(yy)]
        zoom = fig.add_axes(pos)
        plot_map(zoom, b.cx[box[0]:box[2], box[1]:box[3]])
        zoom.set_xlim(box[0], box[2]); zoom.set_ylim(box[1], box[3])
        zoom.set_title(f"{letter}  {label}", loc="left", fontsize=13, pad=9, fontweight="bold")
        ax.add_patch(Rectangle((box[0], box[1]), box[2]-box[0], box[3]-box[1],
                               fill=False, edgecolor="#30383A", linewidth=1.1))
        ax.text(box[0]+12000, box[3]+20000, letter, fontsize=13, fontweight="bold")

    # A color matrix is the map key; the bars prevent confusing land area with population.
    legend = fig.add_axes([.176, .087, .129, .191])
    legend.imshow(np.arange(9).reshape(3, 3), cmap=cmap, vmin=-.5, vmax=8.5,
                  origin="lower", interpolation="nearest")
    legend.set_xticks([0, 1, 2], ["Metro\n1-3", "Nonmetro\n4-6", "Nonmetro\n7-9"], fontsize=9)
    legend.set_yticks([0, 1, 2], ["Fully integrated", "Expanding only*", "Neither reported*"], fontsize=10.5)
    legend.tick_params(length=0, pad=8)
    for spine in legend.spines.values(): spine.set_visible(False)
    legend.set_xlabel("County rurality (RUCC)", fontsize=10.5, labelpad=8)
    fig.text(.035, .287, "Reported implementation within 30 proxy minutes", fontsize=12, fontweight="bold")

    bars = fig.add_axes([.525, .088, .43, .178])
    fig.text(.40, .287, "d  Residents by proximity category", fontsize=12, fontweight="bold")
    s = summary[summary.frame.eq("Contiguous US")].set_index("rurality")
    for j, group in enumerate(RURAL):
        left, y = 0., 2-j
        for c in range(3):
            width = s.loc[group, f"percent_class_{c}"]
            color = COLORS[3*c+j]
            bars.barh(y, width, left=left, height=.58, color=color, edgecolor="white", linewidth=.7)
            lightness = np.dot(to_rgb(color), [.2126, .7152, .0722])
            bars.text(left+width/2, y, f"{width:.1f}", ha="center", va="center", fontsize=11,
                      color="white" if lightness < .52 else "#152323")
            left += width
        assert abs(left-100) < 1e-9
    bars.set_xlim(0, 100); bars.set_ylim(-.55, 2.55)
    bars.set_yticks([2, 1, 0], ["Metro 1-3", "Nonmetro 4-6", "Nonmetro 7-9"], fontsize=11)
    bars.set_xticks([0, 25, 50, 75, 100]); bars.set_xlabel("Share of residents (%)", labelpad=6, fontsize=10.5)
    bars.spines["left"].set_visible(False)
    bars.tick_params(axis="y", length=0, pad=10)
    bars.tick_params(axis="x", labelsize=9, length=3, color="#888888")
    fig.text(.035, .020, "*Expanding only: expanding reported nearby, no fully integrated report nearby. Neither: no expanding or fully integrated report nearby.",
             fontsize=9, color="#454C50")
    fig.text(.035, .004, "2024 observed reports; any of 14 AI applications. Proximity is not verified service access. Rurality is county context; mapped distances are block-group estimates.",
             fontsize=9, color="#454C50")
    output = HERE / "figures"
    output.mkdir(exist_ok=True)
    for ext in ["png", "pdf"]:
        fig.savefig(output / f"AI_maturity_rurality_proximity_2024.{ext}", dpi=300, facecolor="white")
    plt.close(fig)
    after = {str(p): sha(p) for p in protected}
    assert source_hashes == {str(p): sha(p) for p in sources}, "A frozen analysis input changed during the map run"
    manifest = {"timestamp_pacific": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
                "primary_minutes_reproduction_max_error": error,
                "nested_distances_verified": True, "mapped_block_groups": len(b),
                "mapped_population": int(mapped.POPULATION.sum()),
                "destinations": {k: int(v.sum()) for k, v in flags.items()},
                "categories": dict(enumerate(CATEGORIES)), "rurality": dict(enumerate(RURAL)),
                "source_hashes": source_hashes, "frozen_inputs_unchanged": True,
                "manuscript_and_word_writes_performed": False,
                "document_hashes_before": before, "document_hashes_after": after,
                "external_document_changes_during_run": [p for p in before if before[p] != after[p]],
                "disclosure": "Illustrative fixed regional windows; not selected as statistical hotspots. Unknown responses are not verified non-use. All hospitals in the frozen 50-state/DC frame remain eligible destinations. Any-application definition mixes clinical and operational uses. Not a longitudinal maturity analysis.",
                "release_status": "Local exploratory prototype, no manuscript insertion or public release; derived-data rights and original geometry provenance remain subject to review."}
    (HERE / "map_verification.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(summary.to_string(index=False), flush=True)
    print(json.dumps({k: manifest[k] for k in ["mapped_block_groups", "mapped_population", "destinations", "primary_minutes_reproduction_max_error"]}, indent=2))


if __name__ == "__main__":
    main()
