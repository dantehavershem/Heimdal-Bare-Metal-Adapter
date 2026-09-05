# Heimdal Bare-Metal Adapter — Codex Start Here

## 1. Purpose of this document

This document is the technical handoff for continuing development of the **Heimdal Bare-Metal Adapter** inside a Linux VM with Codex.

The repository is intended to become a self-hosted management appliance that extends Heimdal Network OS Deployment / PXE beyond its current Windows-oriented `setup.exe` expectation and evolves into a broader bare-metal deployment platform supporting:

- installer ISO wrapping;
- generic boot-media adaptation;
- deployment capsules compatible with Heimdal PXE;
- external-first ISO/image storage;
- golden-image capture and deployment;
- driver packs and hardware matching;
- future direct publishing into Heimdal PXE;
- future standalone PXE capabilities if required.

The project must remain implementation-driven. Do not redesign the product from scratch unless a current architectural decision is technically impossible. Preserve the existing architecture and incrementally make currently scaffolded features functional.

---

## 2. Repository and source of truth

Repository:

```text
https://github.com/dantehavershem/Heimdal-Bare-Metal-Adapter
```

Primary branch:

```text
main
```

The GitHub repository is the authoritative source of truth.

The temporary development VM on the Mac is disposable. Nothing important should exist only in that VM. Every meaningful code/configuration/documentation change must be committed to GitHub.

The same repository will later be used to build a clean VM on Proxmox using an installer/bootstrap process.

Target future workflow:

```text
Temporary Mac development VM
        ↓
Develop + test
        ↓
Commit and push to GitHub
        ↓
Proxmox server available
        ↓
Create clean Ubuntu VM
        ↓
git clone Heimdal-Bare-Metal-Adapter
        ↓
sudo ./install.sh
        ↓
Fresh Bare-Metal Adapter appliance
```

Do not design the solution around migrating the temporary Mac VM itself.

---

## 3. Product concept

### 3.1 Core problem

Heimdal Network OS Deployment / PXE currently boots a Windows PE environment and expects an executable called:

```text
setup.exe
```

This works naturally with Windows deployment media but creates a compatibility boundary for Linux installers, bootable appliances, rescue media, and future golden-image deployment workflows.

The Bare-Metal Adapter solves this by acting as a self-hosted control and processing plane between source media and Heimdal PXE.

The platform should:

1. inspect a source ISO or image;
2. determine how it boots;
3. select an appropriate adapter strategy;
4. generate a Heimdal-compatible deployment capsule;
5. place the generated result on external storage;
6. allow Heimdal PXE to boot its normal WinPE environment and execute the capsule's root `setup.exe`;
7. hand off from WinPE into the native boot/runtime required by the target payload.

The project is deliberately broader than an Ubuntu-only wrapper.

The correct long-term framing is:

> Wrap supported x86-64 UEFI bootable ISOs automatically, with a generic fallback architecture for additional media types.

Do not claim literal universal ISO compatibility.

---

## 4. Architectural principles

### 4.1 Control plane in the VM, large media outside the VM

This is the most important design principle:

> **Control plane in the VM. Large media stays on external storage.**

The appliance VM contains:

- Linux OS;
- Docker / Compose;
- Web UI;
- API;
- PostgreSQL;
- Redis;
- job workers;
- metadata;
- logs;
- bounded temporary/scratch data.

The appliance VM must **not** become the permanent media repository.

Large data belongs on external storage:

```text
ISO Library
Golden Images
Driver Packs
Build Output / Deployment Capsules
Capture Output
```

Supported storage architecture should include:

- SMB / CIFS;
- Windows shares by UNC path;
- NFS;
- mounted NAS-backed filesystem;
- S3-compatible storage later.

### 4.2 Streaming preferred over large local copies

Bad pattern:

```text
NAS -> copy 80 GB into VM -> process -> copy 80 GB back to NAS
```

Preferred pattern:

```text
NAS source -> worker read/stream -> NAS output
```

Capture should similarly support:

```text
Reference machine -> capture runtime -> compression stream -> external storage
```

