#!/usr/bin/env python3
"""Boot a supplied WinPE ISO with a disposable launcher-test volume."""
import argparse
import datetime
import json
import hashlib
import shutil
import subprocess
import time
from pathlib import Path
from run import build

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--memory-mib', type=int, default=4096,
                    help='Guest RAM in MiB (default: 4096); ISO requirements still apply')
parser.add_argument('--guest-cpus', type=int, default=2,
                    help='Emulated guest CPU count (default: 2)')
parser.add_argument('--firmware-code', type=Path,
                    default=Path('/usr/share/OVMF/OVMF_CODE.fd'))
parser.add_argument('--firmware-vars', type=Path,
                    default=Path('/usr/share/OVMF/OVMF_VARS.fd'))
args = parser.parse_args()
for firmware in (args.firmware_code, args.firmware_vars):
    if not firmware.is_file():
        parser.error(f'Firmware file not found: {firmware}')
if args.guest_cpus <= 0:
    parser.error('--guest-cpus must be positive')
if args.memory_mib <= 0:
    parser.error('--memory-mib must be positive')
# On Linux, /proc/meminfo exposes the outer VM's memory even in this container.
# Leave room for QEMU overhead and the running appliance; swap is not headroom.
meminfo = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
available_mib = int(meminfo['MemAvailable'].split()[0]) // 1024
required_mib = args.memory_mib + 1024
if available_mib < required_mib:
    parser.error(
        f'WinPE needs {required_mib} MiB available RAM '
        f'({args.memory_mib} MiB guest + 1024 MiB reserve); '
        f'only {available_mib} MiB is available. Increase the outer VM RAM '
        'or run the test on another machine.'
    )

output=Path('/output')/('winpe-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
output.mkdir(parents=True)
capsule=output/'capsule';capsule.mkdir()
artifacts=build(capsule)
shutil.copyfile(args.firmware_vars,output/'vars.fd')
command=['qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max','-m',str(args.memory_mib),'-smp',str(args.guest_cpus),
         '-drive',f'if=pflash,format=raw,readonly=on,file={args.firmware_code}',
         '-drive',f'if=pflash,format=raw,file={output / "vars.fd"}',
         '-drive','file=/winpe.iso,media=cdrom,readonly=on,format=raw',
         '-drive',f'file=fat:rw:{capsule},format=raw,media=disk',
         '-boot','order=d,menu=off','-nic','none','-display','none',
         '-qmp',f'unix:{output / "qmp.sock"},server=on,wait=off',
         '-monitor','none','-serial',f'file:{output / "serial.log"}',
         '-no-reboot']
(output/'command.json').write_text(json.dumps(command,indent=2)+'\n')
(output/'build.json').write_text(json.dumps(artifacts,indent=2)+'\n')
runtime = {
    'qemu_version': subprocess.check_output(['qemu-system-x86_64', '--version'], text=True).strip(),
    'packages': subprocess.check_output(['dpkg-query', '-W', 'qemu-system-x86', 'ovmf'], text=True).strip(),
    'guest_cpus': args.guest_cpus, 'memory_mib': args.memory_mib,
    'firmware': {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in (args.firmware_code, args.firmware_vars)},
}
(output/'runtime.json').write_text(json.dumps(runtime,indent=2)+'\n')
print(f'WinPE guest artifacts: {output}',flush=True)
with (output/'qemu.log').open('w') as log:
    process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
    started=time.monotonic()
    try:
        while process.poll() is None:
            serial=(output/'serial.log').read_text(errors='replace') if (output/'serial.log').exists() else ''
            if all(marker in serial for marker in (
                    'BMA_WINPE_STAGE_REACHED', 'BMA_WINPE_BRIDGE_PASSED')):
                report={'passed':True,'scope':'WinPE executes actual SETUP.EXE, STAGE.CMD, and propagates exit code 37',
                        'winpe_stage_marker':'BMA_WINPE_STAGE_REACHED' in serial,'bridge_marker':True,
                        'not_tested':['WinPE PXE loading','Heimdal server integration','WinPE to UEFI handoff','Ubuntu boot'],
                        'elapsed_seconds':round(time.monotonic()-started,1)}
                (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
                print(json.dumps(report,indent=2),flush=True)
                break
            if time.monotonic()-started>1800:
                raise TimeoutError('WinPE launcher test exceeded 30-minute bound')
            time.sleep(2)
        else:
            raise RuntimeError(f'QEMU exited before test completed: {process.returncode}')
    except Exception as error:
        (output/'report.json').write_text(json.dumps({'passed':False,'error':str(error),'scope':'WinPE launcher test','elapsed_seconds':round(time.monotonic()-started,1)},indent=2)+'\n')
        raise
    finally:
        process.terminate()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill();process.wait()
