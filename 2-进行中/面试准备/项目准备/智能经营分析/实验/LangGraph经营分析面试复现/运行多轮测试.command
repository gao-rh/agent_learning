#!/bin/zsh
# 相同uv.lock、本地依赖与字节码缓存；避免iCloud虚拟环境占位阻塞。
set -eu
cd "${0:A:h}"
export UV_PROJECT_ENVIRONMENT="$HOME/Library/Caches/business-analysis-repro/test-venv"
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/business-analysis-repro/pycache"
uv sync --frozen --no-install-project --quiet
exec "$UV_PROJECT_ENVIRONMENT/bin/python" -m business_analysis_repro.conversation_lab "$@"