Deploy should support:

```text
External storage -> deployment runtime -> target disk
```

Use local scratch only when a tool genuinely requires random access or temporary extraction.

### 4.3 One-time UEFI handoff

The preferred boot handoff mechanism is a **one-time UEFI boot entry / BootNext**.

Do not permanently replace:

- Windows Boot Manager;
- firmware boot order;
- the machine's normal OS boot entry.

Initial proof scope:

```text
Architecture: x86-64
Firmware: UEFI
Secure Boot: OFF
Legacy BIOS: later
ARM64: later
```

---

## 5. Target runtime architecture

Typical management-station deployment:

```text
Windows Management Station
├── Browser
└── Linux VM: Heimdal Bare-Metal Adapter
    ├── Web UI
    ├── REST API
    ├── PostgreSQL
    ├── Redis
    ├── Media Worker
    ├── Image Worker
    ├── Capture/Deploy Workers
    └── small bounded cache/scratch

External Storage
├── ISO Library
├── Golden Images
├── Driver Packs
└── Build Output / Deployment Capsules

Heimdal PXE / Network OS Deployment
        ↓
Bare-Metal Endpoints
├── Physical PCs
├── Servers
└── Reference Machines
```

Important Windows-host detail:

Linux does not use Windows mapped drive letters such as:

```text
Z:\
```

Network storage must be exposed through UNC / SMB and mounted in Linux, for example:

```text
\\fileserver01\ISO
\\nas01\GoldenImages
\\fileserver01\Drivers
\\fileserver01\BareMetalOutput
```

Linux mount layout should follow:

```text
/srv/baremetal-adapter/storage/iso
/srv/baremetal-adapter/storage/golden-images
/srv/baremetal-adapter/storage/drivers
/srv/baremetal-adapter/storage/output
/srv/baremetal-adapter/scratch
```

Inside containers the common storage root should appear as:

```text
/storage
```

---

## 6. Temporary Mac VM vs. future Proxmox VM

### 6.1 Temporary Mac development VM

Because local Mac disk space is limited, use a smaller VM:

```text
Disk: 24 GB dynamically allocated/thin if possible
CPU: 2-4 vCPU
RAM: 4-6 GB
```

Do not store large ISOs or test images permanently inside this VM.

Use a Mac-shared folder or network share for media.

### 6.2 Future Proxmox production/development appliance

Recommended initial Proxmox VM:

```text
CPU: 4 vCPU
RAM: 8 GB
System disk: 40 GB
Firmware: UEFI / OVMF
Machine type: q35
Disk controller: VirtIO SCSI
NIC: VirtIO
Network: 1 GbE minimum; faster preferred
```

Later heavy image-processing phase:

```text
CPU: 8 vCPU
RAM: 16 GB
```

Optional later scratch disk:

```text
100-200 GB fast temporary disk
```

The scratch disk is not permanent storage and should support automatic cleanup.

---

## 7. Existing application stack

The current repository already contains the platform foundation.

### Frontend

```text
React
TypeScript
Vite
nginx
```

### Backend

```text
FastAPI
Python
SQLAlchemy
PostgreSQL
```

SQLite fallback may be used for isolated local/unit testing where appropriate, but PostgreSQL is the real appliance database.

### Platform services

```text
PostgreSQL 16
Redis 7
Docker Compose
Background worker process
```

### Existing logical services

The Compose architecture includes or reserves:

```text
postgres
redis
api
worker
web
conversion-worker   # optional/reserved
pxe                 # optional/reserved; disabled initially
```

Do not activate standalone PXE by default. The first integration target is Heimdal PXE.

---

## 8. Current repository capabilities

The current v0.1 foundation includes:

- React/TypeScript management UI;
- FastAPI REST API;
- PostgreSQL metadata store;
- Redis platform service;
- background worker;
- storage-location registration;
- external-first media model;
- browser upload endpoint;
- queued ISO analysis;
- job state/progress/logging;
- ISO inspection logic;
- basic media library;
- Stage-1 WinPE bridge source;
- UEFI proof-stage source;
- sample installer manifest;
- sample golden-image manifest;
- architecture and project documentation;
- functional standalone HTML mockup under `docs/mockups/`.

