# Latest handoff — unattended WinPE PXE test PASSED, 2026-09-06

## Current outcome

The user authorized continuing the isolated PXE/WinPE readiness work and requested
execution without routine confirmations. The diskless network boot and actual
Windows launcher contract now pass automatically; no guest keyboard input is
needed. The missing-image negative control also passes. Both guests have stopped
and their containers were removed. Appliance API/database/Redis are healthy and
worker is online. No test is currently running.

- Positive evidence: `artifacts/pxe-test/winpe-pxe-20260906T003352.579436Z/`,
  passed in 144.6 seconds. All three serial markers, DHCP, both TFTP bootstrap
  requests, and all eight complete HTTP transfers verified. Actual `SETUP.EXE`
  launched `STAGE.CMD` and propagated 37, checked by `RUN-TEST.CMD`.
- Negative evidence: `artifacts/pxe-test/winpe-pxe-20260906T003646.958113Z/`,
  passed in 17.0 seconds. Missing WIM returned 404; no WinPE markers.
- Four HTTP service unit tests and `git diff --check` passed.

## Implementation and reproduction

See `docs/PXE_TEST_LAB.md` for commands and evidence details. New files:
`tools/pxe-test/network_winpe.py`, `netboot_http.py`, `test_netboot_http.py`.
Use the existing three Compose files ending with `compose.winpe-modern.yml`,
entrypoint Python and script `network_winpe.py`. Add `--missing-wim --timeout 300`
for the negative control. Requires 5120 MiB available host RAM; guest uses 4096.

Environment remains QEMU 10.0.11, OVMF 2025.02, trixie lab image. wimboot 2.9.0
is stored in `artifacts/pxe-test/downloads/wimboot`; pinned URL and SHA-256 are
in the lab docs. ISO remains read-only at
`/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO`.

The guest has no DVD or disk: DHCP/TFTP loads iPXE and `autoexec.ipxe`, then HTTP
streams the WIM directly from the ISO extent. wimboot injects startup and launcher
files in RAM. QEMU guestfwd connects to a per-connection stdio HTTP program;
container network is disabled and no service is exposed on the host LAN.

Automatic COM1 preparation needs a bounded retry. Device restart completes
before the port is necessarily ready, and failed redirection can leave a stale
ERRORLEVEL. `(echo marker) > COM1 && goto serial_ready` checks the write itself.
Two earlier positive diagnostic runs reached the launcher but missed this first
marker; their failure reports and screenshots are preserved separately.

## Remaining scope

This milestone proves isolated PXE -> WinPE -> actual Windows launcher execution.
It does not establish Heimdal readiness as a whole. Next work is the generated
capsule and WinPE-to-UEFI/Ubuntu handoff; actual Heimdal server integration is a
separate later test once deployment access is available. Secure Boot and physical
hardware remain untested. Preserve all existing uncommitted work; no commit or
reset has been performed. Older notes below are historical.

---

# Historical DVD launcher pass — 2026-09-06

## Current outcome

The user authorized upgrading the isolated QEMU/firmware environment and retrying the Windows ISO. This is complete: actual Windows launcher execution **passed** in `artifacts/pxe-test/winpe-20260905T233732Z/`. Both serial markers are present and `report.json` records `passed: true`, both marker flags true, and 1170.5 seconds total elapsed (including interactive diagnosis).

The test guest stopped automatically with exit code 0 and its container was removed. The appliance health endpoint is OK; host RAM available returned to 6.4 GiB. No guest needs restarting to complete this milestone.

## Working environment and changes

- Separate image: `heimdal-bare-metal-adapter-pxe-test:trixie`, selected by new `compose.winpe-modern.yml` after the PXE and WinPE Compose files. Original Bookworm image preserved.
- QEMU 10.0.11 (Debian `1:10.0.11+ds-0+deb13u1`), OVMF `2025.02-8+deb13u1`.
- One guest CPU, 4096 MiB RAM, explicit `/usr/share/OVMF/OVMF_CODE_4M.fd` and `/usr/share/OVMF/OVMF_VARS_4M.fd` pair.
- The lab Dockerfile accepts `BASE_IMAGE` while retaining its Bookworm default. `winpe.py` accepts explicit firmware paths and records versions/hashes in `runtime.json`.
- `qmp.py` accepts `--keyboard-layout de` for the German Windows console; default `us` remains suitable for the EFI shell.
- ISO: `/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO`, AMD64 Windows PE/Setup 26100.7840. ISO remained read-only.
- Success did not require changing the launcher source, test scripts, or relaxing either serial-marker requirement.

## Reproduction details

See `docs/PXE_TEST_LAB.md` for the full build/run command and guest commands. The ISO initially fell through to the UEFI shell; boot `fs0:\efi\boot\bootx64.efi` from the observed mapping and accept the DVD prompt. Windows Setup became visible; Shift+F10 opened cmd. Capsule was C:.

