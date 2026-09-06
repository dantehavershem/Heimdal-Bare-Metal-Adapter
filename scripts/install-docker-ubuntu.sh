#!/usr/bin/env bash
# Install Ubuntu-packaged Docker Engine, Compose v2, and Buildx.
# Run as the normal appliance user: bash scripts/install-docker-ubuntu.sh
set -euo pipefail
if [[ "$EUID" -eq 0 ]]; then
  echo "Run this script as your normal user; it invokes sudo when needed." >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != ubuntu ]]; then
  echo "This installer requires Ubuntu." >&2
  exit 1
fi
appliance_user=$(id -un)
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-v2 docker-buildx
sudo systemctl enable --now docker
sudo usermod -aG docker "$appliance_user"
sudo docker info --format 'Docker server: {{.ServerVersion}}'
docker compose version
echo "Docker is ready. New processes must use the updated docker group membership."
