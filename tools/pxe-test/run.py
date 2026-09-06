#!/usr/bin/env python3
"""Real isolated x86-64 UEFI network boot; not a Heimdal server implementation."""
import argparse
import datetime
import hashlib
import json
import shutil
import struct
import subprocess
import sys
from pathlib import Path

SOURCE = Path('/src')
MARKER = 'BMA_PXE_UEFI_REACHED'


def execute(command):
    subprocess.run(command, check=True, timeout=120)


def build(output):
    compiler = ['clang', '--target=x86_64-pc-windows-msvc', '-ffreestanding',
                '-fno-stack-protector', '-fshort-wchar', '-O1', '-c']
    execute(compiler + [str(SOURCE/'winpe-bridge/setup.c'), '-o', str(output/'setup.obj')])
    execute(['llvm-dlltool', '-m', 'i386:x86-64', '-d', str(SOURCE/'winpe-bridge/kernel32.def'),
             '-l', str(output/'kernel32.lib')])
    execute(['lld-link', '/entry:mainCRTStartup', '/subsystem:console', '/nodefaultlib',
             f'/out:{output / "SETUP.EXE"}', str(output/'setup.obj'), str(output/'kernel32.lib')])
    execute(compiler + ['-DPXE_TEST', str(SOURCE/'uefi-stage/stage.c'), '-o', str(output/'stage.obj')])
    execute(['lld-link', '/entry:efi_main', '/subsystem:efi_application', '/nodefaultlib',
             f'/out:{output / "probe.efi"}', str(output/'stage.obj')])
    # A non-destructive Windows contract test to run when WinPE is available.
    (output/'STAGE.CMD').write_bytes(b'@echo off\r\necho BMA_WINPE_STAGE_REACHED\r\necho BMA_WINPE_STAGE_REACHED > COM1\r\nexit /b 37\r\n')
    (output/'RUN-TEST.CMD').write_bytes(b'@echo off\r\ncd /d "%~dp0"\r\nSETUP.EXE\r\nset "BMA_RESULT=%ERRORLEVEL%"\r\necho Bridge returned %BMA_RESULT%\r\nif not "%BMA_RESULT%"=="37" exit /b 1\r\necho BMA_WINPE_BRIDGE_PASSED\r\necho BMA_WINPE_BRIDGE_PASSED > COM1\r\nexit /b 0\r\n')
    result = {}
    for filename, subsystem in [('SETUP.EXE',3),('probe.efi',10)]:
        data=(output/filename).read_bytes()
        pe=struct.unpack_from('<I',data,0x3c)[0]
        assert data[pe:pe+4]==b'PE\0\0'
        assert struct.unpack_from('<H',data,pe+4)[0]==0x8664
        assert struct.unpack_from('<H',data,pe+24+68)[0]==subsystem
        result[filename]={'machine':'AMD64','subsystem':subsystem,'sha256':hashlib.sha256(data).hexdigest()}
    return result


def network_evidence(path):
    packets = path.read_bytes() if path.exists() else b''
    result = {'dhcp_packets':0,'tftp_requests':[],'tftp_errors':0}
    if len(packets)<24:return result
    endian = '<' if packets[:4] == b'\xd4\xc3\xb2\xa1' else '>'
    offset=24
    while offset+16<=len(packets):
        length=struct.unpack_from(endian+'IIII',packets,offset)[2]
        frame=packets[offset+16:offset+16+length];offset+=16+length
        if len(frame)<42 or frame[12:14]!=b'\x08\x00':continue
        ip=frame[14:];header=(ip[0]&15)*4
        if ip[9]!=17 or len(ip)<header+8:continue
        source,destination=struct.unpack_from('!HH',ip,header)
        payload=ip[header+8:]
        if source in (67,68) or destination in (67,68):result['dhcp_packets']+=1
        if destination==69 and payload[:2]==b'\x00\x01':
            result['tftp_requests'].append(payload[2:].split(b'\0')[0].decode('ascii','replace'))
        if source==69 and payload[:2]==b'\x00\x05':result['tftp_errors']+=1
    return result


def boot(output, missing=False, timeout=120):
    folder=output/('missing-bootfile' if missing else 'pxe-boot')
    folder.mkdir()
    firmware=Path('/usr/share/OVMF/OVMF_CODE.fd')
    variables=Path('/usr/share/OVMF/OVMF_VARS.fd')
    if not firmware.exists():
        firmware=Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
        variables=Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
    shutil.copyfile(variables,folder/'vars.fd')
    bootfile='missing.efi' if missing else 'probe.efi'
    command=['qemu-system-x86_64','-machine','q35,accel=tcg','-cpu','max','-m','512','-smp','1',
             '-drive',f'if=pflash,format=raw,readonly=on,file={firmware}',
             '-drive',f'if=pflash,format=raw,file={folder / "vars.fd"}',
             '-boot','order=n,strict=on','-netdev',f'user,id=net0,restrict=on,ipv6=off,tftp={output},bootfile={bootfile}',
             '-device','e1000,netdev=net0',
             '-object',f'filter-dump,id=capture,netdev=net0,file={folder / "network.pcap"}',
             '-display','none','-monitor','none','-serial',f'file:{folder / "serial.log"}',
             '-chardev',f'file,id=debug,path={folder / "debug.log"}',
             '-device','isa-debugcon,iobase=0xe9,chardev=debug',
             '-device','isa-debug-exit,iobase=0xf4,iosize=0x04','-no-reboot']
    (folder/'command.json').write_text(json.dumps(command,indent=2)+'\n')
    print(f'Running {folder.name} (timeout {timeout}s)',flush=True)
    timed_out=False
    with (folder/'qemu.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        try: code=process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True;process.terminate()
            try:code=process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();code=process.wait()
    evidence=network_evidence(folder/'network.pcap')
    reached=MARKER in (folder/'debug.log').read_text(errors='replace')
    passed=(not reached and evidence['tftp_errors']>0 and 'missing.efi' in evidence['tftp_requests']) if missing else (code==33 and reached and evidence['dhcp_packets']>0 and 'probe.efi' in evidence['tftp_requests'])
    return {'passed':passed,'exit_code':code,'timed_out':timed_out,'uefi_marker':reached,**evidence}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--timeout',type=int,default=120)
    args=parser.parse_args()
    output=Path('/output')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    output.mkdir(parents=True)
    report={'scope':'Isolated UEFI DHCP/TFTP boot and bridge artifact build',
            'not_tested':['Heimdal server/protocol implementation','WinPE execution of SETUP.EXE','WinPE to UEFI reboot handoff','Ubuntu installer boot','Secure Boot'],
            'artifacts':build(output)}
    report['positive']=boot(output,timeout=args.timeout)
    report['negative']=boot(output,missing=True,timeout=min(args.timeout,45))
    report['passed']=report['positive']['passed'] and report['negative']['passed']
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
    print(f'Artifacts: {output}',flush=True)
    return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())