The initial test showed both markers and `Bridge returned 37` on screen but COM1 writes failed. Windows had started serial device `ACPI\PNP0501\1` without assigning a `PortName`. Existing driver files were present; `drvload` returned 0x80070103. In the disposable guest, setting `PortName=COM1` under that device’s `Device Parameters` and restarting the device with `pnputil /restart-device` made COM1 available. Rerunning unchanged `RUN-TEST.CMD` then passed automatically. All evidence is retained; `test-19.png` shows initial visual success, `com1-ready.png` shows working COM1, and `serial.log` contains the final genuine guest markers.

## Validation and remaining scope

- Upgraded image built successfully; Compose configuration and `git diff --check` passed.
- Firmware selection and German QMP typing were exercised in the successful run.
- Verified final report, both serial markers, container cleanup, and appliance health.
- No commit/reset. Preserve all prior uncommitted work.
- Windows launcher contract is now verified. WinPE PXE loading, WinPE-to-UEFI handoff, capsule generation, Ubuntu boot, Secure Boot, and Heimdal server integration remain separate milestones.
- Combined newer QEMU and OVMF booted successfully; exact cause of older boot stalls remains unisolated. An external x86-64 host was not needed to finish this launcher test.

Older notes below are historical and their unresolved launcher status is superseded by the verified pass above.

---

# Historical standard Windows ISO attempts — 2026-09-06

The user supplied a new ISO after stopping Hiren’s. Two fresh attempts were made; both are now stopped. Do not automatically restart another identical run.

- New ISO: `/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO`. AMD64 EFI and WinPE verified by reading the media. WIM metadata: Windows PE/Setup 26100.7840. No publisher checksum verification for this ISO.
- Original configuration: `artifacts/pxe-test/winpe-20260905T230745Z/`, two vCPUs. Black screen, no visible Shift+F10 prompt; stopped for comparison at 686.2 seconds. Failure report and operator note retained.
- Single-vCPU comparison: `artifacts/pxe-test/winpe-20260905T231932Z/`. Spinner then black screen, no visible Shift+F10 prompt; stopped with failure report and operator note. No boot-media read errors in captured QMP counters.
- Neither run produced either launcher marker. Actual launcher contract is still unverified.
- `tools/pxe-test/winpe.py` now exposes `--guest-cpus` (positive integer, default 2). Single-vCPU run exercised it; syntax and `git diff --check` passed.
- Both runs required booting `fs0:\efi\boot\bootx64.efi` from the observed UEFI shell mapping, then pressing Return and Space for the DVD boot prompt.
- Media files previously at share root were moved by the user to `_torrents_done`; use the new paths. Do not modify shared media.
- Next investigation: emulator/firmware compatibility or an x86-64 hardware-virtualized test host. Single-vCPU boot did not fix the symptom. No confirmed root cause.
- Details and evidence: `docs/PXE_TEST_LAB.md`. Preserve all existing uncommitted work.

---

# Historical cancellation — 2026-09-06 01:01 Europe/Prague

The user explicitly requested **stop the test**. The `heimdal-winpe-test` container was stopped. Do not automatically restart it from the older resume instructions below.

- RAM upgrade verified: 7.7 GiB usable, 6.4 GiB initially available.
- Resumed run: `artifacts/pxe-test/winpe-20260905T223301Z/`.
- Hiren’s BootCD PE 1.0.8 ISO SHA-256 matched the publisher. ISO remained read-only.
- File loading and Windows boot spinner were seen, then a persistent black screen. Shift+F10, Win+R, and Ctrl+Shift+Esc produced no visible prompt. Neither success marker appeared. No completed harness report was produced; this run was cancelled, not passed or timed out.
- QEMU 7.2.22 stayed running with changing CPU snapshots. Host available RAM remained about 2.1 GiB and swap about 336–340 KiB during boot. No confirmed cause for the black screen.
- Screenshot, serial log, command, build metadata, resume observations, and QMP diagnostic snapshot are retained in that artifact directory.
- `winpe.py` now requires both stage and bridge markers for success. Verified empty output and either single marker reject success, both accept it; `git diff --check` passed. The running process predated the edit.
- User asked whether standard Windows installation media would work: yes, an x64 Windows ISO is suitable for this launcher contract test using Shift+F10 at Windows Setup, without installing Windows. At last check the share contained only Hiren’s and Ubuntu ISOs.
- See `docs/PXE_TEST_LAB.md` for updated evidence and reference links.

The older handoff is retained below as historical context; its automatic-resume instruction is superseded by the explicit stop request above.

---

# Session handoff — 2026-09-06 00:30 Europe/Prague

## Resume objective

Continue the Heimdal Bare-Metal Adapter work by completing the actual WinPE launcher contract test. The user plans to shut down Ubuntu cleanly and increase this VirtualBox VM from approximately 4 GiB to 8 GiB (8192 MB). After restart, verify memory and resume the test; no need to ask again whether to continue.

Repository: `/home/heimdal-bma/Heimdal-Bare-Metal-Adapter`.

## Current state

