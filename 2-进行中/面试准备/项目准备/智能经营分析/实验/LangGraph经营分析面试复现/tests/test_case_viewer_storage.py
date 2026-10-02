"""读取云端占位、断连错误与本机缓存的恢复边界；全部离线。"""
import json
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, build_opener

import pytest

from business_analysis_repro.case_viewer.__main__ import make_handler
from business_analysis_repro.case_viewer.repository import Repository
from business_analysis_repro.case_viewer.storage import LocalReader, RecordUnavailable
from business_analysis_repro.case_viewer.timeline import step_payload


def test_step_cutoff_does_not_expose_future_output():
    events = [
        {'seq': 1, 'kind': 'span_start', 'span_id': 'step', 'inputs': {'question': '原问题'}},
        {'seq': 2, 'kind': 'model_response', 'parent_span_id': 'step', 'content': '实际返回'},
        {'seq': 3, 'kind': 'span_end', 'span_id': 'step', 'output': {'answer': '完成'}},
    ]
    with pytest.raises(FileNotFoundError):
        step_payload(events, 'step', cutoff=0)
    assert step_payload(events, 'step', cutoff=1)['events'] == []
    assert step_payload(events, 'step', cutoff=2)['output'] is None
    assert not step_payload(events, 'step', cutoff=2)['finished']
    assert step_payload(events, 'step')['output'] == {'answer': '完成'}


def test_empty_placeholder_is_retried_and_only_complete_bytes_are_cached(tmp_path, monkeypatch):
    source = tmp_path / 'trace.json'
    source.write_bytes(b'{"ok":true}')
    reader = LocalReader(tmp_path / 'cache')
    original = Path.read_bytes
    attempts = []

    def placeholder(path):
        if path == source:
            attempts.append(path)
            if len(attempts) == 1:
                return b''
        return original(path)

    monkeypatch.setattr(Path, 'read_bytes', placeholder)
    assert reader.read(source) == b'{"ok":true}'
    assert len(attempts) == 2
    assert reader.read(source) == b'{"ok":true}'
    assert len(attempts) == 2
    source.write_bytes(b'{"ok":false}')
    assert reader.read(source) == b'{"ok":false}'
    assert len(attempts) == 3


def test_download_wait_is_bounded_and_later_read_recovers(tmp_path, monkeypatch):
    source = tmp_path / 'source-snapshot.zip'
    source.write_bytes(b'frozen')
    reader = LocalReader(tmp_path / 'cache', timeout=.03)
    release = threading.Event()
    original = Path.read_bytes

    def delayed(path):
        if path == source:
            release.wait(2)
        return original(path)

    monkeypatch.setattr(Path, 'read_bytes', delayed)
    start = time.monotonic()
    try:
        with pytest.raises(RecordUnavailable, match='source-snapshot.zip'):
            reader.read(source)
        assert time.monotonic() - start < .5
        assert len(reader.pending) == 1
        pending = next(iter(reader.pending.values()))
        release.set()
        assert pending['done'].wait(1)
        assert reader.read(source) == b'frozen'
    finally:
        release.set()


def test_disk_cache_survives_reader_restart_without_source_content_read(tmp_path, monkeypatch):
    source = tmp_path / 'turn.json'
    source.write_bytes(b'{"turn":4}')
    cache = tmp_path / 'cache'
    assert LocalReader(cache).read(source) == b'{"turn":4}'
    original = Path.read_bytes

    def evicted(path):
        if path == source:
            raise AssertionError('不应再次触发云端原件读取')
        return original(path)

    monkeypatch.setattr(Path, 'read_bytes', evicted)
    assert LocalReader(cache).read(source) == b'{"turn":4}'


def test_http_bad_snapshot_returns_error_and_health_does_not_read_records(tmp_path):
    batch = tmp_path / 'example'
    batch.mkdir()
    (batch / 'batch.json').write_text(json.dumps({'case_ids': {'Q01': 'fake'}}))
    (batch / 'source-snapshot.zip').write_bytes(b'not a zip')
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(Repository(tmp_path)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    origin = f'http://127.0.0.1:{server.server_port}'
    opener = build_opener(ProxyHandler({}))
    try:
        with opener.open(origin + '/api/health', timeout=2) as response:
            assert json.load(response) == {'status': 'ok', 'mode': 'read_only'}
        with pytest.raises(HTTPError) as error:
            opener.open(origin + '/api/case?batch=example&case=Q01', timeout=2)
        assert error.value.code == 503
        assert 'source-snapshot.zip' in json.load(error.value)['error']
        with opener.open(origin + '/case/example/Q01?turn=4', timeout=2) as response:
            html = response.read().decode()
            assert '__BOOTSTRAP_NONCE__' not in html
            assert '回放页面脚本未能加载' in html
            assert "'nonce-" in response.headers['Content-Security-Policy']
            assert 'unsafe-inline' not in response.headers['Content-Security-Policy']
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
