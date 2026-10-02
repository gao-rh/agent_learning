"""最新报告入口及常驻阅读服务的归属边界；不调用模型。"""

import json
import socket
from types import SimpleNamespace

import pytest

from business_analysis_repro.case_viewer import start_services


def test_latest_report_uses_datetime_instead_of_version_order(tmp_path, monkeypatch):
    old = tmp_path / "测试报告-v9-2026-09-30-23-59-59.md"
    new = tmp_path / "测试报告-v1-2026-10-01-15-55-30.md"
    old.write_text("# old")
    new.write_text("# new")
    monkeypatch.setattr(start_services, "PROJECT", tmp_path)
    assert start_services.report_document() == new


def test_report_reload_preserves_listener_owned_by_another_command(tmp_path, monkeypatch):
    monkeypatch.setattr(start_services, "healthy", lambda *args: False)
    monkeypatch.setattr(start_services.subprocess, "run",
                        lambda *args, **kwargs: SimpleNamespace(stdout="unrelated-server"))

    def do_not_kill(*args):
        raise AssertionError("不得终止未核对归属的服务")

    monkeypatch.setattr(start_services.os, "kill", do_not_kill)
    record = tmp_path / "report.json"
    record.write_text(json.dumps({"pid": 12345}))
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        with pytest.raises(RuntimeError, match="已被占用"):
            start_services.ensure_service("report", port, "/source.md", "# new",
                                          ["/known/render_document.py"], tmp_path)
    assert json.loads(record.read_text()) == {"pid": 12345}
