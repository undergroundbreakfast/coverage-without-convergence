"""Check authorized input paths/schemas without printing any data records."""
import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "code/revision_v143"
SHAPES = Path(os.environ.get("PAPER2_SHAPES_DIR", ROOT / "inputs/shapefiles"))
BASE = ROOT / "Revisions/v138_revision/private"
ITEMS22 = ["wfaipsn", "wfaippd", "wfaiss", "wfaiart", "wfaioacw"]
ITEMS24 = ["aiopef", "aipatd", "airevc", "aiscop", "aisswm", "aitiot", "clinai",
           "clnoai", "diagai", "papcai", "pcoeai", "pdmrai", "pophai", "surgai"]


def main():
    requirements = {
        ROOT / "pr_inclusion_sensitivity_v128_exact/transition_detail_A_v128_50dc_bg_50dc_hosp.csv":
            ["GEOID", "POPULATION", "county_fips", "state_fips", "drive_2022", "drive_2024", "within_2022", "within_2024"],
        BASE / "rucc2023.csv": ["FIPS", "Attribute", "Value"],
        BASE / "chr2024.csv": ["5-digit FIPS Code", "Median Household Income raw value"],
        ROOT / "Revisions/v139_revision/private/2020_Gaz_counties_national.zip": [],
        SHAPES / "USA_BlockGroups_2020Pop.geojson": [],
    }
    for ext in ["shp", "shx", "dbf", "prj"]:
        requirements[SHAPES / f"tl_2024_us_county.{ext}"] = []
    common = ["hospital_id", "ai_flag", "robo_flag", "bsc", "county_fips", "latitude", "longitude", "cntrl", "serv", "sysname"]
    for year in [2022, 2024]:
        fields = ITEMS22 if year == 2022 else ITEMS24 + [item + "_num" for item in ITEMS24]
        requirements[ROOT / f"run_geo_multi_20260322_215110_7a831e/years/{year}/hospital_ai_robotics_enriched_{year}.parquet"] = common + fields
    issues = []
    for path, columns in requirements.items():
        if not path.is_file():
            issues.append({"file": path.name, "issue": "missing required input"})
            continue
        if path.suffix == ".csv":
            with path.open(encoding="latin1", newline="") as stream:
                header = next(csv.reader(stream), [])
        elif path.suffix == ".parquet":
            import pyarrow.parquet as pq
            header = pq.read_schema(path).names
        else:
            continue
        absent = sorted(set(columns) - set(header))
        if absent:
            issues.append({"file": path.name, "missing_columns": absent})
    print(json.dumps({"inputs_ready": not issues, "issues": issues,
                      "note": "Path/schema checks only; no permission or numerical validation implied."}, indent=2))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
