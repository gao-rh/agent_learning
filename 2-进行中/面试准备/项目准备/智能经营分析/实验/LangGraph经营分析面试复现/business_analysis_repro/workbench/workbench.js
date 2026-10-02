'use strict';
(() => {
  const pageKey = 'data-agent-position:' + location.pathname + location.search;
  window.addEventListener('pagehide', () => {
    try { sessionStorage.setItem(pageKey, String(window.scrollY)); } catch {}
  });
  if (!location.hash && !new URLSearchParams(location.search).has('turn')) {
    const saved = Number(sessionStorage.getItem(pageKey) || 0);
    if (saved) window.addEventListener('load', () => window.scrollTo(0, saved));
  }
  const history = document.getElementById('conversation-history');
  if (!history) return;
  const readHistory = async () => {
    if (!history.open) return;
    const list = document.getElementById('conversation-list');
    list.textContent = '正在读取…';
    try {
      const response = await fetch('/api/conversations');
      if (!response.ok) throw Error('历史会话暂时无法读取。');
      const data = await response.json();
      list.replaceChildren();
      for (const item of data.conversations) {
        const link = document.createElement('a');
        link.href = '/?id=' + encodeURIComponent(item.id);
        link.textContent = item.title || '未命名对话';
        list.append(link);
      }
      if (!data.conversations.length) list.textContent = '还没有保存的对话。';
      if (data.unavailable) {
        const note = document.createElement('p');
        note.className = 'wb-muted';
        note.textContent = '部分记录暂未就绪，可能仍在等待 iCloud 下载。';
        if (!data.conversations.length) list.replaceChildren();
        const retry = document.createElement('button');
        retry.type = 'button';
        retry.textContent = '重新读取';
        retry.onclick = readHistory;
        list.append(note, retry);
      }
    } catch (error) {
      list.textContent = error.message;
    }
  };
  history.addEventListener('toggle', readHistory);
})();
