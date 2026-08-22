#!/usr/bin/env sh
set -eu
MODE=${1:-cpu}
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
command -v uv >/dev/null 2>&1 || {
  echo "uv is required: https://docs.astral.sh/uv/" >&2
  exit 1
}
uv python install 3.11
uv sync --project "$ROOT" --extra dev --extra tts
uv run --project "$ROOT" studio doctor --mode "$MODE"

