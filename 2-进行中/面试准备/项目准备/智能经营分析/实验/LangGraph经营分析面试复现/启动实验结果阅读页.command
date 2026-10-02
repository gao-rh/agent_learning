#!/bin/zsh
set -e
cd -- "$(dirname -- "$0")"
exec .venv/bin/python -m business_analysis_repro.case_viewer.start_services
