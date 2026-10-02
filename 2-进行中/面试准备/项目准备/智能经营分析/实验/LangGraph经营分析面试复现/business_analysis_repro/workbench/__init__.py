"""Thin local workbench over existing chat, reports and frozen case records."""

import html
import json
import re
import secrets
import time
import zipfile
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlencode, urlsplit

from ..case_viewer.repository import Repository, public_case
from ..case_viewer.storage import LocalReader, RecordUnavailable, read_bytes, read_text
from ._markdown import render as render_markdown

ASSETS = Path(__file__).parent
VIEWER = ASSETS.parent / "case_viewer"
REPORT = re.compile(r"测试报告-v(\d+)-(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})\.md")
CID = re.compile(r"[a-f0-9]{16}")


def shell(document, active="reports", page="reader"):
    """Add the same navigation without copying the underlying page content."""
    # Legacy trace/utility templates rely on HTML's implicit head and body.
    if "</head>" not in document:
        if not re.search(r"<head(?:\s|>)", document):
            document = re.sub(r"(<html[^>]*>)", r"\1<head>", document, count=1)
        end = re.search(r"</style>|</title>", document)
        if end:
            # These templates keep metadata/title/style before visible content.
            styles = list(re.finditer(r"</style>", document))
            position = styles[0].end() if styles else end.end()
            document = document[:position] + "</head>" + document[position:]
    if not re.search(r"<body(?:\s|>)", document):
        document = document.replace("</head>", "</head><body>", 1)
        document = document.replace("</html>", "</body></html>", 1)
    if "<main" not in document and page in {"utility", "trace"}:
        document = re.sub(r"(<body[^>]*>)", r'\1<main class="wb-main">', document, count=1)
        document = document.replace("</body>", "</main></body>", 1)
    links = "".join(
        f'<a href="{href}"' + (' aria-current="page"' if active == key else "") + f">{label}</a>"
        for key, href, label in (
            ("chat", "/", "对话"), ("reports", "/reports", "测试报告"), ("docs", "/docs", "资料")
        )
    )
    nav = (
        '<header class="wb-nav"><a class="wb-brand" href="/">Data Agent</a>'
        f'<nav aria-label="主导航">{links}</nav></header>'
    )
    document = document.replace(
        "</head>", '<link rel="stylesheet" href="/workbench.css"></head>', 1
    )
    document = re.sub(
        r"(<body[^>]*>)", r'\1' + nav, document, count=1
    ).replace("<body", f'<body data-workbench-page="{page}"', 1)
    return document.replace("</body>", '<script src="/workbench.js"></script></body>', 1)


def page(title, content, active):
    document = (
        '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>{html.escape(title)} · Data Agent</title></head><body>"
        f'<main class="wb-main">{content}</main></body></html>'
    )
    return shell(document, active, "index")


