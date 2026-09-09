# Latest checkpoint — Clonezilla assisted pass; FFU unresolved — 2026-09-09

No test is running. User asked to check FFU failure then continue with Clonezilla.
FFU source WIM verified successfully, QCOW2 structural check passed, no container
OOM. DISM 1392 at 49% remains unexplained; no FFU capture/restore occurred.
Source ISO retained; temporary 8 GiB WIM extraction copies removed. Diagnosis and
hashes: artifacts/pxe-test/ffu-diagnosis-20260909/. Do not call the ISO corrupt.

Clonezilla run winpe-pxe-20260909T194444.732920Z completed PXE -> WinPE capsule ->
UEFI proof -> Clonezilla 3.3.3-15 -> savedisk -> restoredisk -> restored UEFI fixture
boot. Independent evidence-audit.json passed eleven checks, including offline
restored token/EFI hash, source EFI removal, distinct GPT partition identifiers,
firmware target path, two guest resets and full network/capsule proofs.
Assisted pass: live-medium shutdown needed serial CRLF. QMP keyboard Enter did not
reach that serial prompt. GRUB's real target marker contained ANSI controls;
original monitor failed to recognize it and was stopped. Preserve its false/interrupted
report alongside the passing independent audit. Parser now strips ANSI controls
and passes the transcript/regression check. New noeject noprompt options are
unverified until another fresh run; do not claim fully unattended validation.
Monitor elapsed 799.2 seconds. Identity 79999386-8ac9-4506-9c45-9f91cb6b0aba.

This tests a small FAT32/GPT bootable fixture, not a full customer OS, physical
hardware, Secure Boot, production capsule generation, or actual Heimdal delivery.
Current Clonezilla test disks and image-storage disk remain in its artifact folder.
Earlier attempts exposed QEMU serial-option parsing, WinPE serial initialization,
read-only mountpoint use, and a pre-write assertion; reports preserved. Disk
selection now resolves unique QEMU serials, not fixed kernel device names.

Dashboard on port 80 now gives Clonezilla and FFU their own visible result cards,
with individual evidence entries. Live browser verification confirmed the Clonezilla
card and mobile layout without horizontal overflow. 26 targeted
helper tests pass. Frontend build and existing four browser tests passed during
this work. See docs/CLONEZILLA_TEST_LAB.md and docs/FFU_TEST_LAB.md.
Next validation: fresh unattended Clonezilla run with prepared prompt suppression,
then Veeam Linux media; user will provide Windows recovery ISO later. Modern
production image analysis/WIM capsule work and Heimdal delivery remain priorities.

---

# Latest checkpoint — FFU diagnosed, Clonezilla running — 2026-09-09

User requested checking the FFU failure then continuing with Clonezilla.
FFU stopped at 49% WIM application, DISM 1392, exit 1, 1575 seconds. No FFU was
captured/restored. Read-only extraction of apply.log yielded no failing-file detail.
Full WIM verification passed with wimlib-imagex; QCOW2 structural check passed;
no container OOM. Cause remains unresolved. Temporary WIM copies removed, hashes
and evidence retained. Do not repeat FFU now. docs/FFU_TEST_LAB.md has the result.

Clonezilla stable 3.3.3-15 AMD64 downloaded and SHA-256 verified. New harness case
--handoff --clonezilla-iso validates PXE/capsule launch, whole-disk savedisk/restoredisk
of a small UEFI fixture, restored-file integrity, and boot from target. Not a full
customer OS restoration test. All 25 targeted helper tests pass.

Active run: winpe-pxe-20260909T194444.732920Z, container heimdal-clonezilla-test,
2400-second timeout. At this checkpoint loading WinPE via PXE, no pass yet.
Initial launch winpe-pxe-20260909T192414.401805Z failed QEMU device-option parsing;
fixed serial properties on explicit IDE devices before this new run.
Do not launch a duplicate test. Monitor serial/report/QMP in the active run.
Details and limitations: docs/CLONEZILLA_TEST_LAB.md.

Veeam Linux recovery ISOs are available in shared _torrents_done/Veeam; Windows
agent archives contain installers, no generated Windows recovery ISO yet. User
will provide that later. Admin uploads vendor recovery media to Image Library;
analysis selects the adapter and capsule method. Backup source/access configured
separately. Veeam testing has not started; latest instruction prioritizes Clonezilla.

