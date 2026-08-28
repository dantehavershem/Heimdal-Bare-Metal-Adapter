# Bare-Metal Adapter architecture

![Architecture overview](architecture-overview.svg)

## Principle: external-first storage

The appliance is a control and processing plane. Installer ISOs, golden images, driver packs and generated deployment capsules should live on external storage (SMB, NFS, NAS or another mounted filesystem). The VM stores only the OS, containers, PostgreSQL metadata, logs and a bounded scratch volume.

## Core layers

### 1. Management station layer
A Windows management station hosts the appliance VM and provides the administrator access point through the web browser.

### 2. Appliance control plane
Inside the VM, the main services are:

- **Web UI**: React/TypeScript management interface.
- **REST API**: FastAPI service and versioned API endpoints.
- **PostgreSQL**: durable metadata, inventory, jobs and audit trail.
- **Redis**: queue/cache/event platform service.
- **Workers**: long-running media, image and future capture/deploy jobs outside the API process.
- **Local cache/scratch space**: bounded working area for temporary processing.

### 3. External storage plane
The platform reads and writes media against external storage locations such as:

- SMB / Windows shares
- NFS exports
- S3-compatible object storage
- locally mounted NAS-backed paths

These locations hold the ISO library, golden-image repository, driver packs and build output.

### 4. Deployment integration plane
Generated deployment capsules can be uploaded or published to Heimdal PXE / Network OS Deployment. In future phases, the same architecture supports richer capture and deploy flows for physical endpoints.

## Operational model

- the browser manages, builds and monitors jobs;
- browser uploads stream directly to external storage;
- workers read and write media directly from and to registered storage locations;
- Heimdal PXE remains the deployment transport for wrapped media;
- reference machines and target endpoints become future capture/deploy participants.

## Future-capability skeleton already reserved

Media adapters, image conversion, golden-image capture/deploy, driver matching, Heimdal PXE publishing, standalone PXE, RBAC, audit and observability are represented in the service/data architecture even when the engine is not yet enabled.

## Management-station model

A Windows management station can host the appliance VM. Windows or network folders should be exposed as SMB shares and mounted inside the Linux appliance by UNC path; Windows drive letters are not used by the appliance.