Current functional UI areas include:

```text
Dashboard
Media
Jobs
Storage
```

Scaffolded/future areas include:

```text
Build
Bare Metal
PXE
Administration
Golden Images
Driver Packs
```

The HTML functional mockup should be treated as a UX direction/reference, not as a replacement for the React application.

---

## 9. Existing repository structure

Current structure broadly includes:

```text
.env.example
docker-compose.yml
README.md
CODEX_START_HERE.md        # this document

backend/
  Dockerfile
  requirements.txt
  app/
    api/
    core/
    models/
    services/
    workers/

frontend/
  Dockerfile
  package.json
  vite.config.ts
  nginx.conf
  src/

scripts/
  bootstrap.sh
  mount-smb.sh

tools/
  iso_inspect.py

winpe-bridge/
  setup.c
  kernel32.def

uefi-stage/
  stage.c

examples/
  installer-iso.json
  golden-image.json

docs/
  ARCHITECTURE.md
  STORAGE.md
  PROJECT_DESCRIPTION.md
  architecture-overview.svg
  mockups/
    bare-metal-adapter-functional-mockup.html
```

Exact names may evolve, but preserve the architectural separation.

---

## 10. ISO inspection and adapter model

The platform should inspect input media and detect boot characteristics.

### Detection signals

At minimum:

```text
/EFI/BOOT/BOOTX64.EFI
    -> UEFI x64 fallback loader

/EFI/BOOT/BOOTAA64.EFI
    -> UEFI ARM64 fallback loader

/casper/vmlinuz
/casper/initrd
    -> Ubuntu/Casper style Linux installer

/boot/grub/grub.cfg
    -> GRUB

/isolinux/isolinux.cfg
    -> ISOLINUX

/sources/boot.wim
    -> Windows installer
```

Also detect:

- ISO9660;
- UDF where possible;
- El Torito boot catalog;
- architecture;
- BIOS/UEFI bootability;
- volume label;
- known bootloader structures;
- source file SHA-256;
- recommended adapter;
- warnings/compatibility limitations.

### Adapter hierarchy

Long-term adapter model:

```text
WindowsAdapter
LinuxCasperAdapter
GrubAdapter
IsolinuxAdapter
UefiChainloadAdapter
ElToritoAdapter
GenericIsoAdapter
```

### Compatibility strategies

1. **Native EFI chainload**
2. **Kernel + initrd boot**
3. **ISO passthrough / loopback** where technically supported

Adapter detection should produce a recommendation, but the UI/API should later support an advanced manual override.

---

## 11. Heimdal wrapper / deployment capsule design

The generated artifact must be compatible with the current Heimdal WinPE flow.

Conceptual generated capsule:

```text
capsule.iso
├── SETUP.EXE
├── STAGE.CMD
├── deployment.json
├── runtime/
└── original/
    └── source.iso
```

The original vendor ISO should be preserved byte-for-byte whenever practical.

Do not unnecessarily unpack/repack the entire vendor media when preservation is possible.

Suggested neutral volume label:

```text
BMA_<jobid>
```

or another neutral Bare-Metal Adapter label.

Do not reintroduce old internal project labels such as `HIA` into new code/artifacts.

---

## 12. WinPE bridge

The repository contains native Windows bridge source under:

```text
winpe-bridge/
```

Requirements:

- native x64 Windows executable;
- no .NET dependency;
- should run inside Heimdal WinPE;
- root file must be named `SETUP.EXE` in generated deployment media;
- should inspect/read deployment metadata;
- should stage the second-stage boot runtime;
- should configure a one-time UEFI boot handoff;
- should reboot only when the staging operation succeeds.

A laboratory Stage-1 bridge exists conceptually/prototypically, but new builds must use neutral Bare-Metal Adapter naming.