---

# Latest checkpoint — FFU test launched — 2026-09-09

User restored the accidentally deleted Windows ISO. File is regular and matches
its prior 7,368,480,768-byte size. Launched run
`winpe-pxe-20260909T183231.683132Z` at 18:32 UTC in detached container
`heimdal-windows-ffu-test`, with 18,000-second limit (five hours).
At this checkpoint QEMU is running; no FFU result yet. The run created three
new disposable disks under the matching external lab directory. Source ISO and
repository are mounted read-only; networking is isolated. Capture, restore and
target Windows verification must all pass before reporting success.

Monitor with docker logs / docker inspect and the run's serial.log, report.json
and QMP socket. Do not launch a duplicate test. Keep the container after it stops
to record the actual process exit status. Details: docs/FFU_TEST_LAB.md.

---

# Latest checkpoint — FFU prepared, Windows media missing — 2026-09-09

User selected FFU as the next format test. Added --ffu to the isolated Windows
PXE harness, with fresh WIM reference -> FFU capture -> separate blank target
restore -> target-only installed Windows verification. Eight helper tests pass.
No FFU test is running and no FFU pass is claimed. Initial launch exited 2 at
input validation: the prior CCSA_X64FRE_DE-DE_DV9.ISO has disappeared from the
shared folder. A recursive search found no replacement Windows ISO or WIM.
Asked user for the new path or restoration. Removed the stopped failed container
and the empty directory Docker created for the missing source; saved launch logs
and container metadata in artifacts/pxe-test/ffu-preflight-20260909/.
No existing disks or source media were modified. Reproduce with the fail-fast
bind-mount command in docs/FFU_TEST_LAB.md once the ISO is restored.

Product decisions: every Image import is analyzed; plugins supply recognition,
compatibility checks and deployment methods. An Image may be a multi-file set.
NT/OS2/BeOS are parked exploratory cases, not implementation priorities. Focus
on modern Windows ISO, customer golden WIM, FFU, and actual Heimdal delivery.
Potential future vendor restore adapters: Macrium, Acronis, Veeam, Clonezilla.
Do not imply generic DISM support for proprietary backup formats.

NT and BeOS inspection was read-only. NT build 782 ISO had no El Torito boot
entry; its SETUP.TXT and WINNT.EXE explicitly support /B floppy-free setup.
BeOS CUE described three MODE1/2352 data tracks. Neither deployment was tested.
Original image-inspection artifacts are ignored in Git. Earlier WIM pass and
its retained four-file disk chain remain the evidence baseline described below.

---

# Latest checkpoint — Windows WIM baseline passed — 2026-09-09

**Run `winpe-pxe-20260909T123144.006496Z` passed in 5903.1 seconds
(98 minutes 23 seconds). No Windows test is running.**
Source: unchanged, read-only CCSA_X64FRE_DE-DE_DV9.ISO, install.wim index 1,
Windows 11 Enterprise LTSC 2024, AMD64, de-DE, build 26100.7840.

Verified: complete PXE DHCP/TFTP and eight HTTP transfers; actual capsule SETUP.EXE;
full 6,509,992,649-byte WIM; DISM /Apply-Image /CheckIntegrity to a new GPT disk;
BCDBoot and recovery registration; one guest-requested reboot; installed Windows
specialize execution with SystemDrive C: and no MiniNT key; matching unique
identity 5b6bf058-d006-4628-9616-09fa984056fd and complete first-boot marker.
No keyboard input, setup-state bypass, or manual Windows command was used.
The harness stops after the marker: OOBE completion, desktop use, WinRE boot,
customer golden images, Secure Boot and actual Heimdal integration remain untested.
Production WIM ingestion/capsule building is still planned, not implemented.

