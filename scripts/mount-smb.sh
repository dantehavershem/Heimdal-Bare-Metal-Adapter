#!/usr/bin/env bash
set -euo pipefail
# Usage: sudo ./mount-smb.sh //SERVER/Share /srv/baremetal-adapter/storage/iso username domain
SHARE=${1:?SMB share required, e.g. //SERVER/Share}
TARGET=${2:?Target mount path required}
USER=${3:?Username required}
DOMAIN=${4:-}
read -rsp "Password: " PASS; echo
sudo mkdir -p "$TARGET"
CRED=/etc/baremetal-adapter/$(basename "$TARGET").cred
sudo mkdir -p /etc/baremetal-adapter
printf 'username=%s\npassword=%s\n' "$USER" "$PASS" | sudo tee "$CRED" >/dev/null
[ -n "$DOMAIN" ] && printf 'domain=%s\n' "$DOMAIN" | sudo tee -a "$CRED" >/dev/null
sudo chmod 600 "$CRED"
sudo mount -t cifs "$SHARE" "$TARGET" -o "credentials=$CRED,vers=3.0,iocharset=utf8,nofail"
echo "Mounted $SHARE at $TARGET"
