"""Generate a lab-only capsule and uniquely identified disposable GPT staging disk."""
import hashlib
import json
import shutil
import struct
import subprocess
import uuid
import zlib
from pathlib import Path
from run import execute

SOURCE = Path('/src/tools/pxe-test/handoff')
MARKERS = ('BMA_HANDOFF_BOOTNEXT_SET', 'BMA_HANDOFF_BOOTORDER_UNCHANGED', 'BMA_HANDOFF_REBOOT_REQUESTED')
PROOF_MARKERS = ('BMA_HANDOFF_UEFI_REACHED', 'BMA_HANDOFF_BOOTORDER_PRESERVED',
                 'BMA_HANDOFF_BOOTNEXT_CONSUMED', 'BMA_HANDOFF_BOOTCURRENT_MATCHED', 'BMA_HANDOFF_VARIABLES_CLEANED', 'BMA_HANDOFF_PROOF_PASSED')


def disk(path, identity):
    # A basic-data FAT partition is intentional: WinPE assigns it a drive letter.
    # UEFI BootNext uses a GPT partition device path, not the removable-media path.
    first, count, sectors = 2048, 131072, 135168
    entries = bytearray(16384)
    struct.pack_into('<16s16sQQQ72s', entries, 0,
                     uuid.UUID('ebd0a0a2-b9e5-4433-87c0-68b6b72699c7').bytes_le,
                     identity.bytes_le, first, first+count-1, 0, 'BMA Lab Stage'.encode('utf-16le'))
    disk_id = uuid.uuid4()
    def header(current, backup, table):
        h = bytearray(512)
        struct.pack_into('<8sIIIIQQQQ16sQIII', h, 0, b'EFI PART', 0x10000, 92, 0, 0,
                         current, backup, 34, sectors-34, disk_id.bytes_le, table, 128, 128, zlib.crc32(entries))
        struct.pack_into('<I', h, 16, zlib.crc32(h[:92]))
        return h
    with path.open('xb') as f:
        f.truncate(sectors*512)
        mbr=bytearray(512)
        struct.pack_into('<B3sB3sII',mbr,446,0,b'\0\2\0',0xee,b'\xff'*3,1,sectors-1)
        mbr[510:]=b'\x55\xaa';f.write(mbr);f.write(header(1,sectors-1,2));f.write(entries)
        f.seek((sectors-33)*512);f.write(entries);f.write(header(sectors-1,1,sectors-33))
    execute(['mkfs.fat','-F','32','-n','BMA_STAGE','--offset=2048',str(path),'65536'])
    return first,count


