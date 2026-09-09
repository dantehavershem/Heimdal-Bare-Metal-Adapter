# Windows image application lab

This isolated lab applies installation-media WIM index 1 to a new virtual disk
and verifies installed Windows during specialization. It is not a production
capsule builder, customer golden-image validation, or a Heimdal integration test.

## Latest result

**Guest assertions passed:** `winpe-pxe-20260909T123144.006496Z`, 5903.1 seconds
(98 minutes 23 seconds), 9 September 2026. PXE DHCP/TFTP and all eight HTTP
transfers, DISM application with integrity checking, boot files, recovery
registration, one guest-requested reboot and the unique installed-Windows marker
all passed. No guest keyboard input, manual Windows command or setup-state bypass.

The source was Windows 11 Enterprise LTSC 2024, AMD64, de-DE, build 26100.7840,
index 1 in CCSA_X64FRE_DE-DE_DV9.ISO. The guest checks SystemDrive C: and absence
of the WinPE MiniNT registry key before emitting its unique identity and marker.
This confirms installed Windows execution during specialize. OOBE completion,
a desktop session, WinRE boot, customer golden images, Secure Boot, physical
hardware and actual Heimdal deployment remain untested.

The outer command session returned 130 without its final console output.
Persisted report.json says passed=true; a separate successful audit re-evaluated
raw serial, HTTP, PCAP and QMP evidence (evidence-audit.json). Offline SetupUGC
logs independently show FIRSTBOOT.CMD invoked during specialize at 14:09:49;
FIRSTBOOT.LOG records its start and successful COM1 restart. QEMU logged normal
SIGTERM from the harness after marker detection. The guest pass is supported;
a clean outer runner exit was not observed and should not be claimed.

## Reproduce

Source ISO stays read-only. Create a dedicated external directory with at least
40 GiB free. The helper creates a fresh per-run directory and 64 GiB QCOW2 disk,
refusing reuse. Never attach a physical target disk. The guest sees only that
writable disk and two read-only CDs (source and generated lab capsule).
Restricted QEMU user networking provides the private PXE/HTTP test services;
it does not expose the guest to the host LAN or internet.

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.windows-apply.yml build pxe-test
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.windows-apply.yml run --rm --name heimdal-windows-apply-test \
  --entrypoint python3 \
  --volume /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO:/winpe.iso:ro \
  --volume /media/sf_Downloads/Heimdal-BMA-Lab:/disks \
  pxe-test /src/tools/pxe-test/network_winpe.py --apply-windows /disks --timeout 10800
