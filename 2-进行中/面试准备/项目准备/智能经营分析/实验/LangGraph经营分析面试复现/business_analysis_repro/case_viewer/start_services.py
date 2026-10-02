"""独立启动两个只读页面；启动器退出、终端关闭后服务仍可访问。

不注册开机任务、不运行实验、不调用模型。重复启动复用已有服务。
日志和 PID 放在 .runs/viewer-services，便于查看运行状态。
"""
import fcntl
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, build_opener

PROJECT = Path(__file__).resolve().parents[2]
OPENER = build_opener(ProxyHandler({}))


def report_document():
    reports = list(PROJECT.glob('测试报告-v*-*.md'))
    if reports:
        return max(reports, key=lambda p: '-'.join(p.stem.split('-')[2:]))
    return PROJECT / 'business_analysis_repro/clarification_lab/首次试跑结果.md'


def healthy(port, path, expected):
    try:
        with OPENER.open(f'http://127.0.0.1:{port}{path}', timeout=5) as response:
            body = response.read().decode('utf-8')
            return response.status == 200 and expected in body
    except (OSError, ValueError):
        return False


def ensure_service(name, port, path, expected, args, output):
    if healthy(port, path, expected):
        print(f'已在运行：http://127.0.0.1:{port}/', flush=True)
        return
    record = output / f'{name}.json'
    # 新报告仍复用 8770；仅替换本启动器登记且命令吻合的阅读服务。
    if name == 'report' and record.exists():
        pid = json.loads(record.read_text()).get('pid')
        if pid:
            command = subprocess.run(['ps', '-p', str(pid), '-o', 'command='],
                                     capture_output=True, text=True, check=False).stdout
            if str(args[0]) in command and f'--port {port}' in command:
                os.kill(pid, signal.SIGTERM)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    with socket.socket() as probe:
                        if probe.connect_ex(('127.0.0.1', port)) != 0:
                            break
                    time.sleep(0.1)
                record.unlink()
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(('127.0.0.1', port)) == 0:
            raise RuntimeError(f'{port} 已被占用或服务未就绪；未关闭已有进程。')
    if record.exists():
        previous_pid = json.loads(record.read_text()).get('pid')
        if previous_pid:
            try:
                os.kill(previous_pid, 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError(f'{name} 上次进程仍存活但尚未就绪，请查看日志；未重复启动。')
    log_path = output / f'{name}.log'
    with log_path.open('ab') as log:
        process = subprocess.Popen(
            [sys.executable, '-u', *args], cwd=PROJECT,
            stdin=subprocess.DEVNULL, stdout=log, stderr=log,
            start_new_session=True, close_fds=True,
        )
    record.write_text(json.dumps({
        'pid': process.pid, 'port': port, 'started_at': time.time(),
        'log': str(log_path),
    }, ensure_ascii=False, indent=2))
    # 首次启动可能等待 iCloud 文件下载，不把仍在启动误认为进程退出。
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'{name} 启动失败，请查看 {log_path}')
        if healthy(port, path, expected):
            print(f'已后台启动：http://127.0.0.1:{port}/（PID {process.pid}）', flush=True)
            return
        time.sleep(0.25)
    raise RuntimeError(f'{name} 尚未就绪，请查看 {log_path}；未重复创建进程。')


def main():
    output = PROJECT / '.runs/viewer-services'
    output.mkdir(parents=True, exist_ok=True)
    # 避免重复双击时同时检查端口并各启动一份服务。
    with (output / 'start.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ensure_service('cases', 8788, '/api/health', '"status": "ok"',
                       ['-m', 'business_analysis_repro.case_viewer', '--port', '8788'], output)
        reader = Path.home() / '.codex/skills/markdown-reader/scripts/render_document.py'
        report = report_document()
        args = [str(reader), 'serve',
                str(report), '--port', '8770']
        previous = [p for p in PROJECT.glob('测试报告-v*-*.md') if p != report]
        if previous:
            args += ['--related', str(max(previous, key=lambda p: '-'.join(p.stem.split('-')[2:])))]
        for related in [str(PROJECT.parents[1] / '记录/2026-09-09-智能经营分析复现总览与能力缺口-v1.md'),
                        str(PROJECT / 'README.md'),
                        'business_analysis_repro/case_viewer/README.md']:
            if (PROJECT / related).exists():
                args += ['--related', related]
        title = report.read_text().splitlines()[0]
        ensure_service('report', 8770, '/source.md', title, args, output)


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