Diagnosis and correction: the original one-core run reached AppX specialization
but timed out before the verification script. A separate overlay restart hit the
unexpected-restart setup error (181.2 seconds); it was stopped without bypassing
setup state. The image case inherited one vCPU from WinPE; changed to two cores
in one socket. Container RAM limit is now 6 GiB (7 GiB with swap), guest RAM 4 GiB;
run timeout 10800 seconds. FIRSTBOOT.CMD also writes FIRSTBOOT.LOG.
The rerun's AppX preregistration returned 0x0 and AppxSysprepSpecializeOnline
completed at guest-log 14:00:09. SetupUGC invoked FIRSTBOOT.CMD during specialize
at 14:09:49; FIRSTBOOT.LOG confirms invocation and successful COM1 device restart.
The serial log then records the exact identity, Windows version and completion.
This supports the corrected lab configuration; it does not isolate which resource
or timeout change was solely responsible for the original failure.

Evidence directory: `artifacts/pxe-test/winpe-pxe-20260909T123144.006496Z/`.
Includes report.json, serial.log, qmp-events.json, command.json, windows-apply.json,
three live-snapshot*.json records, three snapshot inspections and final-inspection/.
Raw extracted files have SHA256 manifests. The launch wrapper returned exit 130
without its final console report; persisted report.json says passed=true and was
independently checked against raw guest/network/QMP and offline setup evidence.
QEMU logged normal SIGTERM from the harness after marker detection. Do not claim
a clean wrapper exit; the guest assertions are the basis of the lab pass.

Three QMP external snapshots enabled frozen-disk inspection without rebooting the
guest. These were crash-consistent disk snapshots, not VSS backups. ALL FOUR FILES
are needed for the retained latest disk, under
`/media/sf_Downloads/Heimdal-BMA-Lab/winpe-pxe-20260909T123144.006496Z/`:
`startup-live-3.qcow2` -> `startup-current.qcow2` -> `startup-live.qcow2` -> `windows.qcow2`.
Backing paths use /disks/<run>/ inside the container. command.json records initial
launch; live-snapshot-3.json records the final chain. Do not boot the frozen base
as if it were the final disk. Original failed disk and resume overlay remain
separate and preserved with their reports. No physical disks or source ISO writes.

Tools: windows_inspect.py plus Dockerfile.windows-inspect provide read-only QCOW2
and NTFS extraction using dissect.target==3.25.1. Repeated --backing-disk arguments
list immediate backing through base for overlays. Actual extraction verified for
standalone QCOW2 and nested overlays. windows_resume.py provides bounded overlay
startup observation, not setup-state repair. Temporary inspector container removed.
Four Windows helper tests passed; Python syntax and diff checks passed.
Frontend build and all four browser tests passed. Updated dashboard is deployed
on port 80; live desktop evidence and mobile layout checks passed. API, database,
Redis and worker are running. network.pcap is now losslessly compressed as
network.pcap.gz; decompressed SHA256 was verified and recorded in network.retention.json.
Independent evidence-audit.json verifies all guest assertions. The outer session
exit discrepancy remains recorded for runner/CI follow-up; do not repeat a full
image application solely to investigate that transport status.

Next product work: implement image inspection and production WIM capsule building,
then validate a customer generalized golden WIM and actual Heimdal deployment.
Keep ISO as one image format. The dashboard records the lab pass without per-image
or Heimdal readiness claims. Detailed reproduction: docs/WINDOWS_IMAGE_TEST_LAB.md.

---

# Latest Windows WIM test — partial result, timeout — 2026-09-09

Run `winpe-pxe-20260909T095102.307725Z` ended after 7200.6 seconds.
**Overall passed=false:** installed Windows first-boot identity/marker was absent.
The test container stopped; there is no active Windows test.

Verified: complete PXE DHCP/TFTP and all eight HTTP transfers; actual WinPE
capsule SETUP.EXE; full 6,509,992,649-byte install.wim; index 1 DISM /Apply-Image
/CheckIntegrity success; GPT partitioning, BCDBoot, WinRE copy and REAgentC
registration; one guest-requested reboot. UEFI then loaded Windows Boot Manager
from the new disk. Screens progressed through services starting, device setup
(including 60%), and “Getting ready”. No keyboard input was sent. No observed
QEMU I/O failures or container OOM events. This is not a complete first-boot pass,
OOBE completion, customer golden-image validation, or Heimdal readiness.

Source: read-only `/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO`;
Windows 11 Enterprise LTSC 2024, AMD64, de-DE, build 26100.7840, index 1.
The ARM64 host runs the x64 guest under TCG with 4 GiB guest RAM and one vCPU.
Image application took about 65 minutes; startup then consumed the remaining time.
Slow emulation is a possible contributor, not a diagnosed cause of the missing marker.

