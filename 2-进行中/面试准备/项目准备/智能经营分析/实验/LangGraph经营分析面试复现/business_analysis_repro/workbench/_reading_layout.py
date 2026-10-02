# Extracted from recruiting-board/reading_layout.py on 2026-09-30.
"""Shared local Markdown reading layout; no external assets or requests."""
import html

STYLE = r'''
*{box-sizing:border-box}
:root{--toc-width:248px}
body{margin:0;font:17px/1.9 system-ui;color:#172239;background:#fff}
.reader-main{max-width:1008px;margin:0 auto;padding:36px 24px 64px;min-width:0}
body.has-toc{padding-left:calc(var(--toc-width) + 40px)}
body.toc-collapsed{padding-left:0}
body.toc-collapsed .reader-main{padding-top:76px}
a{color:#285fbd;overflow-wrap:anywhere}
:is(a,button,summary):focus-visible{outline:3px solid #84aaff;outline-offset:3px}
h1{font-size:28px;line-height:1.45}h2{font-size:22px;line-height:1.6;margin-top:38px;padding-top:24px;border-top:1px solid #dfe5ef}h3{font-size:19px}
p,li{overflow-wrap:anywhere}li{margin:8px 0}
.reader-navigation{font-size:15px;margin-bottom:28px}
strong{font-weight:650}
code{font:14px/1.65 ui-monospace,monospace;background:#eef2f8;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}
pre{overflow:auto;background:#eef2f8;padding:16px;border-radius:8px}pre code{padding:0;background:none;white-space:pre;overflow-wrap:normal}
.quote{border-left:3px solid #dfe5ef;padding-left:16px;margin:0;color:#33425a}
.line-anchor{display:block;scroll-margin-top:24px}[id]{scroll-margin-top:24px}
article :target{background:#fff4c7}
.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:15px}th,td{text-align:left;vertical-align:top;padding:10px;border:1px solid #dfe5ef}th{background:#eef2f8}
.toc-panel{position:fixed;inset:16px auto 16px 16px;width:var(--toc-width);display:flex;flex-direction:column;background:#f8faff;border:1px solid #dfe5ef;border-radius:12px;z-index:30;box-shadow:0 4px 20px #17223908}
.toc-header{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:15px 14px 11px;border-bottom:1px solid #e4eaf3}
.toc-heading{font-size:16px;font-weight:700}
.toc-caption{font-size:12px;color:#63718a;padding:9px 14px 3px}
.toc-scroll{overflow-y:auto;overscroll-behavior:contain;flex:1;min-height:0;padding:6px 10px 20px;scrollbar-width:thin}
.toc-list{list-style:none;margin:0;padding:0}.toc-list li{margin:3px 0}
.toc-list .toc-list{margin:3px 0 8px 9px;padding-left:8px;border-left:1px solid #dce4f1}
.toc-link{display:block;padding:7px 8px;border-radius:6px;font-size:13px;line-height:1.55;color:#40516c;text-decoration:none}
.toc-link:hover{background:#eaf0fb;color:#174fba}
.toc-link[aria-current="location"]{background:#e1ebff;color:#174fae;font-weight:650;box-shadow:inset 3px 0 #3975db}
.toc-level-2>.toc-link,.toc-level-2>details>summary>.toc-link{font-weight:650;color:#243853;font-size:14px}
.toc-level-4>.toc-link{font-size:12px}
.toc-list summary{display:flex;align-items:center;cursor:pointer;list-style:none;border-radius:6px}
.toc-list summary::-webkit-details-marker{display:none}
.toc-list summary::after{content:'›';font-size:20px;line-height:1;flex-shrink:0;text-align:center;width:26px;color:#75829a;transition:transform .15s}
.toc-list details[open]>summary::after{transform:rotate(90deg)}
.toc-list summary>.toc-link{flex:1;min-width:0}
.toc-button{font:600 13px/1.4 system-ui;border:1px solid #d6dfed;border-radius:7px;padding:8px 11px;background:#fff;color:#344866;cursor:pointer}
.toc-button:hover{background:#edf3ff}
.toc-toggle{position:fixed;top:16px;left:16px;z-index:25;display:none;box-shadow:0 3px 12px #17223914;padding:10px 14px}
.toc-collapsed .toc-panel{display:none}.toc-collapsed .toc-toggle{display:block}
.toc-backdrop{display:none}
@media(min-width:1100px){:root{--toc-width:280px}}
@media(max-width:759px){
 body.has-toc{padding-left:0}.reader-main,body.toc-collapsed .reader-main{padding:72px 18px 40px}
 h1{font-size:25px}.toc-panel{display:none;width:min(320px,calc(100vw - 40px));inset:12px auto 12px 12px;box-shadow:0 8px 36px #17223930}
 .toc-toggle{display:block}.toc-open .toc-toggle{display:none}.toc-open .toc-panel{display:flex}
 .toc-open{overflow:hidden}.toc-open .toc-backdrop{display:block;position:fixed;inset:0;z-index:29;background:#15243c66;border:0;width:100%;height:100%;padding:0}
 [id],.line-anchor{scroll-margin-top:72px}
}
@media print{body.has-toc{padding:0}.toc-panel,.toc-toggle,.toc-backdrop{display:none!important}.reader-main{max-width:none;padding:0}}
'''


