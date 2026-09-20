"""Generate figures and table-format helpers from audited analysis outputs."""

from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from analyze_revision import HERE, OUT, PRIVATE, ROOT, panel

FIG = HERE / "figures"
DATA = HERE / "Source_Data"
for p in [FIG, DATA]:
    p.mkdir(exist_ok=True)


def read(name):
    return pd.read_csv(OUT / f"{name}.csv")


def esc(x):
    return str(x).replace("&", r"\&").replace("%", r"\%").replace("_", r"\_").replace("<", r"$<$")


def table(caption, label, headers, rows, note, widths=None):
    widths = widths or [15 / len(headers)] * len(headers)
    spec = "@{}" + " ".join(f"p{{{w:.2f}cm}}" for w in widths) + "@{}"
    body = [r"\begin{table}[!htbp]\centering\small", r"\caption{" + caption + "}", r"\label{" + label + "}",
            r"\setlength{\tabcolsep}{3pt}", r"\begin{tabular}{" + spec + "}", r"\toprule",
            " & ".join(r"\textbf{" + esc(h) + "}" for h in headers) + r" \\\midrule"]
    body += [" & ".join(esc(v) for v in row) + r" \\" for row in rows]
    body += [r"\bottomrule\end{tabular}", r"\par\smallskip\begin{minipage}{0.97\linewidth}\footnotesize " + note + r"\end{minipage}", r"\end{table}"]
    return "\n".join(body) + "\n"


def save(fig, name):
    fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(FIG / f"{name}.png", dpi=350, bbox_inches="tight")
    plt.close(fig)


def figures():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "axes.spines.top": False,
                         "axes.spines.right": False, "pdf.fonttype": 42, "ps.fonttype": 42})
    r, inc = read("rurality_coverage"), read("rural_income_coverage")
    fig, ax = plt.subplots(1, 2, figsize=(11.3, 4.4), layout="constrained")
    x = np.arange(3)
    ax[0].bar(x-.17, r.coverage_2022_pct, width=.34, color="#406880", label="2022")
    ax[0].bar(x+.17, r.coverage_2024_pct, width=.34, color="#B05644", label="2024")
    ax[0].set_xticks(x, ["Metropolitan\nRUCC 1–3", "Nonmetropolitan\nRUCC 4–6", "Nonmetropolitan\nRUCC 7–9"])
    ax[0].set_ylabel("Population within 30 proxy minutes (%)")
    ax[0].set_ylim(0, 100)
    ax[0].legend(frameon=False, ncols=2, loc="upper right")
    for j, (group, color) in enumerate([("Nonmetro 4-6", "#447567"), ("Nonmetro 7-9", "#89659A")]):
        g = inc[inc.rurality == group]
        bars = ax[1].bar(np.arange(4) + (j-.5)*.36, g.change_pp, width=.36, color=color, label=group.replace("Nonmetro", "RUCC").replace("-", "–"))
        ax[1].bar_label(bars, fmt="%.1f", padding=3, fontsize=10)
    ax[1].set_xticks(np.arange(4), ["Q1\nLowest", "Q2", "Q3", "Q4\nHighest"])
    ax[1].set_xlabel("County median-household-income quartile")
    ax[1].set_ylabel("Coverage gain (percentage points)")
    ax[1].set_ylim(0, 31)
    ax[1].legend(frameon=False, ncols=2, loc="upper left")
    for a, letter in zip(ax, "ab"):
        a.set_title(letter, loc="left", fontweight="bold", pad=13)
        a.set_axisbelow(True)
        a.grid(axis="y", alpha=.2)
    save(fig, "Figure_2_v138")
    r.to_csv(DATA / "Figure_2a_rurality_coverage.csv", index=False)
    inc.to_csv(DATA / "Figure_2b_rural_income.csv", index=False)
    d = panel().merge(pd.read_csv(PRIVATE / "block_group_context.csv", dtype={"GEOID": str})[["GEOID", "rurality"]], on="GEOID", validate="one_to_one")
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2), layout="constrained")
    source = []
    for ax, year, letter in zip(axes, [2022, 2024], "ab"):
        for name, g in d.groupby("rurality", sort=True):
            g = g.sort_values(f"drive_{year}")
            xx, yy = g[f"drive_{year}"].to_numpy(), g.POPULATION.cumsum().to_numpy()/g.POPULATION.sum()*100
            ax.step(np.r_[0, xx], np.r_[0, yy], where="post", label=name.replace("Nonmetro", "RUCC").replace("-", "–"))
            source.append(pd.DataFrame({"year": year, "rurality": name, "proxy_minutes": xx, "cumulative_population_pct": yy}))
        ax.axvline(30, color="0.3", ls="--", lw=1)
        ax.set(xlim=(0, 150), ylim=(0, 100), xlabel="Proxy travel time (minutes)", ylabel="Cumulative population (%)")
        ax.set_title(f"{letter}  {year}", loc="left", fontweight="bold")
        ax.legend(frameon=False, loc="lower right", fontsize=9)
    save(fig, "Supplementary_Figure_2_v138")
    pd.concat(source).to_csv(DATA / "Supplementary_Figure_2_CDF.csv", index=False)



if __name__ == "__main__":
    figures()