Evidence: `artifacts/pxe-test/winpe-pxe-20260909T095102.307725Z/`, including
report.json, serial.log, qmp-events.json, command.json, windows-apply.json and
first-boot.png. The report's scope describes the intended assertion; its
passed=false and marker fields are authoritative for the outcome.
Retained disposable disk (64 GiB virtual, about 14 GiB allocated):
`/media/sf_Downloads/Heimdal-BMA-Lab/winpe-pxe-20260909T095102.307725Z/windows.qcow2`.
Do not overwrite it or reapply the image just to diagnose startup. Next: inspect
installed Windows Panther/setup logs and the first-boot serial script, then resume
this disk with a bounded startup observation. Preserve the original timeout report.
No physical target disks were attached; source ISO and code stayed read-only.

New lab helper `tools/pxe-test/windows_apply.py`, `--apply-windows /disks`, and
`compose.windows-apply.yml` create this isolated case. They refuse an existing
per-run target directory and require 40 GiB free external storage. Preparation
attempt `winpe-pxe-20260909T095017.873435Z` failed before guest launch because
qemu-img was missing; the new image adds qemu-utils. Seventeen unit tests passed
(HTTP, terminal, Ubuntu readiness, two target-disk isolation checks, and two first-boot evidence checks).
See `docs/WINDOWS_IMAGE_TEST_LAB.md` for reproduction and evidence scope.
After the run, marker matching was tightened to require complete serial lines;
identity alone cannot stand in for the completion marker. Two regression checks
passed. The original timeout result is unchanged. Dashboard partial-result text
is deployed on port 80; frontend build, four browser tests, and a live page check
passed. Packet capture is losslessly compressed as network.pcap.gz with a verified
decompressed SHA256 in network.retention.json. The external disk is retained for
diagnosis. This checkpoint is prepared for synchronization with origin/main.

---

# Latest source check — installation WIM available — 2026-09-09

Read-only metadata inspection of
`/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO` found
`/SOURCES/INSTALL.WIM`, with a valid MSWIM header and four XML image entries.
All identify AMD64, de-DE, and build 26100.7840:

1. Windows 11 Enterprise LTSC 2024 (EnterpriseS).
2. Windows 11 Enterprise N LTSC 2024 (EnterpriseSN).
3. Windows 11 IoT Enterprise LTSC (IoTEnterpriseS).
4. Windows 11 IoT Enterprise LTSC Subscription (IoTEnterpriseSK).

Index 1 is an available baseline for developing image application. This is
installation-media image metadata, not proof of full payload integrity, successful
application, or a customer-customized golden image. The user is looking for a
custom golden WIM for subsequent testing. No full image was extracted or deployed.

Large-file handling needs attention before extraction: the current ISO9660 walker
reports install.wim at LBA 355771 with length 2,215,025,353 bytes. The valid WIM XML
is at relative offset 6,509,981,523 with length 11,126, ending at 6,509,992,649 bytes
(exactly the reported directory length plus 2^32). Do not truncate extraction to
the current walker length. Resolve and validate the full file size/extents through
the appropriate optical filesystem metadata before using this source for deployment.
Header/XML layout was cross-checked against Microsoft's go-winio WIM parser:
https://github.com/microsoft/go-winio/blob/main/wim/wim.go

---

# Latest checkpoint — Image Library terminology deployed — 2026-09-08

The user requested the image-first product direction be reflected in the app and
handoff. Navigation and entry points now use Image Library and Images. Golden
Image Deployment is a planned workflow under Build & deploy, not a separate
library. The first production use case is deploying a customer-prepared generalized
Windows WIM through Heimdal without Configuration Manager/SCCM. Detailed scope
and acceptance criteria are recorded below.

Current import/inspection remains ISO-only and the UI states that WIM support and
production capsule generation are planned. This checkpoint does not implement
those capabilities or claim new deployment validation.

Validation: frontend build and all four browser tests passed. Live Image Library,
golden-image scope, and mobile layout were verified on port 80. API, database,
and Redis are healthy; worker is online and shared storage is read-only. Web was
rebuilt, and unused build cache was removed. This checkpoint is committed for
synchronization with origin/main; use git status/fetch to confirm on resume.

