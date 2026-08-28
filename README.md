# Bare-Metal Adapter

Self-hosted management appliance for adapting bootable media to Heimdal Network OS Deployment and evolving into a generic bare-metal installer/golden-image platform.

## Current v0.1 platform foundation

- React/TypeScript management UI
- FastAPI REST API
- PostgreSQL metadata store
- Redis platform service
- out-of-process worker
- external-first storage model
- ISO library and queued ISO analysis
- ISO9660 / El Torito / EFI / Casper / GRUB / ISOLINUX / Windows media detection
- Stage-1 WinPE bridge source carried forward under the new project name
- golden-image and installer capsule schemas
- optional conversion/PXE service profiles reserved

## Storage model

Large media does **not** belong inside the appliance VM. Mount SMB/NFS storage under the host storage root and expose it to containers. A 100 GiB golden image therefore remains on the NAS rather than consuming another 100 GiB of VM disk.

## Quick start

```bash
cp .env.example .env
./scripts/bootstrap.sh
# edit .env and set BAREMETAL_ADAPTER_STORAGE_HOST=/srv/baremetal-adapter/storage
docker compose up -d --build
```

Open `http://<appliance-ip>/`.

Register mounted folders on **Storage**, then queue an ISO from **Media** using its storage ID and relative path.

## Important

The web/API platform is functional foundation code. Stage-1 ISO wrapping and UEFI handoff remain laboratory functionality; golden-image capture/deploy, direct PXE publishing, driver injection and Secure Boot production hardening are deliberately scaffolded but not claimed complete.

### Browser upload behavior
`POST /api/v1/media/upload` writes incoming chunks directly to the selected registered storage location. Uploading a large ISO through the UI therefore uses the VM as the control path, not as persistent media storage.
