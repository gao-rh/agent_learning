"""Selected interview Markdown sources, rendered by the existing local reader."""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
SOURCES = {
    'maas-study': ('阿里云 · Spark 与数仓深度学习', ROOT / '资料/2026-09-16-大模型训练数据岗位系统教学-从概念到面试.md'),
    'xhs': ('小红书 · 商业化 AI Native', ROOT / '岗位准备/小红书-商业化-AI-Native-Engineer.md'),
    'ai-coding': ('AI Coding 与异步任务', ROOT / '资料/AI-Coding与异步任务工程.md'),
    'agent-core': ('Agent 核心问答', ROOT / '资料/2026-09-13-大厂Agent面试重整/README.md'),
    'xhs-sources': ('小红书 · 面经来源', ROOT.parent / '招聘投递记录/资料/面经/小红书-AI-Native面经.md'),
}
EXCLUDED = {'5-归档', '面试记录', '本地资料'}
GERY_EVIDENCE = {
    Path('/Users/gaoronghui/Documents/gery_record/README.md'),
    Path('/Users/gaoronghui/Documents/gery_record/Docs/verification/agent-first-vertical-slice.md'),
}


def slug(title):
    return re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '-')


def sections(text):
    """Preserve explicit question anchors and keep fenced code intact."""
    result, current = [], {'id': 'intro', 'title': '阅读说明', 'body': []}
    pending, fence = None, None
    for line in text.splitlines():
        mark = re.match(r'^\s*(```+|~~~+)', line)
        if mark:
            token = mark[1][0]
            fence = None if fence == token else token
            current['body'].append(line)
            continue
        if not fence:
            anchor = re.fullmatch(r'<a id="([\w-]+)"></a>', line.strip())
            if anchor:
                pending = anchor[1]
                continue
            heading = re.match(r'^(#{1,6}) (.+)$', line)
            if heading and len(heading[1]) == 1:
                current['title'] = heading[2]
                continue
            if heading and (len(heading[1]) == 2 or pending):
                result.append(current)
                current = {'id': pending or slug(heading[2]), 'title': heading[2], 'body': []}
                pending = None
                continue
        current['body'].append(line)
    result.append(current)
    used = set()
    for item in result:
        base, count = item['id'], 1
        while item['id'] in used:
            item['id'] = f'{base}-{count}'
            count += 1
        used.add(item['id'])
        item['body'] = '\n'.join(item['body']).strip()
    return result


def local_targets(source, text):
    for href in re.findall(r'\[[^\]\n]+\]\((<[^>]+>|[^)]+)\)', text):
        href = href.strip('<>')
        if urlsplit(href).scheme or href.startswith('#'):
            continue
        path = (source.parent / unquote(href.split('#')[0])).resolve()
        if path.suffix != '.md' or EXCLUDED.intersection(path.parts):
            continue
        if path.is_relative_to(ROOT) or path.is_relative_to(ROOT.parent / '招聘投递记录') or path in GERY_EVIDENCE:
            yield path


def readable_paths():
    # Only registered sources and their direct, non-archived Markdown references.
    paths = {path.resolve() for _, path in SOURCES.values()}
    for _, source in SOURCES.values():
        paths.update(local_targets(source, source.read_text(encoding='utf-8')))
    return paths


def rewrite_links(text, source):
    registered = {path.resolve(): key for key, (_, path) in SOURCES.items()}

    def link(match):
        label, href = match[1], match[2].strip('<>')
        if urlsplit(href).scheme or href.startswith('#'):
            return match[0]
        path_part, _, fragment = href.partition('#')
        path = (source.parent / unquote(path_part)).resolve()
        if EXCLUDED.intersection(path.parts):
            return label + '（历史资料，按需在本地查阅）'
        if path in registered:
            url = '/prep?doc=' + registered[path]
        else:
            url = '/document?path=' + quote(str(path), safe='')
        if fragment:
            url += '#' + quote(fragment, safe='')
        return f'[{label}]({url})'

    return re.sub(r'\[([^\]\n]+)\]\((<[^>]+>|[^)]+)\)', link, text)


