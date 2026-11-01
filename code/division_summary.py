"""Supplementary Table 5: primary qualifying reports in the geocoded hospital frame.

Usage: python division_summary.py --input RUN_DIRECTORY --output OUTPUT_DIRECTORY
Input: years/{year}/hospital_ai_robotics_enriched_{year}.parquet. These files
contain licensed hospital records and must be obtained through authorized access.
Only division-level aggregates are written. Requires pandas and pyarrow.
The qualifying flag is audited against the published primary item definitions.
"""

from pathlib import Path
import argparse, hashlib, json
import pandas as pd

DIVISIONS = {
    "New England": "CT ME MA NH RI VT",
    "Middle Atlantic": "NJ NY PA",
    "East North Central": "IL IN MI OH WI",
    "West North Central": "IA KS MN MO NE ND SD",
    "South Atlantic": "DE DC FL GA MD NC SC VA WV",
    "East South Central": "AL KY MS TN",
    "West South Central": "AR LA OK TX",
    "Mountain": "AZ CO ID MT NV NM UT WY",
    "Pacific": "AK CA HI OR WA",
}
FIELDS = {
    2022: ["wfaipsn", "wfaippd", "wfaiss", "wfaiart", "wfaioacw"],
    2024: [
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
    ],
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rows = []
    audit = {}
    mapping = {
        state: division
        for division, states in DIVISIONS.items()
        for state in states.split()
    }
    for year, expected in [(2022, (6095, 1118)), (2024, (6076, 1737))]:
        path = args.input / f"years/{year}/hospital_ai_robotics_enriched_{year}.parquet"
        d = pd.read_parquet(path)
        fields = [f + "_num" for f in FIELDS[year]]
        flag = (
            d[fields].eq(1).any(axis=1)
            if year == 2022
            else d[fields].isin([3, 4]).any(axis=1)
        ).astype(int)
        assert flag.equals(d.ai_flag.astype(int)), "Primary qualifying flag mismatch"
        assert (len(d), int(flag.sum())) == expected
        assert not d.hospital_id.duplicated().any()
        d["division"] = d.state.str.strip().str.upper().map(mapping)
        assert d.division.notna().all()
        for division, g in d.groupby("division"):
            n = len(g)
            qual = int(g.ai_flag.sum())
            rows.append(
                {
                    "survey_year": year,
                    "division": division,
                    "hospital_frame_n": n,
                    "qualifying_hospitals_n": qual,
                    "qualifying_percent": qual / n * 100,
                }
            )
        audit[str(year)] = {
            "input_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "frame_n": len(d),
            "qualifying_n": int(flag.sum()),
            "definition_verified": True,
        }
    out = pd.DataFrame(rows)
    out.to_csv(
        args.output / "Supplementary_Table_5_division_qualifying_use.csv", index=False
    )
    # Independently retained phase-portrait output is available in the original run.
    previous = args.input / "csv/manuscript_phase_portrait_ai.csv"
    if previous.exists():
        prior = pd.read_csv(previous)
        check = out.merge(
            prior,
            left_on=["survey_year", "division"],
            right_on=["analysis_year", "unit_label"],
            validate="one_to_one",
        )
        assert (
            len(check) == 18
            and (check.qualifying_percent - check.ai_hospital_prevalence_pct)
            .abs()
            .max()
            < 1e-9
        )
        audit["matches_existing_phase_portrait"] = True
    w = out.pivot(index="division", columns="survey_year")
    w["change"] = w["qualifying_percent"][2024] - w["qualifying_percent"][2022]
    w = w.sort_values("change", ascending=False)
    lines = []
    for div, row in w.iterrows():
        a = int(row[("qualifying_hospitals_n", 2022)])
        b = int(row[("hospital_frame_n", 2022)])
        c = int(row[("qualifying_hospitals_n", 2024)])
        e = int(row[("hospital_frame_n", 2024)])
        lines.append(
            f"{div} & {a:,}/{b:,} & {100 * a / b:.1f} & {c:,}/{e:,} & {100 * c / e:.1f} & {100 * c / e - 100 * a / b:+.1f} "
            + r"\\"
        )
    (args.output / "division_table_rows.tex").write_text("\n".join(lines) + "\n")
    (args.output / "division_audit.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
