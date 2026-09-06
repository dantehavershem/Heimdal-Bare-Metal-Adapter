# Disposable WinPE BootNext handoff lab

This lab extends the verified diskless PXE/WinPE launcher test with a generated
capsule ISO and a disposable GPT/FAT staging disk. It is not the production
capsule builder, a Heimdal server integration, or an installer deployment.

## Build and run

Build the trixie base image as described in `PXE_TEST_LAB.md`, then:

```bash
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.handoff-test.yml build pxe-test
docker compose -f compose.pxe-test.yml -f compose.winpe-test.yml \
  -f compose.handoff-test.yml run --rm --name heimdal-handoff-test \
  --entrypoint python3 \
  --volume /media/sf_Downloads/_torrents_done/CCSA_X64FRE_DE-DE_DV9.ISO:/winpe.iso:ro \
  pxe-test /src/tools/pxe-test/network_winpe.py --handoff
```

Add `--missing-stage` to generate a capsule with its EFI payload absent. This
control must return the expected rejection through the actual root `SETUP.EXE`,
without a firmware handoff or guest reset. Cases run sequentially and require
at least 5120 MiB available host RAM.

## Capsule and target identification

`tools/pxe-test/handoff.py` creates `capsule.iso`, its extracted `capsule/` tree,
`capsule-build.json`, and a sparse `staging.raw` disk in the per-run artifact
directory. The disk has a new GPT partition UUID and a matching marker file.
The capsule contains the actual root `SETUP.EXE`, `STAGE.CMD`, `deployment.json`,
a native `HANDOFF.EXE`, and `runtime/` with an EFI payload and boot option.

WinPE discovers the capsule and staging volume by matching their per-run markers.
It does not partition or format a disk. Only the host lab builder creates the
new disposable disk file. A FAT basic-data partition permits WinPE drive-letter
assignment; the UEFI boot option identifies that GPT partition explicitly and
uses `\\EFI\\BMA\\stage.efi`. No removable-media fallback path is installed.

The script refuses to overwrite an existing `EFI/BMA` directory. Its native
helper verifies staged files byte-for-byte before touching firmware variables.
The minimal Windows ISO does not contain `findstr`; media discovery uses built-in
`for /f`. The test retains the COM1 readiness retry established in the PXE lab.

## One-time firmware handoff

The helper enables `SeSystemEnvironmentPrivilege`, refuses an existing `BootNext`
or lab audit variable, snapshots `BootOrder`, allocates an unused `BootB0xx`
entry, and writes `BootNext`. It reads back the entry and `BootNext`, confirms
`BootOrder` is unchanged, and only then allows `wpeutil reboot`. Failed writes
trigger cleanup attempts and a nonzero exit without requesting a reboot.

The EFI proof independently verifies the original boot order, absence of
`BootNext`, and the matching `BootCurrent`. It deletes its temporary boot entry
and audit variable and verifies their absence. Test telemetry uses QEMU debug
ports; this is lab-specific code, not a production UEFI runtime.

The harness requires actual WinPE serial evidence, exactly one guest-requested
QMP RESET event, EFI verification markers, and successful QEMU debug exit. It
also retains the existing DHCP/TFTP and complete HTTP-transfer checks. Handoff
captures retain 128 bytes per packet to limit disk use; full response sizes and
digests remain in the HTTP log. Initial proof runs used 512 bytes per packet.
`qmp.sock` is reserved for event capture; use `qmp-control.sock` with `qmp.py` for
screenshots or diagnosis. All guest media, firmware, and artifacts are recorded
per run. Shared ISO inputs remain read-only and no host disk is attached.

Firmware API behavior follows Microsoft's
[SetFirmwareEnvironmentVariableExW documentation](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setfirmwareenvironmentvariableexw).

## Ubuntu extension

After the proof passes, build the Ubuntu lab image using `compose.ubuntu-test.yml`
in place of `compose.handoff-test.yml`. It adds x86-64 GRUB EFI modules to the
ARM64 build environment; foreign executables are not needed for compilation.

