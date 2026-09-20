"""Local exploratory stage summaries from the frozen 2024 extract.

No manuscript, Word document, database, or public package is changed.
Outputs contain aggregate counts only and remain subject to license review.
"""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / "v138_revision"
sys.path.insert(0, str(BASE))
from analyze_revision import hospitals, RUN, OP, CLIN
from analyze_context import context, ct_codes

LABELS = {0: "Not implementing", 1: "Exploring", 2: "Piloting/testing",
          3: "Expanding", 4: "Fully integrated"}
RAW_LABELS = {"Not Implementing": 0, "Exploring": 1, "Piloting/Testing": 2,
              "Expanding": 3, "Fully Integrated": 4}


def counts(values):
    known = int(values.notna().sum())
    n = len(values)
    row = {"hospitals": n, "determinate": known, "unknown": n-known}
    for stage, label in LABELS.items():
        k = int(values.eq(stage).sum())
        row[f"n_{stage}"] = k
        row[f"pct_answers_{stage}"] = 100*k/known if known else None
        row[f"pct_frame_{stage}"] = 100*k/n if n else None
    assert sum(row[f"n_{i}"] for i in LABELS) == known
    row["advanced_n"] = row["n_3"] + row["n_4"]
    row["advanced_pct_answers"] = 100*row["advanced_n"]/known if known else None
    return row


def main():
    source = RUN / "years/2024/hospital_ai_robotics_enriched_2024.parquet"
    start_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    h, a = hospitals(2024)
    assert len(h) == 6076 and h.ai_flag.sum() == 1737
    for item in a:
        raw = h[item].map(RAW_LABELS)
        assert np.allclose(raw, a[item], equal_nan=True), item
        other = set(h[item].dropna().unique()) - set(RAW_LABELS)
        assert other <= {"Don't Know"}, (item, other)
    rucc, _ = context()
    h["county_fips"] = h.county_fips.astype(str).str.zfill(5)
    county = ct_codes(h, "county_fips")
    h["rurality"] = pd.cut(county.map(rucc), [0, 3, 6, 9],
                            labels=["Metro", "Nonmetro 4-6", "Nonmetro 7-9"])
    masks = {"All": pd.Series(True, index=h.index)}
    for field in ["size", "rurality"]:
        for value in h[field].dropna().unique():
            masks[f"{field}: {value}"] = h[field].eq(value)
    rows = []
    for group, mask in masks.items():
        for item in a:
            row = {"group": group, "item": item, **counts(a.loc[mask, item])}
            row["dont_know"] = int(h.loc[mask, item].eq("Don't Know").sum())
            row["blank"] = int(h.loc[mask, item].isna().sum())
            assert row["dont_know"] + row["blank"] == row["unknown"]
            rows.append(row)
    stages = pd.DataFrame(rows)
    stages.to_csv(HERE / "application_stages.csv", index=False)
    # Highest observed stage is a profile, not a complete hospital status.
    profiles, breadth = [], []
    named = [c for c in a if c not in ["aitiot", "clnoai"]]
    for scope, cols in [("all14", list(a)), ("named12", named),
                        ("operational6", OP), ("clinical8", CLIN)]:
        for group, mask in masks.items():
            v = a.loc[mask, cols]
            top = v.max(axis=1)
            profiles.append({"scope": scope, "group": group,
                             "all_items_answered": int(v.notna().all(axis=1).sum()),
                             **counts(top)})
            complete = v.notna().all(axis=1)
            cv = v.loc[complete]
            breadth.append({"scope": scope, "group": group, "complete_hospitals": len(cv),
                            "median_expanding_or_integrated_items": float(cv.ge(3).sum(axis=1).median()) if len(cv) else None,
                            "median_fully_integrated_items": float(cv.eq(4).sum(axis=1).median()) if len(cv) else None})
    pd.DataFrame(profiles).to_csv(HERE / "highest_observed_stage.csv", index=False)
    pd.DataFrame(breadth).to_csv(HERE / "complete_answer_breadth.csv", index=False)
    all_counts = stages[stages.group.eq("All")].set_index("item")
    previous = pd.read_csv(BASE / "analysis/application_spatial_metrics.csv").set_index("item")
    assert (all_counts.advanced_n == previous.loc[all_counts.index, "qualifying"]).all()
    assert (all_counts.determinate == previous.loc[all_counts.index, "known"]).all()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == start_hash
    record = {"timestamp_pacific": datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
              "frame": "Frozen geocoded 2024 hospitals; N=6076; no imputation",
              "source_sha256": start_hash, "analytical_stage_labels": LABELS,
              "raw_codes": "AHA codes 1..5 correspond to analytical stages 0..4; raw 0 is don't know",
              "raw_to_analysis_mapping_verified_all14": True,
              "published_application_counts_reproduced": True,
              "outputs": "Local aggregate exploratory summaries; not approved for publication",
              "interpretation": "Item-level reported implementation stage, not time of first adoption, Rogers adopter category, mechanism, or longitudinal stage transition. Item-specific denominators differ; hospital highest observed stage may miss unreported higher stages. Complete-answer breadth has a selected denominator."}
    (HERE / "verification.json").write_text(json.dumps(record, indent=2)+"\n")
    print("ALL APPLICATIONS")
    print(stages[stages.group.eq("All")][["item", "determinate", "n_0", "n_1", "n_2", "n_3", "n_4", "unknown"]].to_string(index=False))
    print("CLINICAL DECISION SUPPORT STRATA")
    print(stages[stages.item.eq("clinai")][["group", "hospitals", "determinate", "n_4", "pct_answers_4", "advanced_pct_answers"]].to_string(index=False))
    print("HIGHEST OBSERVED STAGE ALL14")
    print(pd.DataFrame(profiles).query("scope == 'all14'")[["group", "hospitals", "determinate", "n_0", "n_1", "n_2", "n_3", "n_4", "unknown"]].to_string(index=False))


if __name__ == "__main__":
    main()