Do not blindly reuse old prebuilt binaries if they contain obsolete branding or legacy log labels. Prefer rebuilding from source.

---

## 13. UEFI second-stage handoff

Initial success path:

```text
Bare-metal target / disposable UEFI VM
        ↓
Heimdal PXE
        ↓
Heimdal WinPE
        ↓
SETUP.EXE from Bare-Metal Adapter capsule
        ↓
stage EFI/runtime payload
        ↓
create one-time UEFI boot entry / BootNext
        ↓
reboot
        ↓
Bare-Metal Adapter second-stage runtime starts
```

First proof environment:

```text
UEFI x64
Secure Boot OFF
Disposable VM
Disk 0: normal system disk
Optional Disk 1: small temporary/staging disk for lab testing
```

The first major technical milestone is not “install Ubuntu”.

The first major milestone is:

> Heimdal starts `SETUP.EXE`, the machine safely reboots once, and our second-stage boot environment starts.

Only after that proof is stable should the adapter launch a real Linux installer.

---

## 14. Installer-media boot path

After the handoff proof works, implement the first production-like Linux adapter.

Preferred first target:

```text
x86-64 UEFI Linux kernel/initrd based installer
```

Ubuntu/Casper is a reasonable first concrete implementation because its boot structure is easy to identify.

Flow:

```text
Heimdal WinPE
   ↓
SETUP.EXE
   ↓
one-time UEFI handoff
   ↓
second-stage boot environment
   ↓
GRUB or direct kernel boot
   ↓
vmlinuz
   ↓
initrd
   ↓
native installer environment
```

The original ISO may remain on external storage or be included inside the deployment capsule depending on the adapter strategy.

Do not claim generalized Linux support until multiple adapters have actually been validated.

---

## 15. Golden-image architecture

The platform is intended to support true bare-metal imaging in addition to installer media.

There are two primary payload types:

```text
Installer mode
Image mode
```

### 15.1 Golden-image capture

Conceptual flow:

```text
Reference PC
    ↓
prepare/generalize OS
    ↓
PXE boot capture runtime
    ↓
detect GPT/MBR/disk/partitions/filesystems
    ↓
image partitions/disks
    ↓
compress stream
    ↓
hash/verify
    ↓
write directly to external Golden Images storage
    ↓
create versioned manifest
```

### 15.2 Golden-image deployment

```text
Target machine
    ↓
Heimdal PXE / deployment boot
    ↓
imaging runtime
    ↓
load golden-image manifest
    ↓
partition target disk
    ↓
restore images
    ↓
restore EFI boot data
    ↓
resize filesystems if required
    ↓
verify hashes
    ↓
OS-specific post-deploy identity handling
    ↓
reboot into deployed OS
```

### 15.3 Imaging strategy

Principle:

> **If we understand the filesystem, optimize it. If we do not understand it, clone it.**

Modes:

1. filesystem-aware imaging;
2. exact partition/disk layout imaging;
3. raw sector-by-sector fallback for unsupported/proprietary filesystems.

Likely toolchain:

```text
Partclone
WIM tools
raw dd-like fallback
zstd
lz4
gzip/xz
GPT/MBR utilities
filesystem resize tools
```

---

## 16. OS identity handling

Golden images must not clone machine identity blindly.

### Windows

Before capture:

```text
Sysprep / generalize
```

After restore:

- specialize/OOBE;
- hostname;
- drivers;
- domain/Entra handling;
- machine identity regeneration;
- Heimdal Agent identity handling.

### Linux

Before capture:

- clean `/etc/machine-id` appropriately;
- remove/regenerate SSH host keys as needed;
- ensure cloud-init identity does not clone machine identity.

After restore:

- regenerate machine-id;
- regenerate SSH host keys;
- set hostname/network identity;
- grow filesystem if required.

---

## 17. Driver repository direction

Later feature:

```text
Driver Packs
├── manufacturer
├── model
├── PCI/Device IDs
├── OS/version metadata
└── driver files
```

Goal example:

> One corporate Windows 11 golden image can deploy across Dell, HP and Lenovo systems while hardware-specific drivers are selected separately.

