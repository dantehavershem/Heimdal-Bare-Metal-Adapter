# Implementation audit — 2026-09-05

The repository implements an early storage and ISO-analysis foundation. It does not yet implement an end-to-end Heimdal deployment capsule workflow. The broad service layout follows the architecture, but several existing paths violate the external-first storage and operational reliability requirements.

Baseline: README.md, PROJECT_DESCRIPTION.md, docs/ARCHITECTURE.md, docs/STORAGE.md, docs/architecture-overview.svg, and docs/mockups/bare-metal-adapter-functional-mockup.html. This is a source audit with limited executable probes, not deployment or boot certification.

## Priority findings

### P1 — Browser ISO uploads are blocked by the supplied proxy configuration

`frontend/nginx.conf:1` does not override `client_max_body_size`. Nginx's default is 1 MiB, so ordinary installer ISOs exceed the browser-facing request limit and receive HTTP 413. The UI calls `r.json()` before handling errors, so an HTML proxy error can also leave the upload busy state stuck.

Configure an intentional upload limit and handle non-JSON/network failures with reliable busy-state cleanup. Validate through the web proxy, not just port 8080.

Reference: [Nginx core directives](https://nginx.org/en/docs/http/ngx_http_core_module.html#client_max_body_size).

### P1 — Uploads do not stream directly to external storage

`backend/app/api/routes.py:53` receives a parsed multipart `UploadFile`, then copies its temporary file to the registered location. Starlette uses a `SpooledTemporaryFile`; large uploads spill to temporary disk before this endpoint copies them. Nginx also defaults to buffering the request body. Neither temporary path is configured as bounded external storage. Raising the proxy body limit alone therefore leaves the documented VM disk constraint broken.

Use a genuinely streaming upload path with proxy request buffering disabled, or an explicitly designed direct-to-storage upload mechanism. Add failure cleanup, capacity enforcement, and atomic completion. The existing existence check followed by `open("wb")` also allows concurrent same-name requests to race, and failed writes leave partial files that block retries.

References: [Starlette uploaded files](https://www.starlette.io/requests/), [Nginx request buffering](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_request_buffering).

### P1 — Normal installer sizes overflow the PostgreSQL media column

`backend/app/models/entities.py:24` defines `size_bytes` as `Integer`. PostgreSQL integer tops out at 2,147,483,647 bytes; media at or above 2 GiB cannot be inserted. `backend/app/workers/runner.py:30` flushes this row after hashing and analysis, so the expensive work completes before persistence fails.

Use `BigInteger` and a database migration. Startup `create_all()` does not provide an upgrade path for an existing column.

Reference: [PostgreSQL numeric types](https://www.postgresql.org/docs/16/datatype-numeric.html).

### P1 — External storage is neither constrained nor verified

`backend/app/api/routes.py:36` accepts any absolute storage path. The subsequent containment checks are relative to that user-selected root, not the configured `/storage` boundary. `enabled` is ignored. Status checks directory existence rather than verifying the expected mount. Upload creates missing directories, so an absent share can result in writes to appliance-local storage. Compose also defaults to a local `./storage` directory.

The API has no authentication dependency, while the admin credentials in `.env.example` are unused. This combines unauthenticated storage registration with filesystem read/hash and file creation capabilities wherever container permissions permit. The backend image runs as root by default.

Constrain registered paths, verify external mount identity and writability, refuse unavailable storage, and enforce authentication before exposing the appliance. Explicitly distinguish an allowed laboratory local-storage mode. Revalidate the final upload target after symlink resolution as well as the directory.

### P1 — Worker ownership and failure recovery are missing

`backend/app/workers/runner.py:39` selects a queued job without an atomic claim. Multiple workers can process the same row. The conversion profile starts the same worker, and `--capability` is parsed but ignored. This makes the optional profile a second competing ISO consumer, not an image-conversion worker.

Running jobs have no lease or restart recovery. The exception handler at line 43 commits without first rolling back a failed database transaction; a flush failure can therefore prevent failure recording and terminate the worker, leaving a running job behind.

Implement atomic claims, capability filtering, rollback-safe failure recording, and recovery for abandoned work. Redis is provisioned but unused; decide explicitly whether PostgreSQL or Redis owns the queue.

### P2 — Media recommendations exceed the available evidence

`backend/app/services/iso_inspector.py:61` labels every Casper layout x86-64, even if the path set contains the ARM64 EFI loader. Windows with BOOT.WIM and BOOTX64.EFI selects generic UEFI chainload rather than the mockup's Native Windows route. A sufficiently large non-ISO returns an unknown result without an exception, and the worker still records it as a completed installer-ISO analysis.

The inspector detects path signatures in the primary ISO9660 directory tree. It does not parse boot-catalog entries, EFI binaries, UDF/Joliet/Rock Ridge names, or installer configuration sufficiently to establish actual boot compatibility. Directory sizes come from media without a total traversal/memory budget.

Treat signature matches as candidates, derive architecture from evidence, and distinguish unsupported media from validated deployment compatibility. Add a representative media corpus and bounded malformed-media handling before enabling builds.

### P2 — UI reports success and health without corresponding checks

`frontend/src/main.tsx:12` announces an analysis job was queued for any HTTP response. Storage registration also ignores HTTP failure. Network/JSON errors can leave upload or analysis controls busy. Failed refreshes retain stale data and a previously healthy indicator. `/health` always returns OK without testing database, worker, or storage readiness.

Check HTTP status, display actionable errors, clear busy state in finally blocks, and distinguish API reachability from dependency readiness.

## Architecture and mockup coverage

| Intended capability | Actual implementation |
| --- | --- |
| Small management appliance | Separate React web, FastAPI API, PostgreSQL, Redis, and worker services are declared in Compose; no appliance VM image or full provisioning workflow. |
| External media library | Mounted-path registration, upload copy, SHA-256, ISO analysis, and persisted media listing exist; external mount safety and large-file handling need fixes above. |
| Bounded scratch | Scratch volume and limit/free-space settings exist; the limit settings are never enforced. |
| Modular adapters | One inspector with conditional recommendation strings; no adapter interface, registry, build engine, or validator. |
| Source → analyze → adapter → build → validate | Analysis is implemented; Build renders a placeholder. No capsule build, artifact download, or validation API. |
| WinPE → UEFI handoff | C launcher executes adjacent STAGE.CMD, which is absent. EFI source prints a success message then halts. No build/packaging scripts or actual installer handoff. The message itself proves no integration. |
| Golden images and drivers | Example JSON and descriptive placeholders; no capture/deploy runtime, driver matching, or dedicated models/routes. |
| Capsule schemas | Two example JSON documents, not formal validated schemas or a manifest-processing pipeline. |
| Heimdal publishing | No integration client, connection test, publishing operation, or endpoint orchestration. |
| Standalone PXE | Opt-in container prints a reserved message and sleeps; appropriately disabled by default. |
| Jobs | Database polling, progress and text logs exist for ISO analysis only; no cancellation, retry, lease, or capability routing. |
| Storage backends | Mounted filesystem access plus a laboratory SMB mount script; no native SMB/NFS management or S3 client. |
| Administration | Placeholder UI; unused admin environment variables; AuditEvent table has no event writers; no RBAC. |

The frontend shares the broad sidebar/workspace/card arrangement but does not implement the mockup's detailed design. Navigation replaces Installer ISOs, Golden Images, Driver Packs, and Build Capsule with Media, Bare Metal, and Build, and adds Administration. The gradient hero, grouped navigation, blue action styling, recent-activity dashboard, upload modal/drop zone, analysis detail panel, compatibility display, build stepper, storage capacity/status cards, and PXE form are absent. Jobs use stacked cards rather than the mockup's table and selected log view. This comparison is based on HTML/CSS/JS and React source, not rendered screenshots.

Planned golden-image, driver, standalone PXE, and Secure Boot features are acknowledged as future work by the README; their absence is a scope gap, not a regression. However, wording that these subsystems already exist in the data model or that there is a functioning Stage-1 wrapper is stronger than the implementation supports.

## Validation and limits

- Parsed all 15 Python files successfully with `ast.parse`.
- Both shell scripts passed `bash -n`.
- Executed isolated inspector probes using a minimal descriptor fixture and injected directory path sets: ARM64 Casper was labeled x86-64; Windows x64 selected uefi-chainload. These validate decision logic, not real ISO directory parsing.
- Executed the inspector on a 128 KiB zero-filled file: returned iso9660=false and adapter=unknown without raising.
- Confirmed STAGE.CMD is absent from the repository.
- Docker, installed backend dependencies, and a TypeScript compiler were unavailable. No full stack startup, frontend build, PostgreSQL integration test, browser rendering, actual ISO corpus, or WinPE/UEFI boot test was performed. Dependency installability and C compilation remain unverified.
- Framework/proxy/database behavior was cross-checked against the primary documentation linked above. These findings were not reproduced in running containers.
- Application code was not changed as part of this audit.

## Suggested implementation order

1. Fix large-file persistence, authenticated storage boundaries, mount verification, and the complete browser upload path.
2. Make job claiming, failure handling, restart recovery, and health reporting reliable.
3. Improve ISO classification with explicit unsupported results and representative fixtures.
4. Implement one supported installer adapter end to end, including bridge build, manifest validation, capsule generation, and a repeatable target VM boot test.
5. Bring the UI into alignment with the mockup using real capabilities and status, then expand into the deliberately deferred imaging and publishing workflows.