SCRIPT = r'''
(() => {
  const panel = document.getElementById('reading-toc');
  if (!panel) return;
  const toggle = document.getElementById('toc-toggle');
  const close = document.getElementById('toc-close');
  const backdrop = document.getElementById('toc-backdrop');
  const viewport = window.matchMedia('(min-width:760px)');
  const links = [...panel.querySelectorAll('.toc-link')];
  const targets = links.map(link => ({link, target:document.getElementById(decodeURIComponent(link.hash.slice(1)))})).filter(item => item.target);
  const storageKey = () => 'markdown-reader-toc-' + (viewport.matches ? 'wide' : 'narrow');
  const savedOpen = () => {
    try { const value = localStorage.getItem(storageKey()); return value === null ? viewport.matches : value === 'open'; }
    catch { return viewport.matches; }
  };
  function setOpen(open, persist = false) {
    document.body.classList.toggle('toc-open', open);
    document.body.classList.toggle('toc-collapsed', !open);
    toggle.setAttribute('aria-expanded', String(open));
    close.setAttribute('aria-expanded', String(open));
    if (!viewport.matches && open) {
      panel.setAttribute('role', 'dialog'); panel.setAttribute('aria-modal', 'true');
    } else {
      panel.removeAttribute('role'); panel.removeAttribute('aria-modal');
    }
    if (persist) { try { localStorage.setItem(storageKey(), open ? 'open' : 'closed'); } catch {} }
  }
  function dismiss() { setOpen(false, true); toggle.focus({preventScroll:true}); }
  toggle.addEventListener('click', () => { setOpen(true, true); close.focus({preventScroll:true}); });
  close.addEventListener('click', dismiss);
  backdrop.addEventListener('click', dismiss);
  document.addEventListener('keydown', event => {
    if (!document.body.classList.contains('toc-open')) return;
    if (event.key === 'Escape') { event.preventDefault(); dismiss(); return; }
    if (event.key !== 'Tab' || viewport.matches) return;
    const focusable = [...panel.querySelectorAll('button,a,summary')].filter(el => el.getClientRects().length);
    const first = focusable[0], last = focusable[focusable.length - 1];
    if (event.shiftKey && (document.activeElement === first || !panel.contains(document.activeElement))) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && (document.activeElement === last || !panel.contains(document.activeElement))) {
      event.preventDefault(); first.focus();
    }
  });
  let active;
  function activate(link, reveal = false) {
    if (active !== link) {
      if (active) active.removeAttribute('aria-current');
      active = link;
      if (active) active.setAttribute('aria-current', 'location');
    }
    if (!link || !reveal) return;
    for (let parent = link.parentElement; parent && parent !== panel; parent = parent.parentElement) {
      if (parent.tagName === 'DETAILS') parent.open = true;
    }
    const scroller = panel.querySelector('.toc-scroll');
    if (link.getClientRects().length) {
      const rect = link.getBoundingClientRect(), bounds = scroller.getBoundingClientRect();
      if (rect.top < bounds.top || rect.bottom > bounds.bottom) scroller.scrollTop += rect.top - bounds.top - 60;
    }
  }
  function fromHash() {
    let id;
    try { id = decodeURIComponent(location.hash.slice(1)); } catch { return; }
    const match = targets.find(item => item.target.id === id);
    if (match) activate(match.link, true);
  }
  panel.addEventListener('click', event => {
    const link = event.target.closest('.toc-link');
    if (!link) return;
    // Let anchors keep native history and URL behavior; a link inside summary
    // navigates without also toggling its parent group.
    event.stopPropagation();
    activate(link, true);
    if (!viewport.matches) {
      setOpen(false);
      const target = document.getElementById(decodeURIComponent(link.hash.slice(1)));
      requestAnimationFrame(() => { if (target) { target.tabIndex = -1; target.focus({preventScroll:true}); } });
    }
  });
  let scheduled = false;
  function onScroll() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      let current = targets[0];
      for (const item of targets) {
        if (item.target.getBoundingClientRect().top > 100) break;
        current = item;
      }
      if (current) activate(current.link);
    });
  }
  setOpen(savedOpen());
  fromHash();
  window.addEventListener('hashchange', fromHash);
  window.addEventListener('scroll', onScroll, {passive:true});
  viewport.addEventListener('change', () => { setOpen(savedOpen()); fromHash(); });
  window.addEventListener('load', () => { fromHash(); onScroll(); });
})();
'''