Future capabilities:

- manufacturer/model matching;
- PCI ID matching;
- versioning;
- driver injection/staging;
- separate policies by operating system/version.

Do not implement this before the basic wrapper/handoff is working.

---

## 18. Data model direction

Long-term entities should approximately cover:

```text
media
media_versions
media_hashes
iso_analysis
boot_adapters

golden_images
image_versions
disk_layouts
image_partitions

driver_packs
driver_files
hardware_profiles

deployment_capsules
deployment_profiles

capture_jobs
build_jobs
deployment_jobs

machines
hardware_inventory

users
roles
audit_events
```

Current v0.1 models are intentionally smaller. Add tables incrementally as functional features require them.

Do not over-engineer the schema before workflows exist.

---

## 19. Web UI direction

Primary navigation direction:

```text
Dashboard

Media
  Installer ISOs
  Golden Images
  Disk Images
  Driver Packs

Build
  Wrap ISO
  Create Deployment Capsule
  Image Conversion

Bare Metal
  Capture
  Deploy
  Machines
  Hardware Profiles

PXE
  Heimdal Integration
  Standalone PXE (future / disabled initially)

Jobs

Administration
  Storage
  Networking
  Authentication
  Security
  Logs
```

### Media / ISO analysis UI

Display at least:

- filename;
- source storage;
- size;
- SHA-256;
- ISO9660/UDF;
- El Torito;
- architecture;
- UEFI/BIOS;
- OS/distribution if known;
- bootloader;
- installer type;
- kernel/initrd paths;
- adapter candidates;
- recommended strategy;
- compatibility warnings.

### Jobs UI

Statuses:

```text
queued
running
complete
failed
```

Display:

- progress;
- timestamps;
- log output;
- failure reason;
- retry capability later.

---

## 20. Browser upload behavior

Existing platform behavior should be preserved:

```text
POST /api/v1/media/upload
```

Uploads should be processed in chunks and written directly to the selected registered external storage location.

Do not retain a second persistent copy inside the VM.

Use safe path handling:

- prevent path traversal;
- avoid silent overwrites;
- enforce registered storage boundaries;
- validate free space where possible.

---

## 21. Security principles

Even though initial development is a lab prototype, architecture must support future hardening.

Prepare for:

- SHA-256 and potentially SHA-512 verification;
- immutable source-media hashes;
- signed deployment manifests later;
- EFI signature inspection;
- encrypted/sealed credentials for shares;
- TLS;
- RBAC;
- audit history;
- immutable job/event history where practical;
- Secure Boot support later.

Initial UEFI laboratory testing may use Secure Boot OFF.

Do not claim production Secure Boot support until it has actually been implemented and tested.

---

## 22. Operational tooling to add

The repository should evolve toward an appliance-like operator experience.

Target commands:

```text
sudo ./install.sh
sudo ./bma status
sudo ./bma update
sudo ./bma backup
sudo ./bma diagnostics
```

Suggested repo tooling:

```text
install.sh
bma
scripts/
  bootstrap.sh
  mount-smb.sh
  health-check.sh
  backup.sh
  update.sh
  diagnostics.sh
```

### install.sh goals

The installer should eventually:

1. detect supported Ubuntu version;
2. install required OS packages;
3. install/verify Docker Engine and Compose plugin;
4. create required directories;
5. create or initialize `.env` safely;
6. configure permissions;
7. prepare storage mount points;
8. build/start Compose services;
9. wait for health checks;
10. print appliance URL and status;
11. avoid destroying existing data on repeat runs.

The future Proxmox rebuild should require as few manual steps as possible.

---

## 23. Development workflow inside the VM

Recommended checkout location:

```bash
cd /opt
sudo git clone git@github.com:dantehavershem/Heimdal-Bare-Metal-Adapter.git
sudo chown -R $USER:$USER Heimdal-Bare-Metal-Adapter
cd Heimdal-Bare-Metal-Adapter
```

The VM itself must have GitHub authentication configured, preferably SSH keys.

