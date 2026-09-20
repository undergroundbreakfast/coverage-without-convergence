# Submission Repository Audit - Nature Health v137

Audit date: 2026-06-15

Historical audit, clarified September 20, 2026. This is not a certification of
revision reproducibility or AHA-derived-data redistribution rights.

Repository: `undergroundbreakfast/coverage-without-convergence`

## Summary

The public repository is suitable as a bounded reproducibility repository if the manuscript and README clearly state that licensed AHA source files cannot be redistributed. The repository should be cited as a partial reproducibility package, not as a complete raw-data archive.

## Checks performed

- Confirmed no raw AHA hospital-level CSV, Excel, Parquet, SQLite, or database dump files are visible in the prepared tree.
- No hard-coded credentials were found. Correction: the published utility does not connect to a database or read environment credentials; the prior statement about environment-based credential loading did not describe this dedicated repository's code.
- Confirmed the repository includes only the dedicated Nature Health v137 code, documentation, figure assets, and aggregated tables.
- Added a Nature Health v137 landing description and reproducibility note.
- Added `.gitignore` patterns for raw data, database dumps, environment files, and local geospatial caches.

## Residual limitations

- The original release lacks the full extraction and analysis pipeline. Licensed AHA inputs and database configuration alone do not make it end-to-end reproducible.
- The Nature Health submission should cite a release tag, not only the moving `main` branch.

## Recommended citation language

"Reproducibility scripts, documentation, figure assets, and aggregated derived outputs not restricted by the AHA license are available at `https://github.com/undergroundbreakfast/coverage-without-convergence/tree/v137-submission`. Licensed AHA Annual Survey records cannot be redistributed."
