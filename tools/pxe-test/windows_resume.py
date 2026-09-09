#!/usr/bin/env python3
"""LAB ONLY: observe startup from a preserved Windows disk using a new overlay."""
import argparse
import datetime
import json
import shutil
import subprocess
import time
from pathlib import Path

from windows_apply import evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--disk', type=Path, required=True)
    parser.add_argument('--disk-root', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    if not args.disk.is_file() or args.timeout <= 0:
        parser.error('Existing QCOW2 disk and positive timeout required')
    run = 'windows-resume-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = args.baseline.parent / run
    output.mkdir()
    disk_dir = args.disk_root / run
    disk_dir.mkdir()  # Never reuse or overwrite a target.
    overlay = disk_dir / 'resume.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'qcow2',
                    '-b', str(args.disk.resolve()), str(overlay)], check=True)
    shutil.copyfile(args.baseline / 'vars.fd', output / 'vars.fd')
    original = json.loads((args.baseline / 'command.json').read_text())
    command = [original[0]]
    # Preserve devices and firmware; remove PXE services, capture and original logs.
    for flag, value in zip(original[1::2], original[2::2]):
        if flag in ('-object', '-qmp', '-serial'):
            continue
        if flag == '-netdev':
            value = 'user,id=net0,restrict=on,ipv6=off'
        elif flag == '-smp':
            value = '2'
        elif flag == '-drive' and 'id=windows,' in value:
            value = f'if=none,id=windows,format=qcow2,file={overlay}'
        elif flag == '-drive' and f'file={args.baseline}/vars.fd' in value:
            value = value.replace(str(args.baseline / 'vars.fd'), str(output / 'vars.fd'))
        command.extend([flag, value])
    command.extend(['-qmp', f'unix:{output}/qmp-control.sock,server=on,wait=off',
                    '-serial', f'file:{output}/serial.log'])
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    identity = json.loads((args.baseline / 'windows-apply.json').read_text())['identity']
    report = {'passed': False, 'case': 'windows-startup-resume',
              'baseline': str(args.baseline), 'overlay': str(overlay),
              'scope': 'Follow-up installed Windows specialize marker; not an uninterrupted deployment pass',
              'vcpus': 2, 'timeout_seconds': args.timeout}
    print(f'Resume artifacts: {output}', flush=True)
    started = time.monotonic()
    with (output / 'qemu.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            while process.poll() is None:
                serial = (output / 'serial.log').read_text(errors='replace') if (output / 'serial.log').exists() else ''
                markers, matched = evidence(serial, identity)
                if markers['BMA_WINDOWS_FIRST_BOOT'] and matched:
                    report['passed'] = True
                    break
                if time.monotonic() - started >= args.timeout:
                    report['error'] = 'Installed Windows first-boot verification timed out'
                    break
                time.sleep(1)
            else:
                report['error'] = f'QEMU exited before verification: {process.returncode}'
        finally:
            if process.poll() is None:
                try:
                    subprocess.run(['python3', '/src/tools/pxe-test/qmp.py', str(output / 'qmp-control.sock'),
                                    '--screenshot', str(output / 'final-screen.png')], timeout=40, check=False)
                except subprocess.TimeoutExpired:
                    report['screenshot_error'] = 'QMP screenshot timed out'
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            report['elapsed_seconds'] = round(time.monotonic() - started, 1)
            (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
