"""Check script imports without opening study inputs or running analyses."""

import argparse
import ast
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OPTIONAL = {"polish_figure_labels.py", "update_income_figure_labels.py"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--include-pdf", action="store_true", help="Also import optional PDF utilities"
    )
    args = parser.parse_args()
    paths = sorted((ROOT / "code").glob("*.py"))
    for path in paths:
        ast.parse(path.read_text(), filename=str(path))
    with tempfile.TemporaryDirectory(prefix="coverage-check-") as temp:
        work = Path(temp)
        env = dict(
            os.environ,
            PYTHONDONTWRITEBYTECODE="1",
            PAPER2_DATA_DIR=str(work / "data"),
            PAPER2_OUTPUT_DIR=str(work / "outputs"),
            MPLCONFIGDIR=str(work / "matplotlib"),
            XDG_CACHE_HOME=str(work / "cache"),
        )
        checked = 0
        for path in paths:
            if path.name in OPTIONAL and not args.include_pdf:
                continue
            command = 'import runpy,sys; sys.path.insert(0,sys.argv[2]); runpy.run_path(sys.argv[1],run_name="import_check")'
            subprocess.run(
                [sys.executable, "-c", command, str(path), str(path.parent)],
                env=env,
                check=True,
            )
            checked += 1
        if (work / "data").exists() or (work / "outputs").exists():
            raise RuntimeError("Import created an input or output directory")
        print(
            f"{len(paths)} scripts parsed; {checked} imports passed; no study inputs opened or outputs written."
        )


if __name__ == "__main__":
    main()
