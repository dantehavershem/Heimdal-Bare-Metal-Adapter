# Running the appliance stack

The local deployment uses Docker Compose with PostgreSQL 16, Redis 7, FastAPI, a separate analysis worker, and the Nginx/React GUI. No SQLite runtime is used.

On this machine the GUI is at http://127.0.0.1/ and the API at http://127.0.0.1:8080/. The earlier Vite preview at port 5173 can also use the same API. Database and Redis ports are not published. Web and API bind to loopback while authentication remains unfinished.

## Media storage

The local ignored `.env` selects `/media/sf_Downloads` as the host bind mount. It appears as `/storage` inside the API and worker, with read-only access. The registered location is **Downloads share**; the AMD64 ISO's relative path is `ubuntu-26.04.1-live-server-amd64.iso`.

The API refuses uploads in read-only mode before multipart parsing. Use **Add ISO → On mounted storage**. Analysis reads in place and stores only metadata, SHA-256, results, and job logs in PostgreSQL.

Before starting after a host restart, verify the VirtualBox share is mounted:

```bash
findmnt -T /media/sf_Downloads
docker compose up -d --build
docker compose ps
```

If your current terminal predates Docker group membership, start a new login session or run the Docker command using `sg docker -c 'docker compose ps'`.

## Configuration

The local `.env` contains a generated PostgreSQL password and must not be committed. For a new installation, copy `.env.example`, replace the database password placeholder with a generated secret, and select a real mounted external storage path. Compose derives the API/worker database URL from that password.

The application refuses registered paths outside the configured storage root. Compose refuses to create a missing host source directory. These checks do not establish that an existing host directory is still the intended external mount; mount verification before startup remains necessary.

Do not use `docker compose down -v` unless you intend to delete database and Redis volumes. Normal container restarts retain metadata.

## Current worker and schema behavior

PostgreSQL owns the durable job queue. Workers use row locks with `SKIP LOCKED` to claim ISO analysis jobs. Redis stores an expiring worker heartbeat, which the health endpoint reports alongside database and Redis connectivity. Redis is not a second job queue.

Analysis checkpoints renew a five-minute job lease. Abandoned jobs are marked failed after expiry and require resubmission; work is not silently replayed. A database error is rolled back before failure state is recorded. Sequential reanalysis updates the existing media record.

Startup serializes schema initialization with a PostgreSQL advisory lock. Existing 32-bit `media.size_bytes` columns are upgraded to BIGINT; fresh schemas create BIGINT directly. A broader migration framework will be needed as the data model expands.

## Verification

Run backend tests in the API container:

```bash
docker compose exec -T api python -m unittest discover -s tests -v
```

The PostgreSQL tests create and remove a uniquely named test schema, leaving application tables untouched. They cover large-file metadata and migration, concurrent claims, database failure recovery, stale jobs, ISO path/architecture detection, and storage path escapes.

Frontend checks remain available with `npm run test:e2e` in `frontend/`.

## Scope and remaining work

The AMD64 ISO has been analyzed through the live GUI/API/worker path. Detection and SHA-256 computation are not proof of successful booting or upstream image authenticity.

Authentication/RBAC, verified mount identity, general streaming uploads to writable external storage, full image-format coverage, and capsule generation/boot handoff remain unfinished. Keep the current loopback-only binding until the access-control work is complete. The historical audit remains in IMPLEMENTATION_AUDIT.md; this document records the subsequent runtime improvements.
