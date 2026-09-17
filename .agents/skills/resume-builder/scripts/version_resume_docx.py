#!/usr/bin/env python3
"""Create an auditable small-version derivative of the resume DOCX."""

from __future__ import annotations

import argparse
import copy
import json
import zipfile
from pathlib import Path

from lxml import etree


W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--from-version", required=True)
    parser.add_argument("--to-version", required=True)
    parser.add_argument("--replace-json", type=Path)
    parser.add_argument("--insert-core-ability-json", type=Path)
    parser.add_argument("--move-paragraph-after-json", type=Path)
    parser.add_argument("--remove-top-header-accents", action="store_true")
    parser.add_argument("--collapse-continuation-title")
    parser.add_argument("--force-full-width-title", action="append", default=[])
    parser.add_argument("--tabbed-title", action="append", default=[])
    return parser.parse_args()


def cell_text(cell: etree._Element) -> str:
    return "".join(cell.xpath(".//w:t/text()", namespaces=NS)).strip()


def remove_top_header_accents(xml: bytes) -> bytes:
    root = etree.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    if body is None:
        raise RuntimeError("word/document.xml has no w:body")

    children = list(body)
    if not children or children[0].tag != f"{{{W}}}tbl":
        raise RuntimeError("expected the decorative top table as the first body element")
    top_table = children[0]
    fills = top_table.xpath(".//w:tcPr/w:shd/@w:fill", namespaces=NS)
    if fills[:2] != ["315A9B", "EDF2FA"] or cell_text(top_table):
        raise RuntimeError("first table does not match the known decorative top bar")
    body.remove(top_table)

    children = list(body)
    if children and children[0].tag == f"{{{W}}}p" and not "".join(
        children[0].xpath(".//w:t/text()", namespaces=NS)
    ).strip():
        body.remove(children[0])

    header_table = next(
        (
            table
            for table in body.findall(f"{{{W}}}tbl")
            if "高荣徽" in "".join(table.xpath(".//w:t/text()", namespaces=NS))
        ),
        None,
    )
    if header_table is None:
        raise RuntimeError("could not find the name/contact header table")

    row = header_table.find(f"{{{W}}}tr")
    grid = header_table.find(f"{{{W}}}tblGrid")
    if row is None or grid is None:
        raise RuntimeError("header table is missing row or grid")
    cells = row.findall(f"{{{W}}}tc")
    cols = grid.findall(f"{{{W}}}gridCol")
    if len(cells) != 3 or len(cols) != 3:
        raise RuntimeError("name/contact header no longer has the expected three columns")

    first_fill = cells[0].xpath("./w:tcPr/w:shd/@w:fill", namespaces=NS)
    if cell_text(cells[0]) or first_fill != ["315A9B"]:
        raise RuntimeError("first header cell does not match the known left accent")

    removed_width = int(cols[0].get(f"{{{W}}}w"))
    second_width = int(cols[1].get(f"{{{W}}}w")) + removed_width
    cols[1].set(f"{{{W}}}w", str(second_width))
    tc_width = cells[1].find(f"{{{W}}}tcPr/{{{W}}}tcW")
    if tc_width is not None:
        tc_width.set(f"{{{W}}}w", str(second_width))
    row.remove(cells[0])
    grid.remove(cols[0])

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def collapse_manual_continuation(xml: bytes, title: str) -> bytes:
    root = etree.fromstring(xml)
    body = root.find(f"{{{W}}}body")
    if body is None:
        raise RuntimeError("word/document.xml has no w:body")
    continuation = next(
        (
            table
            for table in body.findall(f"{{{W}}}tbl")
            if title in "".join(table.xpath(".//w:t/text()", namespaces=NS)).strip()
        ),
        None,
    )
    if continuation is None:
        raise RuntimeError(f"continuation title not found: {title}")
    previous = continuation.getprevious()
    if previous is None or not previous.xpath(".//w:br[@w:type='page']", namespaces=NS):
        raise RuntimeError("continuation title is not preceded by a manual page break")
    body.remove(previous)
    body.remove(continuation)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def force_full_width_title_tables(xml: bytes, titles: list[str]) -> bytes:
    root = etree.fromstring(xml)
    tables = root.xpath("//w:tbl", namespaces=NS)
    for title in titles:
        table = next(
            (
                item
                for item in tables
                if title in "".join(item.xpath(".//w:t/text()", namespaces=NS))
            ),
            None,
        )
        if table is None:
            raise RuntimeError(f"title table not found: {title}")
        table_width = table.find(f"{{{W}}}tblPr/{{{W}}}tblW")
        if table_width is None:
            raise RuntimeError(f"title table has no width definition: {title}")
        table_width.set(f"{{{W}}}type", "pct")
        table_width.set(f"{{{W}}}w", "5000")
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def convert_title_tables_to_tabbed_paragraphs(xml: bytes, titles: list[str]) -> bytes:
    root = etree.fromstring(xml)
    tables = root.xpath("//w:tbl", namespaces=NS)
    for title in titles:
        table = next(
            (
                item
                for item in tables
                if title in "".join(item.xpath(".//w:t/text()", namespaces=NS))
            ),
            None,
        )
        if table is None:
            raise RuntimeError(f"title table not found: {title}")
        cells = table.xpath("./w:tr[1]/w:tc", namespaces=NS)
        if len(cells) != 3:
            raise RuntimeError(f"title table must have three cells: {title}")
        paragraphs = [cell.find(f"{{{W}}}p") for cell in cells]
        if any(paragraph is None for paragraph in paragraphs):
            raise RuntimeError(f"title table cell has no paragraph: {title}")

        paragraph = etree.Element(f"{{{W}}}p")
        first_properties = paragraphs[0].find(f"{{{W}}}pPr")
        properties = (
            copy.deepcopy(first_properties)
            if first_properties is not None
            else etree.Element(f"{{{W}}}pPr")
        )
        tabs = properties.find(f"{{{W}}}tabs")
        if tabs is not None:
            properties.remove(tabs)
        tabs = etree.Element(f"{{{W}}}tabs")
        center = etree.SubElement(tabs, f"{{{W}}}tab")
        center.set(f"{{{W}}}val", "center")
        center.set(f"{{{W}}}pos", "5018")
        right = etree.SubElement(tabs, f"{{{W}}}tab")
        right.set(f"{{{W}}}val", "right")
        right.set(f"{{{W}}}pos", "10035")
        properties.insert(0, tabs)
        paragraph.append(properties)

        for index, source in enumerate(paragraphs):
            if index:
                tab_run = etree.Element(f"{{{W}}}r")
                etree.SubElement(tab_run, f"{{{W}}}tab")
                paragraph.append(tab_run)
            for run in source.findall(f"{{{W}}}r"):
                paragraph.append(copy.deepcopy(run))
        table.getparent().replace(table, paragraph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def insert_core_ability(xml: bytes, spec: dict[str, str]) -> bytes:
    required = {"label", "body", "before_label"}
    if set(spec) != required or not all(
        isinstance(spec[key], str) and spec[key] for key in required
    ):
        raise RuntimeError(
            "core ability JSON must contain non-empty label, body, and before_label strings"
        )

    root = etree.fromstring(xml)
    if any(
        spec["label"] in "".join(paragraph.xpath(".//w:t/text()", namespaces=NS))
        for paragraph in root.xpath("//w:p", namespaces=NS)
    ):
        raise RuntimeError(f"core ability already exists: {spec['label']}")

    anchors = [
        paragraph
        for paragraph in root.xpath("//w:p", namespaces=NS)
        if "".join(paragraph.xpath(".//w:t/text()", namespaces=NS)).startswith(
            spec["before_label"]
        )
    ]
    if len(anchors) != 1:
        raise RuntimeError(
            f"expected one core ability anchor for {spec['before_label']}, found {len(anchors)}"
        )
    anchor = anchors[0]
    template = anchor.getprevious()
    if template is None or template.tag != f"{{{W}}}p":
        raise RuntimeError("core ability anchor has no preceding paragraph template")
    style = template.find(f"{{{W}}}pPr/{{{W}}}pStyle")
    if style is None or style.get(f"{{{W}}}val") != "ListBullet":
        raise RuntimeError("preceding core ability paragraph is not a ListBullet")

    paragraph = copy.deepcopy(template)
    text_nodes = paragraph.xpath(".//w:t", namespaces=NS)
    if len(text_nodes) != 2:
        raise RuntimeError(
            f"core ability template must contain two text runs, found {len(text_nodes)}"
        )
    text_nodes[0].text = spec["label"]
    text_nodes[1].text = spec["body"]
    anchor.addprevious(paragraph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def move_paragraph_after(xml: bytes, spec: dict[str, str]) -> bytes:
    required = {"label", "after_label"}
    if set(spec) != required or not all(
        isinstance(spec[key], str) and spec[key] for key in required
    ):
        raise RuntimeError(
            "paragraph move JSON must contain non-empty label and after_label strings"
        )

    root = etree.fromstring(xml)
    paragraphs = root.xpath("//w:p", namespaces=NS)

    def find_one(label: str) -> etree._Element:
        matches = [
            paragraph
            for paragraph in paragraphs
            if "".join(
                paragraph.xpath(".//w:t/text()", namespaces=NS)
            ).startswith(label)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                f"expected one paragraph starting with {label}, found {len(matches)}"
            )
        return matches[0]

    paragraph = find_one(spec["label"])
    anchor = find_one(spec["after_label"])
    if paragraph.getparent() is not anchor.getparent():
        raise RuntimeError("paragraph and target anchor do not share a parent")
    anchor.addnext(paragraph)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def main() -> None:
    args = parse_args()
    if args.source.resolve() == args.output.resolve():
        raise SystemExit("source and output must differ; keep the previous version")
    if not args.source.exists():
        raise SystemExit(f"source not found: {args.source}")

    replacements: dict[str, str] = {}
    if args.replace_json:
        replacements = json.loads(args.replace_json.read_text(encoding="utf-8"))
        if not isinstance(replacements, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in replacements.items()
        ):
            raise SystemExit("replacement JSON must be an object of string-to-string pairs")

    core_ability: dict[str, str] | None = None
    if args.insert_core_ability_json:
        core_ability = json.loads(
            args.insert_core_ability_json.read_text(encoding="utf-8")
        )
        if not isinstance(core_ability, dict):
            raise SystemExit("core ability JSON must be an object")

    paragraph_move: dict[str, str] | None = None
    if args.move_paragraph_after_json:
        paragraph_move = json.loads(
            args.move_paragraph_after_json.read_text(encoding="utf-8")
        )
        if not isinstance(paragraph_move, dict):
            raise SystemExit("paragraph move JSON must be an object")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    hits = {old: 0 for old in replacements}
    version_hits = 0
    with zipfile.ZipFile(args.source, "r") as source_zip, zipfile.ZipFile(
        args.output, "w"
    ) as output_zip:
        for item in source_zip.infolist():
            data = source_zip.read(item.filename)
            if item.filename == "word/document.xml":
                if args.remove_top_header_accents:
                    data = remove_top_header_accents(data)
                if args.collapse_continuation_title:
                    data = collapse_manual_continuation(
                        data, args.collapse_continuation_title
                    )
                if args.force_full_width_title:
                    data = force_full_width_title_tables(
                        data, args.force_full_width_title
                    )
                if args.tabbed_title:
                    data = convert_title_tables_to_tabbed_paragraphs(
                        data, args.tabbed_title
                    )
                if core_ability:
                    data = insert_core_ability(data, core_ability)
                if paragraph_move:
                    data = move_paragraph_after(data, paragraph_move)
            if item.filename.endswith(".xml") or item.filename.endswith(".rels"):
                text = data.decode("utf-8")
                version_hits += text.count(args.from_version)
                text = text.replace(args.from_version, args.to_version)
                for old, new in replacements.items():
                    count = text.count(old)
                    hits[old] += count
                    text = text.replace(old, new)
                data = text.encode("utf-8")
            output_zip.writestr(item, data)

    if version_hits == 0:
        args.output.unlink(missing_ok=True)
        raise SystemExit(f"version token not found: {args.from_version}")
    missing = [old for old, count in hits.items() if count == 0]
    if missing:
        args.output.unlink(missing_ok=True)
        raise SystemExit(f"replacement text not found: {missing}")
    print(f"created {args.output} ({version_hits} version replacements)")


if __name__ == "__main__":
    main()
