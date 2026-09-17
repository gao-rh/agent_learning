#!/usr/bin/env python3
"""Build the offline reading view from AI数据面试准备.md. Python stdlib only."""
from __future__ import annotations

import argparse
import hashlib
import html
import math
import re
from os.path import relpath
from pathlib import Path
from urllib.parse import urlsplit

SOURCE = Path(__file__).resolve().parent.parent / 'AI数据面试准备.md'
OUTPUT = SOURCE.with_suffix('.html')
BYTE_SOURCE = SOURCE.parent.parent / '招聘投递记录' / '资料' / '2026-09-09-字节生活服务面经与题目.md'


def timing_text(answer: str) -> str:
    count = len(re.findall(r'[\u4e00-\u9fff]', answer))
    def duration(rate):
        seconds = math.ceil(count / rate * 60 / 5) * 5
        return f'{seconds // 60}分{seconds % 60:02d}秒'
    return f'{count} 个汉字 · 估计 {duration(260)}–{duration(220)}（按每分钟 220–260 字），另加停顿及英文朗读时间'


def question_matches(text: str) -> dict:
    pattern = r'^### (?P<qid>[A-Z]\d{2})｜(?P<title>[^\n]+)(?P<body>[\s\S]*?)(?=^### [A-Z]\d{2}｜|^## |\Z)'
    return {m['qid']: m for m in re.finditer(pattern, text, re.M)}


def preparation_groups(text: str, questions: dict) -> list[dict]:
    section = re.search(r'^## 核心准备单元\n([\s\S]*?)(?=^## |\Z)', text, re.M)
    if not section:
        return []
    groups, seen = [], set()
    for line in section[1].splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(cells) != 5 or not re.fullmatch(r'[A-Z]\d{2}', cells[0]):
            continue
        core, module, title, member_text, delta = cells
        members = member_text.split('、')
        if core not in members or len(module) != 1 or not title or not delta:
            raise ValueError(f'Invalid preparation group: {core}')
        for qid in members:
            if qid not in questions or qid in seen:
                raise ValueError(f'Unknown or duplicate group member: {qid}')
            seen.add(qid)
        groups.append(dict(core=core, module=module, title=title, members=members, delta=delta))
    if seen != set(questions):
        raise ValueError(f'Ungrouped questions: {sorted(set(questions)-seen)}')
    return groups


def answer_text(body: str) -> str:
    parts = re.split(r'(?m)^##### ([^\n]+)$', body)
    sections = dict(zip(parts[1::2], parts[2::2]))
    value = sections['润色口述'].strip('\n')
    if '口述格式：原文逐行' in parts[0]:
        lines = value.split('\n')
        if any(not line.startswith('> ') for line in lines):
            raise ValueError('Invalid literal answer encoding')
        return '\n'.join(line[2:] for line in lines)
    return value.strip()


def latest_answer(question_body: str) -> str:
    versions = re.split(r'(?m)^#### ([^\n]+)$', question_body)
    values = [answer_text(b) for h,b in zip(versions[1::2], versions[2::2]) if h.startswith('口述记录｜')]
    return values[-1] if values else ''


def oral_record(title: str, body: str) -> str:
    """An answer is explicit source content, never inferred from a discussed tag."""
    pieces = re.split(r'(?m)^##### ([^\n]+)$', body)
    meta = pieces[0]
    parts = dict(zip(pieces[1::2], pieces[2::2]))
    if set(parts) - {'润色口述', '原始依据', '保留原意的说明'}:
        raise ValueError(f'Unknown oral section: {title}')
    if not parts.get('润色口述', '').strip() or not parts.get('原始依据', '').strip():
        raise ValueError(f'Oral record requires answer and evidence: {title}')
    kind = re.search(r'^口述性质：(.+)$', meta, re.M)
    coverage = re.search(r'^口述覆盖：(.+)$', meta, re.M)
    if not kind or not coverage:
        raise ValueError(f'Oral record requires scope: {title}')
    pending = ''
    if parts.get('保留原意的说明', '').strip():
        pending = '<div class="meaning-note"><strong>保留原意的说明</strong>'+markdown(parts['保留原意的说明'])+'</div>'
    rendered = ('<div class="literal-answer">'+html.escape(answer_text(body))+'</div>') if '口述格式：原文逐行' in meta else markdown(parts['润色口述'])
    return ('<article class="oral-record"><div class="oral-meta"><span>'+inline(title)+' · '+inline(kind[1])+'</span></div>'
            '<p class="answer-timing">'+timing_text(answer_text(body))+'</p><div class="oral-answer">'+rendered+'</div>'+
            '<details class="subdetails original"><summary>查看原话与来源</summary><div class="original-body prose">'+markdown(parts['原始依据'])+'</div></details></article>')


def inline(text: str) -> str:
    """Render the small Markdown subset used by this document, escaping raw HTML."""
    tokens: list[str] = []

    def token(value: str) -> str:
        tokens.append(value)
        return f'\x00{len(tokens)-1}\x00'

    def link(m: re.Match) -> str:
        label, href = m.group(1), m.group(2).strip('<>')
        if re.match(r'^(?:javascript|data|vbscript):', href, re.I):
            return token(html.escape(label))
        return token(f'<a href="{html.escape(href, quote=True)}">{html.escape(label)}</a>')

    text = re.sub(r'\[([^\]\n]+)\]\((<[^>]+>|[^)]+)\)', link, text)
    text = re.sub(r'`([^`]+)`', lambda m: token('<code>'+html.escape(m[1])+'</code>'), text)
    text = html.escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], text)


