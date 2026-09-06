# Isolated PXE and bridge test lab

This reproduces the generic network-boot portion of the documented Heimdal workflow. It does not implement Heimdal's server, authentication, image-selection protocol, or deployment integration.

Heimdal describes DHCP/TFTP boot into WinPE, followed by image selection and Windows setup. The lab separates that into independently verifiable stages so reaching an EFI payload cannot be mistaken for a working WinPE-to-UEFI handoff.

## Run the available test

From the repository root:

```bash
mkdir -p artifacts/pxe-test
docker compose -f compose.pxe-test.yml build
docker compose -f compose.pxe-test.yml run --rm pxe-test
```

The separate Compose project runs QEMU's x86-64 software emulation inside a native container. It therefore works on this ARM64 management VM without nested x86 virtualization. It does not change the appliance stack.

The container has no network connection. QEMU supplies DHCP and read-only TFTP within its own user-mode virtual network, with restricted networking. No host network bridge, LAN DHCP service, physical disk, Ubuntu ISO, or shared Downloads folder is attached to this test.

## What is exercised

1. Cross-compile the actual `winpe-bridge/setup.c` into an AMD64 Windows `SETUP.EXE`; verify its PE machine and subsystem fields. This is compilation, not Windows execution.
2. Cross-compile `uefi-stage/stage.c` into an AMD64 EFI application with test-only telemetry.
3. Start a fresh QEMU guest with OVMF firmware and network boot priority.
4. Observe DHCP and the TFTP request for `probe.efi` in a packet capture.
5. Require the executed guest payload's `BMA_PXE_UEFI_REACHED` marker and the expected emulator exit code. Merely finding the file or seeing a download is insufficient.
6. Start a second fresh guest advertising a nonexistent `missing.efi`. Require a matching TFTP request and error, with no execution marker. The bounded timeout ends the unsuccessful boot attempt.

The regular UEFI proof payload no longer prints a claim that the Heimdal/WinPE handoff works. Its message says only that the proof payload was reached. Test telemetry is compiled only with `PXE_TEST`.

## Observed results

Both cases passed in run `20260905T215934.520592Z`:

- Positive: 6 DHCP packets, `probe.efi` requested over TFTP, payload marker received, QEMU exit code 33.
- Negative: `missing.efi` requested, 2 TFTP errors, no payload marker; test stopped after the 45-second bound.

The output directory contains `report.json`, compiled artifacts, exact QEMU commands, serial/debug logs, and `network.pcap` for each case. Generated files are ignored by Git. Every run creates a new timestamped directory; previous results are retained.

## Actual WinPE launcher test

An AMD64 WinPE ISO is needed to execute the Windows side. It can be placed in `/media/sf_Downloads` alongside the installer ISO. Do not confuse a successful UEFI network boot with execution of Windows code.

The harness already generates a small non-destructive capsule:

- `SETUP.EXE`: the repository's native launcher.
- `STAGE.CMD`: emits `BMA_WINPE_STAGE_REACHED` and returns exit code 37.
- `RUN-TEST.CMD`: invokes the launcher and requires that exact exit code; success emits `BMA_WINPE_BRIDGE_PASSED`.

Once WinPE is available, boot it in a disposable guest and expose these three files as a separate virtual data volume. Run `RUN-TEST.CMD` from that volume. Both markers are also sent to COM1 for capture. No disk formatting, partitioning, installation, or reboot handoff is performed by these scripts.

This validates the launcher contract. Testing WinPE itself through network boot additionally requires WinPE boot resources and a suitable network loader (for example iPXE/wimboot). The subsequent capsule-generation, one-time UEFI handoff, Ubuntu boot, Secure Boot, and real Heimdal integration tests remain separate milestones.

## References

