"""Render a canonical Markdown file with the persistent, collapsible reading sidebar.
Standard library only. Serves only explicitly selected Markdown documents on loopback.
"""
import html
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from . import _reading_layout as reading_layout


def render(source, content=None, destinations=None, source_href=None):
    source = Path(source).resolve()
    source_href = source_href or source.as_uri()
    def inline_markup(text):
        def link(match):
            label, url = match.groups()
            if re.search(r'\.md:\d+$', url) and not urlsplit(url).scheme:
                url = re.sub(r':(\d+)$', r'#L\1', url)
            parsed = urlsplit(url.strip('<>'))
            scheme = parsed.scheme.lower()
            href = None
            if scheme in ('http', 'https', 'mailto'):
                href = url
            elif not scheme and not parsed.netloc:
                if not parsed.path:
                    href = '#' + parsed.fragment
                else:
                    target = (source.parent / unquote(parsed.path)).resolve()
                    if destinations is None:
                        href = target.as_uri()
                    else:
                        href = destinations.get(target)
                    if href and parsed.fragment:
                        href += '#' + parsed.fragment
            if href:
                return '<a href="' + html.escape(href, quote=True) + '">' + html.escape(label) + '</a>'
            return '<span title="请从 Markdown 原文查看未登记的链接">' + html.escape(label) + '</span>'
        parts, last = [], 0
        for match in re.finditer(r'\[([^\]]+)\]\(([^)]+)\)', text):
            parts.extend((html.escape(text[last:match.start()]), link(match)))
            last = match.end()
        parts.append(html.escape(text[last:]))
        return re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', ''.join(parts))
    def inline(text):
        return ''.join('<code>' + html.escape(part[1:-1]) + '</code>' if part.startswith('`') and part.endswith('`') and len(part)>1 else inline_markup(part)
                       for part in re.split(r'(`[^`]+`)', text))
    blocks, in_list, table_lines, code_lines, toc = [], False, [], None, []
    heading_ids = set()
    pending_anchor = None
    def flush_table():
        if not table_lines:
            return
        cells = [[cell.strip() for cell in line.strip().strip('|').split('|')] for _, line in table_lines]
        if len(cells) >= 2 and all(re.fullmatch(r':?-{3,}:?', cell) for cell in cells[1]):
            blocks.append('<div class="table-wrap"><table><thead><tr id="L' + str(table_lines[0][0]) + '">' + ''.join('<th scope="col">' + inline(cell) + '</th>' for cell in cells[0]) + '</tr></thead><tbody>')
            for (number, _), row in zip(table_lines[2:], cells[2:]):
                question = re.match(r'([AB]\d+|R\d+)\s*[·｜]', row[0])
                marker = '<span id="' + question[1] + '"></span>' if question else ''
                blocks.append('<tr id="L' + str(number) + '">' + ''.join('<td>' + (marker if index == 0 else '') + inline(cell) + '</td>' for index, cell in enumerate(row)) + '</tr>')
            blocks.append('</tbody></table></div>')
        else:
            blocks.extend('<p id="L' + str(number) + '">' + inline(line) + '</p>' for number, line in table_lines)
        table_lines.clear()
    for number, line in enumerate((content if content is not None else source.read_text()).splitlines(), 1):
        if line.startswith('```'):
            pending_anchor = None
            if code_lines is not None:
                blocks.append('<pre><code>' + html.escape('\n'.join(code_lines)) + '</code></pre>')
                code_lines = None
            else:
                if in_list:
                    blocks.append('</' + in_list + '>'); in_list = False
                flush_table()
                code_lines = []
            continue
        if code_lines is not None:
            code_lines.append(line)
            continue
        ordered = re.match(r'^\d+[.)] (.+)$', line)
        is_item = line.startswith('- ') or bool(ordered)
        list_kind = 'ol' if ordered else 'ul'
        if in_list and (not is_item or in_list != list_kind):
            blocks.append('</' + in_list + '>'); in_list = False
        if line.startswith('|'):
            table_lines.append((number, line))
            continue
        flush_table()
        if not line.strip():
            continue
        explicit = re.fullmatch(r'<a id="([\w-]+)"></a>', line.strip())
        if explicit:
            identity = explicit[1]
            pending_anchor = identity
            if identity not in heading_ids:
                blocks.append('<span id="' + html.escape(identity, quote=True) + '" class="line-anchor"></span>')
                heading_ids.add(identity)
            continue
        heading = re.match(r'^(#{1,6}) (.+)$', line)
        if heading:
            level, title = len(heading[1]), heading[2]
            anchor = re.match(r'([A-Z]\d+)｜', title)
            numbered = re.match(r'(\d+)\.', title)
            identity = anchor[1] if anchor else 'section-' + numbered[1] if numbered else 'focus' if title == '先看重点' else 'heading-' + str(number)
            if identity in heading_ids:
                identity += '-' + str(number)
            heading_ids.add(identity)
            slug = re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '-')
            if slug and slug not in heading_ids:
                blocks.append('<span id="' + html.escape(slug, quote=True) + '" class="line-anchor"></span>')
                heading_ids.add(slug)
            if level in (2, 3, 4):
                toc.append({'level': level, 'id': pending_anchor or identity, 'title': title})
            blocks.append(f'<span id="L{number}" class="line-anchor"></span><h{level} id="{identity}">' + inline(title) + f'</h{level}>')
        elif is_item:
            if not in_list:
                blocks.append('<' + list_kind + '>'); in_list = list_kind
            blocks.append('<li id="L' + str(number) + '">' + inline(ordered[1] if ordered else line[2:]) + '</li>')
        elif line.startswith('>'):
            blocks.append('<p class="quote" id="L' + str(number) + '">' + inline(line.removeprefix('>').removeprefix(' ')) + '</p>')
        else:
            blocks.append('<p id="L' + str(number) + '">' + inline(line) + '</p>')
        pending_anchor = None
    if in_list:
        blocks.append('</' + in_list + '>')
    if code_lines is not None:
        blocks.append('<pre><code>' + html.escape('\n'.join(code_lines)) + '</code></pre>')
    flush_table()
    navigation = '<a href="' + html.escape(source_href, quote=True) + '">查看 Markdown 原文</a>'
    return reading_layout.render(source.stem, navigation, ''.join(blocks), toc)
