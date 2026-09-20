"""Typeset audited aggregate outputs without changing their estimates."""
from pathlib import Path
import csv

HERE = Path(__file__).resolve().parent


def rows(name):
    with (HERE / "analysis" / name).open() as stream:
        return list(csv.DictReader(stream))


def main():
    data = rows("scenario_rurality_coverage.csv")
    scenarios = list(dict.fromkeys(row["scenario"] for row in data))
    lookup = {"observed": "Observed reports", "central": "Reference",
              "half_odds": "Half missing odds", "double_odds": "Double missing odds",
              "favor_poor": "Poorer-county tilt", "favor_rich": "Richer-county tilt",
              "no_income": "No income predictor", "independent_items": "Independent items",
              "independent_waves": "Independent waves", "named_items_only": "Named items only",
              "adverse_wave_odds": "2022 odds up / 2024 down", "reverse_wave_odds": "2022 odds down / 2024 up"}
    assert set(lookup) == set(scenarios)
    text = r"""\FloatBarrier\section{Additional geographic and hospital reporting checks}
\label{sec:additional_checks}
We summarize the existing item-level scenarios by fixed rurality groups, describe reported applications in small rural hospitals, and extend the paired county bootstrap to the persistently outside population. All checks retain the archived inputs and primary definitions. No missing-status model is refitted for these summaries.

\subsection*{Metropolitan and nonmetropolitan proximity}
Expected coverage is aggregated using the same population weights and reconciled Connecticut rurality assignment as the observed estimates. All eleven scenarios retain higher metropolitan coverage and narrower metropolitan--nonmetropolitan gaps in 2024 than in 2022. The expected 2024 metropolitan gap is 26.1--45.1 percentage points for all nonmetropolitan areas, 18.7--38.0 for RUCC 4--6, and 38.9--57.4 for RUCC 7--9. These are comparisons across specified conditional expectations, not confidence intervals or exhaustive bounds.

\begin{table}[!htbp]\centering\footnotesize
\caption{Coverage by rurality under each missing-status scenario.}
\label{tab:scenario_rurality}
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}p{3.6cm}rrrrrr@{}}
\toprule
& \multicolumn{2}{c}{Metro coverage (\%)} & \multicolumn{2}{c}{Nonmetro coverage (\%)} & \multicolumn{2}{c}{Metro gap (pp)} \\
\cmidrule(lr){2-3}\cmidrule(lr){4-5}\cmidrule(l){6-7}
Scenario & 2022 & 2024 & 2022 & 2024 & 2024 & Change \\\midrule
"""
    for name in scenarios:
        m = next(row for row in data if row["scenario"] == name and row["group"] == "Metro")
        n = next(row for row in data if row["scenario"] == name and row["group"] == "All nonmetro")
        vals = [m["coverage_2022_pct"], m["coverage_2024_pct"], n["coverage_2022_pct"], n["coverage_2024_pct"], n["metro_gap_2024_pp"], n["gap_change_pp"]]
        text += lookup[name] + " & " + " & ".join(f"{float(v):.1f}" for v in vals) + r" \\" + "\n"
    text += r"""\bottomrule\end{tabular}
\par\smallskip\begin{minipage}{\linewidth}\footnotesize
Metro = RUCC 1--3 (285,649,549 residents); nonmetro = RUCC 4--9 (45,799,659 residents). Gap is metropolitan minus nonmetropolitan coverage; negative gap change indicates narrowing. Scenario definitions are in Supplementary Note 19. Except observed reports, entries are exact conditional expectations retaining observed answers. National and subgroup values are in Supplementary Data 1. Item models, fitted coefficients, population weights and threshold are unchanged.
\end{minipage}\end{table}
\FloatBarrier

\subsection*{Applications reported by small and rural hospitals}
\begin{table}[!htbp]\centering\footnotesize
\caption{Application reporting by hospital size and rurality in 2024.}
\label{tab:small_rural_applications}
\setlength{\tabcolsep}{3pt}
\begin{tabular}{@{}p{4.5cm}rrr rr@{}}
\toprule
& \multicolumn{3}{c}{Reported share of group (\%)} & \multicolumn{2}{c}{Small RUCC 7--9} \\
\cmidrule(lr){2-4}\cmidrule(l){5-6}
Application & $<$100 beds & RUCC 7--9 & Both & Qualifying & Answered \\\midrule
"""
    apps = rows("application_size_rurality.csv")
    labels = {"aiopef": "Operational efficiency", "aipatd": "Patient flow and demand", "airevc": "Revenue cycle",
              "aiscop": "Supply chain", "aisswm": "Staff scheduling", "aitiot": "Other operational",
              "clinai": "Clinical decision support", "clnoai": "Other clinical", "diagai": "AI-assisted diagnostics",
              "papcai": "Predictive patient care", "pcoeai": "Patient communication", "pdmrai": "Emergency resource allocation",
              "pophai": "Population health", "surgai": "AI-assisted surgery"}
    groups = ["Fewer than 100 beds", "RUCC 7-9", "Fewer than 100 beds and RUCC 7-9"]
    for item, label in labels.items():
        a = [next(row for row in apps if row["item"] == item and row["group"] == group) for group in groups]
        text += label + " & " + " & ".join(f"{float(row['reported_share_of_frame_pct']):.1f}" for row in a)
        text += f" & {a[2]['qualifying_reports']} & {a[2]['determinate_answers']}" + r" \\" + "\n"
    ns = [next(row["hospitals"] for row in apps if row["group"] == group) for group in groups]
    text += r"""\bottomrule\end{tabular}
\par\smallskip\begin{minipage}{\linewidth}\footnotesize
""" + f"Group denominators are {ns[0]}, {ns[1]} and {ns[2]} hospitals, respectively. "
    text += r"""Answered counts determinate responses at any stage; qualifying requires Expanding or Fully Integrated. Unknown items stay in the group denominator but are not counted as qualifying. The groups overlap. These reported shares describe existing reports, not effectiveness, implementation costs or a recommended order of adoption. Full counts, unknown responses and shares among answered items are in Supplementary Data 1.
\end{minipage}\end{table}
\FloatBarrier

\subsection*{Conditional intervals for persistently outside populations}
We use the same 2,000 paired legacy-county resamples and seed as Supplementary Note 6. For each replicate, each subgroup's population is divided by the replicate's total population; that share is then multiplied by the fixed national total of 331,449,208. This standardization avoids interpreting variation in resampled population size as uncertainty about the Census total. Intervals describe conditional spatial variability, not uncertainty about enumerated counts, unreported AI use or questionnaire changes.
\begin{table}[!htbp]\centering\small
\caption{Conditional population intervals from paired county resampling.}
\label{tab:population_intervals}
\setlength{\tabcolsep}{4pt}
\begin{tabular}{@{}p{6.5cm}rr@{}}
\toprule
Population group & Observed (million) & Standardized 95\% interval \\\midrule
"""
    labels = {"outside_both": "Outside reported-AI threshold in both waves",
              "outside_both_near_any": "Of these, within 30 minutes of any hospital",
              "outside_both_far_any": "Of these, outside 30 minutes of any hospital"}
    for row in rows("population_conditional_intervals.csv"):
        if row["quantity"] in labels:
            text += labels[row["quantity"]] + f" & {float(row['estimate_millions']):.1f} & [{float(row['lower95_standardized_millions']):.1f}, {float(row['upper95_standardized_millions']):.1f}]" + r" \\" + "\n"
    text += r"\bottomrule\end{tabular}\end{table}\FloatBarrier" + "\n"
    (HERE / "additional_checks_si.tex").write_text(text)


if __name__ == "__main__":
    main()