Use the same run command with the Ubuntu Compose file, add the read-only volume
`/media/sf_Downloads/_torrents_done/ubuntu-26.04.1-live-server-amd64.iso:/ubuntu.iso:ro`,
and append `--ubuntu-iso /ubuntu.iso` after `--handoff`.

The generated EFI stage first verifies and cleans up the handoff, then loads
`grub.efi` from the same staging volume. GRUB's embedded configuration searches
for the original ISO's Casper kernel and loads its kernel/initrd. The source ISO
is attached read-only, not copied into the capsule. No autoinstall or disk-write
instructions are provided. A pass requires Linux kernel output and the live
Ubuntu installer welcome screen, in addition to all handoff evidence; GRUB or a kernel
banner alone is insufficient.

The production API build queue, external output storage workflow, signed payloads,
physical-machine disk selection and cleanup, recovery from interrupted firmware
updates, and actual Heimdal deployment remain separate work.

## Verified handoff result — 2026-09-06

`artifacts/pxe-test/winpe-pxe-20260906T010359.765597Z/` passed the UEFI handoff
proof in 175.6 seconds. The guest ran the capsule's root launcher without
keyboard input, staged its runtime, and requested exactly one QMP guest RESET.
The EFI payload verified preserved BootOrder, consumed BootNext, and cleanup of
the temporary boot entry and audit variable. QEMU exited with code 33.

Capsule SHA-256:
`288cb6d4838ade8314b5004444c3112855d178427b615a20ba020cc1f91c727d`.

This run predates the additional BootCurrent-match and cleanup-readback checks;
the final Ubuntu variant includes those stricter checks. The original two
contract-test markers are deliberately absent in handoff runs: the actual
capsule executes its handoff script instead of the old exit-37 test fixture.
Read the case-specific `handoff_markers` and `uefi_markers` fields.

Earlier runs `winpe-pxe-20260906T005548.458491Z` and
`winpe-pxe-20260906T010005.453279Z` were stopped after diagnosing the absent
`findstr` utility. Their captures were losslessly compressed to `network.pcap.gz`
to preserve evidence while freeing lab disk space. They are not passes.

The missing-payload control also passed:
`winpe-pxe-20260906T010801.293915Z`, 168.9 seconds, zero guest resets, expected
launcher rejection, and no handoff or EFI execution markers.

Use `--invalid-stage` instead of `--missing-stage` to test a non-EFI payload.
The native helper compares staged bytes and validates AMD64 PE32+ / EFI
application headers before firmware access. This control requires the specific
invalid-image error, propagation through the capsule launcher, and zero resets.

## Disk cleanup requested by user — 2026-09-06

Unused Docker build cache and the obsolete Bookworm `pxe-test:latest` image were
removed. Rebuild that legacy image explicitly if it is ever needed again. The
trixie, handoff, and Ubuntu images and appliance data volumes remain available.

Large completed packet captures were replaced by `network-prefix.pcap.gz`,
containing the first approximately 2 MiB of complete packet records. Each affected
run has `capture-retention.json` with the original full capture's SHA-256 and
uncompressed byte count. Full original packet captures for those runs are no
longer retained. Reports, serial/debug logs, HTTP transfer digests, QMP events,
firmware snapshots, generated capsule files, and source ISOs were preserved.
This supersedes the earlier lossless-compression-only retention description.

Free space increased from 831 MiB to 5.3 GiB; lab artifacts decreased from about
1.8 GiB to 111 MiB while the next test was active. Future tests still consume some
space. No appliance volume or active guest artifact was removed.

The invalid-EFI control passed:
`winpe-pxe-20260906T011119.375712Z`, 185.8 seconds, native error 35 propagated
as capsule exit 66, zero guest resets, and no firmware handoff markers. The
helper rejects the malformed image before opening a firmware-privileged token.


