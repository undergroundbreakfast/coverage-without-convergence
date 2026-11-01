"""Check required input files and schemas without displaying data records."""

import csv
import json
from pathlib import Path
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from config import DATA_DIR, CONTEXT_DIR, SHAPES_DIR

ITEMS22 = ["wfaipsn", "wfaippd", "wfaiss", "wfaiart", "wfaioacw"]
ITEMS24 = [
    "aiopef",
    "aipatd",
    "airevc",
    "aiscop",
    "aisswm",
    "aitiot",
    "clinai",
    "clnoai",
    "diagai",
    "papcai",
    "pcoeai",
    "pdmrai",
    "pophai",
    "surgai",
]


def check_inputs():
    requirements = {
        DATA_DIR / "panel/transition_detail.csv": [
            "GEOID",
            "POPULATION",
            "county_fips",
            "state_fips",
            "drive_2022",
            "drive_2024",
            "within_2022",
            "within_2024",
        ],
        CONTEXT_DIR / "rucc2023.csv": ["FIPS", "Attribute", "Value"],
        CONTEXT_DIR / "chr2024.csv": [
            "5-digit FIPS Code",
            "Median Household Income raw value",
        ],
        CONTEXT_DIR / "2020_Gaz_counties_national.zip": ["GEOID", "ALAND_SQMI"],
        SHAPES_DIR / "USA_BlockGroups_2020Pop.geojson": [],
    }
    for ext in ["shp", "shx", "dbf", "prj"]:
        requirements[SHAPES_DIR / f"tl_2024_us_county.{ext}"] = []
    common = [
        "hospital_id",
        "ai_flag",
        "robo_flag",
        "bsc",
        "county_fips",
        "latitude",
        "longitude",
        "cntrl",
        "serv",
        "sysname",
        "state",
    ]
    for year, items in [(2022, ITEMS22), (2024, ITEMS24)]:
        requirements[
            DATA_DIR
            / f"hospitals/years/{year}/hospital_ai_robotics_enriched_{year}.parquet"
        ] = common + items + [item + "_num" for item in items]
    issues = []
    for path, columns in requirements.items():
        if not path.is_file():
            issues.append({"file": path.name, "issue": "missing required input"})
            continue
        try:
            if path.suffix == ".csv":
                with path.open(encoding="latin1", newline="") as stream:
                    header = next(csv.reader(stream), [])
            elif path.suffix == ".parquet":
                import pyarrow.parquet as pq

                header = pq.read_schema(path).names
            elif path.suffix == ".zip":
                with ZipFile(path) as archive:
                    names = [n for n in archive.namelist() if n.endswith(".txt")]
                    if len(names) != 1:
                        raise ValueError("Expected one county Gazetteer text file")
                    with archive.open(names[0]) as stream:
                        header = (
                            stream.readline().decode("utf-8-sig").strip().split("\t")
                        )
            else:
                continue
            absent = sorted(set(columns) - {c.strip() for c in header})
            if absent:
                issues.append({"file": path.name, "missing_columns": absent})
        except (ValueError, OSError, UnicodeError) as exc:
            issues.append({"file": path.name, "issue": type(exc).__name__})
    return issues


def main():
    issues = check_inputs()
    print(
        json.dumps(
            {
                "inputs_ready": not issues,
                "issues": issues,
                "scope": "File and schema checks; analyses also verify study-frame counts and definitions.",
            },
            indent=2,
        )
    )
    return int(bool(issues))


if __name__ == "__main__":
    raise SystemExit(main())