def markdown(text: str) -> str:
    lines = text.strip().splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.startswith('```'):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code.append(lines[i])
                i += 1
            out.append('<pre><code>'+html.escape('\n'.join(code))+'</code></pre>')
        elif line.startswith('|'):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells):
                    rows.append(cells)
                i += 1
            out.append('<div class="table-wrap"><table>')
            for n, row in enumerate(rows):
                tag = 'th' if n == 0 else 'td'
                out.append('<tr>'+''.join(f'<{tag}>{inline(c)}</{tag}>' for c in row)+'</tr>')
            out.append('</table></div>')
            continue
        elif re.match(r'^#{1,6} ', line):
            level = min(len(line.split(' ', 1)[0]), 4)
            out.append(f'<h{level}>{inline(line.split(" ",1)[1])}</h{level}>')
        elif re.match(r'^(?:- |\d+\. )', line):
            ordered = bool(re.match(r'^\d+\. ', line))
            tag = 'ol' if ordered else 'ul'
            pattern = r'^\d+\. ' if ordered else r'^- '
            out.append(f'<{tag}>')
            while i < len(lines) and re.match(pattern, lines[i].strip()):
                out.append('<li>'+inline(re.sub(pattern, '', lines[i].strip()))+'</li>')
                i += 1
            out.append(f'</{tag}>')
            continue
        elif line.startswith('> '):
            out.append('<blockquote>'+inline(line[2:])+'</blockquote>')
        else:
            out.append('<p>'+inline(line)+'</p>')
        i += 1
    return '\n'.join(out)