---

# Latest handoff — automatic Ubuntu handoff passed — 2026-09-06

## User direction and active work

The user authorized continuing the generated capsule / WinPE-to-UEFI / Ubuntu
lab tests autonomously, requested disk cleanup, and asked to keep this handoff
current while they are away. The current lab milestone is complete; continue
within the authorized scope without asking routine confirmation. The environment now permits full filesystem/network access and
has approval policy `never`; do not pass `sandbox_permissions` to tools.
No subagents are authorized. Preserve uncommitted work.

**Latest run passed:** `artifacts/pxe-test/winpe-pxe-20260906T015249.555025Z/`.
Result: `report.json`, `passed: true`, 1046.2 seconds (17m 26s).
PXE WinPE -> actual capsule SETUP.EXE -> BootNext reboot -> verified UEFI stage
-> GRUB -> Ubuntu 26.04.1 LTS Subiquity Serial welcome screen.
No keyboard input or service restart was used. Only terminal protocol queries
were answered automatically (five response batches); raw guest output is saved.
Exactly one guest RESET, all eight HTTP transfers, DHCP/TFTP, all WinPE handoff
markers, and all six stricter EFI markers passed. BootOrder was preserved,
BootNext consumed, BootCurrent matched, and temporary-variable deletion read back.
The harness exited successfully and removed its container; no lab guest remains.
The original `serial.log`, `debug.log`, `qmp-events.json`, capsule metadata, and
report are retained. The old exit-37 stage/bridge markers are deliberately false
in this case; case-specific handoff and Ubuntu evidence determine its result.

`winpe-pxe-20260906T013237.431234Z` was stopped as a diagnostic after reaching
Subiquity's Serial screen. Its original interrupted report is preserved, not
rewritten as a pass. Ctrl-Alt-F2 was sent for observation; no guest commands or
service changes were made. All stricter EFI checks, one guest reset, and all eight
HTTP transfers are recorded. Slow snap/cloud-init startup accounted for the wait.

Earlier Ubuntu diagnostics:

- `winpe-pxe-20260906T011505.608035Z` booted the source DVD directly and was
  stopped without a pass. Explicit NIC `bootindex=1` now forces the initial PXE
  path; BootNext overrides it for the handoff reboot.
- `winpe-pxe-20260906T011741.080830Z` completed all stricter handoff checks,
  loaded GRUB, booted Ubuntu 26.04.1 LTS / Linux 7.0.0-30-generic, and reached
  the live tty2 shell. It was stopped as a diagnostic, not an unattended pass.
  Serial device initialization exceeded the 90-second systemd device wait;
  `serial-device.png` confirms the device became active later. Manual restart
  of the serial service confirmed that its command launches the Subiquity snap,
  not a conventional login prompt (`serial-unit.png`). The serial output-only
  backend could not answer terminal-size queries from the installer.

The successful automatic run addresses both findings: the generated GRUB command line sets
`systemd.default_device_timeout_sec=600` for slow TCG device setup, and
`serial_terminal.py` answers only terminal queries through a bidirectional socket.
It never writes synthesized markers to the guest-output log or sends shell
commands. Four responder tests passed. Ubuntu success requires the actual installer Serial or Welcome/English UI
alongside the full handoff, kernel, and network evidence. A login banner alone
is insufficient. Five readiness tests cover positive and incomplete evidence. No manual interaction was used in the successful run.

## Completed milestones

- Independent diskless PXE/WinPE launcher: passed, 144.6 seconds, run
  `winpe-pxe-20260906T003352.579436Z`. Missing-WIM control passed in 17.0 seconds,
  run `winpe-pxe-20260906T003646.958113Z`.
- Generated lab capsule / WinPE -> UEFI: passed in 175.6 seconds, run
  `winpe-pxe-20260906T010359.765597Z`. Actual root SETUP.EXE staged the EFI file,
  set BootNext, and caused exactly one guest RESET. The EFI proof verified
  BootOrder preservation, BootNext consumption, and temporary-variable cleanup.
