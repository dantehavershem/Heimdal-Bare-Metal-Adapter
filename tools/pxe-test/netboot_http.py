#!/usr/bin/env python3
"""Serve one private QEMU guestfwd HTTP connection through stdin/stdout."""
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        self.rfile = sys.stdin.buffer
        self.wfile = sys.stdout.buffer

    def finish(self):
        self.wfile.flush()

    def log_message(self, *_):
        pass

    def serve(self, body):
        route = urlsplit(self.path).path
        resource = self.server['resources'].get(route)
        status = 200 if resource else 404
        sent = 0
        digest = hashlib.sha256()
        completed = False
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(resource['size'] if resource else 0))
            self.send_header('Connection', 'close')
            self.end_headers()
            if body and resource:
                with open(resource['path'], 'rb') as source:
                    source.seek(resource.get('offset', 0))
                    remaining = resource['size']
                    while remaining:
                        chunk = source.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise EOFError('Truncated boot resource')
                        self.wfile.write(chunk)
                        digest.update(chunk)
                        sent += len(chunk)
                        remaining -= len(chunk)
            self.wfile.flush()
            completed = True
        except (BrokenPipeError, ConnectionError, EOFError):
            pass
        finally:
            entry = {'method': self.command, 'path': route, 'status': status,
                     'bytes_sent': sent, 'completed': completed,
                     'sha256': digest.hexdigest() if body and resource and completed else None}
            fd = os.open(self.server['log'], os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
            try:
                os.write(fd, (json.dumps(entry) + '\n').encode())
            finally:
                os.close(fd)
            self.close_connection = True

    def do_GET(self):
        self.serve(True)

    def do_HEAD(self):
        self.serve(False)


if __name__ == '__main__':
    Handler(None, ('private-guest', 0), json.loads(Path(sys.argv[1]).read_text()))
