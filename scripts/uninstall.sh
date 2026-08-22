#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
docker compose down
echo "Source, workspaces, models, assets, deliveries, and database volume were preserved."