def build(markdown, document_id='xhs'):
    if document_id not in SOURCES:
        raise KeyError(document_id)
    title, source = SOURCES[document_id]
    source_text = source.read_text(encoding='utf-8')
    digest = hashlib.sha256(source_text.encode()).hexdigest()
    chunks = sections(source_text)
    cards, toc, search_index = [], [], []
    for key, (name, path) in SOURCES.items():
        text = source_text if key == document_id else path.read_text(encoding='utf-8')
        for item in sections(text):
            search_index.append({'doc': name, 'title': item['title'], 'text': item['body'],
                                 'url': '/prep?doc=' + key + '#' + quote(item['id'], safe='')})
    for i, item in enumerate(chunks):
        identity = html.escape(item['id'], quote=True)
        heading = html.escape(item['title'])
        toc.append(f'<a href="#{quote(item["id"], safe="")}">{heading}</a>')
        body = markdown(rewrite_links(item['body'], source))
        opened = ' open' if i < 2 else ''
        cards.append(f'<details class="card" id="{identity}"{opened}><summary>{heading}</summary><div class="prose">{body}</div></details>')
    nav = ''.join(f'<a href="/prep?doc={key}"'+(' aria-current="page"' if key == document_id else '')+'>'+html.escape(name)+'</a>' for key, (name, _) in SOURCES.items())
    data = json.dumps(search_index, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="source-sha256" content="{digest}"><title>{html.escape(title)} · 面试准备</title><style>
:root{{color-scheme:light;--ink:#24332e;--muted:#65716a;--line:#dce5de;--accent:#326954;--bg:#f5f7f3}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.85 -apple-system,BlinkMacSystemFont,"PingFang SC",sans-serif}}a{{color:var(--accent);text-underline-offset:4px}}a:focus-visible,input:focus-visible,summary:focus-visible{{outline:3px solid #90b99c;outline-offset:3px}}.layout{{max-width:1440px;margin:auto;display:grid;grid-template-columns:270px minmax(0,1fr)}}aside{{position:sticky;top:0;height:100vh;overflow:auto;border-right:1px solid var(--line);padding:25px 22px}}aside strong{{display:block;margin:16px 0 8px}}aside a{{display:block;font-size:13px;margin:8px 0;text-decoration:none}}aside a[aria-current]{{font-weight:700;background:#e7efe5;padding:8px;border-radius:6px}}main{{padding:34px 5% 80px;min-width:0}}h1{{font-size:29px;line-height:1.5;margin:9px 0}}.eyebrow{{color:var(--accent);font-size:12px;letter-spacing:2px}}.meta{{font-size:12px;color:var(--muted)}}.toolbar{{margin:23px 0 18px}}input{{width:100%;padding:12px 15px;border:1px solid var(--line);border-radius:8px;background:white;font:inherit}}.result{{background:white;padding:11px 15px;margin:8px 0;border:1px solid var(--line);border-radius:7px}}.result small{{display:block;color:var(--muted)}}.card{{background:#fff;border:1px solid var(--line);border-radius:9px;margin:12px 0;scroll-margin-top:20px}}summary{{cursor:pointer;padding:17px 20px;font-weight:650;font-size:16px}}.prose{{padding:0 23px 22px;overflow-wrap:anywhere}}.prose p{{margin:12px 0}}.prose h3,.prose h4{{margin-top:24px}}blockquote{{margin:12px 0;padding:4px 16px;border-left:3px solid #a7c4ad;background:#f7faf5}}pre{{overflow:auto;max-width:100%;background:#f2f5f0;padding:14px;border-radius:6px;line-height:1.65}}code{{font:13px/1.7 ui-monospace,SFMono-Regular,monospace}}.table-wrap{{overflow:auto;max-width:100%;margin:15px 0}}table{{border-collapse:collapse;font-size:13px;min-width:560px}}th,td{{border:1px solid var(--line);padding:9px 12px;vertical-align:top}}th{{background:#f2f6ef;text-align:left}}footer{{margin-top:26px;font-size:12px;color:var(--muted)}}[hidden]{{display:none!important}}@media(max-width:800px){{.layout{{display:block}}aside{{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line);padding:15px 20px}}aside .toc{{display:none}}aside nav{{display:flex;gap:14px;flex-wrap:wrap}}main{{padding:25px 18px 55px}}h1{{font-size:25px}}.prose{{padding:0 15px 18px}}summary{{padding:15px}}}}
</style></head><body><div class="layout"><aside><a href="http://127.0.0.1:8768/reading/preparation">← 求职工作台 · 准备资料库</a><a href="/">原有口述阅读页</a><strong>岗位与技术资料</strong><nav>{nav}</nav><div class="toc"><strong>本页目录</strong>{''.join(toc)}</div></aside><main><div class="eyebrow">INTERVIEW PREPARATION</div><h1>{html.escape(title)}</h1><p class="meta">Markdown 为内容源 · 答案采用与掌握状态见正文 · 更新后刷新即可读取</p><div class="toolbar"><input type="search" id="prep-search" aria-label="搜索岗位与技术资料" placeholder="搜索本次资料，例如：灰记、allSettled、95%、权限"><div id="search-results" aria-live="polite" hidden></div></div>{''.join(cards)}<footer>仅检索上方登记的 {len(SOURCES)} 份准备资料；本人面试记录、历史归档及原始私人材料未加入搜索。<br><a href="/document?path={quote(str(source.resolve()), safe='')}">打开本页 Markdown 内容源</a></footer></main></div><script>
const entries={data};
const input=document.getElementById('prep-search'),results=document.getElementById('search-results');
input.addEventListener('input',()=>{{const terms=input.value.trim().toLocaleLowerCase().split(/\\s+/).filter(Boolean);results.replaceChildren();results.hidden=!terms.length;if(!terms.length)return;const matches=entries.filter(e=>terms.every(t=>(e.doc+' '+e.title+' '+e.text).toLocaleLowerCase().includes(t)));const count=document.createElement('p');count.textContent='找到 '+matches.length+' 个章节';results.append(count);matches.slice(0,40).forEach(e=>{{const row=document.createElement('div');row.className='result';const a=document.createElement('a');a.href=e.url;a.textContent=e.title;const source=document.createElement('small');source.textContent=e.doc;row.append(a,source);results.append(row);}});}});
function locate(){{let id;try{{id=decodeURIComponent(location.hash.slice(1));}}catch{{return;}}const target=document.getElementById(id);if(target?.classList.contains('card')){{target.open=true;requestAnimationFrame(()=>target.scrollIntoView({{block:'start'}}));}}}}
window.addEventListener('hashchange',locate);locate();
</script></body></html>'''
