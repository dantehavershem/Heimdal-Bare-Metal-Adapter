# Bare-Metal Adapter architecture

## Principle: external-first storage
The appliance is a control and processing plane. Installer ISOs, golden images, driver packs and generated deployment capsules should live on external storage (SMB, NFS, NAS or another mounted filesystem). The VM stores only the OS, containers, PostgreSQL metadata, logs and a bounded scratch volume.

## Core services
- Web: React/TypeScript management UI.
- API: FastAPI service and versioned REST API.
- PostgreSQL: durable metadata, inventory, jobs and audit trail.
- Redis: installed as platform infrastructure for future event/cache/queue use.
- Worker: long-running media and image jobs outside the API process.
- Storage: host-mounted external shares exposed to API/workers at `/storage`.

## Future-capability skeleton already reserved
Media adapters, image conversion, golden image capture/deploy, driver matching, Heimdal PXE publishing, standalone PXE, RBAC, audit and observability are represented in the service/data architecture even when the engine is not yet enabled.

## Management-station model
A Windows management station can host the appliance VM. Windows or network folders should be exposed as SMB shares and mounted inside the Linux appliance by UNC path; Windows drive letters are not used by the appliance.