- [Heimdal Network OS Deployment workflow](https://support.heimdalsecurity.com/hc/en-us/articles/15766632727197-Network-OS-Deployment-PXE)
- [QEMU user networking and TFTP boot](https://www.qemu.org/docs/master/system/invocation.html)
- [iPXE network booting Windows PE](https://ipxe.org/howto/winpe)

## Boot a supplied WinPE ISO

The optional memory override allocates a 4 GiB guest within a 5 GiB container memory limit. The harness requires at least 5 GiB of available outer-VM RAM before starting (4 GiB guest plus a 1 GiB reserve); swap does not count. This is a startup check, not a guarantee against later memory pressure. The management VM was increased from 3.8 GiB to 7.7 GiB usable RAM on 2026-09-06; the resumed run started with 6.4 GiB available. Smaller machines must increase RAM or run the lab elsewhere. On an ARM64 host this uses software emulation and may be slow. The generated virtual FAT disk is disposable and writable; the supplied ISO remains read-only. No physical disk or network interface is attached.

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml run --rm \
  --name heimdal-winpe-test --entrypoint python3 \
  --volume /media/sf_Downloads/HBCD_PE_x64.iso:/winpe.iso:ro \
  pxe-test /src/tools/pxe-test/winpe.py
```

The command prints the guest artifact directory under `/output/winpe-<timestamp>`. The guest can be inspected using its local QMP socket; replace the timestamp below with that directory:

```bash
docker exec heimdal-winpe-test python3 /src/tools/pxe-test/qmp.py \
  /output/winpe-<timestamp>/qmp.sock \
  --screenshot /output/winpe-<timestamp>/screen.png
```

The screenshot is available on the host under `artifacts/pxe-test/winpe-<timestamp>/screen.png`. The same helper accepts `--key` (QEMU key names, such as `meta_l-r` or `ret`) and `--type` to operate the guest console. Once WinPE is ready, use its Run dialog to execute `cmd`, then locate and run `RUN-TEST.CMD` on the attached virtual volume.

`winpe.py` monitors the guest serial port for the test result and stops QEMU after success or a 30-minute timeout. The resulting `report.json` records which execution stages actually passed. Booting the ISO through a virtual CD drive tests the WinPE launcher contract; it does not test WinPE network loading.

## Interrupted run — 2026-09-06

The run in `winpe-20260905T221339Z` ended with the outer VM shutdown. Its serial log shows OVMF starting the DVD boot entry, but contains neither launcher success marker and no completed report. WinPE launcher execution remains unverified. The previously completed PXE positive/negative results are retained. A memory preflight was added to reject the former low-memory configuration before compilation or QEMU startup.

## Resumed run — 2026-09-06 (cancelled by user)

Run `winpe-20260905T223301Z` started after the RAM increase with a 4096 MiB guest and a 5 GiB container limit. The share and ISO were present and the appliance health endpoint reported OK. The ISO identifies itself as Hiren’s BootCD PE 1.0.8. Its SHA-256 is `8c4c670c9c84d6c4b5a9c32e0aa5a55d8c23de851d259207d54679ea774c2498`, matching the [publisher’s checksum](https://www.hirensbootcd.org/download/).

File loading and the Windows boot spinner were observed, followed by a persistent black display. Shift+F10, Win+R, and Ctrl+Shift+Esc produced no visible prompt. QEMU remained running, with changing CPU register snapshots and no QEMU log error. Host available RAM remained about 2.1 GiB, swap about 336–340 KiB, and container memory about 4.3 GiB during these observations. Neither launcher marker was observed. The user requested stopping the test before its timeout; the container was stopped and removed. No completed harness report was produced. The launcher contract remains unverified. Diagnostics are stored beside the serial log and screenshot.

The [Hiren’s FAQ](https://www.hirensbootcd.org/faq/) documents slow DVD boots. [QEMU issue 2235](https://gitlab.com/qemu-project/qemu/-/issues/2235) reports similar boot symptoms on a different host and accelerator. These are diagnostic leads, not proof of the cause here.

The harness success condition now requires both `BMA_WINPE_STAGE_REACHED` and `BMA_WINPE_BRIDGE_PASSED`. Empty output and either marker alone were checked to reject success; both together were checked to accept it. This change was made after the resumed process started, so this run still requires explicit inspection of both markers.

## Standard Windows ISO comparison — 2026-09-06

Media: `/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO` (7,368,480,768 bytes). Read-only ISO inspection found El Torito boot metadata, an AMD64 EFI loader (PE machine `0x8664`), and `sources/boot.wim` (663,493,758 bytes). WIM metadata identifies both Windows PE and Windows Setup as AMD64 build **26100.7840**. No publisher checksum was verified for this ISO.

- `winpe-20260905T230745Z`: original two-vCPU configuration. Stopped through QMP after 686.2 seconds for a controlled comparison; `report.json` records `passed: false`. The display stayed black after boot, and Shift+F10 produced no visible prompt.
- `winpe-20260905T231932Z`: same configuration with `--guest-cpus 1`. Windows spinner appeared, followed by a persistent black display; Shift+F10 again produced no visible prompt. Stopped through QMP, with a completed failure report and operator note. The disk counters reported no read errors. This comparison did not resolve the symptom.

Both attempts initially fell through to the UEFI shell after the DVD prompt. Boot was started from the observed `FS0:` mapping using `fs0:\efi\boot\bootx64.efi`, Return, then Space to accept DVD boot. Neither attempt emitted either launcher marker. Windows launcher execution remains unverified. Both guests are stopped. The shared ISO was not modified.

The harness now accepts positive `--guest-cpus` values (default remains 2) so CPU-count comparisons are reproducible. Its syntax and whitespace checks passed; the one-CPU invocation was exercised in the comparison above. The next useful investigation is emulator/firmware compatibility, ideally comparing a newer isolated QEMU image or an x86-64 host with hardware virtualization. No root cause has been established, and the one-vCPU result is not a fix.

## Upgraded isolated test environment

`compose.winpe-modern.yml` selects a separate `heimdal-bare-metal-adapter-pxe-test:trixie` image, built from Debian 13. The original Bookworm image remains available. The upgraded image installed QEMU **10.0.11** and OVMF **2025.02-8+deb13u1**. Debian 13 uses the paired `OVMF_CODE_4M.fd` and `OVMF_VARS_4M.fd` files; the harness accepts explicit firmware paths and records their SHA-256 values alongside installed versions in each run’s `runtime.json`.

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.winpe-modern.yml build pxe-test
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.winpe-modern.yml run --rm --name heimdal-winpe-test \
  --entrypoint python3 \
  --volume /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO:/winpe.iso:ro \
  pxe-test /src/tools/pxe-test/winpe.py --guest-cpus 1 --memory-mib 4096 \
  --firmware-code /usr/share/OVMF/OVMF_CODE_4M.fd \
  --firmware-vars /usr/share/OVMF/OVMF_VARS_4M.fd
```

The container retains network isolation, a read-only root filesystem, read-only source and ISO mounts, and the existing 5 GiB memory / 6 GiB memory-plus-swap limits. This is a combined emulator/firmware comparison; changing both does not isolate which component causes any difference.

### Verified launcher result

Run `winpe-20260905T233732Z` **passed**. Windows 11 Setup became visible with the upgraded environment. The actual capsule launcher invoked adjacent `STAGE.CMD`, which returned 37; `RUN-TEST.CMD` checked that exit code. Both `BMA_WINPE_STAGE_REACHED` and `BMA_WINPE_BRIDGE_PASSED` were captured in `serial.log`, and the harness wrote `report.json` with `passed: true`, both marker flags true, and elapsed time 1170.5 seconds. This elapsed time includes manual boot interaction and serial-port diagnosis, not just boot time.

The test container exited with code 0 and was removed automatically. The appliance health endpoint remained OK afterward, with 6.4 GiB host RAM available. The original ISO and appliance services were not modified.

Evidence in `artifacts/pxe-test/winpe-20260905T233732Z/`:

- `report.json`, `serial.log`: automated pass and both execution markers.
- `runtime.json`, `command.json`, `build.json`: emulator/firmware versions and hashes, exact guest command, and compiled artifact hashes.
- `screen.png`: Windows Setup; `before-test.png`: the actual capsule and command; `test-19.png`: initial on-screen markers and `Bridge returned 37` before COM1 was prepared.
- `port-name.png`, `com1-ready.png`: missing port name and working COM1 after guest-only preparation.

The combined newer QEMU/OVMF environment booted successfully where the earlier attempts had stalled; this does not establish which component caused the difference. The result validates the Windows launcher contract only. WinPE PXE loading, WinPE-to-UEFI handoff, capsule generation, Ubuntu boot, Secure Boot, and Heimdal integration remain separate milestones.

### German console input and serial preparation

The QMP helper now accepts `--keyboard-layout de`. Its default remains `us` for the UEFI shell. In this ISO, `wpeutil setkeyboardlayout 0409:00000409` reported success but the already-open console retained its German mapping. Use `--keyboard-layout de` when typing commands into that console; the option describes the guest layout and does not change it.

At the Windows Setup screen, press Shift+F10. In this run, `dir c:` identified the disposable `QEMU VVFAT` capsule volume. Running the test initially displayed both markers and exit code 37, but COM1 writes failed. The following diagnostics identified a started serial device with no `PortName` assigned:

```bat
mode com1
pnputil /enum-devices /class Ports
reg query "HKLM\SYSTEM\CurrentControlSet\Enum\ACPI\PNP0501\1\Device Parameters"
reg query HKLM\HARDWARE\DEVICEMAP\SERIALCOMM
```

The observed serial device instance was `ACPI\PNP0501\1`; use the actual instance reported by the guest when reproducing elsewhere. Its existing `msports.inf` and `serial.sys` were present. `drvload x:\windows\inf\msports.inf` returned `0x80070103` and did not resolve the missing name. These commands, executed **inside the disposable WinPE guest**, made COM1 available:

```bat
reg add "HKLM\SYSTEM\CurrentControlSet\Enum\ACPI\PNP0501\1\Device Parameters" /v PortName /t REG_SZ /d COM1 /f
pnputil /restart-device "ACPI\PNP0501\1"
mode com1
c:
run-test.cmd
```

The unchanged test then emitted both markers through COM1 and the harness completed successfully. No serial markers were synthesized by the host and the success condition was not relaxed.

Example QMP command entry (send Return separately):

```bash
docker exec heimdal-winpe-test python3 /src/tools/pxe-test/qmp.py \
  /output/winpe-<timestamp>/qmp.sock --keyboard-layout de --type 'run-test.cmd'
docker exec heimdal-winpe-test python3 /src/tools/pxe-test/qmp.py \
  /output/winpe-<timestamp>/qmp.sock --key ret
```


## Diskless WinPE network test

`tools/pxe-test/network_winpe.py` boots a guest with no DVD or disk. UEFI obtains
`ipxe.efi` through QEMU's isolated DHCP/TFTP service; iPXE loads `autoexec.ipxe`
from TFTP and chains to the HTTP script. The HTTP service streams `sources/boot.wim`
directly from its bounded extent in the read-only ISO, without copying the WIM.
[wimboot](https://ipxe.org/wimboot) injects the launcher, test scripts, and
`winpeshl.ini` into the guest RAM image. This follows the official
[iPXE WinPE flow](https://ipxe.org/howto/winpe) and
[autoexec chainloading support](https://ipxe.org/howto/chainloading).

The container has `network_mode: none`; QEMU has restricted user networking.
HTTP runs as a per-connection stdio program through `guestfwd`, with an exact
resource allowlist. There is no HTTP listener or DHCP service on the host LAN.
The packet capture retains at most 512 bytes per packet. `http.jsonl` separately
records full response byte counts and SHA-256 digests of bytes actually sent.

Obtain the pinned upstream bootloader once (the ISO and lab image are also required):

```bash
mkdir -p artifacts/pxe-test/downloads
curl --fail --location https://github.com/ipxe/wimboot/releases/download/v2.9.0/wimboot \
  --output artifacts/pxe-test/downloads/wimboot
echo '5f067ccdc4d084d5bf77b6c853bd0f8402dfc2b4cd1b103d358993ae97fae8e3  artifacts/pxe-test/downloads/wimboot' | sha256sum --check

docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.winpe-modern.yml run --rm --name heimdal-winpe-pxe-test \
  --entrypoint python3 \
  --volume /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO:/winpe.iso:ro \
  pxe-test /src/tools/pxe-test/network_winpe.py
```

For the negative control, use the same command with `--missing-wim --timeout 300`
appended. Run cases sequentially: each guest reserves 4096 MiB and requires at
least 5120 MiB available host RAM. The default positive timeout is 1800 seconds.

A positive result requires DHCP, TFTP requests for both bootstrap files, all eight
complete HTTP resource transfers, and all three guest serial markers. The actual
`SETUP.EXE` must execute adjacent `STAGE.CMD`, and `RUN-TEST.CMD` must verify its
exit code of 37. The missing-WIM control requires a completed 404, complete
transfers of the other resources, and no WinPE execution markers.

The guest startup script prepares the observed QEMU serial device and retries
its first marker write for a bounded period before launching the test. Device
restart is asynchronous: `mode COM1` can report an unavailable device without
setting a failure exit code. The retry uses `(echo marker) > COM1 && goto serial_ready` so it branches on
the redirection result itself; a subsequent `if errorlevel` can retain a stale
success code after a failed redirection.
This device instance is specific to this lab; it is not Heimdal deployment logic.
The upstream WIM and ISO remain unchanged.

HTTP service checks:

```bash
python3 -m unittest discover -s tools/pxe-test -p 'test_netboot_http.py' -v
```

These cover bounded ISO extent delivery, missing/traversal paths, HEAD requests,
and rejection of truncated transfers as completed downloads.


### Verified network results — 2026-09-06

- Positive: `artifacts/pxe-test/winpe-pxe-20260906T003352.579436Z/`,
  `passed: true`, 144.6 seconds, no guest keyboard interaction. DHCP (14 packets),
  TFTP requests for `ipxe.efi` and `autoexec.ipxe`, all eight HTTP downloads,
  and all three genuine guest markers were verified. `SETUP.EXE` invoked
  `STAGE.CMD` and propagated exit code 37 as checked by `RUN-TEST.CMD`.
- Negative: `artifacts/pxe-test/winpe-pxe-20260906T003646.958113Z/`,
  `passed: true`, 17.0 seconds. Same bootstrap and seven complete resources;
  `/missing.wim` returned 404 and no WinPE execution markers appeared.
- Earlier negative run `winpe-pxe-20260906T002027.118744Z` also passed.
  Diagnostic positive runs `winpe-pxe-20260906T002309.057855Z` and
  `winpe-pxe-20260906T002806.693590Z` reached the launcher but missed the initial
  network marker because COM1 was not ready. They were stopped, not counted as
  passes. The initial bootstrap-loop run is also retained separately.
- WIM delivered: 663493758 bytes; response SHA-256
  `ff75eac08e6589982ff164df01f74965a780e246cafdb7108f1671ca23b7938a`.
- Both final containers exited with code 0 and were automatically removed.
  Appliance health remained OK; four HTTP service tests passed.

Each run contains `report.json`, `serial.log`, `http.jsonl`, `network.pcap`,
`runtime.json`, `command.json`, and the injected payload. Reports must be read
with their `case`: the missing-WIM case tests failure handling, not launcher
execution. Runtime metadata records firmware, iPXE, wimboot, and compiled artifact
hashes. Captures are intentionally truncated per packet; the HTTP log records
whole-response digests, not a publisher authenticity verification of the ISO.

This proves the isolated UEFI PXE -> iPXE/HTTP -> WinPE -> actual launcher path.
It does not yet prove generated deployment capsules, WinPE-to-UEFI handoff,
Ubuntu boot, Secure Boot, physical hardware, or integration with Heimdal's server.
