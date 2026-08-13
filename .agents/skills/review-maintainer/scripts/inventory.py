#!/usr/bin/env python3
"""Create a reproducible vault file inventory without changing source files."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path


SF_DATALESS = 0x40000000


def sha256_file(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def should_skip(relative_path: Path, output_path: Path, summary_path: Path) -> bool:
    parts = relative_path.parts
    if not parts:
        return True
    if parts[0] == ".git" or parts[0].startswith(".git-recovery-"):
        return True
    return relative_path in {output_path, summary_path}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--hash-max-bytes", type=int, default=5 * 1024 * 1024)
    parser.add_argument("--source-commit", default="")
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output.resolve()
    summary = args.summary.resolve()
    output_relative = output.relative_to(root)
    summary_relative = summary.relative_to(root)

    rows: list[dict[str, str | int]] = []
    total_bytes = 0
    hashed_files = 0
    dataless_files = 0
    large_unhashed_files = 0

    for directory, directory_names, file_names in os.walk(root):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(root)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not (
                relative_directory == Path(".")
                and (name == ".git" or name.startswith(".git-recovery-"))
            )
        )
        for file_name in sorted(file_names):
            file_path = directory_path / file_name
            relative_path = file_path.relative_to(root)
            if should_skip(relative_path, output_relative, summary_relative):
                continue
            file_stat = file_path.lstat()
            is_dataless = bool(getattr(file_stat, "st_flags", 0) & SF_DATALESS)
            is_symlink = file_path.is_symlink()
            file_size = file_stat.st_size
            total_bytes += file_size
            checksum = ""
            checksum_state = "not-applicable"
            if is_symlink:
                checksum_state = "symlink"
            elif is_dataless:
                checksum_state = "dataless"
                dataless_files += 1
            elif file_size <= args.hash_max_bytes:
                checksum = sha256_file(file_path)
                checksum_state = "sha256"
                hashed_files += 1
            else:
                checksum_state = "over-size-limit"
                large_unhashed_files += 1
            rows.append(
                {
                    "path": relative_path.as_posix(),
                    "size": file_size,
                    "mtime_ns": file_stat.st_mtime_ns,
                    "kind": "symlink" if is_symlink else "file",
                    "dataless": "yes" if is_dataless else "no",
                    "checksum_state": checksum_state,
                    "sha256": checksum,
                }
            )

    rows.sort(key=lambda row: str(row["path"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(output, "wt", encoding="utf-8", newline="") as destination:
        writer = csv.DictWriter(
            destination,
            fieldnames=[
                "path",
                "size",
                "mtime_ns",
                "kind",
                "dataless",
                "checksum_state",
                "sha256",
            ],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(rows)

    manifest_digest = sha256_file(output)
    summary_data = {
        "source_commit": args.source_commit,
        "file_count": len(rows),
        "total_bytes": total_bytes,
        "hashed_files": hashed_files,
        "dataless_files": dataless_files,
        "large_unhashed_files": large_unhashed_files,
        "hash_max_bytes": args.hash_max_bytes,
        "manifest": output_relative.as_posix(),
        "manifest_sha256": manifest_digest,
    }
    summary.write_text(
        json.dumps(summary_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary_data, ensure_ascii=False))


if __name__ == "__main__":
    main()
