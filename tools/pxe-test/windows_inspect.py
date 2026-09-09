#!/usr/bin/env python3
"""Extract Windows setup evidence from a stopped QCOW2, without mounting it.

Requires dissect.target==3.25.1. Mount the disk (and any overlay backing paths)
read-only in the inspection container. Inspect only stopped disks or frozen backing files after an external snapshot.
"""
import argparse
import hashlib
import json
from pathlib import Path

from dissect.eventlog.evtx import Evtx
from dissect.target import container, filesystem, volume


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('disk', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backing-disk', type=Path, action='append', default=[],
                        help='Read-only backing disk; repeat in order from immediate backing to base')
    args = parser.parse_args()
    args.output.mkdir()  # Preserve prior evidence rather than overwriting it.
    backing = None
    for path in reversed(args.backing_disk):
        backing = container.open(path, backing_file=backing)
    disk = container.open(args.disk, backing_file=backing)
    manifest = []
    for partition in volume.open(disk).volumes:
        try:
            fs = filesystem.open(partition)
        except filesystem.FilesystemError:
            continue
        if not fs.path('/Windows/Panther').exists():
            continue
        paths = list(fs.path('/Windows/Panther').rglob('*'))
        paths.extend(fs.path('/BMA-LAB').rglob('*'))
        paths.append(fs.path('/Windows/INF/setupapi.dev.log'))
        paths.extend(p for p in fs.path('/Windows/System32/winevt/Logs').iterdir()
                     if p.name == 'System.evtx' or 'AppXDeployment' in p.name)
        for path in paths:
            if not path.is_file() or path.suffix.lower() not in ('.log', '.xml', '.cmd', '.evtx'):
                continue
            data = path.read_bytes()
            dest = args.output / str(path).lstrip('/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            manifest.append({'source': str(path), 'bytes': len(data),
                             'sha256': hashlib.sha256(data).hexdigest()})
            if path.suffix.lower() == '.evtx':
                with path.open() as stream:
                    records = [json.loads(json.dumps(record, default=str)) for record in Evtx(stream)]
                dest.with_suffix('.evtx.json').write_text(json.dumps(records, indent=2) + '\n')
        (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        print(f'Extracted {len(manifest)} evidence files to {args.output}')
        return
    raise RuntimeError('No Windows Panther directory found')


if __name__ == '__main__':
    main()
