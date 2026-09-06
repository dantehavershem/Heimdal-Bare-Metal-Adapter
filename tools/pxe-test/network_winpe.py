#!/usr/bin/env python3
"""Diskless WinPE PXE/TFTP -> iPXE/HTTP -> wimboot launcher contract test."""
import argparse
import datetime
import hashlib
import json
import shutil
import signal
import struct
import subprocess
import sys
import time
from pathlib import Path

from run import build
sys.path.insert(0, '/src/backend')
from app.services.iso_inspector import parse_dir_record, read_sector, walk

MARKERS = ('BMA_WINPE_NETWORK_REACHED', 'BMA_WINPE_STAGE_REACHED', 'BMA_WINPE_BRIDGE_PASSED')
REQUIRED = ('boot.ipxe', 'wimboot', 'winpeshl.ini', 'lab-start.cmd',
            'SETUP.EXE', 'STAGE.CMD', 'RUN-TEST.CMD', 'boot.wim')


def packets(path):
    """Read only captured packet records; never load the whole pcap into RAM."""
    evidence = {'dhcp_packets': 0, 'tftp_requests': [], 'tftp_errors': 0}
    if not path.exists():
        return evidence
    with path.open('rb') as f:
        header = f.read(24)
        if len(header) != 24:
            return evidence
        if header[:4] not in (b'\xd4\xc3\xb2\xa1', b'\xa1\xb2\xc3\xd4'):
            raise ValueError('Unsupported pcap format')
        endian = '<' if header[:4] == b'\xd4\xc3\xb2\xa1' else '>'
        while True:
            record = f.read(16)
            if len(record) < 16:
                break
            length = struct.unpack(endian + 'IIII', record)[2]
            if length > 65536:
                raise ValueError('Invalid pcap record length')
            frame = f.read(length)
            if len(frame) != length:
                break
            if len(frame) < 42 or frame[12:14] != b'\x08\x00':
                continue
            ip = frame[14:]
            ihl = (ip[0] & 15) * 4
            if ip[9] != 17 or len(ip) < ihl + 8:
                continue
            src, dst = struct.unpack_from('!HH', ip, ihl)
            data = ip[ihl + 8:]
            if src in (67, 68) or dst in (67, 68):
                evidence['dhcp_packets'] += 1
            if dst == 69 and data[:2] == b'\x00\x01':
                name = data[2:].split(b'\0', 1)[0].decode('ascii', 'replace')
                if name not in evidence['tftp_requests']:
                    evidence['tftp_requests'].append(name)
            if src == 69 and data[:2] == b'\x00\x05':
                evidence['tftp_errors'] += 1
    return evidence


def requests(path):
    result = []
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                result.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # A guestfwd child may currently be appending the last record.
    return result


