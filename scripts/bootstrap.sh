#!/usr/bin/env bash
set -euo pipefail
BASE=/srv/baremetal-adapter
sudo mkdir -p "$BASE"/{storage/{iso,golden-images,drivers,output},scratch}
sudo chown -R "$USER":"$USER" "$BASE"
if [ ! -f .env ]; then cp .env.example .env; fi
printf '\nSet BAREMETAL_ADAPTER_STORAGE_HOST=%s/storage in .env before starting.\n' "$BASE"
echo "Then run: docker compose up -d --build"
