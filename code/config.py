"""Shared input and output locations for the analysis scripts."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = (
    Path(os.environ.get("PAPER2_DATA_DIR", PROJECT_ROOT / "data"))
    .expanduser()
    .resolve()
)
OUTPUT_DIR = (
    Path(os.environ.get("PAPER2_OUTPUT_DIR", PROJECT_ROOT / "outputs"))
    .expanduser()
    .resolve()
)
CONTEXT_DIR = DATA_DIR / "context"
SHAPES_DIR = (
    Path(os.environ.get("PAPER2_SHAPES_DIR", DATA_DIR / "geography"))
    .expanduser()
    .resolve()
)


def prepare_output_dirs():
    """Create output directories only when an analysis is explicitly run."""
    if (
        OUTPUT_DIR == DATA_DIR
        or OUTPUT_DIR.is_relative_to(DATA_DIR)
        or DATA_DIR.is_relative_to(OUTPUT_DIR)
    ):
        raise ValueError(
            "Input and output directories must be separate, non-nested locations."
        )
    for topic in [
        "access",
        "reporting",
        "sensitivity",
        "additional",
        "implementation",
        "publication",
    ]:
        for child in ["", "analysis", "cache", "figures", "Source_Data"]:
            (OUTPUT_DIR / topic / child).mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "additional/Source_Data/revision_additions").mkdir(
        parents=True, exist_ok=True
    )
    (OUTPUT_DIR / "tables").mkdir(parents=True, exist_ok=True)