Normal development loop:

```text
Codex edits repository
      ↓
git diff / review
      ↓
docker compose build
      ↓
docker compose up -d
      ↓
test API/UI
      ↓
commit
      ↓
push GitHub
```

Codex should work milestone-by-milestone.

Do not make broad speculative rewrites that break working platform pieces.

---

## 24. Required coding discipline for Codex

When modifying the repo:

1. Read the existing implementation before changing architecture.
2. Preserve working API endpoints unless intentionally versioning them.
3. Keep storage external-first.
4. Do not introduce large generated test media into Git.
5. Never commit credentials, `.env`, share passwords or private keys.
6. Keep scripts idempotent where possible.
7. Add clear logs for long-running operations.
8. Add health checks for services.
9. Validate paths rigorously before any destructive disk/image operation.
10. Mark destructive operations explicitly in the UI/API.
11. Prefer explicit state transitions for jobs.
12. Do not silently report a future/scaffolded feature as functional.
13. Keep old `HIA` naming out of the new project.
14. Update documentation when a milestone changes real behavior.
15. Commit coherent milestones rather than giant unrelated changes.

---

## 25. First development milestone on the VM

### Milestone 0 — Make the existing appliance cleanly installable and verifiable

Goal:

> A fresh Ubuntu VM can clone the repo, run the installer/bootstrap, start all base services, and pass health checks without manual repair.

Tasks:

1. Audit current `docker-compose.yml` and Dockerfiles.
2. Verify build contexts and dependencies.
3. Add/complete `install.sh`.
4. Add `scripts/health-check.sh`.
5. Add a small `bma` operator CLI wrapper with at least:
   - `status`
   - `logs`
   - `health`
   - `update` placeholder or safe implementation.
6. Ensure `.env.example` is sufficient for a clean deployment.
7. Confirm fresh database initialization.
8. Confirm API health endpoint.
9. Confirm Web UI is reachable.
10. Confirm worker is running.
11. Confirm external storage root exists and is visible in API + worker containers.
12. Add concise installation documentation.

Acceptance criteria:

```text
docker compose ps
```

shows all required base services healthy/running.

The UI loads in the browser.

The health endpoint returns success.

---

## 26. Second development milestone

### Milestone 1 — Real Media -> ISO Analysis workflow

Goal:

> Upload or select a real ISO on external storage and receive a stored analysis result through the UI.

Tasks:

1. Validate current browser-upload implementation.
2. Confirm chunked upload writes directly to selected external storage.
3. Calculate SHA-256.
4. Queue ISO analysis job.
5. Worker reads ISO from external storage.
6. Detect known boot structures.
7. Persist structured analysis result.
8. Display result in React UI.
9. Display job log and progress.
10. Handle failures cleanly.

Acceptance test examples:

- Windows ISO;
- Ubuntu ISO;
- known simple/legacy ISO.

Do not proceed to wrapper generation until this path is reliable.

---

## 27. Third development milestone

### Milestone 2 — Build -> Wrap ISO

Goal:

> Select an analyzed ISO and generate a Heimdal-compatible deployment capsule on external output storage.

Workflow:

```text
Select analyzed media
      ↓
Review detected adapter
      ↓
Choose output storage/path
      ↓
Queue build-wrapper job
      ↓
Generate deployment manifest
      ↓
Build capsule ISO
      ↓
SHA-256 output
      ↓
Persist build result
      ↓
Show result in UI
```

Required initial capsule contents:

```text
SETUP.EXE
STAGE.CMD
deployment.json
runtime/
original/source.iso   # when preserving original media is the selected strategy
```

Use `xorriso -as mkisofs` or equivalent if available in the backend image.

Build output must be written directly to external output storage.

Add progress/logging.

Do not claim that the resulting capsule fully boots arbitrary Linux installers until the second-stage adapter has been implemented.

---

## 28. Fourth development milestone

### Milestone 3 — WinPE -> one-time UEFI handoff proof

Goal:

