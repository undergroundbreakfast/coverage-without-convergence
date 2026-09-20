"""Rebuild scientific maps from frozen values and original Census geometry."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, ListedColormap
from matplotlib.cm import ScalarMappable
from matplotlib.patches import Patch
import geopandas as gpd
import pandas as pd
import numpy as np
from analyze_revision import SHAPES, HERE, PRIVATE, panel, hospitals, points, distance
from build_revision_exhibits import FIG, DATA, save


def main():
    d = panel()
    d = d[~d.state_fips.isin(["02", "15"])].copy()
    assert len(d) == 236879
    cache = PRIVATE / "display_geometry.parquet"
    if cache.exists():
        b = gpd.read_parquet(cache)
    else:
        print("Reading public Census block-group geometry for maps", flush=True)
        b = gpd.read_file(SHAPES / "USA_BlockGroups_2020Pop.geojson", columns=["GEOID"])
        b.GEOID = b.GEOID.astype(str).str.zfill(12)
        b = b[b.GEOID.isin(d.GEOID)].to_crs(5070)
        # Display simplification only. Original geometries define all distances.
        b.geometry = b.geometry.simplify(70, preserve_topology=True)
        b.to_parquet(cache)
    b = b.merge(d, on="GEOID", validate="one_to_one")
    bounds = b.total_bounds
    def setup(ax, letter):
        ax.set_xlim(bounds[0]-60000, bounds[2]+60000)
        ax.set_ylim(bounds[1]-60000, bounds[3]+60000)
        ax.set_axis_off()
        ax.text(0, 1.015, letter, transform=ax.transAxes, fontsize=14, fontweight="bold")
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":11, "pdf.fonttype":42})
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.8))
    fig.subplots_adjust(left=.025, right=.98, top=.94, bottom=.13, wspace=.06, hspace=.1)
    norm = Normalize(0, 180, clip=True)
    cmap = "magma_r"
    for i, y in enumerate([2022, 2024]):
        b.plot(column=f"drive_{y}", ax=axes[i,0], cmap=cmap, norm=norm, linewidth=0, rasterized=True)
        b.plot(column=f"within_{y}", ax=axes[i,1], cmap=ListedColormap(["#D9D9D9", "#396C8E"]), vmin=0, vmax=1, linewidth=0, rasterized=True)
        for j in range(2):
            setup(axes[i,j], "abcd"[i*2+j])
            axes[i,j].set_title(str(y), fontsize=12, pad=3)
    cbax = fig.add_axes([.10, .065, .33, .019])
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cmap), cax=cbax, orientation="horizontal", extend="max")
    cb.set_label("Proxy travel time (minutes)")
    cb.set_ticks([0,30,60,90,120,150,180])
    fig.legend(handles=[Patch(facecolor="#396C8E", label="Within 30 proxy minutes"), Patch(facecolor="#D9D9D9", label="Outside 30 proxy minutes")], loc="lower center", bbox_to_anchor=(.76,.035), frameon=False)
    save(fig, "Figure_1_v138")
    fig, ax = plt.subplots(1,2,figsize=(12,4.8))
    fig.subplots_adjust(left=.025,right=.98,top=.96,bottom=.22,wspace=.06)
    b["newly_within"] = (b.within_2022.eq(0) & b.within_2024.eq(1)).astype(int)
    b["reduction"] = b.drive_2022 - b.drive_2024
    b.plot(column="newly_within", cmap=ListedColormap(["#E7E7E7", "#396C8E"]), vmin=0,vmax=1, ax=ax[0], linewidth=0,rasterized=True)
    b.plot(color="#E7E7E7", ax=ax[1], linewidth=0,rasterized=True)
    b[b.reduction>0].plot(column="reduction", cmap="viridis", norm=Normalize(0,60,clip=True), ax=ax[1],linewidth=0,rasterized=True)
    for a, letter in zip(ax,"ab"):
        setup(a,letter)
    fig.legend(handles=[Patch(facecolor="#396C8E",label="Newly within 30 proxy minutes"),Patch(facecolor="#E7E7E7",label="Other block groups")],loc="lower center",bbox_to_anchor=(.26,.025),frameon=False)
    cbax=fig.add_axes([.60,.105,.31,.035])
    cb=fig.colorbar(ScalarMappable(norm=Normalize(0,60),cmap="viridis"),cax=cbax,orientation="horizontal",extend="max")
    cb.set_label("Positive reduction in proxy travel time (minutes)")
    save(fig,"Figure_3_v138")
    b[["GEOID","POPULATION","drive_2022","drive_2024","within_2022","within_2024","newly_within","reduction"]].to_csv(DATA / "Figures_1_and_3_block_group_plot_values.csv",index=False)
    print("Maps completed",flush=True)
    # Rebuild the original flag-sensitivity figure with accessible labels.
    d=panel(); h,a=hospitals(2024); _,coords=points(d)
    rows=[]
    for label,threshold in [("Any activity",1),("Expanding or integrated",3)]:
        flag=a.ge(threshold).any(axis=1)
        miles,_=distance(coords,h[flag])
        rows.append({"definition":label,"destinations":int(flag.sum()),"geocoded_hospitals":len(h),"hospital_percentage":100*flag.mean(),"coverage_percentage":100*np.average(miles*1.95<=30,weights=d.POPULATION)})
    f=pd.DataFrame(rows)
    fig,ax=plt.subplots(figsize=(7.2,3.8),layout="constrained")
    x=np.arange(2)
    for offset,col,color,label in [(-.18,"hospital_percentage","#406880","Geocoded hospitals"),(.18,"coverage_percentage","#B05644","Population within 30 proxy minutes")]:
        bars=ax.bar(x+offset,f[col],width=.36,color=color,label=label)
        ax.bar_label(bars,fmt="%.1f%%",padding=3)
    ax.set_xticks(x,f.definition);ax.set_ylim(0,100);ax.set_ylabel("Percent")
    ax.legend(loc="upper left",frameon=False,fontsize=9)
    save(fig,"Supplementary_Figure_1_v138")
    f.to_csv(DATA / "Supplementary_Figure_1_flag_sensitivity.csv",index=False)


if __name__ == "__main__":
    main()
