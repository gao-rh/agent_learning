#!/usr/bin/env python3
"""Local editor for the interview document. Python standard library only."""
from __future__ import annotations

import argparse
import hashlib
import html
import importlib.util
import json
import os
import re
import secrets
import tempfile
import threading
import uuid
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit
from urllib.request import urlopen

spec = importlib.util.spec_from_file_location('interview_reader', Path(__file__).with_name('生成面试阅读页.py'))
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)

prep_spec = importlib.util.spec_from_file_location('interview_preparation', Path(__file__).with_name('面试岗位阅读视图.py'))
prep_reader = importlib.util.module_from_spec(prep_spec)
prep_spec.loader.exec_module(prep_reader)


class Conflict(Exception):
    pass


def atomic_write(path: Path, text: str) -> None:
    fd, name = tempfile.mkstemp(prefix='.'+path.name+'.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        if path.exists():
            os.chmod(name, path.stat().st_mode & 0o777)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


class Document:
    def __init__(self, source: Path):
        self.source = source.resolve()
        self.lock = threading.Lock()

    def save(self, data: dict) -> dict:
        qid, answer, version, request_id = (data.get(k) for k in ('qid', 'answer', 'baseVersion', 'requestId'))
        if not isinstance(qid, str) or not re.fullmatch(r'[A-Z]\d{2}', qid):
            raise ValueError('题号不正确。')
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 30000 or '\x00' in answer:
            raise ValueError('请填写有效口述，最多 30000 字。')
        if not isinstance(version, str) or not re.fullmatch(r'[a-f0-9]{64}', version):
            raise ValueError('缺少版本信息，请刷新页面后再编辑。')
        if not isinstance(request_id, str) or str(uuid.UUID(request_id)) != request_id:
            raise ValueError('保存编号无效，请重新打开编辑框。')
        answer = answer.replace('\r\n', '\n').replace('\r', '\n')
        with self.lock:
            original = self.source.read_text(encoding='utf-8')
            matches = reader.question_matches(original)
            if qid not in matches:
                raise ValueError('找不到这道题，请刷新页面。')
            match = matches[qid]
            body = match['body']
            marker = f'编辑编号：{request_id}'
            if re.search(r'^'+re.escape(marker)+r'$', body, re.M):
                if reader.latest_answer(body) == answer:
                    return {'saved': True, 'qid': qid, 'duplicate': True}
                raise Conflict('这次修改已经保存过，但此后还有新版本。请复制当前编辑内容，再刷新核对。')
            if hashlib.sha256(body.encode()).hexdigest() != version:
                raise Conflict('这道题已有新版本，本次没有覆盖。请先复制编辑框中的文字，刷新查看最新口述后再修改。')
            if reader.latest_answer(body) == answer:
                return {'saved': True, 'qid': qid, 'unchanged': True}
            stamp = datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')
            # Quote every line so pasted headings cannot create new document sections.
            literal = '\n'.join('> '+line for line in answer.split('\n'))
            addition = (f'\n\n#### 口述记录｜{stamp} · 本人编辑\n\n口述性质：本人编辑\n\n'
                        '口述覆盖：本版由本人手动修改；具体回答范围以正文为准。\n\n'
                        f'{marker}\n\n口述格式：原文逐行\n\n##### 润色口述\n\n{literal}\n\n'
                        '##### 原始依据\n\n本版由本人在阅读页直接编辑并保存，文字按输入原样保留；没有经过 AI 改写。'
                        '此前回答及其原始依据保留在本题历史口述中。\n\n')
            boundary = body.find('\n#### 本模块材料')
            if boundary >= 0:
                updated = body[:boundary].rstrip()+addition+body[boundary:]
            else:
                updated = body.rstrip()+addition
            candidate = original[:match.start('body')]+updated+original[match.end('body'):]
            rendered = reader.build(candidate, self.source.parent / '资料' / '面试口述反馈.json')
            if self.source.read_text(encoding='utf-8') != original:
                raise Conflict('保存前文档发生了变化，本次没有覆盖。文字仍在编辑框中，请刷新后核对。')
            atomic_write(self.source, candidate)
            # Markdown is authoritative; the live view always renders from it.
            try:
                atomic_write(self.source.with_suffix('.html'), rendered)
            except OSError as error:
                print(f'口述已保存；离线 HTML 更新失败：{error}', flush=True)
            return {'saved': True, 'qid': qid}

    def page(self, token: str) -> str:
        text = self.source.read_text(encoding='utf-8')
        output = reader.build(text, self.source.parent / '资料' / '面试口述反馈.json').replace('<meta name="edit-token" content="">', f'<meta name="edit-token" content="{token}">')
        # Only explicitly linked Markdown sources are readable through this service.
        def local_link(match):
            href = html.unescape(match[1])
            if urlsplit(href).scheme or href.startswith('#') or urlsplit(href).path == '/prep':
                return match[0]
            path = (self.source.parent/unquote(href.split('#')[0])).resolve()
            if path == self.source.with_suffix('.html'):
                fragment = urlsplit(href).fragment
                return 'href="/'+('#'+html.escape(quote(fragment, safe='')) if fragment else '')+'"'
            return f'href="/document?path={quote(str(path), safe="")}"'
        return re.sub(r'href="([^"]+)"', local_link, output)

    def linked_document(self, path: Path) -> str:
        source = self.source.read_text(encoding='utf-8')
        allowed = {self.source, (self.source.parent/'README.md').resolve()}
        for href in re.findall(r'\[[^\]\n]+\]\(([^)]+)\)', source):
            if not urlsplit(href).scheme and not href.startswith('#'):
                allowed.add((self.source.parent/unquote(href.split('#')[0])).resolve())
        if path.suffix != '.md' or (path not in allowed and path not in prep_reader.readable_paths()):
            raise FileNotFoundError(path)
        return path.read_text(encoding='utf-8')


def make_server(source: Path, port: int) -> ThreadingHTTPServer:
    # Preserve open edit forms during a controlled local service update.
    token = os.environ.pop('INTERVIEW_ORAL_EDIT_TOKEN', '') or secrets.token_urlsafe(32)
    document = Document(source)
    origin = f'http://127.0.0.1:{port}'

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, body, content_type='application/json; charset=utf-8'):
            encoded = (json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else body).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(encoded)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
            self.end_headers()
            self.wfile.write(encoded)

        def valid_host(self):
            if self.headers.get('Host') != f'127.0.0.1:{port}':
                self.reply(403, {'error': '仅接受本机编辑页面请求。'})
                return False
            return True

        def do_GET(self):
            if not self.valid_host():
                return
            url = urlsplit(self.path)
            try:
                if url.path in {'/', '/AI数据面试准备.html'}:
                    self.reply(200, document.page(token), 'text/html; charset=utf-8')
                elif url.path == '/api/health':
                    self.reply(200, {'service': 'interview-oral-editor', 'ready': True})
                elif url.path == '/prep':
                    document_id = parse_qs(url.query).get('doc', ['xhs'])[0]
                    self.reply(200, prep_reader.build(reader.markdown, document_id), 'text/html; charset=utf-8')
                elif url.path == '/document':
                    path = Path(parse_qs(url.query).get('path', [''])[0]).resolve()
                    self.reply(200, document.linked_document(path), 'text/plain; charset=utf-8')
                else:
                    self.reply(404, {'error': '没有这个页面。'})
            except (FileNotFoundError, KeyError):
                self.reply(404, {'error': '找不到这份资料。'})
            except Exception as error:
                print(f'读取失败：{error}', flush=True)
                self.reply(500, {'error': '文档暂时无法读取，请检查编辑服务。'})

        def do_POST(self):
            if not self.valid_host():
                return
            if self.path != '/api/answer':
                self.reply(404, {'error': '没有这个保存接口。'})
                return
            if self.headers.get('Origin') != origin or not secrets.compare_digest(self.headers.get('X-Edit-Token', ''), token):
                self.reply(403, {'error': '编辑页面已过期，请复制文字后刷新页面再试。'})
                return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size <= 0 or size > 200000 or self.headers.get_content_type() != 'application/json':
                    raise ValueError('请求格式或长度不正确。')
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError('请求内容不正确。')
                self.reply(200, document.save(data))
            except Conflict as error:
                self.reply(409, {'error': str(error)})
            except (ValueError, TypeError) as error:
                self.reply(400, {'error': str(error)})
            except Exception as error:
                print(f'保存失败：{error}', flush=True)
                self.reply(500, {'error': '未能完成保存，文字仍在编辑框中，请稍后重试。'})

        def log_message(self, *_):
            pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=reader.SOURCE, help='Document path; override for isolated verification')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--open', action='store_true', help='Open the local page in the default browser')
    args = parser.parse_args()
    address = f'http://127.0.0.1:{args.port}/'
    try:
        server = make_server(args.source, args.port)
    except OSError:
        try:
            with urlopen(address+'api/health', timeout=2) as response:
                running = json.load(response).get('service') == 'interview-oral-editor'
        except Exception:
            running = False
        if not running:
            raise SystemExit(f'无法启动：端口 {args.port} 已被其他程序占用，或本机服务无法监听。')
        print(f'编辑服务已在运行：{address}', flush=True)
        if args.open:
            webbrowser.open(address)
        return
    print(f'面试口述编辑已启动：{address}\n关闭服务不会删除已保存的口述。', flush=True)
    if args.open:
        webbrowser.open(address)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