STYLE = r'''
:root{color-scheme:light;--ink:#24332e;--muted:#68756f;--line:#e3e8e2;--paper:#fff;--bg:#f6f7f3;--accent:#326954;--wash:#eaf2eb}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:15px;line-height:1.7}button,input,select{font:inherit}button,a,input,select,summary{-webkit-tap-highlight-color:transparent}button{cursor:pointer}button:focus-visible,a:focus-visible,input:focus-visible,summary:focus-visible,select:focus-visible{outline:3px solid #7aab91;outline-offset:3px}a{color:var(--accent);text-underline-offset:4px}button{color:inherit}button:disabled{opacity:.45;cursor:default}[hidden]{display:none!important}
.layout{max-width:1600px;margin:auto;display:grid;grid-template-columns:258px minmax(0,1fr)}.sidebar{height:100vh;position:sticky;top:0;border-right:1px solid var(--line);background:#fbfcf9;padding:32px 20px;display:flex;flex-direction:column;overflow:auto}.brand{display:flex;gap:12px;align-items:center;margin:0 10px 30px}.brand-mark{width:35px;height:35px;background:var(--accent);color:white;display:grid;place-items:center;border-radius:9px;font:600 16px ui-monospace,monospace}.brand strong{font-size:15px;display:block}.brand small{font-size:11px;color:var(--muted);letter-spacing:1px}.nav-label{font-size:11px;color:var(--muted);letter-spacing:1.4px;margin:12px 12px 8px}.nav-btn{border:0;background:none;width:100%;text-align:left;display:flex;align-items:center;gap:10px;padding:11px 12px;border-radius:7px;margin:2px 0;font-size:13px;line-height:1.5}.nav-btn:hover{background:#f0f3ed}.nav-btn.active{background:var(--wash);color:#245641;font-weight:600}.nav-code{font-family:ui-monospace,monospace;width:19px;font-size:11px;color:var(--muted)}.nav-name{flex:1}.nav-count{font-size:11px;color:var(--muted);font-variant-numeric:tabular-nums}.sidebar-foot{margin-top:auto;padding:26px 12px 0;font-size:11px;color:var(--muted)}.sidebar-foot a{display:block;margin-bottom:8px;font-size:12px}.main{min-width:0;padding:42px 5.2% 72px;max-width:1190px}.eyebrow{font-size:11px;letter-spacing:2px;color:var(--accent);font-weight:600}.hero h1{font-size:34px;font-weight:650;letter-spacing:-1px;line-height:1.3;margin:10px 0}.subtitle{color:var(--muted);font-size:14px;margin:12px 0 19px;max-width:750px}.meta{display:flex;gap:10px;flex-wrap:wrap;font-size:11px;color:var(--muted);align-items:center}.meta span{padding-right:12px;border-right:1px solid #d5ddd4}.meta span:last-child{border:0}.toolbar{position:sticky;top:0;z-index:5;background:var(--bg);padding:24px 0 16px;margin-top:12px}.search{display:flex;align-items:center;background:white;border:1px solid #dbe2d9;border-radius:9px;padding:0 14px;gap:12px;height:45px}.search svg{flex:0 0 17px;color:var(--muted)}.search input{width:100%;border:0;outline:none;background:transparent;font-size:14px;color:var(--ink);min-width:0}.search input:focus-visible{outline:none}.search:focus-within{border-color:var(--accent);box-shadow:0 0 0 2px #32695412}.search-clear{border:0;background:none;font-size:20px;color:var(--muted);padding:1px 6px}.toolbar-row{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:12px;flex-wrap:wrap}.filter-group{display:flex;align-items:center;gap:7px}.chip{border:1px solid var(--line);background:transparent;padding:5px 11px;border-radius:6px;font-size:12px;white-space:nowrap}.chip.active{background:var(--accent);border-color:var(--accent);color:white}.small-actions{display:flex;gap:12px}.text-btn{border:0;background:transparent;padding:5px 0;font-size:12px;color:var(--muted)}.text-btn:hover{color:var(--accent)}.result-note{font-size:11px;color:var(--muted);margin:12px 0 0}.mobile-select{display:none}.module{margin:14px 0 34px}.section-heading{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:15px}.section-heading h2{font-size:22px;line-height:1.45;margin:0;font-weight:620;letter-spacing:-.35px}.section-kicker{font-size:10px;letter-spacing:1.5px;color:var(--accent);margin-bottom:7px}.section-count{font-size:11px;white-space:nowrap;color:var(--muted);padding-top:6px}.module-purpose{font-size:13px;color:var(--muted);max-width:750px;line-height:1.85;margin:0 0 18px}.module-purpose p{margin:0}.question-list{border:1px solid var(--line);border-radius:10px;overflow:hidden;background:var(--paper)}.question{border-top:1px solid var(--line);scroll-margin-top:166px}.question:first-child{border:0}.question summary{list-style:none;display:grid;grid-template-columns:36px minmax(0,1fr) 14px;gap:12px;align-items:start;padding:20px 22px;cursor:pointer}.question summary::-webkit-details-marker{display:none}.question summary:hover{background:#f9fbf7}.qid{font:500 11px/26px ui-monospace,SFMono-Regular,monospace;color:#789182}.qtitle{font-size:15px;line-height:1.8;font-weight:550}.qtags{display:flex;gap:6px;margin-top:6px;flex-wrap:wrap}.tag{font-size:10px;line-height:1.5;padding:2px 6px;border-radius:4px;font-weight:400;color:#6c7c70;background:#f0f4ee}.status{color:#756b55;background:#f6f2e8}.chevron{border-right:1.5px solid #819186;border-bottom:1.5px solid #819186;width:7px;height:7px;transform:rotate(45deg);margin-top:9px;transition:transform .15s}.question[open]{background:#fcfdfb}.question[open] .chevron{transform:rotate(225deg);margin-top:13px}.question[open] .qtitle{color:#285c47}.qbody{padding:0 40px 24px 70px;max-width:860px;font-size:14px;line-height:1.9;color:#55615a}.body-label{font-size:10px;letter-spacing:1px;color:#819085;margin:0 0 10px}.qbody ul{margin:0;padding-left:18px}.qbody li{padding-left:3px;margin:8px 0}.qbody strong{color:var(--ink)}.module-materials{margin-top:17px;color:var(--muted);font-size:12px}.module-materials summary{cursor:pointer;padding:8px 0;list-style:none}.module-materials summary:before{content:'＋';margin-right:7px;color:var(--accent)}.module-materials[open] summary:before{content:'－'}.module-materials .prose{padding:4px 0 2px;line-height:1.95}.module-materials p{margin:9px 0}.empty{padding:52px 20px;border:1px dashed #d9e1d5;border-radius:10px;text-align:center;background:#fcfdf9}.empty h3{margin:0 0 8px;font-size:18px}.empty p{color:var(--muted);font-size:13px}.prose{font-size:14px;line-height:1.95;overflow-wrap:anywhere}.prose h2{font-size:23px;margin:28px 0 18px}.prose h3{font-size:17px;margin:27px 0 14px}.prose h4{font-size:15px}.prose p{margin:12px 0}.prose li{margin:9px 0}.prose ul,.prose ol{padding-left:22px}.prose blockquote{margin:18px 0;padding:12px 17px;border-left:3px solid #a3bea8;background:#edf3eb;color:#58725e}.table-wrap{max-width:100%;overflow:auto;margin:18px 0;border:1px solid var(--line);border-radius:8px;background:white}table{width:100%;border-collapse:collapse;text-align:left;font-size:12px;line-height:1.8}th{background:#f0f4ed;color:#4b6953;font-weight:550}td,th{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}tr:last-child td{border:0}td:first-child{min-width:100px}code{font-family:ui-monospace,SFMono-Regular,monospace;font-size:.9em;background:#edf1e9;padding:2px 4px;border-radius:3px}pre{overflow:auto;max-width:100%;background:#edf1e9;padding:15px;border-radius:8px;line-height:1.7}pre code{padding:0}.doc-panel{background:white;border:1px solid var(--line);padding:22px 30px 30px;border-radius:10px;margin-top:18px}.footer{border-top:1px solid var(--line);padding-top:18px;margin-top:40px;color:var(--muted);font-size:11px}.footer a{margin-right:12px}.skip{position:absolute;top:-50px;left:10px;background:white;padding:8px;z-index:10}.skip:focus{top:10px}
@media(min-width:1500px){.main{padding-left:65px;padding-right:65px}.hero h1{font-size:37px}}
@media(max-width:1050px){.layout{grid-template-columns:220px minmax(0,1fr)}.sidebar{padding:25px 13px}.main{padding:32px 28px 60px}.question summary{padding:18px;gap:8px}.qbody{padding-left:61px;padding-right:25px}.qtitle{font-size:14px}.section-heading h2{font-size:20px}}
@media(max-width:720px){.layout{display:block}.sidebar{display:none}.main{padding:28px 17px 45px;max-width:none}.hero h1{font-size:28px}.subtitle{font-size:12px;line-height:1.85;margin:12px 0 14px}.eyebrow{font-size:10px}.meta{font-size:10px;gap:8px}.meta span{padding-right:8px}.toolbar{padding-top:16px;margin-top:8px}.mobile-select{display:block;width:100%;height:40px;margin-bottom:10px;background:white;border:1px solid var(--line);border-radius:7px;padding:0 10px;color:var(--ink);font-size:13px}.search{height:42px;padding:0 11px}.search input{font-size:13px}.toolbar-row{gap:8px}.small-actions{gap:10px}.chip{font-size:11px;padding:5px 9px}.text-btn{font-size:11px}.result-note{font-size:10px}.section-heading{gap:10px;margin-bottom:12px}.section-heading h2{font-size:19px}.section-count{font-size:10px}.section-kicker{font-size:9px}.module-purpose{font-size:12px}.question summary{grid-template-columns:29px minmax(0,1fr) 9px;gap:8px;padding:16px 12px}.qid{font-size:10px;line-height:24px}.qtitle{font-size:14px;line-height:1.75}.qbody{padding:0 20px 20px 49px;font-size:13px;line-height:1.85}.body-label{font-size:9px}.tag{font-size:9px}.doc-panel{padding:16px 15px}.prose{font-size:13px}.prose h2{font-size:20px}.prose h3{font-size:16px}.table-wrap table{min-width:590px}.footer{font-size:10px}.question{scroll-margin-top:210px}}
@media print{.sidebar,.toolbar,.footer,.mobile-select,.module-materials summary{display:none!important}.layout{display:block}.main{padding:0;max-width:none}.hero{margin-bottom:25px}.module[hidden],.question[hidden]{display:block!important}.qbody{display:block!important}.question-list{border:0}.question{break-inside:avoid}.qtitle{font-size:12pt}body{background:white}.module{break-before:auto}.qbody{font-size:10pt}.module-materials{display:none}}
'''

