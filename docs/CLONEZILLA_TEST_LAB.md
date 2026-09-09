# Clonezilla lab

Assisted lab round trip passed: `winpe-pxe-20260909T194444.732920Z`.
No test is running. Independent `evidence-audit.json` passed all eleven checks
(exit 0), using raw serial/network/UEFI evidence and offline target inspection.
Monitor elapsed 799.2 seconds (13 minutes 19 seconds, including intervention).

The original report remains passed=false, interrupted after the genuine target
boot marker: the old parser did not strip GRUB's ANSI cursor controls. Corrected
parser tested against the actual transcript and a regression test. Do not replace
or conceal the original report. This is an assisted evidence-based pass, not a
clean fully unattended runner pass.

The live-medium shutdown prompt required CRLF over serial. QMP keyboard Enter
was ineffective; QMP chardev-change added a CRLF input file while appending to the
existing serial log. The restored target then booted. New `noeject noprompt` boot
options are prepared but have not been validated in a fresh end-to-end run.
Intervention record: `artifacts/pxe-test/clonezilla-intervention-20260909.json`.

Offline checks confirmed target identity and EFI hash against the original
fixture, source EFI removal, differing source/target partition GUIDs, and firmware
starting target partition cff46f9c-258e-43d7-9915-e1fa637ec30d. Two guest resets and
all capsule/network proofs passed. The image set is retained inside clone-store.raw.
An attempted Dissect inspection of its modern ext4 filesystem was unsupported;
no offline image-set manifest was produced or claimed.

Source: Clonezilla Live 3.3.3-15 AMD64, downloaded from the project's SourceForge
release. SHA-256 checked against the official NCHC mirror:
`482518ea32af3b82ed15d09e2e7714806775deb62aeed81491e534f6cc6bbc47`.
ISO and checksum page retained in external `Heimdal-BMA-Lab/clonezilla-download/`.

## Scope and acceptance

PXE DHCP/TFTP -> iPXE HTTP -> Windows WinPE -> actual capsule SETUP.EXE ->
one-time UEFI handoff proof -> GRUB -> Clonezilla Debian Live.

A capsule script checks QEMU disk serial numbers before any writes. It uses
Clonezilla `ocs-sr savedisk` to save a small FAT32/GPT UEFI fixture to an image
set, then `ocs-sr restoredisk` to a separate, initially blank disk. It compares
the restored identity file and bootloader SHA-256, then sets BootNext for the
restored disk while preserving the preceding BootOrder. The restored GRUB
bootloader emits a run-specific marker over serial.

Acceptance requires all original capsule and UEFI proof markers, all network
transfers, two guest reboots, save/restore/content markers, and the exact target
boot identity. Merely reaching a menu or restoring files is insufficient.
After verifying the restore, the disposable source bootloader is removed and its
GPT identifiers randomized to prevent firmware resolving a cloned partition GUID
to the source. The source disk has no firmware boot index. The explicit target BootNext entry
is created using the target disk device path.

This verifies a small bootable fixture, not restoration of a complete customer
Windows/Linux installation, production ingestion, physical hardware, Secure Boot,
or actual Heimdal delivery. The recovery ISO remains attached read-only; this is
not proof of streaming the entire Clonezilla runtime solely over PXE.

## Disks and isolation

Only new files inside the run's artifact directory are writable. QEMU user
networking is restricted; host/LAN DHCP is never enabled. No physical disks are
attached. Source ISO and code are mounted read-only.

- sda: existing 66 MiB capsule handoff staging disk.
- Source: 66 MiB bootable fixture, resolved by serial BMA_CLONE_SOURCE.
- Storage: 1 GiB image storage, resolved by serial BMA_CLONE_STORE.
- Target: 66 MiB blank target, resolved by serial BMA_CLONE_TARGET.

The first launch `winpe-pxe-20260909T192414.401805Z` failed before guest execution:
QEMU rejected the legacy drive serial option. Fixed by setting serial on explicit
ide-hd devices at ports 3, 4 and 5. Preserve the failed launch report.

Use image `heimdal-bare-metal-adapter-pxe-test:ubuntu`, same read-only bind mounts
and a 6 GiB container limit (7 GiB with swap), 4 GiB guest RAM, two CPU cores, with `/clonezilla.iso` mounted.
Entrypoint:

```sh
python3 /src/tools/pxe-test/network_winpe.py \
  --handoff --clonezilla-iso /clonezilla.iso --timeout 2400
```

## Related Windows diagnosis

FFU run `winpe-pxe-20260909T183231.683132Z` failed before FFU capture, at 49% of
WIM application, DISM error 1392, elapsed 1575 seconds. The saved DISM log contains
startup information only; it does not identify a failing file. Full WIM verified
successfully with wimlib-imagex (exit 0). QCOW2 check found no structural errors;
container OOMKilled=false. The cause remains unresolved, not proven ISO corruption.

Verification used the full 6,509,992,649-byte WIM at LBA 355771. Ordinary ISO9660
extraction incorrectly yields 2,215,025,353 bytes due to the large-file size
limitation already documented for this ISO. Temporary extracted WIMs were removed
after verification; hashes and verification log are in
`artifacts/pxe-test/ffu-diagnosis-20260909/`. Original disk and ISO retained.

Additional development attempts: run 192540.581104Z reached WinPE but serial
initialization reported insufficient resources. Stopped and switched this batch
case to two CPU cores, file serial capture, and 6 GiB container headroom. Run
192914.428304Z completed PXE/capsule/UEFI and started Clonezilla, then failed before
imaging because working directories were under the read-only capsule /mnt. Fixed
the script to use /run for temporary mountpoints; current run uses that correction.

Run 193652.147350Z reached the fixture script but a pre-write assertion stopped
it before imaging. The fixed /dev/sdX assumptions were replaced with unique
serial-number discovery; current run logs resolved device mapping. Never rely
on kernel enumeration order to select a restore destination.
