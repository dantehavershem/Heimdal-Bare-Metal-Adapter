"""LAB ONLY: apply Windows index 1 to a newly created, disposable QEMU disk."""
import json
import shutil
import uuid
from pathlib import Path
from run import execute

MARKERS = ('BMA_WINDOWS_IMAGE_APPLIED', 'BMA_WINDOWS_BOOT_CONFIGURED',
           'BMA_WINDOWS_RECOVERY_CONFIGURED', 'BMA_WINDOWS_FIRST_BOOT')


def evidence(serial, identity):
    lines = set(serial.splitlines())
    return ({marker: marker in lines for marker in MARKERS},
            'BMA_WINDOWS_FIRST_BOOT_' + identity in lines)


def prepare(output, payload, disk_root):
    if shutil.disk_usage(disk_root).free < 40 * 1024**3:
        raise ValueError('Windows lab requires 40 GiB free on external test storage')
    target = disk_root / output.name
    target.mkdir()  # Refuse reuse; no existing disk may be attached to this test.
    disk = target / 'windows.qcow2'
    execute(['qemu-img', 'create', '-f', 'qcow2', str(disk), '64G'])
    capsule = output / 'windows-capsule'; capsule.mkdir()
    identity = str(uuid.uuid4())
    (capsule / 'BMA-WINDOWS-LAB.TXT').write_text(identity + '\r\n')
    shutil.copyfile(payload/'SETUP.EXE', capsule/'SETUP.EXE')
    def batch(name, text):
        (capsule/name).write_bytes(text.replace('\n','\r\n').encode())
    batch('PARTITION.TXT', '''select disk 0
clean
convert gpt
create partition efi size=260
format quick fs=fat32 label="BMA EFI"
assign letter=S
create partition msr size=16
create partition primary
shrink minimum=2048
format quick fs=ntfs label="BMA Windows"
assign letter=W
create partition primary
format quick fs=ntfs label="BMA Recovery"
assign letter=R
set id=de94bba4-06d1-4d40-a16a-bfd50179d6ac
gpt attributes=0x8000000000000001
exit
''')
    # Runs from the installed Windows partition during specialize, not from PE.
    batch('FIRSTBOOT.CMD', r'''@echo off
call :verify > "%~dp0FIRSTBOOT.LOG" 2>&1
exit /b %errorlevel%
:verify
echo BMA_WINDOWS_VERIFY_STARTED %date% %time%
if /i not "%SystemDrive%"=="C:" exit /b 91
reg query HKLM\SYSTEM\CurrentControlSet\Control\MiniNT > nul 2>&1
if not errorlevel 1 exit /b 93
reg add "HKLM\SYSTEM\CurrentControlSet\Enum\ACPI\PNP0501\1\Device Parameters" /v PortName /t REG_SZ /d COM1 /f
pnputil /restart-device "ACPI\PNP0501\1"
set /a TRIES=30
:retry
(echo BMA_WINDOWS_FIRST_BOOT_IDENTITY) > COM1 && goto done
set /a TRIES-=1
if %TRIES% LEQ 0 exit /b 94
ping -n 2 127.0.0.1 > nul
goto retry
:done
ver > COM1
(echo BMA_WINDOWS_FIRST_BOOT) > COM1
exit /b 0
'''.replace('BMA_WINDOWS_FIRST_BOOT_IDENTITY', 'BMA_WINDOWS_FIRST_BOOT_'+identity))
    (capsule/'unattend.xml').write_text('''<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend" xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
<settings pass="specialize"><component name="Microsoft-Windows-Deployment" processorArchitecture="amd64" publicKeyToken="31bf3856ad364e35" language="neutral" versionScope="nonSxS">
<RunSynchronous><RunSynchronousCommand wcm:action="add"><Order>1</Order><Path>cmd.exe /c C:\\BMA-LAB\\FIRSTBOOT.CMD</Path></RunSynchronousCommand></RunSynchronous>
</component></settings></unattend>
''')
    batch('STAGE.CMD', r'''@echo off
cd /d "%~dp0"
set "SOURCE="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do if exist %%D:\sources\install.wim set "SOURCE=%%D:\sources\install.wim"
if not defined SOURCE goto failed
for %%F in ("%SOURCE%") do if not "%%~zF"=="6509992649" goto failed
(echo BMA_WINDOWS_SOURCE_SIZE_VERIFIED_6509992649) > COM1
dism /Get-WimInfo /WimFile:"%SOURCE%" /Index:1 > COM1 2>&1
if errorlevel 1 goto failed
diskpart /s PARTITION.TXT > COM1 2>&1
if errorlevel 1 goto failed
if not exist S:\ goto failed
if not exist W:\ goto failed
if not exist R:\ goto failed
mkdir W:\scratch
(echo BMA_WINDOWS_APPLY_STARTED) > COM1
dism /Apply-Image /ImageFile:"%SOURCE%" /Index:1 /ApplyDir:W:\ /CheckIntegrity /ScratchDir:W:\scratch /LogPath:W:\apply.log > COM1 2>&1
if errorlevel 1 goto failed
(echo BMA_WINDOWS_IMAGE_APPLIED) > COM1
W:\Windows\System32\bcdboot W:\Windows /s S: /f UEFI > COM1 2>&1
if errorlevel 1 goto failed
if not exist S:\EFI\Microsoft\Boot\BCD goto failed
(echo BMA_WINDOWS_BOOT_CONFIGURED) > COM1
mkdir R:\Recovery\WindowsRE
copy /b W:\Windows\System32\Recovery\winre.wim R:\Recovery\WindowsRE\winre.wim > COM1 2>&1
if errorlevel 1 goto failed
W:\Windows\System32\reagentc /Setreimage /Path R:\Recovery\WindowsRE /Target W:\Windows > COM1 2>&1
if errorlevel 1 goto failed
(echo BMA_WINDOWS_RECOVERY_CONFIGURED) > COM1
mkdir W:\BMA-LAB
copy /b FIRSTBOOT.CMD W:\BMA-LAB\FIRSTBOOT.CMD > nul || goto failed
if not exist W:\Windows\Panther mkdir W:\Windows\Panther
copy /b unattend.xml W:\Windows\Panther\unattend.xml > nul || goto failed
(echo BMA_WINDOWS_REBOOT_REQUESTED) > COM1
wpeutil reboot
exit /b 99
:failed
(echo BMA_WINDOWS_APPLY_FAILED) > COM1
exit /b 90
''')
    execute(['xorriso','-as','mkisofs','-quiet','-J','-R','-V','BMA_WIN_LAB','-o',str(output/'windows-capsule.iso'),str(capsule)])
    (output/'windows-apply.json').write_text(json.dumps({'disk':str(disk),'index':1,'identity':identity,
        'scope':'Disposable disk image application and installed Windows specialize pass; no Heimdal integration'},indent=2)+'\n')
    startup=r'''set "CAPSULE="
for %%D in (C D E F G H I J K L M N O P Q R S T U V W Y Z) do if exist %%D:\BMA-WINDOWS-LAB.TXT (
 for /f "usebackq delims=" %%I in ("%%D:\BMA-WINDOWS-LAB.TXT") do if "%%I"=="IDENTITY" set "CAPSULE=%%D:"
)
if not defined CAPSULE goto serial_failed
"%CAPSULE%\SETUP.EXE"
(echo BMA_WINDOWS_APPLY_FAILED) > COM1
'''.replace('IDENTITY',identity)
    return disk, startup, identity