> Heimdal PXE starts the generated root `SETUP.EXE`, which stages a second-stage EFI payload and causes exactly one controlled reboot into that payload.

Use a disposable UEFI VM.

Secure Boot OFF.

Do not perform destructive disk imaging yet.

Acceptance criterion:

```text
Heimdal PXE
 -> WinPE
 -> SETUP.EXE
 -> successful staged handoff
 -> reboot
 -> Bare-Metal Adapter EFI/runtime proof screen/log
```

After proof, normal boot order must remain intact.

---

## 29. Fifth development milestone

### Milestone 4 — First real Linux installer adapter

Recommended first adapter:

```text
LinuxCasperAdapter
```

Goal:

> A supported Ubuntu-style ISO is analyzed, wrapped, launched through Heimdal WinPE, handed off to the second-stage runtime, and enters the native Linux installer environment.

Keep the implementation explicit and adapter-specific.

Do not generalize prematurely.

---

## 30. Milestones after ISO wrapping

Once installer wrapping is proven:

### Milestone 5 — Golden-image data model and capture runtime

### Milestone 6 — Golden-image deployment runtime

### Milestone 7 — Windows and Linux identity regeneration

### Milestone 8 — Driver repository and matching

### Milestone 9 — Heimdal PXE publishing integration

### Milestone 10 — Authentication/RBAC/audit hardening

### Milestone 11 — Secure Boot strategy and signed runtime

### Milestone 12 — Optional standalone PXE mode

Do not work on these early milestones at the expense of the first functional wrap/handoff path.

---

## 31. Suggested first Codex prompt

After cloning the repo inside the VM, use this as the first implementation instruction:

```text
You are working in the Heimdal-Bare-Metal-Adapter repository.

Read CODEX_START_HERE.md, README.md, docs/ARCHITECTURE.md, docs/STORAGE.md, docker-compose.yml, the backend, frontend, scripts, winpe-bridge and uefi-stage directories before changing anything.

Your first milestone is Milestone 0 from CODEX_START_HERE.md: turn the current v0.1 repository into a clean, installable development appliance without changing the established architecture or UI direction.

Tasks:
- audit Docker Compose and both Dockerfiles;
- fix only verified issues;
- add a root install.sh for a fresh Ubuntu VM;
- add scripts/health-check.sh;
- add a small root `bma` operator CLI supporting at least status, health, logs and update;
- make the process idempotent and safe to rerun;
- keep large media external-first;
- do not activate standalone PXE;
- do not implement golden-image capture/deploy yet;
- do not redesign the frontend;
- do not introduce old HIA naming;
- do not commit credentials or generated media;
- update README/docs only where real behavior changes.

Before editing, summarize the current architecture and identify concrete issues you found. Then implement the milestone, run all available validation/tests, show git diff, and clearly state what passed and what remains incomplete.
```

---

## 32. Definition of success for the project

The project is successful when a clean appliance can eventually support this end-to-end flow:

```text
Administrator
   ↓
Bare-Metal Adapter Web UI
   ↓
Select/upload installer ISO or golden image
   ↓
Analyze / validate
   ↓
Build deployment capsule/profile
   ↓
Store output externally
   ↓
Publish/use with Heimdal PXE
   ↓
PXE boot target machine
   ↓
Heimdal WinPE executes SETUP.EXE
   ↓
one-time second-stage boot
   ↓
native installer or imaging runtime
   ↓
install/restore target system
   ↓
post-deploy identity handling
   ↓
normal reboot into deployed OS
```

The platform must remain small, self-hosted, reproducible from Git, and independent of storing large deployment payloads inside the appliance VM.

---

## 33. Immediate next action

On the temporary Mac VM:

1. install Ubuntu;
2. configure GitHub SSH authentication;
3. clone this repository;
4. open the repository in VS Code/Codex;
5. give Codex the prompt in Section 31;
6. complete Milestone 0;
7. commit/push the result;
8. then move to the first real Media -> ISO Analysis test.

The temporary VM is a development environment only. The repeatable installer and Git repository are the product assets that matter.
