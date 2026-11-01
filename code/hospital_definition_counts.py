"""Tabulate 2024 reported AI definitions in the geocoded hospital frame.

Input is the authorized hospital_ai_robotics_enriched_2024.parquet analysis
extract described in the reproduction guide. No hospital records are exported.
Requires pandas and pyarrow. Usage: python hospital_definition_counts.py
--input PATH --output PATH.csv
"""

from pathlib import Path
import argparse
import pandas as pd

OP = ["aiopef", "aipatd", "airevc", "aiscop", "aisswm", "aitiot"]
CLIN = ["clinai", "clnoai", "diagai", "papcai", "pcoeai", "pdmrai", "pophai", "surgai"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    data = pd.read_parquet(args.input, columns=[f + "_num" for f in OP + CLIN])
    assert len(data) == 6076, "Expected the 2024 geocoded analysis frame"
    flags = {
        "All 14 items, Expanding or Fully Integrated": data.isin([3, 4]).any(axis=1),
        "Operational 6 items, Expanding or Fully Integrated": data[
            [f + "_num" for f in OP]
        ]
        .isin([3, 4])
        .any(axis=1),
        "Clinical 8 items, Expanding or Fully Integrated": data[
            [f + "_num" for f in CLIN]
        ]
        .isin([3, 4])
        .any(axis=1),
        "All 14 items, Fully Integrated": data.eq(4).any(axis=1),
    }
    expected = [1737, 1091, 1557, 859]
    rows = []
    for (definition, flag), count in zip(flags.items(), expected):
        assert int(flag.sum()) == count, definition
        rows.append(
            dict(
                survey_year=2024,
                frame="Geocoded hospitals",
                definition=definition,
                qualifying_hospitals_n=count,
                hospital_frame_n=len(data),
                qualifying_percent=100 * count / len(data),
                difference_from_all_14_primary_n=count - expected[0],
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.output, index=False)


if __name__ == "__main__":
    main()
