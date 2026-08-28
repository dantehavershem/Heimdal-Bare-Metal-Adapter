# Project Description

## Overview

Bare-Metal Adapter is a self-hosted platform for adapting bootable media to Heimdal Network OS Deployment and expanding that workflow into a broader bare-metal deployment capability.

The initial use case is straightforward: Heimdal PXE currently boots WinPE and expects a `setup.exe` workflow. That works naturally for Windows media but not for many Linux, appliance, or custom deployment scenarios. Bare-Metal Adapter introduces an intermediate control plane that can analyze source media, determine how it boots, select the appropriate adapter strategy, and generate a Heimdal-compatible deployment capsule.

## Problem the project solves

Many useful deployment targets are not packaged in a form that Heimdal's current PXE expectation can consume directly. At the same time, customers often want more than installer-driven operating-system deployment: they want reusable golden images, external media libraries, and an operational model that can scale without filling the management VM with dozens or hundreds of gigabytes of ISO and image content.

Bare-Metal Adapter addresses that by separating:

- the **control plane** (UI, API, metadata, jobs, orchestration), and
- the **data plane** (ISOs, golden images, driver packs, generated deployment capsules).

## Key goals

1. **Adapt bootable ISOs to Heimdal PXE**  
   Inspect source media, detect EFI/BIOS and common boot structures, and prepare a Heimdal-compatible wrapper or deployment capsule.

2. **Support external-first media handling**  
   Keep large media on SMB, NFS, S3-compatible or mounted storage rather than inside the VM.

3. **Enable true bare-metal workflows**  
   Evolve beyond installer media into golden-image capture and deployment for physical machines and servers.

4. **Provide a management-station deployment model**  
   Allow the solution to run self-hosted as a VM on a Windows management station while using existing network shares and storage.

5. **Provide a long-term extensible platform**  
   Keep the architecture modular enough to add driver matching, PXE publishing, image conversion, capture/deploy runtimes and future automation.

## Operating model

A typical deployment model is:

- a Windows management station hosts the Bare-Metal Adapter VM;
- the VM provides the web UI, API, metadata store and background workers;
- network shares or mounted storage provide ISO libraries, golden-image repositories, driver repositories and output locations;
- users interact through the browser and manage jobs centrally;
- workers read and write media directly against external storage;
- generated deployment capsules can later be uploaded or published into Heimdal PXE workflows.

## Current scope in v0.1

The current codebase provides the platform foundation and scaffolding needed to grow into the full product vision. It already includes:

- the React/TypeScript web UI foundation;
- the FastAPI backend and versioned API entry point;
- PostgreSQL and Redis platform services;
- a worker model for long-running media jobs;
- an ISO inspection engine with detection for common boot structures;
- storage abstractions aligned to the external-first model;
- example schemas for installer and golden-image deployment capsules;
- the early WinPE bridge and UEFI handoff proof-of-concept source.

## Strategic direction

The strategic direction is to turn a practical compatibility workaround into a reusable deployment platform:

- **short term**: analyze media, wrap supported ISOs, and generate Heimdal-compatible deployment capsules;
- **medium term**: add richer adapter logic, validation, publishing workflows and job orchestration;
- **long term**: support golden-image capture/deploy, driver matching, PXE publication, and broader bare-metal deployment scenarios.

## Architectural principle

The key architectural principle is simple:

> **Control plane in the VM. Large media stays on external storage.**

That principle keeps the appliance small, portable and operationally practical while still allowing it to orchestrate large deployment libraries and future bare-metal imaging workflows.