STYLE += r'''
.source-jumps{display:flex;flex-wrap:wrap;gap:8px;margin:20px 0}.source-jumps a{border:1px solid var(--line);border-radius:6px;padding:5px 12px;text-decoration:none;font-size:12px}.interview-source{border:1px solid var(--line);border-radius:8px;margin:16px 0;scroll-margin-top:140px;overflow:hidden}.interview-source>summary{padding:16px 18px;background:var(--bg);font-size:15px;font-weight:600;cursor:pointer;line-height:1.7}.interview-source>div{padding:0 18px 18px}.interview-source .table-wrap table{min-width:0;width:100%}.interview-source td:first-child,.interview-source th:first-child{width:52px;min-width:0;white-space:nowrap}.interview-source td{line-height:1.8}.interview-source td:last-child,.interview-source th:last-child{width:72px;font-size:12px}.interview-source td:last-child a{display:inline-block;margin-right:5px}.interview-source p{overflow-wrap:anywhere}
.byte-evidence{margin:14px 0;color:var(--muted)}.byte-evidence>summary{cursor:pointer;font-size:12px}.byte-evidence .table-wrap{color:var(--ink)}
@media(max-width:720px){.interview-source td:first-child,.interview-source th:first-child{width:40px}.interview-source td:last-child,.interview-source th:last-child{width:36px;font-size:11px}.interview-source>summary{font-size:14px;padding:13px 12px}.interview-source>div{padding:0 10px 12px}.interview-source td{padding:10px 8px}.interview-source{scroll-margin-top:150px}}
'''

# Nested disclosure controls must not inherit the question's three-column summary.
STYLE += r'''
.qbody{max-width:940px}.oral-heading{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0 0 8px}.oral-heading h3{font-size:15px;color:var(--ink);margin:0}.oral-heading span{font-size:10px;color:var(--muted)}.oral-meta{font-size:10px;color:#748079;line-height:1.7}.oral-scope{font-size:12px;padding:10px 13px;background:#f0f4ee;border-radius:6px;color:#637265;line-height:1.8;margin:12px 0 18px}.oral-answer{color:#34463b;line-height:1.95;font-size:15px}.oral-answer p{margin:0 0 15px}.oral-answer p:last-child{margin-bottom:19px}.question .subdetails{border-top:1px solid var(--line);margin-top:5px}.question .subdetails>summary{display:block;list-style:none;padding:12px 0;font-size:12px;font-weight:500;color:#526b5a;line-height:1.6;cursor:pointer}.question .subdetails>summary:hover{background:transparent;color:var(--accent)}.question .subdetails>summary:after{content:'＋';float:right;margin-left:12px;font-size:13px;color:#839183}.question .subdetails[open]>summary:after{content:'－'}.original-body{font-size:12px;max-height:480px;overflow:auto;overscroll-behavior:contain;padding:0 7px 10px 0}.original-body blockquote{margin:10px 0;line-height:1.9;padding:11px 14px;background:#f0f3ee;color:#657367}.meaning-note{font-size:12px;color:#7a6845;background:#faf5e9;padding:11px 14px;border-radius:6px;margin:16px 0;line-height:1.85}.meaning-note strong{color:#7a6845;font-size:11px}.meaning-note p{margin:5px 0 0}.no-oral{font-size:13px;color:var(--muted);padding:4px 0 13px}.preparation-notes{padding-bottom:12px}.supplement-body{padding:0 0 14px;font-size:12px}.supplement-body p{margin:2px 0 12px}.supplement-body label{display:block;font-size:11px;color:var(--muted);margin-bottom:6px}.oral-prompt{display:block;width:100%;resize:vertical;border:1px solid #d5dfd4;background:white;border-radius:7px;padding:12px;color:#4a5e4f;font:12px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}.oral-prompt:focus-visible{outline:2px solid #7aab91;outline-offset:2px}.copy-row{display:flex;align-items:center;gap:12px;margin-top:10px;flex-wrap:wrap}.copy-status{font-size:11px;color:var(--accent)}.supplement-rule{font-size:11px;color:var(--muted);margin-top:13px!important}.question .supplement>summary{color:var(--accent)}.history .oral-record{padding-top:8px}.history{margin-bottom:7px}.tag.oral-tag{background:#e9f2e8;color:#42674b}
@media(max-width:720px){.qbody{padding-left:18px;padding-right:18px}.oral-answer{font-size:14px;line-height:1.9}.oral-heading h3{font-size:14px}.oral-heading span{font-size:9px}.oral-scope{font-size:11px}.oral-meta{font-size:10px}.meaning-note{font-size:11px}.original-body{font-size:12px}.question .subdetails>summary{font-size:12px}.oral-prompt{font-size:13px}}
@media print{.supplement,.original,.history{display:none!important}.oral-answer{font-size:10pt}.preparation-notes{display:block!important}}
'''

STYLE += r'''
.prep-unit{border-top:1px solid var(--line);scroll-margin-top:165px}.prep-unit:first-child{border-top:0}.prep-unit>summary{display:grid;grid-template-columns:36px minmax(0,1fr) 10px;gap:12px;padding:20px 22px;list-style:none;cursor:pointer}.prep-unit>summary::-webkit-details-marker{display:none}.prep-unit>summary:hover{background:#f7faf4}.unit-code{font:500 11px/26px ui-monospace,monospace;color:#789182}.unit-title{font-size:15px;font-weight:600;color:#285c47}.unit-meta{display:block;margin-top:5px;font-size:11px;color:var(--muted)}.unit-chevron{border-right:1.5px solid #819186;border-bottom:1.5px solid #819186;width:7px;height:7px;transform:rotate(45deg);margin-top:9px}.prep-unit[open]>summary .unit-chevron{transform:rotate(225deg)}.unit-body{padding:0 20px 20px}.reuse-note{background:#edf3e9;padding:12px 16px;border-radius:7px;font-size:12px;line-height:1.85;margin-bottom:14px}.reuse-note strong{color:#48684f}.reuse-note p{margin:5px 0}.unit-links{font-size:11px;overflow-wrap:anywhere}.unit-body>.question{border:1px solid var(--line);border-radius:8px;background:#fff}.unit-body .qbody{max-width:none;padding-left:24px;padding-right:24px}.unit-body .question>summary{padding:16px}.followups{margin-top:16px;border-top:1px solid var(--line)}.followups>summary{padding:13px 4px;cursor:pointer;font-size:12px;color:#526b5a}.unit-hint{font-size:12px;color:var(--muted);margin:0 4px 12px}.followups .question{border:1px solid var(--line);border-radius:7px;margin:8px 0;background:#fff}
@media(max-width:720px){.prep-unit>summary{grid-template-columns:29px minmax(0,1fr) 9px;padding:16px 12px;gap:8px}.unit-title{font-size:14px}.unit-body{padding:0 10px 14px}.unit-body .qbody{padding:0 14px 18px}.unit-body .question>summary{padding:13px 10px}.reuse-note{padding:10px 12px}.prep-unit{scroll-margin-top:220px}}
.reading-workflow{font-size:12px;color:#617165;margin-top:16px}.answer-timing{font-size:12px;color:#617165}.unit-links{margin:0 0 12px}.quick-questions{display:flex;gap:9px;flex-wrap:wrap;margin:14px 0 8px}.quick-questions a{font-size:12px;padding:5px 11px;border:1px solid #d6e2d6;border-radius:6px;background:white;text-decoration:none}.module-overview{margin-top:12px}.module-overview>summary{cursor:pointer;font-size:12px;color:var(--accent);padding:5px 0}.module-overview .table-wrap table{min-width:0}.module-overview td,.module-overview th{overflow-wrap:anywhere}
@media(max-width:720px){.answer-input{min-height:330px;padding:12px;font-size:14px}.editor-hint,.edit-status,.reader-notice{font-size:11px}}
'''

