"""Start the existing chat server as a persistent local workbench, without model calls."""

import fcntl
import webbrowser

from ..case_viewer.start_services import PROJECT, ensure_service


def main():
    output = PROJECT / ".runs/workbench-services"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "start.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        ensure_service(
            "workbench", 8787, "/api/health", '"workbench": "minimal-v1"',
            ["-m", "business_analysis_repro.playground", "--port", "8787"], output,
        )
    webbrowser.open("http://127.0.0.1:8787/")


if __name__ == "__main__":
    main()
