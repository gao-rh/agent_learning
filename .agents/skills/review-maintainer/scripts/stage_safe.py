#!/usr/bin/env python3
"""Stage safe vault files without asking Git to open File Provider paths."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
from pathlib import Path


ALLOWED_SUFFIXES = {
    ".gz",
    ".json",
    ".lock",
    ".md",
    ".mmd",
    ".mjs",
    ".png",
    ".py",
    ".svg",
    ".toml",
    ".tsv",
}
EXCLUDED_ROOTS = {".git", ".local", ".obsidian"}
EXCLUDED_DIRECTORY_NAMES = {
    ".git",
    ".local",
    ".obsidian",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "outputs",
    "venv",
}
EXCLUDED_NAMES = {".DS_Store"}
MAX_BYTES = 5 * 1024 * 1024


def run_git(root: Path, *arguments: str, input_bytes: bytes | None = None) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=root,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout


def is_allowed(relative_path: Path, file_size: int) -> bool:
    if not relative_path.parts:
        return False
    if relative_path.parts[0] in EXCLUDED_ROOTS:
        return False
    if relative_path.parts[0].startswith(".git-recovery-"):
        return False
    if "参考资料" in relative_path.parts and relative_path.parts[0] == "学习资料":
        return False
    if relative_path.name in EXCLUDED_NAMES:
        return False
    if relative_path.name == ".gitignore":
        return True
    if relative_path.name.startswith(".env"):
        return False
    if relative_path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False
    return file_size <= MAX_BYTES


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    tracked_output = run_git(root, "ls-files", "-z")
    tracked_paths = {
        Path(value.decode("utf-8"))
        for value in tracked_output.split(b"\0")
        if value
    }

    staged_entries: list[bytes] = []
    staged_count = 0
    deletion_count = 0

    for tracked_path in sorted(tracked_paths, key=lambda item: item.as_posix()):
        absolute_path = root / tracked_path
        if absolute_path.exists() or absolute_path.is_symlink():
            continue
        staged_entries.append(
            f"0 {'0' * 40}\t{tracked_path.as_posix()}\n".encode("utf-8")
        )
        deletion_count += 1

    for directory, directory_names, file_names in os.walk(root):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(root)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not (
                name in EXCLUDED_DIRECTORY_NAMES
                or
                (relative_directory == Path(".") and name in EXCLUDED_ROOTS)
                or name.startswith(".git-recovery-")
                or (
                    relative_directory.parts[:1] == ("学习资料",)
                    and name == "参考资料"
                )
            )
        )
        for file_name in sorted(file_names):
            absolute_path = directory_path / file_name
            relative_path = absolute_path.relative_to(root)
            file_stat = absolute_path.lstat()
            if not is_allowed(relative_path, file_stat.st_size):
                continue
            with absolute_path.open("rb") as source:
                blob_id = run_git(root, "hash-object", "-w", "--stdin", input_bytes=source.read())
            mode = "100755" if file_stat.st_mode & stat.S_IXUSR else "100644"
            staged_entries.append(
                mode.encode("ascii")
                + b" "
                + blob_id.strip()
                + b"\t"
                + relative_path.as_posix().encode("utf-8")
                + b"\n"
            )
            staged_count += 1

    if staged_entries:
        run_git(root, "update-index", "--index-info", input_bytes=b"".join(staged_entries))
    print(f"staged_files={staged_count}")
    print(f"staged_deletions={deletion_count}")


if __name__ == "__main__":
    main()
