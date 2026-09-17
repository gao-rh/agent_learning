#!/usr/bin/env python3
"""Stage safe vault files without asking Git to open File Provider paths."""

from __future__ import annotations

import argparse
import os
import stat
import subprocess
from pathlib import Path


ALLOWED_SUFFIXES = {
    ".command",
    ".css",
    ".gz",
    ".json",
    ".html",
    ".js",
    ".lock",
    ".md",
    ".mmd",
    ".mjs",
    ".png",
    ".py",
    ".svg",
    ".toml",
    ".tsv",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_ROOTS = {".git", ".local", ".obsidian", "tmp", "output"}
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


def is_allowed(relative_path: Path, file_size: int, *, explicit: bool = False) -> bool:
    if not relative_path.parts:
        return False
    if (
        explicit and relative_path.parts[:2] == ("output", "docx")
        and relative_path.suffix.lower() == ".docx"
    ):
        return file_size <= MAX_BYTES
    if relative_path.parts[0] in EXCLUDED_ROOTS:
        return False
    if relative_path.parts[0].startswith(".git-recovery-"):
        return False
    if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_path.parts[:-1]):
        return False
    if "本地资料" in relative_path.parts:
        return False
    if "参考资料" in relative_path.parts and relative_path.parts[0] == "4-学习资料":
        return False
    if relative_path.name in EXCLUDED_NAMES:
        return False
    if relative_path.name in {".gitignore", ".rgignore", ".python-version", "keys.env.example"}:
        return file_size <= MAX_BYTES
    if relative_path.name.startswith(".env"):
        return False
    if relative_path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False
    return file_size <= MAX_BYTES


def is_protected(relative_path: Path) -> bool:
    """These sources require explicitly selected paths, not a default bulk scan."""
    return (
        relative_path.parts[:1] == ("5-归档",)
        or relative_path.parts[:3] == ("2-进行中", "面试准备", "面试记录")
        or relative_path.parts[:3] == ("1-清单", "旧内容迁移判断", "资料")
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--files", type=Path, nargs="+", help="Only stage these explicitly authorized files, relative to root")
    parser.add_argument("--dry-run", action="store_true", help="List eligible additions/deletions without reading content or changing the index")
    args = parser.parse_args()
    root = args.root.resolve()

    tracked_output = run_git(root, "ls-files", "-z")
    tracked_paths = {
        Path(value.decode("utf-8"))
        for value in tracked_output.split(b"\0")
        if value
    }

    if args.files:
        candidates = set()
        for value in args.files:
            # Normalize '..' without following a final symlink outside the vault.
            absolute = Path(os.path.abspath(root / value))
            if not absolute.is_relative_to(root):
                parser.error(f"Path is outside root: {value}")
            if absolute.is_dir():
                parser.error(f"Expected a file, not a directory: {value}")
            if not absolute.exists() and absolute.relative_to(root) not in tracked_paths:
                parser.error(f"Path does not exist and is not tracked: {value}")
            candidates.add(absolute.relative_to(root))
    else:
        candidate_output = run_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        candidates = {Path(value.decode("utf-8")) for value in candidate_output.split(b"\0") if value}
        candidates = {path for path in candidates if not is_protected(path)}

    # Also honor ignore rules for already-tracked paths; never untrack them here.
    ignore_result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"], cwd=root,
        input=b"".join(path.as_posix().encode("utf-8") + b"\0" for path in sorted(candidates)),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if ignore_result.returncode not in (0, 1):
        raise RuntimeError(ignore_result.stderr.decode("utf-8"))
    ignored = {Path(value.decode("utf-8")) for value in ignore_result.stdout.split(b"\0") if value}

    staged_entries: list[bytes] = []
    staged_count = 0
    deletion_count = 0

    for relative_path in sorted(candidates - ignored, key=lambda item: item.as_posix()):
        absolute_path = root / relative_path
        if absolute_path.is_symlink() or absolute_path.resolve() != absolute_path:
            continue
        exists = absolute_path.exists()
        size = absolute_path.stat().st_size if exists else 0
        if not is_allowed(relative_path, size, explicit=bool(args.files)):
            continue
        if not exists:
            if relative_path in tracked_paths:
                if args.dry_run:
                    print(f"delete\t{relative_path.as_posix()}")
                else:
                    staged_entries.append(f"0 {'0' * 40}\t{relative_path.as_posix()}\0".encode("utf-8"))
                deletion_count += 1
            continue
        if not absolute_path.is_file():
            continue
        if args.dry_run:
            print(f"add\t{relative_path.as_posix()}")
        else:
            file_stat = absolute_path.stat()
            with absolute_path.open("rb") as source:
                blob_id = run_git(root, "hash-object", "-w", "--stdin", input_bytes=source.read())
            mode = "100755" if file_stat.st_mode & stat.S_IXUSR else "100644"
            staged_entries.append(
                mode.encode("ascii") + b" " + blob_id.strip() + b"\t"
                + relative_path.as_posix().encode("utf-8") + b"\0"
            )
        staged_count += 1

    if staged_entries:
        run_git(root, "update-index", "-z", "--index-info", input_bytes=b"".join(staged_entries))
    prefix = "eligible" if args.dry_run else "staged"
    print(f"{prefix}_files={staged_count}")
    print(f"{prefix}_deletions={deletion_count}")


if __name__ == "__main__":
    main()
