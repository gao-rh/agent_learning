#!/usr/bin/env python3
"""Check relative Markdown links in the human-facing vault."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_PATTERN = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
IGNORED_SCHEMES = {"http", "https", "mailto", "obsidian", "data"}


def iter_markdown(root: Path):
    excluded_roots = {".git", ".local"}
    for file_path in root.rglob("*.md"):
        relative = file_path.relative_to(root)
        if relative.parts and (
            relative.parts[0] in excluded_roots
            or relative.parts[0].startswith(".git-recovery-")
        ):
            continue
        if (
            len(relative.parts) >= 3
            and relative.parts[0] == "学习资料"
            and "参考资料" in relative.parts
        ):
            continue
        if relative.parts[:2] == ("归档", "旧规划与旧制度"):
            continue
        if relative.parts[:3] == ("清单", "旧内容迁移判断", "资料"):
            continue
        if relative == Path("归档/迁移记录/规划文档全量台账-迁移前.md"):
            continue
        yield file_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []

    for markdown_path in sorted(iter_markdown(root)):
        text = markdown_path.read_text(encoding="utf-8")
        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in LINK_PATTERN.finditer(line):
                raw_target = match.group(1).strip().strip("<>")
                if not raw_target or raw_target.startswith("#"):
                    continue
                split_target = urlsplit(raw_target)
                if split_target.scheme.lower() in IGNORED_SCHEMES:
                    continue
                decoded_path = unquote(split_target.path)
                if not decoded_path:
                    continue
                candidate = Path(decoded_path)
                if not candidate.is_absolute():
                    candidate = markdown_path.parent / candidate
                if not candidate.exists():
                    relative_markdown = markdown_path.relative_to(root).as_posix()
                    failures.append(
                        f"{relative_markdown}:{line_number}: {raw_target}"
                    )

    if failures:
        print("\n".join(failures))
        raise SystemExit(1)
    print("markdown_links_ok=yes")


if __name__ == "__main__":
    main()
