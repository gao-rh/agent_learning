#!/bin/zsh
# 仅启动本地服务；发出业务问题后才调用模型。
set -eu
cd "${0:A:h}"
runtime_python="$HOME/Library/Caches/business-analysis-repro/test-venv/bin/python"
if [[ ! -x "$runtime_python" ]]; then
  export UV_PROJECT_ENVIRONMENT="$HOME/Library/Caches/business-analysis-repro/test-venv"
  uv sync --frozen --no-install-project --quiet
fi
export PYTHONPYCACHEPREFIX="$HOME/Library/Caches/business-analysis-repro/pycache"
exec "$runtime_python" -m business_analysis_repro.workbench.start