STYLE += r'''
.interview-source .table-wrap table{table-layout:fixed}
.interview-source .byte-answer-row>td{padding:0 12px 14px;width:auto;min-width:0;white-space:normal;font-size:13px}
.byte-answer{border:1px solid #dbe5da;border-radius:7px;background:#f8faf6;scroll-margin-top:145px}
.byte-answer>summary{cursor:pointer;padding:9px 13px;color:var(--accent);font-size:12px;font-weight:550;line-height:1.8}
.byte-answer[open]>summary{border-bottom:1px solid #e1e8df}
.byte-answer-content{padding:0 16px 15px;color:var(--ink);font-size:13px;line-height:1.9;overflow-wrap:anywhere}
.byte-answer-content pre{white-space:pre;overflow:auto;max-width:100%;font-size:12px}
.byte-answer-content p:last-child{margin-bottom:0}
@media(max-width:720px){.interview-source .byte-answer-row>td{padding:0 6px 10px}.byte-answer-content{padding:0 10px 12px}.byte-answer{scroll-margin-top:165px}}
'''


SCRIPT = r'''
(() => {
  const search = document.getElementById('search');
  const allCards = [...document.querySelectorAll('.question')];
  const searchText = new Map(allCards.map(card => [card, card.id+' '+[...card.querySelectorAll('.qtitle,.oral-answer,.original-body,.interview-extension')].map(n=>n.textContent).join(' ').toLocaleLowerCase()]));
  const units = [...document.querySelectorAll('.prep-unit')];
  const unitText = new Map(units.map(unit=>[unit,[...unit.querySelectorAll('.unit-title')].map(n=>n.textContent).join(' ')+' '+[...unit.querySelectorAll('.question')].map(card=>searchText.get(card)).join(' ')]));
  const modules = [...document.querySelectorAll('.module')];
  const navs = [...document.querySelectorAll('[data-nav]')];
  const chooser = document.getElementById('mobile-module');
  const questions = document.getElementById('questions');
  const panels = [...document.querySelectorAll('.doc-panel')];
  const seenButton = document.getElementById('seen-filter');
  let active = modules.some(m=>m.dataset.module==='H') ? 'H' : 'A', onlySeen = false;
  function apply() {
    const isDoc = panels.some(p => p.id === active);
    questions.hidden = isDoc;
    panels.forEach(p => p.hidden = p.id !== active);
    document.getElementById('question-controls').hidden = isDoc;
    const terms = search.value.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let count = 0, covered = 0;
    units.forEach(unit => {
      const match = (active === 'all' || unit.dataset.module === active) && (!onlySeen || unit.dataset.seen === 'true') && terms.every(t => unitText.get(unit).toLocaleLowerCase().includes(t));
      unit.hidden = !match;
      if (match) {
        count++;covered+=unit.querySelectorAll('.question').length;
        if(terms.length){unit.open=true;unit.querySelectorAll('.question').forEach(card=>{if(terms.every(t=>searchText.get(card).toLocaleLowerCase().includes(t))){card.open=true;if(card.closest('.followups'))card.closest('.followups').open=true;}});}
      }
    });
    modules.forEach(m => m.hidden = ![...m.querySelectorAll('.prep-unit')].some(q => !q.hidden));
    navs.forEach(n => { const selected = n.dataset.nav === active; n.classList.toggle('active',selected); n.setAttribute('aria-current', selected ? 'page' : 'false'); });
    chooser.value = active;
    document.getElementById('all-filter').classList.toggle('active',!onlySeen);
    seenButton.classList.toggle('active',onlySeen);
    document.getElementById('all-filter').setAttribute('aria-pressed',String(!onlySeen));
    seenButton.setAttribute('aria-pressed',String(onlySeen));
    document.getElementById('result-note').textContent = isDoc ? '' : `显示 ${count} 个准备单元 · 覆盖 ${covered} 种问法`;
    document.getElementById('empty').hidden = count > 0 || isDoc;
    document.getElementById('clear-search').hidden = search.value.length === 0;
    document.getElementById('expand').disabled = count === 0;
    document.getElementById('collapse').disabled = count === 0;
  }
  function navigate(value) { active=value; search.value=''; onlySeen=false; apply(); window.scrollTo({top:0,behavior:'instant'}); }
  navs.forEach(n => n.addEventListener('click',() => navigate(n.dataset.nav)));
  chooser.addEventListener('change',() => navigate(chooser.value));
  search.addEventListener('input',() => { active='all'; apply(); });
  document.getElementById('clear-search').addEventListener('click',() => { search.value=''; apply(); search.focus(); });
  document.getElementById('all-filter').addEventListener('click',() => { onlySeen=false; apply(); });
  seenButton.addEventListener('click',() => { onlySeen=true; apply(); });
  document.getElementById('expand').addEventListener('click',() => units.filter(c=>!c.hidden).forEach(c=>c.open=true));
  document.getElementById('collapse').addEventListener('click',() => units.filter(c=>!c.hidden).forEach(c=>c.open=false));
  document.getElementById('reset').addEventListener('click',() => navigate('all'));
  function locate() {
    const id=location.hash.slice(1);
    const source=document.getElementById(id);
    if(source?.classList.contains('byte-answer')){
      navigate('byte-interviews');source.closest('.interview-source').open=true;source.open=true;
      requestAnimationFrame(()=>source.scrollIntoView({block:'start',behavior:'instant'}));return;
    }
    if(source?.classList.contains('interview-source')){
      navigate('byte-interviews');source.open=true;requestAnimationFrame(()=>source.scrollIntoView({block:'start',behavior:'instant'}));return;
    }
    if (panels.some(p => p.id === id)) { navigate(id); return; }
    const target=id.match(/^([A-Z]\d{2})(?:-feedback)?$/);
    if (target) {
      const card=document.getElementById(target[1]);
      if(card){ if(id.endsWith('-feedback'))history.replaceState(null,'','#'+card.id);navigate(card.dataset.module);card.closest('.prep-unit').open=true;if(card.closest('.followups'))card.closest('.followups').open=true;card.open=true;requestAnimationFrame(()=>(document.getElementById(id)||card).scrollIntoView({behavior:'instant'}));return; }
    }
    apply();
  }
  window.addEventListener('hashchange',locate);
  locate();
})();
'''


