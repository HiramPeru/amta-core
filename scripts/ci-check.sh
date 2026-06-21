#!/usr/bin/env bash
set -euo pipefail

./scripts/check.sh
git diff --exit-code -- .amta/generated schemas
