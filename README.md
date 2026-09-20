# More hospitals report artificial intelligence use but geographic divides persist

Analysis code for the Communications Health revision, v143.

**v143-code: revision scripts, tests and documentation.** New revision tables and
finished figures are withheld pending redistribution-rights confirmation. The
`v137-submission` release remains the historical original submission; its assets
are retained unchanged. Neither this update nor the software license certifies
rights to redistribute AHA-derived outputs.

## Study scope

The study measures population proximity to hospitals reporting artificial
intelligence use in the 2022 and 2024 American Hospital Association surveys.
Geographic gaps persist while metropolitan-nonmetropolitan gaps narrow. Coverage
growth depends on the expanded 2024 instrument; reported implementation depth and
missing-status assumptions are examined separately. Premature mortality is
pre-existing health-burden context, not evidence of an AI effect on mortality.

Proximity is not verified service availability, clinical effectiveness, or patient
exposure. Survey constructs are not fully equivalent across waves.

## Start here

- [Reproduction guide](docs/reproduction_v143.md): inputs, execution order and limits.
- [Output guide](docs/output_map_v143.md): manuscript figures, tables and source summaries.
- [Version history](CHANGELOG.md): original release versus this code update.
- [Data and licensing boundaries](docs/data_and_licensing.md).
- [Publication status](docs/release_checklist.md): scope and remaining rights gates.

## What can be run without licensed inputs?

The generic calculation tests and package-integrity checks require no AHA data:

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/validate_release.py
python code/geospatial_access_workflow_v137.py
```

The last command checks archived file presence and CSV schemas only. It does not
regenerate or numerically validate the paper. The legacy midpoint-quantile helper
is not used in the revision's production quantiles.

## Revision code

`code/revision_v143/` contains the actual analysis-stage scripts, including the
reporting models, fixed-reporting panel, per-application analyses, income-aware
spatial scenarios, and implementation-depth maps. A separate pinned environment
and a no-data import check are documented in the reproduction guide.

These scripts require authorized frozen extracts and contextual inputs. They are
not a turnkey extraction pipeline from independently obtained AHA files. The
original release does not contain that extraction pipeline either. Source-data
licensing alone does not provide the missing extraction work or map provenance.

## Files and version boundaries

- `results/nature_health_v137/`: archived original-submission assets.
- New revision figures and aggregate summaries are not included in this code update.
- `code/geospatial_access_workflow_v137.py`: legacy method helpers, with tested
  input-validation fixes in this update; the original tag remains unchanged.
- `code/revision_v143/`: revision analysis and plotting scripts.
- `release_manifest.json`: explicit file inventory and checksums.
- `CITATION.cff`: citation metadata for the code snapshot; no DOI is claimed.

The revised Figure 2 is a rurality/income comparison, not the original Figure 2
travel-time distribution. Use the output guide rather than assuming numbering is
stable across versions. Corrected maps have been prepared locally but are not
included in this code update. Historical image defects are documented rather than
silently rewriting the tag.

## Data availability

The authors do not distribute licensed AHA records covered by their agreement.
Source-data access must be arranged with AHA. No raw hospital records, individual
hospital predictions, fine-grained derived map-value files, credentials, reviewer
responses, or correspondence are included here. New aggregate summaries and
finished figures remain local pending redistribution/provenance review; absence
of identifiers is not evidence of permission.

The MIT license covers author-owned software and documentation only. It does not
grant rights to AHA data, third-party geography, or other third-party materials.

## Existing public archive

The [v137-submission release](https://github.com/undergroundbreakfast/coverage-without-convergence/releases/tag/v137-submission)
is retained as historical. Do not cite it as containing the v143 analyses.
Use the [v143-code snapshot](https://github.com/undergroundbreakfast/coverage-without-convergence/tree/v143-code)
for this revision code, with the input and reproduction limits described above.
