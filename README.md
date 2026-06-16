# Coverage without convergence

Dedicated reproducibility repository for the Nature Health submission:

**Coverage without convergence: Geographic inequality in proximity to AI-reporting hospitals in the United States, 2022-2024**

This repository contains the public, releasable materials for the manuscript's proximity and access analyses. It is intentionally narrow: it does not include companion-project outputs on robotics, causal mortality analyses, propensity/TMLE models, dissertation artifacts, or old exploratory logs.

## What this repository supports

The manuscript links 2022 and 2024 American Hospital Association (AHA) AI-use measures to U.S. Census block groups and county health data to estimate population proximity to hospitals reporting active AI deployment. The analysis focuses on:

- population coverage within policy-relevant travel-time thresholds;
- access-distance inequality using Lorenz/Gini and related distributional summaries;
- threshold-crossing and persistent-exclusion transition groups;
- pre-diffusion health-burden overlap using Years of Potential Life Lost (YPLL) as descriptive context.

The manuscript does **not** estimate causal effects of AI deployment on mortality.

## Repository structure

- `code/`: geospatial proximity and inequality workflow.
- `docs/`: reproducibility notes and submission audit.
- `results/nature_health_v137/figures/`: main and supplementary figure assets for v137.
- `results/nature_health_v137/tables/`: aggregated manuscript tables for v137.
- `requirements.txt`: lightweight Python dependency list.
- `LICENSE`: MIT license for code and documentation in this repository.

## Data availability limits

Raw AHA Annual Survey hospital-level files are licensed and cannot be redistributed here. The repository therefore provides a partial reproducibility package: code, documentation, figures, and aggregated derived outputs that do not disclose restricted hospital-level AHA records.

Running the full pipeline from raw inputs requires:

- licensed AHA Annual Survey files for 2022 and 2024;
- a geocoded AHA hospital frame;
- U.S. Census 2020 block-group population data;
- County Health Rankings county-level covariates and YPLL measures;
- local database credentials and path configuration.

Database credentials are expected through environment variables, especially `POSTGRESQL_KEY`; credentials and raw data should never be committed.

## Main output mapping

- Figure 1: `results/nature_health_v137/figures/2022_vs_2024_diffusion_v137.png`
- Figure 2: `results/nature_health_v137/figures/manuscript_travel_distribution_ai_rucc.png`
- Figure 3: `results/nature_health_v137/figures/2022_2024_delta_map_v137.png`
- Supplementary figure: `results/nature_health_v137/figures/appendix_ai_flag_mode_sensitivity_2024_v137.png`
- Main tables: `results/nature_health_v137/tables/`

See `docs/nature_health_v137_reproducibility_note.md` for the detailed reproducibility boundary and manuscript-output mapping.

## Suggested manuscript citation

Reproducibility scripts, documentation, figures, and aggregated derived outputs not restricted by the AHA license are available at:

`https://github.com/undergroundbreakfast/coverage-without-convergence/tree/v137-submission`

