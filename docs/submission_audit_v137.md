# Submission Repository Audit - Nature Health v137

Audit date: 2026-06-15

Repository: `undergroundbreakfast/coverage-without-convergence`

## Summary

The public repository is suitable as a bounded reproducibility repository if the manuscript and README clearly state that licensed AHA source files cannot be redistributed. The repository should be cited as a partial reproducibility package, not as a complete raw-data archive.

## Checks performed

- Confirmed no raw AHA hospital-level CSV, Excel, Parquet, SQLite, or database dump files are visible in the prepared tree.
- Confirmed code obtains database credentials from environment variables rather than hard-coded password strings.
- Confirmed the repository includes only the dedicated Nature Health v137 code, documentation, figure assets, and aggregated tables.
- Added a Nature Health v137 landing description and reproducibility note.
- Added `.gitignore` patterns for raw data, database dumps, environment files, and local geospatial caches.

## Residual limitations

- Full end-to-end reproduction requires licensed AHA files and local database configuration.
- The Nature Health submission should cite a release tag, not only the moving `main` branch.

## Recommended citation language

"Reproducibility scripts, documentation, figure assets, and aggregated derived outputs not restricted by the AHA license are available at `https://github.com/undergroundbreakfast/coverage-without-convergence/tree/v137-submission`. Licensed AHA Annual Survey records cannot be redistributed."