def build(text: str, feedback_path=None) -> str:
    # The optional legacy argument is ignored: feedback is no longer loaded into the page.
    question_map = question_matches(text)
    groups = preparation_groups(text, question_map)
    card_data = {}
    sections = re.split(r'(?m)^(## .+)$', text)
    guide = sections[0]
    resources: list[str] = []
    modules: list[dict] = []
    answered = 0
    ids: set[str] = set()
    for heading, content in zip(sections[1::2], sections[2::2]):
        match = re.search(r'([A-Z])｜(.+?)：(\d+)\s*题', heading)
        if not match:
            if heading.startswith('## 一、'):
                guide += heading+content
            else:
                resources.append(heading+content)
            continue
        letter, title, expected = match.groups()
        pieces = re.split(r'(?m)^### ([A-Z]\d{2})｜(.+)$', content)
        intro = pieces[0]
        cards: list[str] = []
        material = ''
        for i in range(1, len(pieces), 3):
            qid, question, body = pieces[i:i+3]
            if qid in ids:
                raise ValueError(f'Duplicate question: {qid}')
            ids.add(qid)
            state = re.search(r'^准备状态：(.*)$', body, re.M)
            if not state or state[1].strip() not in {'待继续','待验证','已理解'}:
                raise ValueError(f'Invalid preparation status: {qid}')
            status = state[1].strip()
            body = re.sub(r'^准备状态：.*\n?', '', body, flags=re.M).strip()
            # Explicit level-4 sections separate oral versions from module resources.
            subsections = re.split(r'(?m)^#### ([^\n]+)$', body)
            oral_versions = []
            extension_html = ''
            for subheading, subbody in zip(subsections[1::2], subsections[2::2]):
                if subheading.startswith('口述记录｜'):
                    oral_versions.append((subheading.split('｜', 1)[1], oral_record(subheading.split('｜', 1)[1], subbody)))
                elif subheading == '本模块材料':
                    material += '\n\n'+subbody.strip()
                elif subheading == '项目追问与八股':
                    extension_html += '<details class="subdetails interview-extension" open><summary>项目追问与八股</summary><div class="prose">'+markdown(subbody.strip())+'</div></details>'
                else:
                    raise ValueError(f'Unknown question section: {qid} {subheading}')
            notes = []
            tail = []
            for line in subsections[0].splitlines():
                if line.startswith('- ') and not tail:
                    notes.append(line)
                elif line.strip():
                    tail.append(line)
            if not notes:
                raise ValueError(f'Missing preparation notes: {qid}')
            if tail:
                material += '\n\n'.join(tail)
            tags = []
            if oral_versions:
                answered += 1
                tags.append('<span class="tag oral-tag">已有口述</span>')
            if status != '待继续':
                tags.append('<span class="tag status">'+html.escape(status)+'</span>')
            tags_html = '<span class="qtags">'+''.join(tags)+'</span>' if tags else ''
            if oral_versions:
                current = oral_versions[-1][1]
                history = ''.join(f'<details class="subdetails history"><summary>历史口述 · {inline(t)}</summary>{v}</details>' for t,v in reversed(oral_versions[:-1]))
                answer_html = '<div class="oral-heading"><h3>我的口述</h3></div><div class="read-answer">'+current+history+'</div>'
            else:
                answer_html = '<div class="oral-heading"><h3>我的口述</h3></div><div class="read-answer"><p class="no-oral">这道题暂时没有口述。可以在当前对话中补充。</p></div>'
            card = f'<details class="question" id="{qid}" data-module="{letter}" data-seen="{str(bool(oral_versions)).lower()}" data-status="{status}"><summary><span class="qid">{qid}</span><span><span class="qtitle">{inline(question)}</span>{tags_html}</span><span class="chevron" aria-hidden="true"></span></summary><div class="qbody">{extension_html}{answer_html}</div></details>'
            cards.append(card)
            card_data[qid] = dict(html=card, module=letter, seen=bool(oral_versions))
        if len(cards) != int(expected):
            raise ValueError(f'Module {letter}: declared {expected} questions, found {len(cards)}')
        modules.append({'letter':letter,'title':title,'intro':intro,'cards':cards,'material':material})
    if not modules or len({m['letter'] for m in modules}) != len(modules):
        raise ValueError('Missing or duplicate question modules')
    if not groups:
        groups = [dict(core=qid, module=data['module'], title=question_map[qid]['title'], members=[qid], delta='先讲结论，再按追问展开。') for qid, data in card_data.items()]
    module_map = {m['letter']: m for m in modules}
    for m in modules:
        m['cards'] = []
    for group in groups:
        core, letter, members = group['core'], group['module'], group['members']
        if letter not in module_map:
            raise ValueError(f'Unknown group module: {letter}')
        def member_card(qid):
            card = card_data[qid]['html'].replace(f'data-module="{card_data[qid]["module"]}"', f'data-module="{letter}"')
            return card.replace('class="question"', 'class="question" open', 1) if qid == core else card
        related = [qid for qid in members if qid != core]
        followups = ('<details class="followups"><summary>其他问法与差异追问 · '+str(len(related))+' 项</summary>'+''.join(member_card(qid) for qid in related)+'</details>') if related else ''
        links = ' · '.join(f'<a href="#{qid}">{qid}</a>' for qid in members)
        seen_count = sum(card_data[qid]['seen'] for qid in members)
        unit = (f'<details class="prep-unit" id="unit-{core}" data-module="{letter}" data-seen="{str(seen_count > 0).lower()}"><summary>'
                f'<span class="unit-code">{core}</span><span><span class="unit-title">{inline(group["title"])}</span>'
                f'<span class="unit-meta">'+(f'主问题＋{len(related)} 项补充' if related else '独立准备')+(f' · {seen_count} 处已有口述' if seen_count else '')+'</span></span><span class="unit-chevron" aria-hidden="true"></span></summary>'
                f'<div class="unit-body"><div class="unit-links">{links}</div>'
                +member_card(core)+followups+'</div></details>')
        module_map[letter]['cards'].append(unit)
    # Keep stable question IDs when moving a question into a more useful module.
    # General interview preparation is the initial reading entry point.
    modules.sort(key=lambda m: (m['letter'] != 'H', m['letter']))
    nav = ['<button class="nav-btn" data-nav="all"><span class="nav-code">◎</span><span class="nav-name">全部准备单元</span><span class="nav-count">'+str(len(groups))+'</span></button>']
    nav.insert(0, '<a class="nav-btn" href="/prep?doc=xhs"><span class="nav-code">◎</span><span class="nav-name">小红书 · AI Native 准备</span></a>')
    nav.insert(0, '<a class="nav-btn" href="http://127.0.0.1:8768/reading/preparation"><span class="nav-code">↗</span><span class="nav-name">求职工作台 · 准备资料库</span></a>')
    options = [f'<option value="all">全部准备单元 · {len(groups)}份</option>']
    module_html = []
    for m in modules:
        letter,title,count=m['letter'],m['title'],len(m['cards'])
        nav.append(f'<button class="nav-btn" data-nav="{letter}"><span class="nav-code">{letter}</span><span class="nav-name">{html.escape(title)}</span><span class="nav-count">{count:02d}</span></button>')
        options.append(f'<option value="{letter}">{letter} · {html.escape(title)} · {count}份</option>')
        material = f'<details class="module-materials"><summary>本模块材料与补充说明</summary><div class="prose">{markdown(m["material"])}</div></details>' if m['material'] else ''
        intro_html = ''
        if '<div class="table-wrap">' in intro_html:
            lead, overview = intro_html.split('<div class="table-wrap">', 1)
            shortcuts = '<div class="quick-questions"><a href="#H01">自我介绍</a><a href="#H07">项目难点</a><a href="#F06">离职原因</a></div>' if letter == 'H' else ''
            intro_html = lead+shortcuts
        module_html.append(f'<section class="module" data-module="{letter}"><div class="section-heading"><div><div class="section-kicker">MODULE {letter}</div><h2>{html.escape(title)}</h2></div><span class="section-count">{count:02d} 份准备材料</span></div><div class="module-purpose">{intro_html}</div><div class="question-list">'+''.join(m['cards'])+'</div>'+material+'</section>')
    focus_match = re.search(r'^## 本次聚焦｜智能经营分析的项目追问\n([\s\S]*?)(?=^## |\Z)', text, re.M)
    focus_html = '<h2>智能经分：本次项目追问</h2>'+markdown(focus_match[1]) if focus_match else '<h2>智能经分：本次项目追问</h2><p>暂未整理。</p>'
    nav.insert(0, '<button class="nav-btn" data-nav="project-focus"><span class="nav-code">◎</span><span class="nav-name">智能经分 · 本次追问</span></button>')
    byte_text = BYTE_SOURCE.read_text(encoding='utf-8')
    def byte_link(match):
        target = match[1]
        if urlsplit(target).scheme or target.startswith('#'):
            return match[0]
        path, marker, fragment = target.partition('#')
        return ']('+relpath(BYTE_SOURCE.parent / path, SOURCE.parent)+marker+fragment+')'
    byte_render_text = re.sub(r'\]\(([^)]+)\)', byte_link, byte_text)
    byte_parts = re.split(r'(?m)^## (BD\d{2}｜[^\n]+)\n', byte_render_text)
    byte_intro = re.sub(r'^# [^\n]+', '## 字节数据岗 · 近期去重题单', byte_parts[0], count=1)
    byte_cards, byte_links = [], []
    for heading, body in zip(byte_parts[1::2], byte_parts[2::2]):
        code = heading.split('｜', 1)[0]
        remainder = ''
        if '\n## 未收录的线索与范围' in body:
            body, remainder = body.split('\n## 未收录的线索与范围', 1)
            remainder = markdown('## 未收录的线索与范围'+remainder)
        opened = ' open' if code in {'BD01', 'BD02', 'BD03'} else ''
        answer_pattern = r'^### (数\d{2})｜参考答案\n([\s\S]*?)(?=^### 数\d{2}｜参考答案|\Z)'
        answer_matches = list(re.finditer(answer_pattern, body, re.M))
        answers = {m[1]: m[2].strip() for m in answer_matches}
        if len(answers) != len(answer_matches):
            raise ValueError('Duplicate reference answer in '+code)
        question_body = re.sub(answer_pattern, '', body, flags=re.M)
        question_ids = set(re.findall(r'^\| (数\d{2}) \|', question_body, re.M))
        if not answers.keys() <= question_ids:
            raise ValueError('Reference answer without question in '+code)
        rendered_body = markdown(question_body)
        def add_answer(match):
            qid = match[1]
            question_row = match[0].replace('<tr>', '<tr data-byte-question="'+qid+'">', 1)
            if qid not in answers:
                return question_row
            answer_id = 'byte-answer-'+qid[1:]
            return question_row+'<tr class="byte-answer-row"><td colspan="3"><details class="byte-answer" id="'+answer_id+'"><summary>展开参考答案</summary><div class="byte-answer-content">'+markdown(answers[qid])+'</div></details></td></tr>'
        rendered_body = re.sub(r'<tr><td>(数\d{2})</td>[\s\S]*?</tr>', add_answer, rendered_body)
        byte_cards.append(f'<details class="interview-source" id="byte-{code}"{opened}><summary>{inline(heading)}</summary><div>{rendered_body}</div></details>'+remainder)
        short_title = heading.split('｜', 1)[1].split(' · ', 1)[0]
        byte_links.append(f'<a href="#byte-{code}">{inline(short_title)}</a>')
    byte_intro, _, byte_evidence = byte_intro.partition('\n## 来源与时间\n')
    byte_evidence_html = '<details class="byte-evidence"><summary>查看来源与日期依据</summary>'+markdown(byte_evidence)+'</details>' if byte_evidence else ''
    byte_html = markdown(byte_intro)+'<nav class="source-jumps" aria-label="跳到题目模块">'+''.join(byte_links)+'</nav>'+byte_evidence_html+''.join(byte_cards)
    byte_digest = hashlib.sha256(byte_text.encode()).hexdigest()
    nav.insert(0, '<button class="nav-btn" data-nav="byte-interviews"><span class="nav-code">◎</span><span class="nav-name">字节数据岗 · 去重题单</span><span class="nav-count">'+str(len(byte_cards))+'</span></button>')
    for value,label in [('byte-interviews','字节数据岗 · 去重题单'),('project-focus','智能经分 · 本次追问'),('guide','阅读说明'),('resources','资料入口')]:
        options.append(f'<option value="{value}">{label}</option>')
    reading_guide = '<h2>阅读说明</h2><p>按模块或题号查找问题，展开后查看当前口述。历史版本和原始来源可以继续展开。</p><p>补充、修正和建议在当前对话中讨论，确认后的内容更新到同一份本地文档。</p>'
    seen_links = set()
    links_html = []
    for label, target in re.findall(r'\[([^\]\n]+)\]\((<[^>]+>|[^)]+)\)', text):
        target = target.strip('<>')
        if target in seen_links or '.md' not in target.split('#')[0] or target.startswith('#'):
            continue
        seen_links.add(target)
        links_html.append('<li>'+inline('['+label+']('+target+')')+'</li>')
    resource_index = '<h2>资料入口</h2><ul>'+''.join(links_html)+'</ul>'
    date = re.search(r'更新：(\d{4}-\d{2}-\d{2})',text)[1]
    digest = hashlib.sha256(text.encode()).hexdigest()
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI数据面试准备 · 阅读版</title><meta name="source-sha256" content="{digest}"><meta name="byte-source-sha256" content="{byte_digest}"><meta name="edit-token" content=""><meta name="description" content="按题查看口述、历史版本和原始依据；新增内容在对话中整理。"><style>{STYLE}</style></head>
<body><a class="skip" href="#main">跳到正文</a><div class="layout"><aside class="sidebar"><div class="brand"><span class="brand-mark">AI</span><div><strong>数据面试准备</strong><small>INTERVIEW NOTES</small></div></div><div class="nav-label">问题模块</div><nav aria-label="问题模块">{''.join(nav)}</nav><div class="nav-label" style="margin-top:25px">参考与记录</div><button class="nav-btn" data-nav="guide"><span class="nav-name">阅读说明</span></button><button class="nav-btn" data-nav="resources"><span class="nav-name">资料入口</span></button><div class="sidebar-foot"><a href="AI数据面试准备.md">打开 Markdown 内容源 ↗</a>口述与来源保存在本地<br>阅读页由内容源自动生成</div></aside>
<main class="main" id="main"><header class="hero"><div class="eyebrow">AI × DATA · INTERVIEW PREP</div><h1>AI数据面试准备</h1><p class="subtitle">理解 Data Agent 的实际做法，讲清自己的项目。<br>聚焦语义层、数据建模与可靠的数据分析。</p><div class="meta"><span>AI 数据研发 · 阿里流通中心 / 字节生活服务</span><span>{len(modules)} 个模块 / {len(groups)} 个准备单元</span><span>覆盖 {len(ids)} 种问法</span><span>{answered} 题已有口述</span><span>更新 {date}</span></div><p class="reading-workflow">口述与确认在对话中完成，这里查看整理后的内容。</p></header>
<div class="toolbar"><label class="mobile-select-label"><select class="mobile-select" id="mobile-module" aria-label="切换模块">{''.join(options)}</select></label><div class="search"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" aria-hidden="true"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></svg><input id="search" type="search" autocomplete="off" placeholder="搜索题号或口述，例如：A07、语义、Flink" aria-label="搜索全部问题"><button class="search-clear" id="clear-search" aria-label="清空搜索" hidden>×</button></div><div id="question-controls" class="toolbar-row"><div class="filter-group"><button id="all-filter" class="chip active" aria-pressed="true">全部题目</button><button id="seen-filter" class="chip" aria-pressed="false">已有口述</button></div><div class="small-actions"><button id="expand" class="text-btn">展开单元</button><button id="collapse" class="text-btn">收起单元</button></div></div><p id="result-note" class="result-note" role="status" aria-live="polite"></p></div>
<div id="questions">{''.join(module_html)}<div id="empty" class="empty" hidden><h3>没有找到匹配的准备单元</h3><p>换一个关键词，或返回全部题目。</p><button class="chip" id="reset">重置筛选</button></div></div><section id="byte-interviews" class="doc-panel prose" hidden>{byte_html}</section><section id="project-focus" class="doc-panel prose" hidden>{focus_html}</section><section id="guide" class="doc-panel prose" hidden>{reading_guide}</section><section id="resources" class="doc-panel prose" hidden>{resource_index}</section><footer class="footer"><a href="AI数据面试准备.md">查看内容源</a><a href="README.md">面试准备资料入口</a><br>口述在对话中补充，历史版本与原始来源保留。</footer></main></div><script>{SCRIPT}</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Check that the reading page matches the current Markdown')
    args = parser.parse_args()
    text = SOURCE.read_text(encoding='utf-8')
    output = build(text).replace('href="/prep?doc=xhs"', 'href="http://127.0.0.1:8767/prep?doc=xhs"')
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding='utf-8') != output:
            raise SystemExit('Reading page is stale. Run this script without --check.')
        print('reading_page_matches_source=yes')
    else:
        OUTPUT.write_text(output, encoding='utf-8')
        print(f'Generated {OUTPUT} ({len(output.encode()):,} bytes)')


if __name__ == '__main__':
    main()
