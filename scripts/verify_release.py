"""Verify the public software inventory and file checksums."""

import ast
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git",
    ".venv",
    "venv",
    "data",
    "outputs",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}
ROOT_FILES = {
    ".gitignore",
    ".zenodo.json",
    "README.md",
    "CHANGELOG.md",
    "LICENSE",
    "CITATION.cff",
    "requirements.txt",
    "requirements-figures.txt",
}
DIRECTORY_TYPES = {
    "code": ".py",
    "scripts": ".py",
    "tests": ".py",
    "docs": ".md",
    ".github": ".yml",
}
PATTERNS = [
    r"/(?:Users|home)/",
    r"\bgh[pousr]_[A-Za-z0-9]{20,}",
    r"github_pat_[A-Za-z0-9_]{20,}",
    r"AKIA[A-Z0-9]{16}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    r"postgres(?:ql)?://[^\s]+",
]


def valid_path(name):
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        return False
    if len(path.parts) == 1:
        return name in ROOT_FILES
    return (
        path.parts[0] in DIRECTORY_TYPES
        and path.suffix == DIRECTORY_TYPES[path.parts[0]]
        and not any(p in EXCLUDED for p in path.parts)
    )


def verify():
    manifest = json.loads((ROOT / "release_manifest.json").read_text())
    seen = set()
    for record in manifest["files"]:
        name = record["path"]
        if name in seen or not valid_path(name):
            raise ValueError(f"Duplicate or unexpected inventory path: {name}")
        seen.add(name)
        path = ROOT / name
        if path.is_symlink():
            raise ValueError(f"Symlink in software inventory: {name}")
        data = path.read_bytes()
        if (
            len(data) != record["bytes"]
            or hashlib.sha256(data).hexdigest() != record["sha256"]
        ):
            raise ValueError(f"Checksum mismatch: {name}")
        text = data.decode("utf-8")
        if any(re.search(pattern, text) for pattern in PATTERNS):
            raise ValueError(f"Potential sensitive text in {name}")
        if path.suffix == ".py":
            ast.parse(text, filename=name)
    actual = {
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file()
        and not any(part in EXCLUDED for part in p.relative_to(ROOT).parts)
        and p.name not in {"release_manifest.json", ".DS_Store"}
    }
    if actual != seen:
        raise ValueError(
            f"Inventory differs from software tree; extra={sorted(actual - seen)}, missing={sorted(seen - actual)}"
        )
    return manifest


def main():
    manifest = verify()
    print(
        json.dumps(
            {
                "version": manifest["version"],
                "verified_files": len(manifest["files"]),
                "integrity_checks_passed": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
