"""Run the analysis stages in dependency order using prepared study inputs."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
from config import DATA_DIR, OUTPUT_DIR, prepare_output_dirs
from check_inputs import check_inputs

NUMERICAL = [
    "analyze_access",
    "analyze_context",
    "analyze_uncertainty",
    "analyze_reporting",
    "sensitivity_analysis",
    "summarize_sensitivity",
    "extend_evidence",
    "build_additional_tables",
    "division_summary",
    "hospital_definition_counts",
]
FIGURES = [
    "plot_access",
    "plot_maps",
    "plot_figure1",
    "sensitivity_figures",
    "income_access_map",
    "implementation_stages",
    "maturity_map",
    "paired_maps",
]
FIGURE_FILES = {
    "Figure_1": "additional/figures/Figure_1_v142",
    "Figure_2": "access/figures/Figure_2_v138",
    "Figure_3": "access/figures/Figure_3_v138",
    "Supplementary_Figure_1": "access/figures/Supplementary_Figure_1_v138",
    "Supplementary_Figure_2": "access/figures/Supplementary_Figure_2_v138",
    "Supplementary_Figure_3": "sensitivity/figures/rural_income_sensitivity",
    "Supplementary_Figure_4": "sensitivity/figures/income_access_bivariate_CBG",
    "Supplementary_Figure_5": "publication/figures/Supplementary_Figure_5_v143",
    "Supplementary_Figure_6": "publication/figures/Supplementary_Figure_6_v143",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stage", choices=["numerical", "figures", "all"], default="numerical"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List stages without opening inputs or running calculations",
    )
    args = parser.parse_args()
    names = (NUMERICAL if args.stage in ["numerical", "all"] else []) + (
        FIGURES if args.stage in ["figures", "all"] else []
    )
    if args.list:
        print("\n".join(names))
        return
    issues = check_inputs()
    if issues:
        raise SystemExit(
            "Required inputs are missing or incomplete. Run python scripts/check_inputs.py for details."
        )
    prepare_output_dirs()
    for name in names:
        command = [sys.executable, str(ROOT / "code" / (name + ".py"))]
        if name == "sensitivity_analysis":
            command += ["--draws", "300"]
        elif name == "division_summary":
            command += [
                "--input",
                str(DATA_DIR / "hospitals"),
                "--output",
                str(OUTPUT_DIR / "tables"),
            ]
        elif name == "hospital_definition_counts":
            command += [
                "--input",
                str(
                    DATA_DIR
                    / "hospitals/years/2024/hospital_ai_robotics_enriched_2024.parquet"
                ),
                "--output",
                str(
                    OUTPUT_DIR
                    / "tables/Supplementary_Tables_6_7_15_hospital_counts.csv"
                ),
            ]
        print("Running", name, flush=True)
        subprocess.run(command, check=True)
    if args.stage in ["figures", "all"]:
        destination = OUTPUT_DIR / "figures"
        destination.mkdir(exist_ok=True)
        for label, relative in FIGURE_FILES.items():
            for extension in ["pdf", "png"]:
                source = OUTPUT_DIR / f"{relative}.{extension}"
                if not source.is_file():
                    raise FileNotFoundError(f"Expected generated figure: {source}")
                shutil.copyfile(source, destination / f"{label}.{extension}")
        print("Collected figures in", destination)


if __name__ == "__main__":
    main()