def resource(path, offset=0, size=None):
    return {'path': str(path), 'offset': offset,
            'size': path.stat().st_size if size is None else size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iso', type=Path, default=Path('/winpe.iso'))
    parser.add_argument('--wimboot', type=Path, default=Path('/output/downloads/wimboot'))
    parser.add_argument('--missing-wim', action='store_true')
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout must be positive')
    mem = dict(line.split(':', 1) for line in Path('/proc/meminfo').read_text().splitlines())
    available = int(mem['MemAvailable'].split()[0]) // 1024
    if available < 5120:
        parser.error(f'4096 MiB guest requires 5120 MiB available RAM; found {available}')
    for path in (args.iso, args.wimboot):
        if not path.is_file():
            parser.error(f'Missing input: {path}')
    # Locate only the WIM extent. Serve it from the read-only ISO without copying it.
    with args.iso.open('rb') as source:
        root = None
        for lba in range(16, 64):
            block = read_sector(source, lba)
            if block[:7] == b'\x01CD001\x01':
                root = parse_dir_record(block[156:190])
                break
        if root is None:
            parser.error('ISO9660 primary volume descriptor not found')
        entries = dict(walk(source, root['extent'], root['size']))
        wim = entries.get('/SOURCES/BOOT.WIM')
        if not wim or wim['is_dir']:
            parser.error('ISO does not contain /SOURCES/BOOT.WIM')
        offset = wim['extent'] * 2048
        if offset + wim['size'] > args.iso.stat().st_size:
            parser.error('Truncated ISO boot image')
        source.seek(offset)
        if source.read(8) != b'MSWIM\0\0\0':
            parser.error('Invalid WIM header')

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output = Path('/output') / ('winpe-pxe-' + stamp)
    output.mkdir()
    payload = output / 'payload'; payload.mkdir()
    artifacts = build(payload)
    firmware = Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
    variables = Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
    shutil.copyfile(variables, output / 'vars.fd')
    shutil.copyfile('/usr/lib/ipxe/ipxe-amd64.efi', payload / 'ipxe.efi')
    shutil.copyfile(args.wimboot, payload / 'wimboot')
    # iPXE wimboot injects these files into the in-memory System32 directory.
    # No physical disk, virtual capsule disk, or DVD is attached to the guest.
    startup = r'''@echo off
wpeinit
reg add "HKLM\SYSTEM\CurrentControlSet\Enum\ACPI\PNP0501\1\Device Parameters" /v PortName /t REG_SZ /d COM1 /f
pnputil /restart-device "ACPI\PNP0501\1"
set /a SERIAL_TRIES=30
:serial_retry
(echo BMA_WINPE_NETWORK_REACHED) > COM1 && goto serial_ready
set /a SERIAL_TRIES-=1
if %SERIAL_TRIES% LEQ 0 goto serial_failed
ping -n 2 127.0.0.1 > nul
goto serial_retry
:serial_ready
echo BMA_WINPE_NETWORK_REACHED
call "%SYSTEMROOT%\System32\RUN-TEST.CMD"
cmd /k
exit /b
:serial_failed
echo Serial preparation failed; launcher test not started.
cmd /k
'''
    (payload / 'lab-start.cmd').write_bytes(startup.replace('\n', '\r\n').encode())
    (payload / 'winpeshl.ini').write_bytes(
        b'[LaunchApps]\r\n%SYSTEMROOT%\\System32\\cmd.exe, /d /c %SYSTEMROOT%\\System32\\lab-start.cmd\r\n')
    base = 'http://10.0.2.100'
    (payload / 'autoexec.ipxe').write_text(f'#!ipxe\ndhcp\nchain {base}/boot.ipxe\n')
    script = ['#!ipxe', f'kernel {base}/wimboot index=2']
    for name in REQUIRED[2:-1]:
        script.append(f'initrd {base}/{name} {name}')
    script.extend([f'initrd {base}/{"missing.wim" if args.missing_wim else "boot.wim"} boot.wim', 'boot'])
    (payload / 'boot.ipxe').write_text('\n'.join(script) + '\n')
    routes = {'/' + name: resource(payload / name) for name in REQUIRED[:-1]}
    if not args.missing_wim:
        routes['/boot.wim'] = resource(args.iso, offset, wim['size'])
    manifest = output / 'http-manifest.json'
    manifest.write_text(json.dumps({'log': str(output / 'http.jsonl'), 'resources': routes}, indent=2) + '\n')
    net = (f'user,id=net0,restrict=on,ipv6=off,tftp={payload},bootfile=ipxe.efi,'
           f'guestfwd=tcp:10.0.2.100:80-cmd:python3 /src/tools/pxe-test/netboot_http.py {manifest}')
    command = ['qemu-system-x86_64', '-machine', 'q35,accel=tcg', '-cpu', 'max', '-m', '4096', '-smp', '1',
               '-drive', f'if=pflash,format=raw,readonly=on,file={firmware}',
               '-drive', f'if=pflash,format=raw,file={output / "vars.fd"}',
               '-boot', 'order=n,strict=on', '-netdev', net, '-device', 'e1000,netdev=net0',
               '-object', f'filter-dump,id=capture,netdev=net0,file={output / "network.pcap"},maxlen=512',
               '-display', 'none', '-qmp', f'unix:{output / "qmp.sock"},server=on,wait=off',
               '-monitor', 'none', '-serial', f'file:{output / "serial.log"}', '-no-reboot']
    runtime = {'packages': subprocess.check_output(['dpkg-query', '-W', 'qemu-system-x86', 'ovmf', 'ipxe'], text=True).strip(),
               'iso_size': args.iso.stat().st_size, 'boot_wim_size': wim['size'], 'artifacts': artifacts,
               'sha256': {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in
                          (firmware, variables, payload / 'ipxe.efi', payload / 'wimboot')}}
    (output / 'runtime.json').write_text(json.dumps(runtime, indent=2) + '\n')
    (output / 'command.json').write_text(json.dumps(command, indent=2) + '\n')
    print(f'WinPE PXE artifacts: {output}', flush=True)
    print('iPXE autoexec script selects http://10.0.2.100/boot.ipxe', flush=True)
    started = time.monotonic()
    report = {'passed': False, 'case': 'missing-wim' if args.missing_wim else 'network-boot',
              'scope': 'Diskless WinPE over PXE/TFTP and iPXE/HTTP, executing actual SETUP.EXE',
              'not_tested': ['Heimdal integration', 'WinPE-to-UEFI handoff', 'Ubuntu boot', 'Secure Boot']}
    def interrupted(signum, _):
        raise InterruptedError(f'Test interrupted by signal {signum}')
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    process = None
    try:
        with (output / 'qemu.log').open('w') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
            negative_seen = None
            while process.poll() is None:
                serial_path = output / 'serial.log'
                serial = serial_path.read_text(errors='replace') if serial_path.exists() else ''
                http = requests(output / 'http.jsonl')
                markers = {marker: marker in serial for marker in MARKERS}
                if args.missing_wim:
                    missing = any(r['path'] == '/missing.wim' and r['status'] == 404 and r['completed'] for r in http)
                    if missing and negative_seen is None:
                        negative_seen = time.monotonic()
                    if negative_seen is not None and time.monotonic() - negative_seen >= 5:
                        if any(markers.values()):
                            raise RuntimeError('Unexpected WinPE marker in missing-WIM test')
                        break
                elif all(markers.values()):
                    break
                if time.monotonic() - started > args.timeout:
                    raise TimeoutError(f'WinPE PXE test exceeded {args.timeout}-second bound')
                time.sleep(1)
            else:
                raise RuntimeError(f'QEMU exited before completion: {process.returncode}')
    except Exception as error:
        report['error'] = str(error)
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill(); process.wait()
        http = requests(output / 'http.jsonl')
        serial_path = output / 'serial.log'
        serial = serial_path.read_text(errors='replace') if serial_path.exists() else ''
        marker_evidence = {m: m in serial for m in MARKERS}
        network = packets(output / 'network.pcap')
        transfers = {name: any(r['method'] == 'GET' and r['path'] == '/' + name and
                               r['status'] == 200 and r['completed'] and r['bytes_sent'] == routes['/' + name]['size']
                               for r in http) for name in REQUIRED if '/' + name in routes}
        base_ok = network['dhcp_packets'] > 0 and all(name in network['tftp_requests'] for name in ('ipxe.efi', 'autoexec.ipxe'))
        if args.missing_wim:
            case_ok = (any(r['path'] == '/missing.wim' and r['status'] == 404 and r['completed'] for r in http)
                       and all(transfers.values()) and not any(marker_evidence.values()))
        else:
            case_ok = all(marker_evidence.values()) and all(transfers.values())
        report.update(passed=base_ok and case_ok and 'error' not in report,
                      markers=marker_evidence, network=network, http_transfers=transfers,
                      elapsed_seconds=round(time.monotonic() - started, 1))
        if not report['passed'] and 'error' not in report:
            report['error'] = 'Required execution or network evidence missing'
        (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
