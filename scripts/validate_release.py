"""Verify an explicit release inventory, not numerical reproduction or rights."""
import ast
import csv
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
SUFFIXES = {".md", ".py", ".txt", ".csv", ".png", ".pdf", ".json", ".cff"}
IDENTIFIERS = {"geoid", "county_fips", "hospital_id", "latitude", "longitude", "sysname"}
PATTERNS = [r"/(?:Users|home)/", r"\bgh[pousr]_[A-Za-z0-9]{20,}",
            r"github_pat_[A-Za-z0-9_]{20,}", r"AKIA[A-Z0-9]{16}",
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"postgres(?:ql)?://[^\s]+", r"[A-Za-z0-9._%+-]+@gmail\.com"]


def inspect(name, data):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe inventory path: {name}")
    if path.suffix not in SUFFIXES and name not in {".gitignore", "LICENSE"}:
        raise ValueError(f"Unexpected release file type: {name}")
    if any(part in {"private", "analysis", "Source_Data", ".git", "__pycache__"} for part in path.parts):
        raise ValueError(f"Runtime/private path in release: {name}")
    if path.suffix in {".png", ".pdf"}:
        magic = b"\x89PNG\r\n\x1a\n" if path.suffix == ".png" else b"%PDF-"
        if not data.startswith(magic):
            raise ValueError(f"Invalid media signature: {name}")
        return
    text = data.decode("utf-8")
    if any(re.search(p, text) for p in PATTERNS):
        raise ValueError(f"Potential sensitive text requires review: {name}")
    if path.suffix == ".py":
        ast.parse(text, filename=name)
    if path.suffix == ".csv":
        rows = list(csv.reader(io.StringIO(text)))
        if len(rows) < 2 or len(rows) > 1001:
            raise ValueError(f"Unexpected aggregate table size: {name}")
        header = [c.strip().lower() for c in rows[0]]
        if IDENTIFIERS.intersection(header):
            raise ValueError(f"Granular identifier columns in release: {name}")
        if any(len(row) != len(header) for row in rows[1:]):
            raise ValueError(f"Malformed CSV row: {name}")


def main():
    manifest = json.loads((ROOT / "release_manifest.json").read_text())
    seen = set()
    for record in manifest["files"]:
        name = record["path"]
        if name in seen:
            raise ValueError(f"Duplicate inventory entry: {name}")
        seen.add(name)
        path = ROOT / name
        if path.is_symlink():
            raise ValueError(f"Symlink in release: {name}")
        data = path.read_bytes()
        if len(data) != record["bytes"] or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError(f"Checksum mismatch: {name}")
        inspect(name, data)
    print(json.dumps({"inventoried_files_checked": len(seen), "integrity_checks_passed": True,
                      "status": manifest["status"], "rights_clearance_certified": False,
                      "end_to_end_reproduction_certified": False}, indent=2))
    return seen


if __name__ == "__main__":
    main()
