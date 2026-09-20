# Version history

## v143-code, September 20, 2026

- Uses the current title and Communications Health revision context.
- Adds revision analysis-stage scripts, tests and documentation. Corrected figures
  and new aggregate summaries remain local pending redistribution-rights confirmation.
- Documents missing extraction/provenance dependencies and release rights gates.
- Fixes zero-weight behavior in the legacy quantile helper; defines the all-zero
  Gini convention; rejects invalid numeric inputs; adds data-free tests.
- Separates minimal helper requirements from the pinned revision environment.
- Clarifies that the original validator checks schemas, not scientific results.
- Removes manuscript-composition code and its unavailable internal dependency from
  the distributable plotting module; plotting computations are retained.

No manuscript estimate is changed by the generic-helper fixes. Revision scripts
use their original production calculations. Source/package hashes record changes.
No new revision-derived data or images are published in this code-only update.

## v137-submission, June 2026

Original public release, commit f82720314a3630304e121e097820d60497ccd675. Preserved
without retagging. Contains the original title, figures, tables and method helpers,
not the revision analyses or the full extraction pipeline. The archived map images
have known legend/occlusion defects; use revision figures for the revised paper.