- The working tree contains extensive uncommitted implementation changes and new files. Preserve them; no commit or reset was performed in this session.
- Docker appliance services restarted automatically and were healthy: web, API, worker, PostgreSQL, Redis.
- GUI: http://127.0.0.1/ ; API health: http://127.0.0.1:8080/api/v1/health . Last response: status/database/redis OK, worker online, storage read-only.
- External media share `/media/sf_Downloads` was mounted as VirtualBox `vboxsf`. Containers read it at `/storage`. Verify the mount again after reboot before starting media work.
- `.env` contains credentials. Do not print or commit it.
- Architecture: ARM64 management VM; the x86-64 QEMU guest runs with TCG software emulation.

## Verified this session

- Backend: `docker compose exec -T api python -m unittest discover -s tests -v` — all 7 passed. Failure-recovery test intentionally logs a database exception. Deprecation/resource warnings remain.
- Frontend (from `frontend/`): `npm run build` — passed.
- Frontend: `npm run test:e2e -- --workers=1` — all 4 passed.
- `git diff --check` — passed.
- Added a startup RAM check and `--memory-mib` option to `tools/pxe-test/winpe.py`. Default guest RAM remains 4096 MiB. It requires guest RAM plus 1024 MiB reserve in Linux MemAvailable; swap does not count. Verified it rejected the current machine with approximately 2593 MiB available, before creating artifacts or launching QEMU. This is a startup check, not protection against subsequent competing allocations.
- Updated `docs/PXE_TEST_LAB.md` with memory requirements and interrupted-run status.

## Boot-test evidence

- Earlier completed PXE run: `artifacts/pxe-test/20260905T215934.520592Z/report.json`. Positive DHCP/TFTP/EFI execution and negative missing-payload cases passed, as recorded in `docs/PXE_TEST_LAB.md`.
- Interrupted WinPE run: `artifacts/pxe-test/winpe-20260905T221339Z/`.
- Its serial log shows OVMF starting the DVD boot entry. It contains no launcher success markers and there is no completed report. Do not claim Windows launcher execution passed.
- Existing screenshot: `artifacts/pxe-test/winpe-20260905T221339Z/screen.png`.
- The outer VM restarted at 00:25 after an unclean shutdown. Previous-boot samples at 00:20 showed approximately 500 MiB available RAM and 2.6 GiB swap used. Terminal/Firefox exited afterward. No recorded OOM kill or kernel panic was found. Memory pressure is a clue, not a confirmed crash cause; host VirtualBox logs were not obtained. User chose to resume work and add RAM.

## Resume steps

1. Read this file and `docs/PXE_TEST_LAB.md`; check any applicable AGENTS.md.
2. Run `free -h`, `findmnt -T /media/sf_Downloads`, `docker compose ps`, and the API health request. The default WinPE test needs at least 5120 MiB available RAM. Avoid concurrent heavy workloads.
3. Confirm `/media/sf_Downloads/HBCD_PE_x64.iso` exists. Do not modify the ISO or shared media.
4. Use the existing test image and launch the disposable test from the repository root:

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml run --rm \
  --name heimdal-winpe-test --entrypoint python3 \
  --volume /media/sf_Downloads/HBCD_PE_x64.iso:/winpe.iso:ro \
  pxe-test /src/tools/pxe-test/winpe.py
```

The source tree is bind-mounted read-only into the container, so the updated script does not require an image rebuild. Check image availability first. The override limits the container to 5 GiB memory and 6 GiB memory-plus-swap. The guest has no network or physical disk attached; its capsule data volume is disposable. The harness has a 30-minute timeout.

5. Record the new `/output/winpe-<timestamp>` printed by the harness. Use the local QMP helper to inspect the display and operate WinPE:

```bash
docker exec heimdal-winpe-test python3 /src/tools/pxe-test/qmp.py \
  /output/winpe-<timestamp>/qmp.sock \
  --screenshot /output/winpe-<timestamp>/screen.png
```

The screenshot maps to `artifacts/pxe-test/winpe-<timestamp>/screen.png` on the outer VM. Inspect it before deciding input. The helper supports `--key` (e.g. `meta_l-r`, `ret`) and `--type`. Once Windows PE is ready, open cmd, locate the attached capsule volume, and run `RUN-TEST.CMD`. Check memory periodically while the emulated guest boots.

6. Require both `BMA_WINPE_STAGE_REACHED` and `BMA_WINPE_BRIDGE_PASSED` in serial output and inspect the final report. The test checks the real SETUP.EXE launcher invoking adjacent STAGE.CMD and propagating exit code 37. Update this handoff and PXE notes with actual results.

## Scope still unfinished

WinPE network loading, WinPE-to-UEFI handoff, capsule generation, Ubuntu boot, Secure Boot, and Heimdal server integration are separate milestones. Successful DVD boot or direct EFI PXE boot proves none of those. Broader application gaps are recorded in `docs/RUNNING_STACK.md`; `docs/IMPLEMENTATION_AUDIT.md` is a historical audit predating many fixes.

## Tool environment

Sandbox commands currently fail at startup with `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`. Read/write/test commands in this session used the normal require_escalated approval mechanism. Do not disable AppArmor or change sandbox security settings as a workaround. This failure is separate from the VM crash investigation.