```

Allow 6 GiB available host memory. The Windows override limits the container to
6 GiB RAM and 7 GiB including swap. Guest RAM is 4 GiB, with two cores in one
socket. The ARM64 host emulates x64 through TCG; this is not a performance benchmark.
Source code is mounted read-only, so Python/script changes require no image rebuild.

## Application and acceptance

The actual capsule SETUP.EXE invokes its adjacent STAGE.CMD:

1. Locate install.wim and verify its Windows-reported 64-bit size is
   6,509,992,649 bytes. Read index 1 metadata with DISM before disk changes.
   Windows reads the DVD filesystem directly, avoiding the current ISO9660
   walker's wrapped file length and a full WIM copy onto the appliance.
2. Partition the sole disposable disk as GPT: 260 MiB FAT32 EFI, 16 MiB MSR,
   Windows NTFS, and 2048 MiB recovery.
3. Apply index 1 with DISM /CheckIntegrity. Scratch and apply.log are on the
   virtual disk. Emit the application marker only on successful exit.
4. Run BCDBoot, confirm BCD exists, copy winre.wim and register recovery with
   REAgentC. Each operation must succeed before its marker is emitted.
5. Install the lab answer file and FIRSTBOOT.CMD, then reboot. The script runs
   during installed Windows specialize, verifies C: and absence of MiniNT,
   logs invocation/output to C:\BMA-LAB\FIRSTBOOT.LOG, initializes COM1, and
   emits a unique run identity plus the first-boot completion marker.

Success requires complete DHCP/TFTP and HTTP evidence, all four Windows markers,
the exact run identity and at least one guest-requested QMP RESET. Windows marker
matching requires complete lines; the identity alone is not the completion marker.
The standard exit-37 smoke-test stage/bridge markers are not expected in this case.
The harness stops after its marker: it does not wait for OOBE or graceful Windows
shutdown. A retained disk may therefore still be mid-specialization.

## Diagnosis of the earlier timeout

Original run `winpe-pxe-20260909T095102.307725Z` timed out after 7200.6 seconds.
WIM application, boot and recovery passed, but the first-boot marker was absent.
Offline logs showed AppXSVC timeout 0x800705b4 during AppxSysprepSpecializeOnline,
plus service/DCOM timeouts and one guest disk retry. QEMU's zero failed I/O counters
and empty setuperr.log files did not rule out those guest-level problems.
The script and answer file were present, with no recorded invocation.

An isolated overlay resume, `windows-resume-20260909T122741.841261Z`, reached the
unexpected-restart installation error. It was stopped after 181.2 seconds without
bypassing setup state. The original disk remained read-only. Its error screenshot
and extracted logs are retained separately.

The Windows case had inherited one vCPU from the WinPE smoke test. The fresh run
used two cores, more container memory headroom, a longer overall limit and a local
verification log. These changes were tested together; no single-cause claim is
made. The fresh run successfully preregistered packages (0x0), completed AppX
specialization at 14:00:09, and invoked the verification script at 14:09:49.

## Retained evidence and disk chain

Artifacts are under `artifacts/pxe-test/<run>/`: report.json, serial.log,
qmp-events.json, command.json, windows-apply.json and network evidence.
Three live QMP external snapshots allowed inspection of frozen backing files
without restarting Windows. They were crash-consistent disk snapshots, not VSS
backups. Recorded AppX server events grew from 83 to 447 to 970 with no error-level
entries in those snapshots. All raw extracted files have SHA256 manifests.

For the passed run, the final disk chain is under external storage:

```text
Heimdal-BMA-Lab/winpe-pxe-20260909T123144.006496Z/
  startup-live-3.qcow2   (latest layer)
    -> startup-current.qcow2
      -> startup-live.qcow2
        -> windows.qcow2 (frozen original base)
```

**Retain all four files.** Backing paths use /disks/<run>/ inside the test container.
command.json records initial launch; live-snapshot.json, live-snapshot-2.json and
live-snapshot-3.json record the pivots. Do not boot the frozen base as the latest
state. Snapshot inspections and final-inspection/ retain the setup evidence.
Use qmp-control.sock for observation; qmp.sock belongs to the harness event reader.
The passed run’s PCAP is retained as network.pcap.gz, with verified decompressed
SHA256 in network.retention.json. Review completed disposable disks separately
from source images and appliance data.

## Offline reader and resume helper

Inspect only stopped disks or frozen backing files after an external snapshot;
never read an active writable layer. The reader avoids full raw-disk conversion.

```bash
docker build -f tools/pxe-test/Dockerfile.windows-inspect \
  -t heimdal-windows-inspect:lab .
```

Mount the repository at /src:ro, disk directory at /disk:ro and an evidence
directory at /evidence. Pass `/disk/windows.qcow2 /evidence/new-inspection` to
extract Panther, setupapi, verification and relevant raw EVTX files plus JSON
and hashes. Output must be a new directory. For the final chain above, pass:

```text
/disk/startup-live-3.qcow2 /evidence/new-inspection
--backing-disk /disk/startup-current.qcow2
--backing-disk /disk/startup-live.qcow2
--backing-disk /disk/windows.qcow2
```

Repeated backing disks are ordered from immediate backing to base. Explicit
backings avoid Dissect's automatic absolute-backing-path handling. Actual
extraction was verified on standalone disks and the complete nested chain.
Panther logs use guest local time; EVTX timestamps are UTC, two hours earlier in
this lab. Keep these clocks distinct when comparing records.

windows_resume.py creates a new overlay and cloned firmware variables for a
bounded boot observation. It never repairs setup state. Its marker result is a
separate follow-up result and must not replace the original deployment report.

## References

- [Microsoft capture/apply sequence](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/capture-and-apply-windows-using-a-single-wim?view=windows-11)
- [Microsoft answer-file guidance](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/update-windows-settings-and-scripts-create-your-own-answer-file-sxs?view=windows-11)
- [Windows 11 processor requirements](https://learn.microsoft.com/en-us/windows/whats-new/windows-11-requirements)
- [ERROR_TIMEOUT](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--1300-1699-)
- [Dissect file APIs](https://docs.dissect.tools/en/stable/advanced/api.html)
- [QEMU live block operations](https://www.qemu.org/docs/master/interop/live-block-operations)
