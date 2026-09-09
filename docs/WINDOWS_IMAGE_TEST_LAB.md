# Windows image application lab

This is an isolated baseline test of applying installation-media WIM index 1 to a
new virtual disk. It is not a production capsule builder, customer golden-image
validation, or a Heimdal integration test.

## Run

The source Windows ISO stays read-only. Create a dedicated external directory
with at least 40 GiB free; never pass a physical disk. The helper creates a fresh
per-run directory and a 64 GiB QCOW2 disk, refusing directory reuse. The guest sees
only that writable disk and two read-only CDs (source and generated lab capsule).
It has no host/LAN network access. The disk is initially blank and initially fails
UEFI disk boot, falling through to PXE; after image application it boots from disk.

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.windows-apply.yml build pxe-test
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.windows-apply.yml run --rm --name heimdal-windows-apply-test \
  --entrypoint python3 \
  --volume /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO:/winpe.iso:ro \
  --volume /media/sf_Downloads/Heimdal-BMA-Lab:/disks \
  pxe-test /src/tools/pxe-test/network_winpe.py --apply-windows /disks --timeout 7200
```

At least 5120 MiB available host memory is required. The standard WinPE override
limits the container to 5 GiB RAM and 6 GiB memory plus swap. The Windows apply
image adds qemu-utils for QCOW2 creation. Source code is mounted read-only, so
Python/script changes do not require rebuilding the image.

## Application and evidence

The actual SETUP.EXE launcher invokes the capsule's adjacent STAGE.CMD:

1. Locate source install.wim and confirm the Windows-reported 64-bit file size is
   6,509,992,649 bytes; read index 1 metadata with DISM before any disk changes.
   This baseline intentionally targets the already-inspected source ISO. Windows
   reads its filesystem directly, avoiding the current ISO9660 walker's wrapped
   file length and any full WIM copy onto the appliance.
2. Partition the sole disposable disk as GPT with a 260 MiB FAT32 EFI partition,
   16 MiB MSR, Windows NTFS partition, and 2048 MiB recovery partition.
3. Apply WIM index 1 with DISM /CheckIntegrity, with scratch and log files on the
   target virtual disk. Emit an application marker only on successful exit.
4. Run BCDBoot, confirm BCD exists, copy winre.wim, and register recovery with
   REAgentC. Each operation must succeed before its marker is emitted.
5. Install a lab answer file and first-boot script, then reboot. The script runs
   during installed Windows's specialize pass, verifies SystemDrive is C: and
   the WinPE MiniNT registry key is absent, initializes COM1, and emits a unique
   per-run identity plus first-boot marker.

Success requires complete DHCP/TFTP and HTTP bootstrap evidence, all application,
boot, recovery, and first-boot markers, the matching per-run identity, and at
least one guest-requested QMP RESET. This confirms installed Windows reaches
specialization; it does not mean OOBE was completed or a user desktop was tested.
Recovery registration does not by itself prove booting into WinRE.

`serial.log`, `qmp-events.json`, `windows-apply.json`, `command.json`, HTTP evidence,
and `report.json` are in the standard local per-run artifact directory. The
QCOW2 disk is external; its path is recorded in windows-apply.json. Use
qmp-control.sock with qmp.py for screenshots; qmp.sock belongs to event capture.
Do not delete the external disk while its guest is running. Review and clean up
completed disposable disks separately from source images and appliance data.

The existing exit-37 launcher fixture markers are not expected for this case;
use the case-specific windows_markers and first_boot_identity_matched fields.

The application sequence follows Microsoft's
[capture/apply guide](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/capture-and-apply-windows-using-a-single-wim?view=windows-11)
and [answer-file guidance](https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/update-windows-settings-and-scripts-create-your-own-answer-file-sxs?view=windows-11).

## Current result

Run `winpe-pxe-20260909T095102.307725Z` ended at 7200.6 seconds with
`passed=false`: the installed Windows first-boot marker and identity were absent.
PXE bootstrap, all HTTP transfers, DISM application with integrity checking,
BCDBoot, recovery registration and one guest-requested reboot passed. Windows
Boot Manager loaded from the new GPT disk, and the screen progressed through
starting services and device setup to “Getting ready”. No keyboard input was sent.
No observed QEMU disk I/O failures or container OOM events explain the timeout.

The applied disk is retained on external storage for Panther/setup-log inspection
and a bounded follow-up boot. Do not redo image application or overwrite the
original timeout report. Slow x64-on-ARM TCG is a possible contributor; the reason
for the absent serial marker is not diagnosed. Seventeen unit tests passed.
Earlier preparation winpe-pxe-20260909T095017.873435Z stopped before guest launch
because qemu-img was absent. The new image includes the missing utility.
