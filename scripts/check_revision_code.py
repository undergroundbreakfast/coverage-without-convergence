"""Import revision scripts and exercise production helpers on synthetic inputs."""
import importlib.metadata
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REV = ROOT / "code/revision_v143/Revisions"


def main():
    files = sorted(REV.rglob("*.py"))
    if len(files) != 17:
        raise SystemExit(f"Expected 17 revision scripts; found {len(files)}")
    with tempfile.TemporaryDirectory(prefix="paper2-import-") as temp:
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", MPLCONFIGDIR=temp, XDG_CACHE_HOME=temp)
        for path in files:
            command = "import runpy,sys; sys.path.insert(0,sys.argv[2]); runpy.run_path(sys.argv[1],run_name='import_check')"
            result = subprocess.run([sys.executable, "-c", command, str(path), str(path.parent)],
                                    env=env, capture_output=True, text=True)
            if result.returncode:
                raise SystemExit(f"Import failed: {path.relative_to(ROOT)}\n{result.stderr}")
            print("Import OK:", path.relative_to(ROOT))
        os.environ["MPLCONFIGDIR"] = temp
        sys.path.insert(0, str(REV / "v138_revision"))
        import numpy as np
        import pandas as pd
        from analyze_revision import distance, gini, metrics
        stages = runpy.run_path(str(REV / "adoption_stage_audit_20260920/audit.py"))
        summary = stages["counts"](pd.Series([0., 1., 2., 3., 4., np.nan]))
        assert summary["determinate"] == 5 and summary["unknown"] == 1
        assert summary["advanced_n"] == 2 and summary["pct_answers_4"] == 20.
        assert gini(np.array([0., 2.]), np.array([1., 1.])) == .5
        destinations = pd.DataFrame({"latitude": [0., 0.], "longitude": [0., 1.]})
        points = np.deg2rad([[0., 0.], [0., .75]])
        broad, _ = distance(points, destinations)
        strict, _ = distance(points, destinations.iloc[:1])
        assert broad[0] == .1 and np.all(strict >= broad)
        result = metrics(np.array([1., 2., 3.]), np.array([1., 1., 1.]))
        assert result["median_miles"] == 2. and result["coverage30_pct"] == 100.
    print(json.dumps({"revision_imports": len(files), "synthetic_checks_passed": True,
                      "licensed_data_opened": False,
                      "end_to_end_reproduction": False,
                      "numpy": importlib.metadata.version("numpy")}, indent=2))


if __name__ == "__main__":
    main()