- Missing EFI payload: passed in 168.9 seconds, run
  `winpe-pxe-20260906T010801.293915Z`. Capsule exit 60; no reset or handoff.
- Invalid EFI payload: passed in 185.8 seconds, run
  `winpe-pxe-20260906T011119.375712Z`. Native invalid-image error 35 propagated
  as capsule exit 66 before firmware access; no reset or handoff.
- Ubuntu installer handoff: passed in 1046.2 seconds, run
  `winpe-pxe-20260906T015249.555025Z`, including matching BootCurrent and
  deletion readback. The earlier standalone proof predates those extra checks.

## Code and runtime

See `docs/HANDOFF_TEST_LAB.md` for full design, commands, and evidence scope.
New lab files: `tools/pxe-test/handoff.py`, `tools/pxe-test/handoff/` native helper,
EFI proof and chainloader, `Dockerfile.handoff`, `Dockerfile.ubuntu`, and
`compose.handoff-test.yml` / `compose.ubuntu-test.yml`. `network_winpe.py` now
supports `--handoff`, `--missing-stage`, `--invalid-stage`, and `--ubuntu-iso`.

The generated capsule contains root SETUP.EXE, STAGE.CMD, deployment.json,
HANDOFF.EXE, and runtime files. A uniquely marked GPT/FAT lab disk is created
by the host; WinPE never partitions or formats a disk. Native verification checks
copied bytes and AMD64 EFI PE headers before firmware operations. BootNext is
one-time; BootOrder is never written. Existing BootNext/audit entries are refused.
Only disposable guest firmware and staging storage are changed.

The basic handoff and full Ubuntu boot chain have both passed independently. The live source ISO is attached read-only. GRUB loads its
original Casper kernel/initrd. No installation or autoinstall is requested.
The positive Ubuntu condition requires the actual installer welcome screen, not merely
GRUB or a kernel banner. No production capsule API/build queue is implemented.

Minimal WinPE does not include findstr; discovery now uses built-in for /f.
The first two handoff diagnostic attempts were stopped and retained separately.
Use the case-specific handoff/UEFI markers; the old exit-37 test markers are not
expected when executing a real capsule handoff script.

Images: trixie base (QEMU 10.0.11 / OVMF 2025.02), handoff, and Ubuntu lab images.
Ubuntu image adds x86-64 GRUB modules to the ARM64 build environment.
Inputs: read-only Windows ISO and `ubuntu-26.04.1-live-server-amd64.iso`, both under
`/media/sf_Downloads/_torrents_done/`. wimboot remains pinned in lab downloads.

## Disk cleanup and dashboard

User-requested cleanup recovered about 4.5 GiB: free space rose from 831 MiB to
5.3 GiB. Removed unused Docker build cache and obsolete Bookworm pxe-test:latest.
Current images, appliance containers/data volumes, and source ISOs were preserved.
Large completed pcaps were trimmed to initial complete packet records in
`network-prefix.pcap.gz`; `capture-retention.json` records full original hashes,
sizes, and the truncation. Full original captures for those runs are gone.
Reports, HTTP digests, serial/debug logs, QMP events, capsules, and firmware remain.
After the final Ubuntu run and dashboard rebuild, free space is 5.2 GiB and lab
artifacts total 264 MiB. The four newest large captures were losslessly gzipped
and their decompressed SHA-256 verified before removing the uncompressed copies,
recovering 98,343,923 bytes. Their retention records explicitly say full capture
retained. This differs from the earlier prefix-only retention described above.
The temporary extracted Subiquity snap was removed. The new web build cache was
pruned (Docker reported 567.9 MB); appliance volumes and lab images remain.
Final API health: status/database/Redis OK, worker online, storage read-only.
Only the five appliance containers remain running; no QEMU test guest remains.

Dashboard and PXE Integration now display recorded lab results with date,
duration, evidence details, the automatic Ubuntu pass, and remaining milestones. Build and four browser tests
passed; live desktop/mobile checks passed. The running web container was rebuilt. Dashboard is http://127.0.0.1:80/ inside the
VM; the former port 5173 preview is no longer running. Port 80 was not changed
by the most recent dashboard update.
The follow-up dashboard update makes the automatic boot-chain pass prominent,
updates the Heimdal integration banner beyond the old launcher-only result, and
states that app capsule generation is next. Build and all four browser tests
passed; live Dashboard/PXE Integration wording, disabled publishing, and mobile
layout were verified. Web was rebuilt on port 80 and its build cache removed.

