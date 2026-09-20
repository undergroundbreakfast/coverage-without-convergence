# Code scope

`geospatial_access_workflow_v137.py` supplies generic methods and archived-file
checks. It makes no database connection and does not reproduce manuscript outputs.
The candidate fixes zero-weight quantiles, explicitly handles all-zero Gini, and
rejects invalid inputs. These changes do not recompute manuscript estimates.

`revision_v143/` supplies the actual revision analysis-stage scripts on frozen
authorized extracts. See [the run guide](../docs/reproduction_v143.md). Raw-data
extraction and licensed records are not provided. The revision uses its own
production distance/quantile conventions; do not substitute the legacy helpers.
