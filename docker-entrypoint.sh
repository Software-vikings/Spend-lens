#!/bin/sh
set -eu
if [ ! -f "${SPENDLENS_DB:-/app/data/spendlens.db}" ]; then
  python -m spendlens.pipeline
fi
exec "$@"