GitHub authentication is configured. The shutdown checkpoint following `cebd798`
includes the latest dashboard, lab harness, test documentation, and agreed next
steps. The user requested Git synchronization before shutting down. On resume,
check `git status --short` and fetch origin to confirm branch synchronization.
No force push/reset. ISO inputs, local configuration, Docker data, and detailed
lab artifacts are intentionally excluded from Git and remain on this machine.
The shutdown check found no QEMU guest running; only appliance services remain.
Use a normal OS shutdown to stop those services cleanly.

## Product direction clarified by the user

The product must bridge the gap between a supplied image and a working Heimdal
deployment. It is not limited to classifying media or passing through images
that already fit the current boot path. An unsupported result identifies a
missing adapter today, not the intended product boundary. Build the necessary
adapter where technically feasible; explain concrete limitations where it is not.
Do not promise that every image can work on every target.

Hiren's BootCD PE is a concrete intended use case: identify its boot requirements,
package its WinPE image and supporting files, provide the appropriate boot
process, and verify that its desktop and bundled tools are usable. Success for
recovery media means a working recovery environment, not an OS installation.
A kernel, launcher, or desktop appearing alone is insufficient evidence that all
required tools and resources work. The existing Microsoft WinPE pass does not
prove Hiren's support; the earlier Hiren's attempt stalled in the older QEMU
setup and remains unverified.

The harness should prove each adapter produces its intended usable environment,
then validate the resulting capsule through actual Heimdal deployment. Legacy
media such as OS/2 may require a separate BIOS path and additional boot media;
that is an adapter investigation, not a reason to redefine the product around
only the formats currently supported. This direction informs the production
capsule-builder sequence below; no new Hiren's or OS/2 test was started today.

## Image model and first production use case

The user clarified that all deployment sources are **Images**. ISO is one format,
not the top-level product concept. Use **Image Library** in the UI. Keep image
format (ISO, WIM, and future formats), intended use (OS installation, golden-image
application, recovery environment), and actual deployment support distinct.
A recognized file format alone does not establish deployability.

The first production use case is a customer who has a prepared Windows golden
image and Heimdal, but no Configuration Manager/SCCM. Accept a customer-prepared,
generalized WIM alongside ISO inputs in the future image model; reference-machine
capture is not a prerequisite for this use case. The Windows adapter should
prepare the selected target disk, apply the image, handle required drivers,
configure boot and recovery, and reboot into Windows to complete setup.

Acceptance: a blank target boots into the customer's deployed Windows image
through Heimdal, with recorded evidence. The capsule builder and harness must
validate this outcome, not just a WinPE launch or a firmware handoff.

The user subsequently requested implementing this terminology and direction.
The UI now uses Image Library and image-oriented entry points; the golden-image
page describes a deployment workflow rather than a second image library. Actual
import and inspection remain ISO-only, explicitly stated in the UI. WIM support,
image application, and production capsule generation are not implemented by this
terminology update. No new guest boot tests were started for it.

## Remaining scope

1. Extend image ingestion and inspection to customer-prepared generalized WIM
   images, keeping format, intended use, and adapter support distinct.
2. Implement the Windows golden-image adapter and production capsule builder;
   save generated capsules on configured external storage.
3. Connect generation to the dashboard with job progress and download/output
   details.
4. Run the existing harness against the app-generated capsule, extending it to
   verify Windows image application and the installed OS boot on a blank target.
5. Once the lab acceptance passes, validate that capsule through actual Heimdal
   deployment. Retain results and evidence for both paths.

The lab boot chain is proven; app-generated capsules and actual Heimdal deployment
are not yet validated. Keep the lab-only helpers distinct from production
firmware/runtime code. Physical
targets, Secure Boot, installation to disk, and actual Heimdal integration remain
unverified. Publish/create-capsule controls remain disabled until their backend
implementation exists; do not mark individual library images validated from these
recorded lab results.
The user expects continued work, not a request to resume after each test.

---

# Historical unattended WinPE PXE pass — 2026-09-06

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
