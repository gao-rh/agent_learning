"""The integrated workbench reads frozen evidence and never starts a run on GET."""

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

import pytest

from business_analysis_repro.playground.server import ChatStore, make_handler
from business_analysis_repro.workbench import Workbench, shell


@pytest.fixture
def site(tmp_path):
    project = tmp_path / "topic" / "实验" / "project"
    project.mkdir(parents=True)
    (project / "README.md").write_text(
        '# Run\n## Stable section\n<a id="stable"></a>\n'
        '[source](.env)\n<script>alert("private")</script>\n'
    )
    runs = project / ".runs"
    case = runs / "frozen" / "C01"
    case.mkdir(parents=True)
    (case.parent / "batch.json").write_text(json.dumps({"kind": "knowledge", "case_ids": ["C01"]}))
    (case / "session.json").write_text(json.dumps({"case": {"id": "C01", "question": "第一轮原话"}}))
    for n in (1, 2):
        (case / f"turn-{n}.json").write_text(json.dumps({
            "turn_number": n, "run_id": f"run-{n}", "question": f"第{n}轮",
            "resolver_result": {"outcome": "clarify", "question": f"回复{n}"},
            "validation": {"accepted": True, "execution_enabled": False},
        }))
    (case / "trace.jsonl").write_text("\n".join(json.dumps({
        "seq": n, "run_id": f"run-{n}", "kind": "experiment_input",
        "name": "example", "time": "2026-10-02T00:00:00+00:00", "payload": {}
    }) for n in (1, 2)))
    names = ["测试报告-v99-2026-09-30-23-59-59", "测试报告-v1-2026-10-02-17-10-19"]
    for name in names:
        (project / (name + ".md")).write_text(
            "# " + name + "\n\n**仅计划确认通过，未执行取数。**\n\n"
            "[回放](http://127.0.0.1:8788/case/frozen/C01?turn=2)\n"
        )
    calls = []

    def execute(*args, **kwargs):
        calls.append(args[2])
        return {"status": "completed", "answer": "离线助手回复", "response_kind": "conversation"}, []

    store = ChatStore(runs / "playground", executor=execute)
    workbench = Workbench(project, runs, store.root)
    yield project, workbench, store, calls, names


def test_report_order_and_links_use_frozen_report_identity(site):
    _, workbench, _, calls, names = site
    assert workbench.reports()[0]["id"] == names[1]
    payload, _, status = workbench.get(urlsplit("/reports/" + quote(names[0])))
    assert status == 200
    text = payload.decode()
    assert '/case/frozen/C01?turn=2&amp;report=' + quote(names[0]) in text
    assert workbench.report_context("frozen", names[0])["id"] == names[0]
    assert calls == []


def test_registered_documents_escape_html_and_do_not_expose_arbitrary_files(site):
    project, workbench, _, _, _ = site
    (project / ".env").write_text("SECRET=never-serve")
    payload, _, status = workbench.get(urlsplit("/docs/run"))
    assert status == 200
    assert b'&lt;script&gt;' in payload and b'<script>alert' not in payload
    assert b'id="stable"' in payload and b'reading-toc' in payload
    for path in ("/docs/.env", "/docs/run/.env", "/reports/../../.env", "/docs/%2e%2e/source.md"):
        result = workbench.get(urlsplit(path))
        assert result is None or result[2] == 404
        assert "never-serve" not in str(result)


def test_unavailable_history_keeps_readable_records_and_offers_retry(site):
    _, workbench, store, _, _ = site
    for cid in ("a" * 16, "b" * 16):
        directory = store.directory(cid)
        directory.mkdir(parents=True)
        (directory / "conversation.json").write_text(json.dumps({
            "messages": [{"role": "user", "content": "已有问题"}]
        }))

    class Reader:
        def read(self, path):
            if path.parent.name == "b" * 16:
                raise OSError("cloud file not ready")
            return path.read_bytes()

    workbench.history_reader = Reader()
    payload = workbench.conversations_list()
    assert payload["unavailable"] == 1
    assert [item["id"] for item in payload["conversations"]] == ["a" * 16]


def test_legacy_implicit_body_trace_keeps_navigation_and_existing_content():
    legacy = ('<!doctype html><html><meta charset="utf-8"><title>Trace</title>'
              '<style>body{padding:28px}</style><h1>Trace</h1><details>证据</details></html>')
    document = shell(legacy, "chat", "trace")
    assert document.count('aria-label="主导航"') == 1
    assert '<link rel="stylesheet" href="/workbench.css">' in document
    assert '<body data-workbench-page="trace">' in document
    assert '<main class="wb-main"><h1>Trace</h1><details>证据</details></main>' in document


def test_http_navigation_retains_chat_and_separates_turn_evidence(site):
    project, workbench, store, calls, names = site
    http = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store, workbench))
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{http.server_port}"
    cid = "a" * 16
    try:
        for path in ("/", "/reports", "/docs", "/usage", "/knowledge", "/case/frozen/C01",
                     "/case/frozen/C01/trace?turn=2", "/docs/run"):
            with urlopen(origin + path) as response:
                text = response.read().decode()
                assert 'aria-label="主导航"' in text
        assert calls == []
        with urlopen(origin + "/api/raw?batch=frozen&case=C01&turn=2") as response:
            events = [json.loads(line) for line in response.read().decode().splitlines()]
            assert {e["run_id"] for e in events} == {"run-2"}
        request = Request(origin + "/api/message", data=json.dumps({
            "id": cid, "request_id": "b" * 16, "text": "离线输入"
        }).encode(), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            assert json.load(response)["messages"][-1]["content"] == "离线助手回复"
        with urlopen(origin + "/reports/" + quote(names[1])) as response:
            assert response.status == 200
        with urlopen(origin + "/api/conversation?id=" + cid) as response:
            assert json.load(response)["messages"][-1]["content"] == "离线助手回复"
        with urlopen(origin + "/api/conversations") as response:
            assert json.load(response)["conversations"][0]["id"] == cid
        assert calls == ["离线输入"]
        with pytest.raises(HTTPError) as error:
            urlopen(Request(origin + "/api/run", data=b"{}", method="POST"))
        assert error.value.code == 404
        assert (project / ".runs/frozen/C01/trace.jsonl").read_text().count("run-2") == 1
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=3)
