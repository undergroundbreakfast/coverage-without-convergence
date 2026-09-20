# Reproducing the revision analyses

## Boundary

This code snapshot distributes 17 analysis/plotting scripts, not a complete raw-AHA
extraction pipeline. The scripts begin with the study's frozen geocoded extracts
and population panel. Independently obtaining a survey license does not guarantee
that these extracts can be reconstructed without additional extraction work.
The v137 public release supplies no substitute extraction implementation.

Data-free unit tests and revision import/synthetic checks have a narrower purpose
than reproduction: they check code integrity and selected calculations without
making network requests or opening licensed records. The repackaged pipeline has
not been independently rerun end to end from newly acquired AHA records.

## Environment

Use Python 3.14. The minimal root requirements are sufficient for generic-helper
tests. The revision environment lists the tested versions of its direct scientific
dependencies; it is not a full platform-independent lockfile.

```bash
python -m pip install -r code/revision_v143/requirements.txt
python scripts/check_revision_code.py
python scripts/check_revision_inputs.py
```

The last command is expected to report missing private inputs in a public download.
It checks paths and selected column schemas without printing records. It does not
grant access, download anything, or infer missing data. Configure `PAPER2_SHAPES_DIR`
for authorized geometry, or use the package-relative `inputs/shapefiles` directory
under `code/revision_v143/`.

## Required inputs

All paths below are relative to `code/revision_v143/`.

| Input | Required content | Not distributed |
| --- | --- | --- |
| `run_geo_multi_20260322_215110_7a831e/years/2022/hospital_ai_robotics_enriched_2022.parquet` | Frozen geocoded 2022 hospitals, N=6,095; 1,118 qualifying | Licensed extract |
| Corresponding `years/2024/hospital_ai_robotics_enriched_2024.parquet` | Frozen geocoded 2024 hospitals, N=6,076; 1,737 qualifying | Licensed extract |
| `pr_inclusion_sensitivity_v128_exact/transition_detail_A_v128_50dc_bg_50dc_hosp.csv` | 238,433 unique GEOIDs, 331,449,208 residents, both waves' distances/transitions | Fine-grained derived panel |
| `Revisions/v138_revision/private/rucc2023.csv` | USDA 2023 RUCC export, including `FIPS`, `Attribute`, `Value` | Context input |
| `Revisions/v138_revision/private/chr2024.csv` | CHR 2024 export with its original two-row header structure | Context input |
| `Revisions/v139_revision/private/2020_Gaz_counties_national.zip` | Census county Gazetteer, including land area for density | Context input |
| `USA_BlockGroups_2020Pop.geojson` under the shapes directory | `GEOID`, `population`, original polygons and CRS | Geometry/population layer; provenance requires verification |
| `tl_2024_us_county.shp` and companion `.dbf`, `.shx`, `.prj` files under shapes | County/planning-region boundaries | Geometry |

Both hospital extracts require `hospital_id`, `ai_flag`, `robo_flag`, `bsc`,
`county_fips`, `latitude`, `longitude`, `cntrl`, `serv`, and `sysname`. The five 2022
items are `wfaipsn`, `wfaippd`, `wfaiss`, `wfaiart`, `wfaioacw`, with Yes/No text.
The 2024 items are `aiopef`, `aipatd`, `airevc`, `aiscop`, `aisswm`, `aitiot`,
`clinai`, `clnoai`, `diagai`, `papcai`, `pcoeai`, `pdmrai`, `pophai`, `surgai`.
Each needs an analytical `_num` column (0=not implementing through 4=fully
integrated; unknown is missing). Maturity validation also requires the original
stage-label columns. Do not confuse this recoding with the original survey codes.

The panel needs `GEOID`, `POPULATION`, `county_fips`, `state_fips`, `drive_2022`,
`drive_2024`, `within_2022`, `within_2024`. GEOIDs and FIPS retain leading zeros.
The preflight lists minimum schema checks; count, stage consistency and exact
distance agreement are asserted by the analysis scripts themselves.

## Execution order

Commands below are relative to `code/revision_v143/`. Each script resolves its own
location. Create `analysis`, `private`, `figures`, and `Source_Data` directories
inside each analysis directory before running; these are ignored runtime outputs.
Also create `Revisions/v142_revision/Source_Data/revision_additions` and
`Revisions/v143_revision/figures`. None of these output trees is a release input.

1. `python Revisions/v138_revision/analyze_revision.py`
2. `python Revisions/v138_revision/analyze_context.py`
3. `python Revisions/v138_revision/analyze_uncertainty.py`
4. `python Revisions/v139_revision/analyze_reporting.py`
5. `python Revisions/income_spatial_sensitivity_20260919/analyze.py --draws 300`
6. `python Revisions/income_spatial_sensitivity_20260919/summarize.py`
7. `python Revisions/v142_revision/extend_evidence.py`
8. `python Revisions/v142_revision/build_additional_tables.py`

The primary run must reproduce the frozen distances to within 1e-7 minutes before
later results are used. The radius is 3,958.7613 miles, minutes per mile 1.95, and
exact zero distances alone are replaced by 0.1 miles. Production quantiles use
`statsmodels.stats.weightstats.DescrStatsW.quantile`, not the legacy utility's
midpoint interpolation. Frozen counts and values are assertions, not instructions
to alter an independently derived dataset to force a match.

After the numerical runs, generate figures in this order:

1. `python Revisions/v138_revision/build_revision_exhibits.py`
2. `python Revisions/v138_revision/build_maps.py`
3. `python Revisions/v142_revision/refresh_figure1.py`
4. `python Revisions/income_spatial_sensitivity_20260919/figures.py`
5. `python Revisions/income_spatial_sensitivity_20260919/income_access_map.py`
6. `python Revisions/adoption_stage_audit_20260920/audit.py`
7. `python Revisions/adoption_stage_audit_20260920/maturity_map.py`
8. `python Revisions/adoption_stage_audit_20260920/publication_figures.py`
9. `python Revisions/adoption_stage_audit_20260920/paired_maps.py`

Some plotting filenames retain the analysis version in which they originated.
The [output map](output_map_v143.md) identifies their v143 manuscript equivalents.
The income plotting script also generates exploratory figures not used in the
manuscript. Only explicitly mapped and rights-cleared figures should be considered
for a future derived-output release; none is added by this code-only update.

## Checks and provenance

`docs/revision_source_manifest.json` records the earlier software-package provenance.
`docs/candidate_code_changes.json` records the prepared code's source hashes and scoped
portability changes. Scientific calculation bodies are retained; the two removed
blocks generated manuscript/response drafts, not analytical results. Import-time
execution is guarded in two scripts so imports do not run analyses.

`release_manifest.json` fixes the code-snapshot contents. Validation is checksum/schema
verification, not approval of derived-data rights. After any edit, regenerate the
review inventory deliberately and rerun checks; do not bypass a mismatch.

Runtime products include sensitive caches and fine-grained derived geography.
Never publish an entire analysis directory. New revision aggregate outputs and
finished maps are not included in this code snapshot and remain subject to rights review.
Historical SI analyses predating the 17 revision scripts are not all reimplemented
here; the output guide marks that limitation rather than claiming full coverage.
