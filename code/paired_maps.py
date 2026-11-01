"""Matched observed-report maps; no licensed record-level outputs are published."""

from config import (
    OUTPUT_DIR,
    prepare_output_dirs,
)
import geopandas as gpd
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

HERE = OUTPUT_DIR / "implementation"
OUT = HERE.parent / "publication/figures"
COLORS = ["#D4ECE6", "#76B7A9", "#216E66", "#EAD2E2", "#B677A5", "#77345E"]
RURAL = ["Metro", "Nonmetro 4-6", "Nonmetro 7-9"]


def main():
    prepare_output_dirs()
    d = pd.read_csv(
        HERE / "cache/maturity_map_block_group_values.csv", dtype={"GEOID": str}
    )
    b = gpd.read_parquet(HERE.parent / "access/cache/display_geometry.parquet").merge(
        d, on="GEOID", validate="one_to_one"
    )
    assert len(b) == 236879 and b.POPULATION.sum() == 329260546
    rural = b.rurality.map(dict(zip(RURAL, range(3)))).astype(int)
    s = pd.read_csv(HERE / "maturity_proximity_rurality_summary.csv")
    s = s[s.frame.eq("Contiguous US")].set_index("rurality")
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 12, "pdf.fonttype": 42}
    )
    fig = plt.figure(figsize=(13, 7.4), facecolor="white")
    bounds = b.total_bounds
    cmap = ListedColormap(COLORS)
    for j, key in enumerate(["expanding_or_integrated", "fully_integrated"]):
        b["display_class"] = (b[f"minutes_{key}"] > 30).astype(int) * 3 + rural
        ax = fig.add_axes([0.02 + 0.50 * j, 0.41, 0.46, 0.54])
        b.plot(
            column="display_class",
            cmap=cmap,
            vmin=-0.5,
            vmax=5.5,
            ax=ax,
            linewidth=0,
            rasterized=True,
        )
        ax.set_xlim(bounds[0] - 35000, bounds[2] + 35000)
        ax.set_ylim(bounds[1] - 35000, bounds[3] + 35000)
        ax.set_axis_off()
        ax.text(
            0.015,
            0.985,
            "ab"[j],
            transform=ax.transAxes,
            fontsize=18,
            fontweight="bold",
            va="top",
        )
        # Threshold labels serve as panel definitions, not redundant embedded titles.
        fig.text(
            0.025 + 0.50 * j,
            0.945,
            ["Expanding or fully integrated", "Fully integrated"][j],
            fontsize=16,
            fontweight="bold",
        )
        bars = fig.add_axes([0.11 + 0.5 * j, 0.19, 0.35, 0.175])
        vals = []
        for i, g in enumerate(RURAL):
            v = s.loc[g, "percent_class_0"] + (
                s.loc[g, "percent_class_1"] if j == 0 else 0
            )
            vals.append(v)
            bars.barh(2 - i, v, height=0.55, color=COLORS[i])
            bars.text(v + 1.5, 2 - i, f"{v:.1f}%", va="center", fontsize=12)
        bars.set_xlim(0, 100)
        bars.set_ylim(-0.6, 2.6)
        bars.set_yticks(
            [2, 1, 0], ["Metro", "Nonmetro 4-6", "Nonmetro 7-9"], fontsize=12
        )
        bars.set_xticks([0, 25, 50, 75, 100])
        bars.set_xlabel("Residents within 30 proxy minutes (%)", fontsize=11)
        bars.tick_params(axis="y", length=0, pad=8)
        for spine in ["top", "right", "left"]:
            bars.spines[spine].set_visible(False)
    legend = fig.add_axes([0.32, 0.012, 0.36, 0.096])
    legend.set_axis_off()
    for row, label in enumerate(
        ["Within threshold", "No qualifying report within threshold"]
    ):
        y = 1 - row * 0.43
        legend.text(-0.025, y - 0.12, label, ha="right", va="center", fontsize=11)
        for col, labelcol in enumerate(["Metro 1-3", "Nonmetro 4-6", "Nonmetro 7-9"]):
            x = col * 0.335
            legend.add_patch(
                Rectangle(
                    (x, y - 0.27),
                    0.285,
                    0.29,
                    color=COLORS[row * 3 + col],
                    clip_on=False,
                )
            )
            if row == 1:
                legend.text(
                    x + 0.1425, y - 0.34, labelcol, ha="center", va="top", fontsize=11
                )
    OUT.mkdir(parents=True, exist_ok=True)
    for ext in ["png", "pdf"]:
        fig.savefig(
            OUT / f"Supplementary_Figure_6_v143.{ext}", dpi=300, facecolor="white"
        )
    plt.close(fig)
    print("Matched maps complete; all block groups and population retained")


if __name__ == "__main__":
    main()