class Workbench:
    def __init__(self, project, runs, conversations):
        self.project = Path(project).resolve()
        self.runs = Path(runs).resolve()
        self.conversations = Path(conversations)
        self.repository = Repository(self.runs)
        self.history_reader = LocalReader(timeout=0.2)
        topic = self.project.parents[1]
        ongoing = next((p for p in self.project.parents if p.name == "2-进行中"), self.project)
        self.documents = {
            "workbench": ("工作台说明", ASSETS / "README.md"),
            "overview": ("项目介绍", topic / "记录/2026-09-09-智能经营分析复现总览与能力缺口-v1.md"),
            "run": ("运行说明", self.project / "README.md"),
            "knowledge": ("指标与维度", self.project / "business_analysis_repro/playground/指标维度矩阵.md"),
            "code": ("执行链路与代码阅读", self.project / "business_analysis_repro/playground/并行实现与验收.md"),
            "experience": ("Agent 经验", ongoing / "Agent经验/README.md"),
        }
        for name, title in (("premium", "保费分析"), ("penetration", "渗透率分析"),
                            ("channel", "渠道分析"), ("merchant", "商户分析")):
            self.documents["skill-" + name] = (
                title, self.project / f"business_analysis_repro/playground/analysis_skills/{name}/SKILL.md"
            )
        self.documents = {k: v for k, v in self.documents.items() if v[1].is_file()}

    def reports(self):
        items = []
        for path in self.project.glob("测试报告-v*-*.md"):
            match = REPORT.fullmatch(path.name)
            if match and not path.is_symlink():
                items.append({"id": path.stem, "version": match[1], "stamp": match[2], "path": path})
        return sorted(items, key=lambda r: (r["stamp"], int(r["version"])), reverse=True)

    def report(self, identity):
        return next((r for r in self.reports() if r["id"] == identity), None)

    def report_text(self, report):
        return read_text(report["path"])

    def report_context(self, batch, requested=""):
        # A report can cover several frozen batches. Never infer it from "latest".
        reports = self.reports()
        selected = next((r for r in reports if r["id"] == requested), None)
        if selected and f"/case/{batch}/" in self.report_text(selected):
            return self.public_report(selected)
        for report in reports:
            if f"/case/{batch}/" in self.report_text(report):
                return self.public_report(report)
        return None

    @staticmethod
    def public_report(report):
        return {"id": report["id"], "title": "测试报告 v" + report["version"],
                "url": "/reports/" + quote(report["id"]), "time": report["stamp"]}

    @staticmethod
    def metadata(text):
        lines = [s.strip().lstrip("> ").strip() for s in text.splitlines() if s.strip()]
        title = next((s[2:] for s in lines if s.startswith("# ")), "测试报告")
        result = next((s for s in lines if "**" in s), "")
        result = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", result).replace("**", "")
        return title, result

    def report_list(self):
        rows = []
        for report in self.reports():
            title, result = self.metadata(self.report_text(report))
            stamp = report["stamp"]
            date = stamp[:10] + " " + stamp[11:].replace("-", ":")
            href = "/reports/" + quote(report["id"])
            rows.append(
                '<article class="wb-report-row"><div>'
                f'<h2><a href="{href}">{html.escape(title)}</a></h2>'
                f'<p class="wb-muted">{date}</p><p>{html.escape(result)}</p></div>'
                f'<a class="wb-open" href="{href}">打开报告 →</a></article>'
            )
        return page("测试报告", '<h1>测试报告</h1><p class="wb-muted">'
                    "按测试时间查看历次结果。</p>" + "".join(rows or [
                        '<p>还没有测试报告。</p>']), "reports")

    def docs_list(self):
        def links(ids):
            return "".join(
                f'<a class="wb-doc-link" href="/docs/{key}">{html.escape(self.documents[key][0])}</a>'
                for key in ids if key in self.documents
            )
        content = '<h1>资料</h1><p class="wb-muted">项目相关内容的统一入口。</p>'
        content += '<section><h2>项目与实践</h2>' + links(
            ["workbench", "overview", "run", "code", "experience"]) + "</section>"
        content += '<section><h2>业务与方法</h2><a class="wb-doc-link" href="/knowledge">'
        content += "业务知识与 Skill 内容</a>" + links(
            ["knowledge", "skill-premium", "skill-penetration", "skill-channel", "skill-merchant"]
        ) + "</section>"
        content += '<section><h2>运行记录</h2><a class="wb-doc-link" href="/usage">'
        content += "Token 用量</a></section>"
        return page("资料", content, "docs")

    def destinations(self):
        result = {p.resolve(): "/docs/" + key for key, (_, p) in self.documents.items()}
        result.update({r["path"].resolve(): "/reports/" + quote(r["id"]) for r in self.reports()})
        return result

    @staticmethod
    def local_links(text, report_id=""):
        def replace(match):
            parsed = urlsplit(html.unescape(match[1]))
            if parsed.hostname not in ("127.0.0.1", "localhost"):
                return match[0]
            if parsed.port == 8788 and parsed.path.startswith("/case/"):
                query = parse_qs(parsed.query)
                if report_id:
                    query["report"] = [report_id]
                href = parsed.path + ("?" + urlencode(query, doseq=True) if query else "")
                href += ("#" + parsed.fragment) if parsed.fragment else ""
            elif parsed.port == 8787:
                href = parsed.path + ("?" + parsed.query if parsed.query else "")
                href += ("#" + parsed.fragment) if parsed.fragment else ""
            elif parsed.port == 8770:
                href = "/reports"
            else:
                return match[0]
            return 'href="' + html.escape(href, quote=True) + '"'
        return re.sub(r'href="([^"]+)"', replace, text)

    def document(self, path, route, active, report_id=""):
        content = read_text(path)
        rendered = render_markdown(
            path, content=content, destinations=self.destinations(),
            source_href=route + "/source.md"
        )
        title, _ = self.metadata(content)
        rendered = re.sub(r"<title>.*?</title>",
                          lambda _: "<title>" + html.escape(title) + " · Data Agent</title>",
                          rendered, count=1)
        rendered = self.local_links(rendered, report_id)
        label, parent = ("所有测试报告", "/reports") if active == "reports" else ("资料", "/docs")
        back = f'<a href="{parent}">← {label}</a> · '
        rendered = rendered.replace('<nav class="reader-navigation">',
                                    '<nav class="reader-navigation">' + back)
        return shell(rendered, active)

    def conversations_list(self):
        rows = []
        if not self.conversations.exists():
            return {"conversations": rows, "unavailable": 0}
        paths = []
        for directory in self.conversations.iterdir():
            if not CID.fullmatch(directory.name) or directory.is_symlink():
                continue
            path = directory / "conversation.json"
            if not path.is_file() or path.is_symlink():
                continue
            paths.append(path)
        paths.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        paths = paths[:50]
        deadline = time.monotonic() + 3
        unavailable = 0
        for index, path in enumerate(paths):
            if time.monotonic() >= deadline:
                unavailable += len(paths) - index
                break
            try:
                data = json.loads(self.history_reader.read(path))
                title = next((m.get("content", "") for m in data.get("messages", [])
                              if m.get("role") == "user"), "未命名对话")
                rows.append({"id": path.parent.name, "title": title[:80],
                             "updated_at": path.stat().st_mtime})
            except (OSError, ValueError, RecordUnavailable):
                unavailable += 1
                continue
        return {"conversations": rows, "unavailable": unavailable}

    def get(self, url):
        """Return (payload, content type, status), or None for a chat route."""
        path = unquote(url.path)
        params = parse_qs(url.query)
        arg = lambda key: params.get(key, [""])[0]
        kind = "text/html; charset=utf-8"
        try:
            if path in ("/workbench.css", "/workbench.js"):
                return read_bytes(ASSETS / path[1:]), (
                    "text/css" if path.endswith(".css") else "text/javascript"
                ) + "; charset=utf-8", 200
            if path == "/reports":
                return self.report_list().encode(), kind, 200
            if path == "/docs":
                return self.docs_list().encode(), kind, 200
            parts = path.strip("/").split("/")
            if len(parts) in (2, 3) and parts[0] in ("reports", "docs"):
                report = self.report(parts[1]) if parts[0] == "reports" else None
                source = report["path"] if report else (
                    self.documents.get(parts[1], ("", None))[1] if parts[0] == "docs" else None
                )
                if source is None or (len(parts) == 3 and parts[2] != "source.md"):
                    raise FileNotFoundError
                if len(parts) == 3:
                    return read_bytes(source), "text/plain; charset=utf-8", 200
                active = "reports" if report else "docs"
                return self.document(source, path, active, report["id"] if report else "").encode(), kind, 200
            if path == "/cases" or (
                len(parts) in (3, 4) and parts[0] == "case"
                and (len(parts) == 3 or parts[3] == "trace")
            ):
                body = read_text(VIEWER / "app.html")
                body = body.replace("/app.js", "/viewer/app.js").replace("/app.css", "/viewer/app.css")
                body = re.sub(r'<header class="top">.*?</header>', (
                    '<div class="wb-case-tools"><button id="toggle-cases" '
                    'aria-controls="case-sidebar" aria-expanded="false">选择案例</button>'
                    '<button id="refresh">刷新记录</button></div>'), body, count=1)
                body = body.replace("__BOOTSTRAP_NONCE__", secrets.token_urlsafe(16))
                body = body.replace('<script src="/viewer/app.js">', (
                    '<script>window.DATA_AGENT_WORKBENCH=true;</script>'
                    '<script src="/viewer/app.js">'))
                return shell(body, "reports", "case").encode(), kind, 200
            if path in ("/viewer/app.css", "/viewer/app.js"):
                return read_bytes(VIEWER / path.split("/")[-1]), (
                    "text/css" if path.endswith(".css") else "text/javascript"
                ) + "; charset=utf-8", 200
            payload = None
            if path == "/api/batches":
                payload = {"batches": self.repository.batches()}
            elif path == "/api/batch":
                payload = self.repository.overview(arg("batch"))
            elif path == "/api/case":
                payload = public_case(self.repository.case(arg("batch"), arg("case")))
            elif path == "/api/step":
                payload = self.repository.detail(arg("batch"), arg("case"), int(arg("turn")),
                                                 arg("step"), int(arg("cutoff")) if arg("cutoff") else None)
            elif path == "/api/raw":
                case = self.repository.case(arg("batch"), arg("case"))
                turn = next(t for t in case["turns"] if t["number"] == int(arg("turn")))
                body = "\n".join(json.dumps(e, ensure_ascii=False) for e in turn["_events"])
                return body.encode(), "text/plain; charset=utf-8", 200
            elif path == "/api/report-context":
                payload = {"report": self.report_context(arg("batch"), arg("report"))}
            elif path == "/api/conversations":
                payload = self.conversations_list()
            if payload is not None:
                return payload, "application/json; charset=utf-8", 200
            return None
        except (FileNotFoundError, StopIteration):
            return self.error("未找到该报告、资料或案例记录。", 404)
        except (RecordUnavailable, zipfile.BadZipFile, OSError):
            return self.error("记录暂时无法读取，请稍后重新读取。不会用当前记录替代历史内容。", 503)
        except (ValueError, KeyError):
            return self.error("记录或请求参数不完整。", 400)

    @staticmethod
    def error(message, status):
        return {"error": message}, "application/json; charset=utf-8", status