The first Ubuntu attempt, `winpe-pxe-20260906T011505.608035Z`, booted the source
DVD directly rather than PXE. It was stopped and did not pass: no HTTP transfers
or handoff markers were present. Handoff runs now use explicit NIC `bootindex=1`
instead of relying on the legacy `-boot order=n` hint when a bootable DVD is
attached. BootNext still overrides that normal network-first order for the single
handoff reboot.


### Ubuntu serial-console diagnosis

`winpe-pxe-20260906T011741.080830Z` completed the stricter firmware proof and
reached the Ubuntu 26.04.1 LTS live tty2 shell (Linux 7.0.0-30-generic). It was
stopped as a diagnostic. TCG device initialization exceeded the default 90-second
systemd wait; the ttyS0 device later became active, verified in `serial-device.png`.
The serial service was manually restarted to inspect it. `serial-unit.png` shows
that it starts Subiquity via snap rather than a normal getty login prompt.

Subsequent generated GRUB configurations include
`systemd.default_device_timeout_sec=600`, supported by the
[systemd kernel-command-line interface](https://github.com/systemd/systemd/blob/main/man/kernel-command-line.xml).
This lab allowance changes neither the vendor ISO nor its initrd.

Ubuntu runs now use a bidirectional serial socket. `serial_terminal.py` answers
cursor-position, size, and terminal-capability queries so the installer can
initialize its terminal. Only raw guest output goes to `serial.log`; responses
are input bytes and cannot fabricate evidence. The harness requires the installer Serial welcome text and both mode buttons,
or the Welcome/English language screen, with kernel and all handoff checks still
required. A login banner alone is insufficient. Four responder tests cover split queries, multiple queries,
unsupported capabilities, and never echoing guest evidence as input.


`winpe-pxe-20260906T013237.431234Z` reached the actual Subiquity Serial welcome
screen, with all stricter firmware checks, one reset, and eight HTTP transfers.
Its in-memory check expected the later language screen, so it was stopped as a
diagnostic; its interrupted report remains unchanged. Ctrl-Alt-F2 was sent for
observation, without commands or service changes. The vendor snap's Serial view
confirms this is the expected first serial screen. Five readiness tests now cover
that screen, language welcome, and rejection of incomplete/banner-only evidence.
The fresh automatic run, `winpe-pxe-20260906T015249.555025Z`, **passed in
1046.2 seconds**. The actual Subiquity Serial welcome screen appeared with no
keyboard input or manual service restart. All eight complete HTTP transfers,
DHCP/TFTP, three WinPE handoff markers, six EFI proof markers, and exactly one
guest RESET were verified. The serial responder sent five protocol-response
batches; the serial log contains genuine guest output. The test container exited
successfully and was automatically removed. No installation to disk occurred.

The historical exit-37 fixture's stage/bridge fields are false in this report by
design: this capsule executes a handoff, not the exit-37 fixture. Use the report's
case-specific handoff/UEFI fields and `ubuntu_userspace_reached` to assess it.
This proves the isolated lab boot path, not actual Heimdal deployment, production
capsule generation, physical hardware support, or Secure Boot.


Final cleanup after the automatic pass: four newer full captures (invalid EFI,
two Ubuntu diagnostics, and the passing Ubuntu run) were losslessly gzipped and
their decompressed SHA-256 verified. Their retention records identify full
capture retention; earlier prefix-only records remain explicitly distinct.
The extracted temporary Subiquity snap and new web build cache were removed.
Final disk free space: 5.2 GiB; retained lab artifacts: 264 MiB. No test guest is
running. Appliance health is OK and shared storage remains read-only.

The dashboard's recorded milestones now include the Ubuntu pass. Frontend build,
four browser tests, and a live check of the new run ID passed. Nine terminal and
readiness unit tests passed. The shutdown checkpoint following `cebd798` includes these changes; detailed
lab artifacts and source ISOs remain local and are excluded from Git.
