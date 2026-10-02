#!/bin/zsh
# 双击运行：密钥仍由既有 settings.py 从本机配置读取。
cd "$(dirname "$0")" || exit 1
if [[ ! -x .venv/bin/python ]]; then
  echo '请先在这个目录运行 uv sync --frozen。'
  read -r '?按回车退出'
  exit 1
fi
if /usr/bin/curl -fsS http://127.0.0.1:8787/api/health 2>/dev/null | /usr/bin/grep -q langgraph-playground; then
  open http://127.0.0.1:8787
else
  .venv/bin/python -m business_analysis_repro.playground --open
fi
