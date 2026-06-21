#!/usr/bin/env bash
set -euo pipefail

ruff check .
mypy amta
python -m pytest
amta validate
amta build
git diff --check