def toc_tree(entries):
    roots, stack = [], []
    for entry in entries:
        node = dict(entry, children=[])
        while stack and stack[-1]['level'] >= node['level']:
            stack.pop()
        (stack[-1]['children'] if stack else roots).append(node)
        stack.append(node)

    def render(nodes):
        items = []
        for node in nodes:
            link = '<a class="toc-link" href="#' + html.escape(node['id'], quote=True) + '">' + html.escape(node['title']) + '</a>'
            if node['children']:
                link = '<details' + (' open' if node['level'] == 2 else '') + '><summary>' + link + '</summary>' + render(node['children']) + '</details>'
            items.append('<li class="toc-level-' + str(node['level']) + '">' + link + '</li>')
        return '<ul class="toc-list">' + ''.join(items) + '</ul>'
    return render(roots)


def render(title, navigation, body, entries):
    sidebar = ''
    if entries:
        sidebar = (
            '<button id="toc-toggle" class="toc-button toc-toggle" aria-controls="reading-toc" aria-expanded="false">☰ 目录</button>'
            '<button id="toc-backdrop" class="toc-backdrop" aria-label="关闭目录" tabindex="-1"></button>'
            '<aside id="reading-toc" class="toc-panel" aria-labelledby="toc-heading">'
            '<div class="toc-header"><span id="toc-heading" class="toc-heading">本页目录</span>'
            '<button id="toc-close" class="toc-button" aria-controls="reading-toc" aria-expanded="true">收起</button></div>'
            '<div class="toc-caption">点击标题跳转 · 箭头展开分组</div>'
            '<nav class="toc-scroll" aria-label="文章目录">' + toc_tree(entries) + '</nav></aside>'
        )
    return (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>' + html.escape(title) + '</title><style>' + STYLE + '</style></head><body' + (' class="has-toc"' if entries else '') + '>'
        + sidebar + '<main class="reader-main"><nav class="reader-navigation">' + navigation + '</nav><article>' + body + '</article></main>'
        + ('<script id="reading-navigation">' + SCRIPT + '</script>' if entries else '') + '</body></html>'
    )
