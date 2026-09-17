#!/usr/bin/env python3
"""Export a DOCX to PDF and PNG previews with macOS CJK fonts visible."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docx", required=True, type=Path)
    parser.add_argument("--pdf", required=True, type=Path)
    parser.add_argument("--preview-dir", required=True, type=Path)
    parser.add_argument("--dpi", type=int, default=160)
    return parser.parse_args()


def run(command: list[str], env: dict[str, str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True, env=env)


def main() -> None:
    args = parse_args()
    if not args.docx.exists():
        raise SystemExit(f"DOCX not found: {args.docx}")

    runtime = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"
    tools = runtime / "bin/override"
    soffice = tools / "soffice"
    pdftoppm = tools / "pdftoppm"
    pdfinfo = tools / "pdfinfo"
    for required in (soffice, pdftoppm, pdfinfo):
        if not required.exists():
            raise SystemExit(f"required bundled dependency not found: {required}")

    args.pdf.parent.mkdir(parents=True, exist_ok=True)
    if args.preview_dir.exists():
        shutil.rmtree(args.preview_dir)
    args.preview_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="resume-render-") as temp:
        temp_dir = Path(temp)
        font_config = temp_dir / "fonts.conf"
        font_cache = temp_dir / "font-cache"
        font_config.write_text(
            """<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "urn:fontconfig:fonts.dtd">
<fontconfig>
  <dir>/System/Library/Fonts</dir>
  <dir>/Library/Fonts</dir>
  <dir prefix="xdg">fonts</dir>
  <cachedir>{cache}</cachedir>
</fontconfig>
""".format(cache=font_cache),
            encoding="utf-8",
        )
        env = os.environ.copy()
        env["FONTCONFIG_FILE"] = str(font_config)
        env.pop("FONTCONFIG_PATH", None)
        run(
            [
                str(soffice),
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(temp_dir),
                str(args.docx.resolve()),
            ],
            env,
        )
        generated = temp_dir / f"{args.docx.stem}.pdf"
        if not generated.exists():
            raise SystemExit("LibreOffice returned without creating a PDF")
        shutil.copy2(generated, args.pdf)
        run([str(pdfinfo), str(args.pdf)], env)
        prefix = args.preview_dir / "page"
        run(
            [
                str(pdftoppm),
                "-png",
                "-r",
                str(args.dpi),
                str(args.pdf),
                str(prefix),
            ],
            env,
        )
    pages = sorted(args.preview_dir.glob("page-*.png"))
    if not pages:
        raise SystemExit("no PNG previews were created")
    print(f"created {args.pdf} and {len(pages)} preview page(s) in {args.preview_dir}")
    print("visual inspection is still required")


if __name__ == "__main__":
    main()
