# Reproduction guide

## Environment

Use Python 3.14 with `requirements.txt`. The scientific dependency versions match the analysis environment. They pin the direct dependencies, rather than every transitive dependency or operating-system library.

The PDF typography utilities additionally require `requirements-figures.txt` and locally installed Arial fonts. No fonts are distributed.

## Inputs and outputs

The default input directory is `data/` at the repository root. Follow [inputs.md](inputs.md) for the layout and required columns. An existing input directory can be selected without modifying the scripts:

```sh
export PAPER2_DATA_DIR=/path/to/prepared-inputs
export PAPER2_OUTPUT_DIR=/path/to/new-analysis-outputs
```

`PAPER2_SHAPES_DIR` optionally selects a separate geography directory. Otherwise geography is read from `data/geography/`.

Use separate, non-nested input and output locations. Start with a new output directory for each input set: the scripts reuse intermediate geographic and model caches. Reusing a cache from another input set can invalidate a run.

```sh
python scripts/check_inputs.py
python scripts/run_analysis.py --stage all
```

`check_inputs.py` reports missing files and columns without displaying records. Analysis scripts additionally check sample counts, primary definitions, geographic joins, and agreement with the frozen distances. These checks are expected to fail for a different study frame; do not alter inputs to force a match.

`run_analysis.py --list --stage all` lists the execution order without opening data or running an analysis. Numerical stages precede figure generation. The runner uses the original 300 draws per missing-response scenario; paired county bootstrap analyses retain their original 2,000 resamples and random seeds.

## Execution order

| Stage | Scripts, in order |
| --- | --- |
| Access and uncertainty | `analyze_access.py`, `analyze_context.py`, `analyze_uncertainty.py` |
| Reporting and missing responses | `analyze_reporting.py`, `sensitivity_analysis.py`, `summarize_sensitivity.py` |
| Additional summaries | `extend_evidence.py`, `build_additional_tables.py`, `division_summary.py`, `hospital_definition_counts.py` |
| Figures and implementation stages | `plot_access.py`, `plot_maps.py`, `plot_figure1.py`, `sensitivity_figures.py`, `income_access_map.py`, `implementation_stages.py`, `maturity_map.py`, `paired_maps.py` |

The runner supplies the input/output arguments needed by the two hospital tabulation scripts. Other scripts resolve locations through `code/config.py`.

Generated files are grouped under `outputs/access/`, `reporting/`, `sensitivity/`, `additional/`, `implementation/`, and `publication/`. Within those groups, `analysis/` holds summaries, `cache/` holds intermediate values, and `figures/` holds images. A completed figure run collects nine numbered figures into `outputs/figures/`. Intermediate filenames retain historical suffixes so existing output references remain identifiable.

## Optional figure typography

The numerical and plotting stages create the scientific plots. Two additional utilities reproduce the panel typography and scenario-label edits applied to the publication vector figures. They require the matching pre-typography PDFs, which are not bundled; those PDFs can differ in layout and labels from the analysis plots. They preserve the remaining drawing operations and validate the text replacements.

```sh
python -m pip install -r requirements-figures.txt
python code/polish_figure_labels.py \
  --source /path/to/pre-typography-figures \
  --output outputs/formatted_figures \
  --font-dir /path/to/arial-fonts
python code/update_income_figure_labels.py \
  --source outputs/formatted_figures/Supplementary_Figure_3.pdf \
  --output outputs/final_figures/Supplementary_Figure_3.pdf
```

The font directory must contain `Arial.ttf` and `Arial Bold.ttf`. The second utility uses Matplotlib's bundled DejaVu Sans, or an explicit `--font-file` path. Supply the matching vector PDFs using the numbered filenames in the output index. The scripts deliberately fail if the expected text objects differ. Typography checks and rendered previews are written alongside the formatted output.

## Checks and interpretation

```sh
python -m unittest discover -s tests -v
python scripts/check_code.py
python scripts/check_code.py --include-pdf  # after installing the optional dependencies
python scripts/verify_release.py
```

Tests cover production distance and quantile conventions, weighted inequality, implementation counts, preservation of observed survey responses, and exact scenario probabilities. Import checks do not open study inputs. File checks verify the release inventory and checksums. These checks do not independently reproduce the study from raw survey records.

The code uses a 3,958.7613-mile Earth radius and 1.95 minutes per mile. Only exact-zero distances are replaced by 0.1 miles. Quantiles use `statsmodels.stats.weightstats.DescrStatsW`. Survey item definitions differ between years, missing answers are not verified non-use, and simulation percentiles are conditional scenario ranges rather than confidence intervals.

## Software archive

Create an archive from the explicit release inventory:

```sh
python scripts/package_release.py --output /path/to/coverage-without-convergence-1.0.0.zip
```

This command verifies checksums and includes only inventoried software files. Local inputs, computed outputs, caches, and Git history are excluded.
