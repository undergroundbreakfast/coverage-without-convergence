"""Create a software ZIP using only the verified release inventory."""

import argparse
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED, ZipInfo
from verify_release import ROOT, verify


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = verify()
    destination = args.output.expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Archive already exists: {destination}")
    if destination == ROOT or destination.is_relative_to(ROOT):
        raise ValueError("Write the archive outside the software directory.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    names = sorted([r["path"] for r in manifest["files"]] + ["release_manifest.json"])
    with ZipFile(destination, "x", compression=ZIP_DEFLATED) as archive:
        for name in names:
            info = ZipInfo(
                f"coverage-without-convergence-{manifest['version']}/{name}",
                date_time=(2026, 11, 1, 0, 0, 0),
            )
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / name).read_bytes())
    print(destination)


if __name__ == "__main__":
    main()
