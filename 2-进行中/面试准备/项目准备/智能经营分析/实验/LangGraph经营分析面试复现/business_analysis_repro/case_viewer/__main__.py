"""python -m business_analysis_repro.case_viewer；固定模板读现有结果，不运行实验。"""
import argparse
import json
import secrets
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .repository import Repository, public_case
from .storage import RecordUnavailable, read_bytes, read_text

ASSETS = Path(__file__).parent


def make_handler(repository):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def send(self, body, content_type='application/json; charset=utf-8', status=200, nonce=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            script = "'self'" + (f" 'nonce-{nonce}'" if nonce else '')
            self.send_header('Content-Security-Policy', f"default-src 'self'; script-src {script}; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlparse(self.path)
            params = parse_qs(url.query)
            def arg(key):
                return params.get(key, [''])[0]
            try:
                if url.path == '/api/health':
                    return self.send({'status': 'ok', 'mode': 'read_only'})
                if url.path == '/' or url.path.startswith('/case/'):
                    nonce = secrets.token_urlsafe(16)
                    body = read_text(ASSETS/'app.html').replace('__BOOTSTRAP_NONCE__', nonce).encode()
                    return self.send(body, 'text/html; charset=utf-8', nonce=nonce)
                if url.path in {'/app.js','/app.css'}:
                    return self.send(read_bytes(ASSETS/url.path[1:]), 'text/javascript; charset=utf-8' if url.path.endswith('.js') else 'text/css; charset=utf-8')
                if url.path == '/api/batches':
                    return self.send({'batches': repository.batches()})
                if url.path == '/api/batch':
                    return self.send(repository.overview(arg('batch')))
                if url.path == '/api/case':
                    return self.send(public_case(repository.case(arg('batch'),arg('case'))))
                if url.path == '/api/step':
                    cutoff = int(arg('cutoff')) if arg('cutoff') else None
                    return self.send(repository.detail(arg('batch'),arg('case'),int(arg('turn')),arg('step'),cutoff))
                if url.path == '/api/raw':
                    case = repository.case(arg('batch'),arg('case'))
                    turn = next((t for t in case['turns'] if t['number']==int(arg('turn'))),None)
                    if turn is None:
                        raise FileNotFoundError('轮次不存在')
                    body = '\n'.join(json.dumps(e,ensure_ascii=False) for e in turn['_events']).encode()
                    return self.send(body,'text/plain; charset=utf-8')
                raise FileNotFoundError('页面不存在')
            except (FileNotFoundError, StopIteration):
                self.send({'error':'未找到该批次、案例或执行步骤。'},status=404)
            except RecordUnavailable as error:
                self.send({'error':str(error)},status=503)
            except zipfile.BadZipFile:
                self.send({'error':'source-snapshot.zip 尚未完整读取，或快照格式损坏。请重新读取；不会用当前版本替代历史快照。'},status=503)
            except (ValueError, KeyError):
                self.send({'error':'请求参数或记录格式不完整。'},status=400)
            except OSError:
                self.send({'error':'记录暂时无法读取，请刷新重试。'},status=503)

        def do_POST(self):
            self.send({'error':'查看器只读，不提供执行接口。'},status=405)
    return Handler


def main():
    parser=argparse.ArgumentParser(description='只读案例查看器，不加载密钥或发起模型调用。')
    parser.add_argument('--runs',type=Path,default=Path(__file__).resolve().parents[2]/'.runs')
    parser.add_argument('--port',type=int,default=8788)
    args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),make_handler(Repository(args.runs)))
    print(f'案例查看器：http://127.0.0.1:{server.server_port}/',flush=True)
    print(f'只读实验目录：{args.runs.resolve()}',flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=='__main__':
    main()
