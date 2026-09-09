# FFU capture and restore lab

Status (2026-09-09): failed before FFU capture. Run
`winpe-pxe-20260909T183231.683132Z` exited 1 after 1575 seconds, DISM error 1392
at 49% of initial WIM application. No FFU capture, restore, or target boot occurred.

The full source WIM subsequently passed wimlib-imagex verification (exit 0), and
qemu-img check found no QCOW2 structural errors. Container OOMKilled=false.
The saved DISM log does not identify the failing file. Cause remains unresolved;
do not label the current ISO corrupt. Diagnosis evidence:
`artifacts/pxe-test/ffu-diagnosis-20260909/` and failed run `dism-inspection/`.
User directed continuing with Clonezilla after checking the failure; no FFU retry.

Earlier missing-input launch evidence: `artifacts/pxe-test/ffu-preflight-20260909/`.
This is lab tooling, not production FFU ingestion or Heimdal readiness.

## Method

Reuse the PXE WinPE capsule harness with `--apply-windows /disks --ffu`.
Create three exclusive, disposable QCOW2 disks in a new run directory:

- Disk 0: 64 GiB reference, populated from stock install.wim index 1, with GPT,
  EFI, MSR, Windows and recovery partitions. Never booted before capture.
- Disk 1: 48 GiB NTFS storage for `V:\baseline.ffu` and DISM logs.
- Disk 2: 64 GiB blank restoration target, the only disk with firmware boot priority.

Run DISM Capture-FFU, Get-ImageInfo and Apply-FFU. Change the source disk GUID
and offline it before restoring the original captured GUID onto the target.
Inspect restored partition layout, BCD, Windows kernel and recovery image.
No post-restore BCDBoot repair: the test should exercise the captured boot files.
Write a run-specific restoration token only to the target. The captured first-boot
script requires that token before emitting any installed-system success markers.
A source boot or a previous WIM pass therefore cannot satisfy FFU acceptance.

Require all previous WIM markers, four FFU markers, matching run identity,
guest reboot and complete PXE/HTTP transfer evidence. Same-size restore only.
This baseline uses an unbooted Microsoft image; it does not validate capturing a
customer-customized, Sysprep-generalized reference PC, OOBE completion, WinRE boot,
optimized FFU, different target sizes, physical hardware, or Heimdal delivery.
The existing harness stops Windows during specialize after its verification marker.

## Run after source restoration

Requires 75 GiB available external space, 4 GiB guest RAM, 6 GiB container limit
(7 GiB with swap), two guest cores. The ISO must be the prior index-1 source;
its install.wim size is checked by the inherited lab script.
Use an existing lab image built with Dockerfile.windows-apply. Bind mounts below
fail if the source path is missing instead of creating a directory at that path.

```sh
test -f /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO && \
docker run -d --name heimdal-windows-ffu-test \
  --network none --read-only --memory 6g --memory-swap 7g --cpus 2 \
  --tmpfs /tmp:size=256m --tmpfs /var/tmp:size=256m \
  --mount type=bind,src=/home/heimdal-bma/Heimdal-Bare-Metal-Adapter,dst=/src,readonly \
  --mount type=bind,src=/home/heimdal-bma/Heimdal-Bare-Metal-Adapter/artifacts/pxe-test,dst=/output \
  --mount type=bind,src=/media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO,dst=/winpe.iso,readonly \
  --mount type=bind,src=/media/sf_Downloads/Heimdal-BMA-Lab,dst=/disks \
  --entrypoint python3 heimdal-bare-metal-adapter-pxe-test:windows-apply \
  /src/tools/pxe-test/network_winpe.py --apply-windows /disks --ffu --timeout 18000
```

Retain the stopped container until its exit status and logs are recorded; prior
WIM work had an outer session exit discrepancy despite passing guest assertions.
Do not classify a running test as passed. Capture reports, serial, network and
QMP evidence, and inspect the restored disk after stopping.

Reference: [Microsoft FFU capture and application](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/deploy-windows-using-full-flash-update--ffu?view=windows-11).
