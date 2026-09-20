"""Remove only the free-standing year headings; preserve the map data and keys."""
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, ListedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Patch
import geopandas as gpd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
sys.path.insert(0, str(BASE))
from analyze_revision import panel


def main():
    d = panel()
    d = d[~d.state_fips.isin(["02", "15"])].copy()
    assert len(d) == 236879
    b = gpd.read_parquet(BASE / "private/display_geometry.parquet").merge(d, on="GEOID", validate="one_to_one")
    bounds = b.total_bounds
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "pdf.fonttype": 42})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.8))
    fig.subplots_adjust(left=.025, right=.98, top=.94, bottom=.13, wspace=.06, hspace=.1)
    norm = Normalize(0, 180, clip=True)
    for i, year in enumerate([2022, 2024]):
        b.plot(column=f"drive_{year}", ax=axes[i, 0], cmap="magma_r", norm=norm, linewidth=0, rasterized=True)
        b.plot(column=f"within_{year}", ax=axes[i, 1], cmap=ListedColormap(["#D9D9D9", "#396C8E"]), vmin=0, vmax=1, linewidth=0, rasterized=True)
        for j in range(2):
            ax = axes[i, j]
            ax.set_xlim(bounds[0]-60000, bounds[2]+60000)
            ax.set_ylim(bounds[1]-60000, bounds[3]+60000)
            ax.set_axis_off()
            ax.text(0, 1.015, "abcd"[i*2+j], transform=ax.transAxes, fontsize=14, fontweight="bold")
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap="magma_r"), cax=fig.add_axes([.10, .065, .33, .019]), orientation="horizontal", extend="max")
    cb.set_label("Proxy travel time (minutes)")
    cb.set_ticks([0, 30, 60, 90, 120, 150, 180])
    fig.legend(handles=[Patch(facecolor="#396C8E", label="Within 30 proxy minutes"), Patch(facecolor="#D9D9D9", label="Outside 30 proxy minutes")], loc="lower center", bbox_to_anchor=(.76, .035), frameon=False)
    for ext in ["png", "pdf"]:
        fig.savefig(HERE / f"figures/Figure_1_v142.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
