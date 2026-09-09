"""Disposable Clonezilla savedisk/restoredisk fixture and independent UEFI boot proof."""
import json
import re
import uuid
from pathlib import Path
from run import execute

MARKERS = ('BMA_CLONEZILLA_STARTED', 'BMA_CLONEZILLA_SAVED',
           'BMA_CLONEZILLA_RESTORED', 'BMA_CLONEZILLA_CONTENT_VERIFIED')


def reached(serial, identity):
    # Firmware/GRUB may place ANSI cursor controls before an otherwise exact marker.
    plain = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", serial)
    lines = set(plain.splitlines())
    return all(m in lines for m in MARKERS) and 'BMA_CLONEZILLA_TARGET_BOOT_' + identity in lines


def prepare(output, capsule):
    from handoff import disk
    identity = str(uuid.uuid4())
    source = output / 'clone-source.raw'
    disk(source, uuid.uuid4())
    config = output / 'fixture-grub.cfg'
    config.write_text('serial --unit=0 --speed=115200\nterminal_output serial\necho BMA_CLONEZILLA_TARGET_BOOT_' + identity + '\nsleep 300\nhalt\n')
    execute(['grub-mkstandalone', '-O', 'x86_64-efi', '-d', '/usr/lib/grub/x86_64-efi',
             '--locales=', '--fonts=', '--modules=serial echo sleep halt',
             '-o', str(output / 'fixture.efi'), 'boot/grub/grub.cfg=' + str(config)])
    token = output / 'fixture-token.txt';token.write_text(identity + '\n')
    spec = str(source) + '@@1048576'
    execute(['mmd', '-i', spec, '::EFI', '::EFI/BOOT'])
    execute(['mcopy', '-i', spec, str(output / 'fixture.efi'), '::EFI/BOOT/BOOTX64.EFI'])
    execute(['mcopy', '-i', spec, str(token), '::BMA-FIXTURE.TXT'])
    for name, size in [('clone-target.raw', source.stat().st_size), ('clone-store.raw', 1024**3)]:
        with (output / name).open('xb') as f:f.truncate(size)
    script = r'''#!/bin/bash
set -euo pipefail
exec > >(tee /tmp/bma-clonezilla.log /dev/ttyS0) 2>&1
trap 'echo "BMA_CLONEZILLA_FAILED line=$LINENO command=$BASH_COMMAND"; cp /tmp/bma-clonezilla.log /home/partimag/bma-lab.log 2>/dev/null || true' ERR
printf '\nBMA_CLONEZILLA_STARTED\n'
# QEMU-owned disks only. Refuse any unexpected disk identity before writes.
resolve_disk() {
 local role=$1 disk
 disk=$(lsblk -dn -o NAME,SERIAL | awk -v serial="BMA_CLONE_$role" '$2 == serial {print $1}')
 test -n "$disk"
 test "$(printf '%s\n' "$disk" | wc -l)" -eq 1
 test -b "/dev/$disk"
 printf '%s' "$disk"
}
SOURCE=$(resolve_disk SOURCE)
STORE=$(resolve_disk STORE)
TARGET=$(resolve_disk TARGET)
echo "BMA disk mapping: source=$SOURCE store=$STORE target=$TARGET"
test "$SOURCE" != "$STORE" && test "$SOURCE" != "$TARGET" && test "$STORE" != "$TARGET"
mkdir -p /run/bma-source /run/bma-target /home/partimag
mount -o ro /dev/${SOURCE}1 /run/bma-source
test "$(cat /run/bma-source/BMA-FIXTURE.TXT)" = "IDENTITY"
sha256sum /run/bma-source/EFI/BOOT/BOOTX64.EFI | cut -d' ' -f1 > /tmp/bma-efi.sha256
umount /run/bma-source
mkfs.ext4 -F -L BMA_IMAGES /dev/$STORE
mount /dev/$STORE /home/partimag
ocs-sr -batch -q2 -j2 -z1 -sfsck -senc -p true savedisk bma-fixture "$SOURCE"
echo BMA_CLONEZILLA_SAVED
ocs-sr -batch -k0 -iefi -ssnf -p true restoredisk bma-fixture "$TARGET"
echo BMA_CLONEZILLA_RESTORED
mount -o ro /dev/${TARGET}1 /run/bma-target
test "$(cat /run/bma-target/BMA-FIXTURE.TXT)" = "IDENTITY"
test "$(sha256sum /run/bma-target/EFI/BOOT/BOOTX64.EFI | cut -d' ' -f1)" = "$(cat /tmp/bma-efi.sha256)"
umount /run/bma-target
echo BMA_CLONEZILLA_CONTENT_VERIFIED
# Remove the disposable source bootloader and randomize its GPT identifiers.
# A duplicated partition GUID must not let firmware resolve BootNext to source.
mount /dev/${SOURCE}1 /run/bma-source
rm /run/bma-source/EFI/BOOT/BOOTX64.EFI
umount /run/bma-source
sgdisk -G /dev/$SOURCE
oldorder=$(efibootmgr | sed -n 's/^BootOrder: //p')
efibootmgr -c -d /dev/$TARGET -p 1 -L BMA-Clonezilla-Target -l '\EFI\BOOT\BOOTX64.EFI'
entry=$(efibootmgr | sed -n '/BMA-Clonezilla-Target/s/^Boot\([0-9A-Fa-f]\{4\}\).*/\1/p')
test ${#entry} -eq 4
efibootmgr -o "$oldorder"
efibootmgr -n "$entry"
cp /tmp/bma-clonezilla.log /home/partimag/bma-lab.log
sync
reboot
'''.replace('IDENTITY', identity)
    (capsule / 'clonezilla-test.sh').write_text(script)
    (output / 'clonezilla.json').write_text(json.dumps({'identity': identity,
        'scope': 'Clonezilla whole-disk save/restore of small FAT UEFI fixture; target boot proof',
        'not_tested': ['customer OS restoration', 'Heimdal', 'Secure Boot', 'physical hardware']}, indent=2)+'\n')
    return identity


def config():
    return '''serial --unit=0 --speed=115200
terminal_output serial console
echo BMA_CLONEZILLA_GRUB_STARTED
search --no-floppy --file --set=root /live/vmlinuz
linux /live/vmlinuz boot=live union=overlay noeject noprompt username=user config components noswap edd=on nomodeset locales=en_US.UTF-8 keyboard-layouts=us console=tty0 console=ttyS0,115200n8 ocs_live_batch=yes ocs_prerun="mount -o ro LABEL=BMA_LAB /mnt" ocs_live_run="bash /mnt/clonezilla-test.sh" systemd.default_device_timeout_sec=600
initrd /live/initrd.img
boot
'''


def drives(output):
    result=[]
    for bus, (name, serial) in enumerate([('source','SOURCE'),('store','STORE'),('target','TARGET')], start=3):
        result += ['-drive', f'if=none,id=clone{name},format=raw,file={output / ("clone-"+name+".raw")}',
                   '-device', f'ide-hd,drive=clone{name},bus=ide.{bus},serial=BMA_CLONE_{serial}']
    return result
