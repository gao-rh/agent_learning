#!/usr/bin/env python3
"""Read-only readiness check for the Chapter 3 learning experiments."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


TOPIC_DIR = Path(__file__).resolve().parents[2]
BOOK_REPO = TOPIC_DIR / "资料" / "本地资料" / "深入理解AI-Agent"
CHAPTER = BOOK_REPO / "chapter3"
VENV_PYTHON = BOOK_REPO / ".venv" / "bin" / "python"

API_KEYS = (
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "KIMI_API_KEY",
    "MOONSHOT_API_KEY",
    "DASHSCOPE_API_KEY",
    "SILICONFLOW_API_KEY",
    "ARK_API_KEY",
    "DOUBAO_API_KEY",
    "MEM0_API_KEY",
    "MEMOBASE_API_KEY",
)

PROJECTS = (
    "user-memory",
    "user-memory-evaluation",
    "mem0",
    "memobase",
    "log-sanitization",
    "dense-embedding",
    "sparse-embedding",
    "retrieval-pipeline",
    "structured-index",
    "agentic-rag",
    "agentic-rag-for-user-memory",
    "contextual-retrieval",
    "contextual-retrieval-for-user-memory",
    "structured-knowledge-extraction",
)

MODEL_CACHES = {
    "MiniLM dense encoder": "models--sentence-transformers--all-MiniLM-L6-v2",
    "BGE reranker": "models--BAAI--bge-reranker-base",
    "Qwen3 embedding": "models--Qwen--Qwen3-Embedding-0.6B",
}


def run(*args: str, cwd: Path | None = None) -> tuple[int, str]:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=20,
            check=False,
        )
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)


def display(label: str, ok: bool, detail: str) -> None:
    print(f"[{'READY' if ok else 'WAIT '}] {label}: {detail}")


def configured_keys() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in API_KEYS:
        if os.getenv(name):
            found[name] = "shell"

    env_files = [BOOK_REPO / ".env", *CHAPTER.glob("*/.env")]
    for env_file in env_files:
        if not env_file.is_file():
            continue
        for raw_line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip().strip("'\"")
            placeholder = not value or "your_" in value.lower() or value.lower() in {"xxx", "changeme"}
            if name in API_KEYS and not placeholder:
                found.setdefault(name, "local .env")
    return found


def main() -> int:
    print("Chapter 3 experiment preflight (read-only)\n")

    display("official repository", BOOK_REPO.is_dir(), str(BOOK_REPO))
    commit_code, commit = run("git", "rev-parse", "HEAD", cwd=BOOK_REPO)
    display("official commit", commit_code == 0, commit or "unavailable")

    missing_projects = [name for name in PROJECTS if not (CHAPTER / name).is_dir()]
    display(
        "experiment sources",
        not missing_projects,
        "all 14 companion directories present" if not missing_projects else f"missing {missing_projects}",
    )

    py_code, py_output = run(str(VENV_PYTHON), "--version") if VENV_PYTHON.exists() else (1, "missing")
    display("locked Python environment", py_code == 0, py_output)
    import_code, import_output = (
        run(
            str(VENV_PYTHON),
            "-c",
            "import torch,transformers,annoy,hnswlib,mem0,memobase; print('core imports ok')",
        )
        if VENV_PYTHON.exists()
        else (1, "environment missing")
    )
    display("core Python imports", import_code == 0, import_output.splitlines()[-1])

    key_sources = configured_keys()
    display(
        "LLM credentials",
        bool(key_sources),
        ", ".join(f"{name} ({source})" for name, source in sorted(key_sources.items()))
        if key_sources
        else "none detected; offline/local stages only",
    )

    ollama_code, ollama_output = run("ollama", "list") if shutil.which("ollama") else (1, "not installed")
    display("Ollama qwen3:0.6b", ollama_code == 0 and "qwen3:0.6b" in ollama_output, "installed" if "qwen3:0.6b" in ollama_output else ollama_output)
    docker_code, docker_output = run("docker", "--version") if shutil.which("docker") else (1, "not installed")
    display("Docker CLI", docker_code == 0, docker_output)

    hf_cache = Path.home() / ".cache" / "huggingface" / "hub"
    for label, dirname in MODEL_CACHES.items():
        path = hf_cache / dirname
        display(label, path.is_dir(), "cached" if path.is_dir() else "download later")

    layer_counts = {}
    cases_root = CHAPTER / "user-memory-evaluation" / "test_cases"
    for layer in ("layer1", "layer2", "layer3"):
        layer_counts[layer] = len(list((cases_root / layer).glob("*.yaml")))
    display("3-1 evaluation cases", list(layer_counts.values()) == [20, 20, 20], json.dumps(layer_counts))

    intel_pdf = CHAPTER / "structured-index" / "data" / "intel-sdm-volume-1.pdf"
    display("3-7 Intel PDF", intel_pdf.is_file(), f"{intel_pdf.stat().st_size / 1024 / 1024:.1f} MiB" if intel_pdf.is_file() else "missing")

    cail_sample = CHAPTER / "structured-knowledge-extraction" / "data" / "official" / "cail2018_sample_seed37.jsonl"
    cail_archive = CHAPTER / "structured-knowledge-extraction" / "data" / "official" / "CAIL2018_ALL_DATA.zip"
    sample_rows = sum(1 for _ in cail_sample.open(encoding="utf-8")) if cail_sample.is_file() else 0
    display("3-12 fixed CAIL sample", sample_rows == 420, f"{sample_rows} rows")
    display("3-12 original CAIL archive", cail_archive.is_file(), "present" if cail_archive.is_file() else "deferred download")

    contextual_store = CHAPTER / "contextual-retrieval" / "document_store.json"
    display("3-10 generated contextual corpus", contextual_store.is_file(), "present" if contextual_store.is_file() else "must be generated live; README default cannot run yet")

    upstream_passed = 0
    pointers = list(CHAPTER.glob("*/validation/latest.json"))
    for pointer in pointers:
        try:
            if json.loads(pointer.read_text(encoding="utf-8")).get("status") == "passed":
                upstream_passed += 1
        except (OSError, json.JSONDecodeError):
            pass
    display(
        "validation pointers (author history + local diagnostics)",
        upstream_passed == len(pointers) and bool(pointers),
        f"{upstream_passed}/{len(pointers)} pointers currently say passed; inspect provenance before citing",
    )

    free_gib = shutil.disk_usage(BOOK_REPO).free / 1024**3
    display("free disk", free_gib >= 8, f"{free_gib:.1f} GiB; recheck before large model/data downloads")

    print("\nReadiness summary:")
    print("- Start now: 3-1 offline evaluation and 3-2 representation inspection.")
    print("- Fully local candidate: 3-3 and 3-5.")
    print("- Cached retrieval models: 3-4 and 3-6; ANNOY on this Mac needs an isolated Linux check.")
    print("- Live-generation/Judge gates remain external conditions, not setup failures.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
