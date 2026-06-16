# Nature Health v137 Reproducibility Note

This note documents the public reproducibility scope for the Nature Health v137 submission, **"Coverage without convergence: Geographic inequality in proximity to AI-reporting hospitals in the United States, 2022-2024."**

## Data dependencies

The analysis requires:

- American Hospital Association Annual Survey hospital files for 2022 and 2024. These are licensed data and are not redistributed here.
- A geocoded AHA hospital frame used to locate hospitals reporting AI deployment.
- U.S. Census 2020 block-group population data.
- County Health Rankings county-level covariates and Years of Potential Life Lost (YPLL) measures.
- Public geographic boundary and routing support files used by the geospatial workflow.

## Reproducibility boundary

The repository can document and reproduce the analysis logic, generated outputs, and derived nonrestricted tables and figures. It cannot reproduce the full pipeline from raw inputs unless the user has licensed AHA files and updates local database credentials and path configuration.

The manuscript Data Availability statement should therefore use bounded language such as "reproducibility scripts, analysis outputs, and aggregated derived tables not restricted by the AHA license" rather than claiming that all source data or all analytic files are public.

## Script orientation

- `code/geospatial_access_workflow_v137.py` documents reusable public calculations for proxy drive-time conversion, population-weighted quantiles, weighted Gini, threshold coverage, and validation of the releasable v137 outputs.
- The dedicated repository intentionally excludes companion-project scripts and outputs for robotics, propensity/TMLE, and causal mortality analyses.

## Manuscript-output mapping

Main-text outputs in v137 are assembled from the geospatial workflow and final manuscript figure assets:

- Figure 1: contiguous-U.S. block-group proximity maps for 2022 and 2024.
- Figure 2: Rural-Urban Continuum Code (RUCC)-stratified travel-time cumulative distribution function.
- Figure 3: threshold-crossing and proxy travel-time reduction maps.
- Tables 1-3: 50-state-plus-D.C. longitudinal summary, contiguous-U.S. block-group summary, and transition-group profile.
- Supplementary Notes 1-12: frame crosswalks, AI taxonomy, sensitivity analyses, bootstrap intervals, alternative inequality metrics, E2SFCA benchmark, and OSRM proxy validation.

## Interpretation boundary

The Nature Health manuscript estimates proximity to AI-reporting hospitals. It does not verify access to a specific AI service, does not measure AI-specific capacity, and does not estimate causal effects of AI deployment on mortality. YPLL is used only as pre-diffusion health-burden context.

## Release hygiene before submission

Before submitting the manuscript, freeze the public repository state with a release tag:

```bash
git tag -a v137-submission -m "Nature Health v137 submission reproducibility package"
git push origin main --tags
```

If the final submitted manuscript changes after v137, create a new release tag matching the submitted version.
