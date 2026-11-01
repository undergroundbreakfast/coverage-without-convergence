# Figure and table index

All script names below are relative to `code/`. The runner places numbered figures in `outputs/figures/`; intermediate outputs remain grouped by analysis topic. Table references follow the final supplementary material.

| Article item or analysis | Generating scripts | Output or scope |
| --- | --- | --- |
| Main Table 1: spatial estimates and intervals | `analyze_access.py`, `analyze_uncertainty.py`, `extend_evidence.py` | `access/analysis/spatial_metrics.csv`, `paired_bootstrap_intervals.csv`; `additional/analysis/population_conditional_intervals.csv` |
| Figure 1 | `plot_maps.py`, then `plot_figure1.py` | Coverage and proxy-time maps for the two years |
| Figure 2 | `analyze_context.py`, `plot_access.py` | Rurality and rural-income coverage comparisons |
| Figure 3 | `plot_maps.py` | Changes in proximity and proxy time |
| Supplementary Figure 1 | `plot_maps.py` | Alternative reporting definitions |
| Supplementary Figure 2 | `plot_access.py` | Population-weighted travel-time distributions |
| Supplementary Figure 3 | `sensitivity_analysis.py`, `sensitivity_figures.py` | Rural-income contrasts across missing-response scenarios |
| Supplementary Figure 4 | `income_access_map.py` | Income and proximity map |
| Supplementary Figure 5 | `maturity_map.py` | Implementation-stage proximity and rurality |
| Supplementary Figure 6 | `maturity_map.py`, `paired_maps.py` | Matched maps for two implementation-stage thresholds |
| Supplementary Table 5 | `division_summary.py` | `tables/Supplementary_Table_5_division_qualifying_use.csv` |
| Supplementary Tables 6, 7, and 15: geocoded hospital counts | `hospital_definition_counts.py` | `tables/Supplementary_Tables_6_7_15_hospital_counts.csv` |
| Reporting and completeness models | `analyze_context.py`, `analyze_reporting.py` | Hospital strata, coefficients, exclusions, and reporting diagnostics under `access/analysis/` and `reporting/analysis/` |
| Fixed-reporting and per-application analyses | `analyze_access.py` | Balanced-frame, application, and benchmark summaries under `access/analysis/` |
| Missing-response scenarios | `sensitivity_analysis.py`, `summarize_sensitivity.py` | Scenario definitions, exact expected coverage, simulated intervals, and model diagnostics under `sensitivity/analysis/` |
| Supplementary Tables 38–40 | `extend_evidence.py`, `build_additional_tables.py` | Scenario rurality coverage, application/size/rurality summaries, and population-weighted intervals under `additional/analysis/` |
| Supplementary Tables 41–42 | `implementation_stages.py`, `maturity_map.py` | Application-stage and maturity-proximity summaries under `implementation/` |

The two PDF utilities apply presentation changes to the figures; they do not calculate estimates. See the reproduction guide for their commands. Fixed explanatory text in table-formatting helpers describes this study frame and should be reviewed when adapting the code to another dataset.

## Coverage limits

This package does not regenerate every cell in the main and supplementary tables. Full-survey hospital denominators, some transition summaries, earlier premature-mortality context, and earlier routing validation require additional source preparation or analyses outside this package. Hospital-count scripts reproduce the geocoded counts identified above, not the full-survey totals. The article's supplementary files provide the final reported summaries and figures.

Detailed intermediate files can contain hospital-derived or fine-grained spatial information. Generated outputs are local analysis products; their inclusion here as output paths does not grant redistribution rights.