def prepare(output, payload, missing=False, ubuntu=None, invalid=False):
    capsule=output/'capsule';capsule.mkdir();runtime=capsule/'runtime';runtime.mkdir()
    identity=uuid.uuid4()
    first,count=disk(output/'staging.raw',identity)
    marker=output/'BMA-TARGET.TXT';marker.write_text(str(identity)+'\r\n')
    execute(['mcopy','-i',str(output/'staging.raw')+'@@1048576',str(marker),'::BMA-TARGET.TXT'])
    compiler=['clang','--target=x86_64-pc-windows-msvc','-ffreestanding','-fno-stack-protector','-fshort-wchar','-O1','-c']
    execute(compiler+[str(SOURCE/'firmware.c'),'-o',str(output/'firmware.obj')])
    for lib in ('kernel32','advapi32'):
        execute(['llvm-dlltool','-m','i386:x86-64','-d',str(SOURCE/(lib+'.def')),'-l',str(output/(lib+'.lib'))])
    execute(['lld-link','/entry:mainCRTStartup','/subsystem:console','/nodefaultlib',
             '/out:'+str(capsule/'HANDOFF.EXE'),str(output/'firmware.obj'),str(output/'kernel32.lib'),str(output/'advapi32.lib')])
    execute(compiler+(['-DUBUNTU_TEST'] if ubuntu else [])+[str(SOURCE/'proof.c'),'-o',str(output/'handoff-proof.obj')])
    execute(['lld-link','/entry:efi_main','/subsystem:efi_application','/nodefaultlib',
             '/out:'+str(runtime/'stage.efi'),str(output/'handoff-proof.obj')])
    if ubuntu:
        config=output/'grub.cfg'
        config.write_text('serial --unit=0 --speed=115200\nterminal_output serial console\necho BMA_UBUNTU_GRUB_STARTED\nsearch --no-floppy --file --set=root /casper/vmlinuz\nlinux /casper/vmlinuz boot=casper console=tty0 console=ttyS0,115200n8 systemd.default_device_timeout_sec=600\ninitrd /casper/initrd\nboot\n')
        execute(['grub-mkstandalone','-O','x86_64-efi','-d','/usr/lib/grub/x86_64-efi',
                 '--locales=','--fonts=','--modules=part_gpt part_msdos fat iso9660 serial search search_fs_file linux normal',
                 '-o',str(runtime/'grub.efi'),'boot/grub/grub.cfg='+str(config)])
    shutil.copyfile(payload/'SETUP.EXE' ,capsule/'SETUP.EXE')
    # EFI_LOAD_OPTION, hard-drive node, file-path node, end node.
    name='Bare-Metal Adapter lab\0'.encode('utf-16le')
    target='\\EFI\\BMA\\stage.efi\0'.encode('utf-16le')
    device=(struct.pack('<BBHIQQ16sBB',4,1,42,1,first,count,identity.bytes_le,2,2)
            +struct.pack('<BBH',4,4,len(target)+4)+target+b'\x7f\xff\x04\0')
    (runtime/'boot-option.bin').write_bytes(struct.pack('<IH',1,len(device))+name+device)
    stage=r'''@echo off
cd /d "%~dp0"
if not exist runtime\stage.efi goto missing
set "BMA_TARGET="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do if exist %%D:\BMA-TARGET.TXT (
  for /f "usebackq delims=" %%I in ("%%D:\BMA-TARGET.TXT") do if "%%I"=="IDENTITY" set "BMA_TARGET=%%D:"
)
if not defined BMA_TARGET exit /b 61
if exist "%BMA_TARGET%\EFI\BMA" exit /b 62
mkdir "%BMA_TARGET%\EFI\BMA" || exit /b 63
copy /b runtime\stage.efi "%BMA_TARGET%\EFI\BMA\stage.efi" > nul || exit /b 64
if exist runtime\grub.efi copy /b runtime\grub.efi "%BMA_TARGET%\EFI\BMA\grub.efi" > nul || exit /b 68
HANDOFF.EXE
if errorlevel 1 exit /b 66
(echo BMA_HANDOFF_REBOOT_REQUESTED) > COM1
wpeutil reboot
exit /b 67
:missing
(echo BMA_HANDOFF_MISSING_PAYLOAD) > COM1
exit /b 60
'''.replace('IDENTITY',str(identity))
    (capsule/'STAGE.CMD').write_bytes(stage.replace('\n','\r\n').encode())
    (capsule/'BMA-CAPSULE.TXT').write_text(str(identity)+'\r\n')
    if missing:(runtime/'stage.efi').unlink()
    if invalid:(runtime/'stage.efi').write_bytes(b'Invalid EFI test payload\n')
    manifest={'schema_version':1,'scope':'Disposable-VM BootNext proof only',
              'target_partition_guid':str(identity),'normal_boot_order':'preserve',
              'secure_boot':False,'linux_adapter':'Ubuntu Casper on attached read-only source ISO' if ubuntu else 'not included',
              'source_iso':str(ubuntu) if ubuntu else None,
              'files':{str(p.relative_to(capsule)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in capsule.rglob('*') if p.is_file()}}
    (capsule/'deployment.json').write_text(json.dumps(manifest,indent=2)+'\n')
    execute(['xorriso','-as','mkisofs','-quiet','-J','-R','-V','BMA_LAB','-o',str(output/'capsule.iso'),str(capsule)])
    metadata={'capsule_sha256':hashlib.sha256((output/'capsule.iso').read_bytes()).hexdigest(),**manifest}
    (output/'capsule-build.json').write_text(json.dumps(metadata,indent=2)+'\n')
    startup=r'''set "BMA_CAPSULE="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do if exist %%D:\BMA-CAPSULE.TXT (
  for /f "usebackq delims=" %%I in ("%%D:\BMA-CAPSULE.TXT") do if "%%I"=="IDENTITY" set "BMA_CAPSULE=%%D:"
)
if not defined BMA_CAPSULE goto serial_failed
"%BMA_CAPSULE%\SETUP.EXE"
set "BMA_RESULT=%ERRORLEVEL%"
echo Capsule returned %BMA_RESULT%
(echo BMA_HANDOFF_CAPSULE_EXIT_%BMA_RESULT%) > COM1
if "%BMA_RESULT%"=="60" (echo BMA_HANDOFF_REJECTED_MISSING) > COM1
'''.replace('IDENTITY',str(identity))
    return startup
