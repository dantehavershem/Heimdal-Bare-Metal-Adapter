# Management GUI

The React interface follows the functional mockup in `../docs/mockups/` and uses the existing `/api/v1` endpoints. It includes Dashboard, Installer ISOs, Golden Images, Driver Packs, Build Capsule, Jobs, PXE Integration, and Storage.

## Run locally

```bash
npm ci
npm run dev -- --host 127.0.0.1
```

Open the URL printed by Vite. The development server proxies `/api` to `http://localhost:8080`. Without the API, the interface remains navigable and displays unavailable data. It does not substitute demo records.

The Docker frontend build uses `npm ci` and the committed lockfile. Fonts are local system fonts; no external font request is required.

## Available workflows

- Register a mounted storage path and display filesystem availability/capacity.
- Submit an existing ISO for analysis or upload and then queue analysis.
- Search the media library and inspect detected architecture, candidate adapter, paths, and checksum.
- Follow jobs and view their logs.

Build, capture/deploy, driver management, and PXE publishing are visibly unavailable until their backend engines exist. Adapter suggestions are not presented as validated boot compatibility. Storage path availability does not certify an external mount.

The backend limitations in `../docs/IMPLEMENTATION_AUDIT.md` still apply, including large-file persistence and upload buffering/size limits. The GUI handles failed requests but does not resolve these backend issues.

## Verify

```bash
npm run build
npx playwright install chromium
npm run test:e2e
```

Browser tests use controlled API responses to exercise navigation, media inspection, job submission and rejection, HTML upload errors, connection loss, and mobile overflow. Screenshots are written under the ignored `test-results/` directory. These are frontend checks, not live deployment or boot tests.
