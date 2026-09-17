#!/usr/bin/env python3
"""Check relative Markdown links in the human-facing vault."""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_START_PATTERN = re.compile(r"!?\[[^\]]*\]\(")
EXCLUDED_ROOTS = {".git", ".local", ".obsidian", "5-归档", "tmp", "output"}
EXCLUDED_DIRECTORY_NAMES = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".ipynb_checkpoints", "build", "dist", ".next", ".turbo", "本地资料",
    ".runs", ".cache", "outputs",
}


def iter_link_targets(line: str):
    """Keep balanced parentheses and angle-wrapped paths intact."""
    for match in LINK_START_PATTERN.finditer(line):
        start = match.end()
        if line[start:].lstrip().startswith("<"):
            left = line.index("<", start)
            right = line.find(">", left + 1)
            if right >= 0:
                yield line[left + 1:right]
            continue
        depth = 1
        escaped = False
        for end in range(start, len(line)):
            char = line[end]
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    target = re.sub(r'''\s+["'][^"']*["']\s*$''', "", line[start:end].strip())
                    yield target.replace(r"\(", "(").replace(r"\)", ")")
                    break


def is_excluded(relative: Path) -> bool:
    parts = relative.parts
    return bool(parts) and (
        parts[0] in EXCLUDED_ROOTS
        or parts[0].startswith(".git-recovery-")
        or any(part in EXCLUDED_DIRECTORY_NAMES for part in parts)
        or (parts[0] == "4-学习资料" and "参考资料" in parts)
        or parts[:3] == ("1-清单", "旧内容迁移判断", "资料")
        or parts[:3] == ("2-进行中", "面试准备", "面试记录")
    )


def iter_markdown(root: Path):
    for directory, names, files in os.walk(root, followlinks=False):
        parent = Path(directory)
        names[:] = sorted(
            name for name in names
            if not is_excluded((parent / name).relative_to(root))
            and not (parent / name).is_symlink()
        )
        for name in sorted(files):
            path = parent / name
            if path.suffix.lower() == ".md" and not path.is_symlink():
                yield path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--files", type=Path, nargs="+", help="Only check these explicitly authorized files, relative to root")
    parser.add_argument("--list", action="store_true", help="List the selected files without reading their content")
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []

    if args.files:
        selected = sorted({(root / path).resolve() for path in args.files})
        for path in selected:
            if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != ".md":
                parser.error(f"Expected an existing Markdown file within root: {path}")
    else:
        selected = sorted(iter_markdown(root))
    if args.list:
        for path in selected:
            print(path.relative_to(root).as_posix())
        return

    checked_links = 0
    for markdown_path in selected:
        try:
            text = markdown_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            failures.append(f"{markdown_path.relative_to(root)}: read failed: {error}")
            continue
        fence = None
        for line_number, line in enumerate(text.splitlines(), start=1):
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
            if marker:
                token = marker.group(1)
                if fence is None:
                    fence = token
                elif token[0] == fence[0] and len(token) >= len(fence):
                    fence = None
                continue
            if fence:
                continue
            line = re.sub(r"`+[^`]*`+", "", line)
            for raw_target in iter_link_targets(line):
                raw_target = raw_target.strip()
                if not raw_target or raw_target.startswith("#"):
                    continue
                split_target = urlsplit(raw_target)
                if split_target.scheme:
                    continue
                decoded_path = unquote(split_target.path)
                if not decoded_path:
                    continue
                candidate = Path(decoded_path)
                if not candidate.is_absolute():
                    candidate = markdown_path.parent / candidate
                # Codex file links may carry a line or line:column suffix.
                if not candidate.exists() and re.search(r":\d+(?::\d+)?$", str(candidate)):
                    candidate = Path(re.sub(r":\d+(?::\d+)?$", "", str(candidate)))
                checked_links += 1
                if not candidate.exists():
                    relative_markdown = markdown_path.relative_to(root).as_posix()
                    failures.append(
                        f"{relative_markdown}:{line_number}: {raw_target}"
                    )

    print(f"checked_files={len(selected)} checked_local_links={checked_links}")
    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print("markdown_links_ok=yes")


if __name__ == "__main__":
    main()
