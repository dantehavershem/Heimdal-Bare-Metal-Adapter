"""LAB ONLY: fresh WIM reference -> FFU -> separate blank disk -> specialize."""
import json
import shutil
import uuid
import windows_apply
from run import execute

MARKERS = ('BMA_FFU_CAPTURED', 'BMA_FFU_APPLIED', 'BMA_FFU_LAYOUT_VERIFIED',
           'BMA_FFU_TARGET_FIRST_BOOT')


def evidence(serial, identity):
    markers, matched = windows_apply.evidence(serial, identity)
    lines = set(serial.splitlines())
    markers.update({marker: marker in lines for marker in MARKERS})
    return markers, matched


def prepare(output, payload, disk_root):
    if shutil.disk_usage(disk_root).free < 75 * 1024**3:
        raise ValueError('FFU lab requires 75 GiB free on external test storage')
    source, startup, identity = windows_apply.prepare(output, payload, disk_root)
    target = source.parent / 'ffu-target.qcow2'
    store = source.parent / 'ffu-storage.qcow2'
    execute(['qemu-img', 'create', '-f', 'qcow2', str(store), '48G'])
    execute(['qemu-img', 'create', '-f', 'qcow2', str(target), '64G'])
    capsule = output / 'windows-capsule'
    def batch(name, text):
        (capsule / name).write_bytes(text.replace('\n', '\r\n').encode())
    # Source disk 0, NTFS image storage disk 1, blank restore target disk 2.
    batch('FFU-STORAGE.TXT', '''select disk 1
clean
convert gpt
create partition primary
format quick fs=ntfs label="BMA FFU"
assign letter=V
exit
''')
    batch('FFU-OFFLINE.TXT', f'''select volume S
remove letter=S
select volume W
remove letter=W
select volume R
remove letter=R
select disk 0
uniqueid disk id={uuid.uuid4()}
offline disk
select disk 2
clean
exit
''')
    batch('FFU-MOUNT.TXT', '''select disk 2
online disk
select partition 1
assign letter=S
select partition 3
assign letter=W
select partition 4
assign letter=R
detail partition
list partition
exit
''')
    first = (capsule / 'FIRSTBOOT.CMD').read_text()
    first = first.replace(':verify\n', ':verify\nif not exist C:\\BMA-LAB\\FFU-RESTORED-' + identity + '.TXT exit /b 95\n', 1)
    first = first.replace('ver > COM1', '(echo BMA_FFU_TARGET_FIRST_BOOT) > COM1\nver > COM1')
    batch('FIRSTBOOT.CMD', first)
    stage = (capsule / 'STAGE.CMD').read_text()
    stage = stage.replace('(echo BMA_WINDOWS_REBOOT_REQUESTED) > COM1', r'''diskpart /s FFU-STORAGE.TXT > COM1 2>&1
if errorlevel 1 goto failed
if not exist V:\ goto failed
mkdir V:\scratch
(echo BMA_FFU_CAPTURE_STARTED) > COM1
dism /Capture-FFU /ImageFile:V:\baseline.ffu /CaptureDrive:\\.\PhysicalDrive0 /Name:BMA-Windows-Baseline /ScratchDir:V:\scratch /LogPath:V:\capture.log > COM1 2>&1
if errorlevel 1 goto failed
if not exist V:\baseline.ffu goto failed
(echo BMA_FFU_CAPTURED) > COM1
dism /Get-ImageInfo /ImageFile:V:\baseline.ffu > COM1 2>&1
if errorlevel 1 goto failed
diskpart /s FFU-OFFLINE.TXT > COM1 2>&1
if errorlevel 1 goto failed
(echo BMA_FFU_APPLY_STARTED) > COM1
dism /Apply-FFU /ImageFile:V:\baseline.ffu /ApplyDrive:\\.\PhysicalDrive2 /ScratchDir:V:\scratch /LogPath:V:\restore.log > COM1 2>&1
if errorlevel 1 goto failed
(echo BMA_FFU_APPLIED) > COM1
diskpart /s FFU-MOUNT.TXT > COM1 2>&1
if errorlevel 1 goto failed
if not exist S:\EFI\Microsoft\Boot\BCD goto failed
if not exist W:\Windows\System32\ntoskrnl.exe goto failed
if not exist R:\Recovery\WindowsRE\winre.wim goto failed
if not exist W:\BMA-LAB\FIRSTBOOT.CMD goto failed
bcdedit /store S:\EFI\Microsoft\Boot\BCD /enum all > COM1 2>&1
if errorlevel 1 goto failed
(echo BMA_FFU_LAYOUT_VERIFIED) > COM1
(echo IDENTITY) > W:\BMA-LAB\FFU-RESTORED-IDENTITY.TXT
if errorlevel 1 goto failed
(echo BMA_WINDOWS_REBOOT_REQUESTED) > COM1'''.replace('IDENTITY', identity))
    batch('STAGE.CMD', stage)
    (output / 'windows-capsule.iso').unlink()  # Only this run's generated capsule.
    execute(['xorriso', '-as', 'mkisofs', '-quiet', '-J', '-R', '-V', 'BMA_WIN_LAB',
             '-o', str(output / 'windows-capsule.iso'), str(capsule)])
    (output / 'windows-ffu.json').write_text(json.dumps({
        'source_disk': str(source), 'storage_disk': str(store), 'target_disk': str(target),
        'identity': identity, 'ffu_path_in_guest': 'V:\\baseline.ffu',
        'scope': 'Unbooted stock WIM reference; FFU capture/restore and restored target specialize',
        'not_tested': ['customer Sysprep capture', 'optimized FFU / different disk sizes',
                       'OOBE completion', 'WinRE boot', 'Heimdal delivery']}, indent=2) + '\n')
    return source, startup, identity


def drives(source):
    return [
        '-drive', f'if=none,id=ffustore,format=qcow2,file={source.parent / "ffu-storage.qcow2"}',
        '-device', 'ide-hd,drive=ffustore,bus=ide.1,unit=0',
        '-drive', f'if=none,id=ffutarget,format=qcow2,file={source.parent / "ffu-target.qcow2"}',
        '-device', 'ide-hd,drive=ffutarget,bus=ide.4,unit=0,bootindex=1']
