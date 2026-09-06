"""Exercise HTTP resource boundaries through the actual guestfwd stdio interface."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SERVER = Path(__file__).with_name('netboot_http.py')


class ResourceServerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'iso').write_bytes(b'prefixPAYLOADsuffix')
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'log': str(self.root / 'http.jsonl'),
            'resources': {'/boot.wim': {'path': str(self.root / 'iso'), 'offset': 6, 'size': 7}}}))

    def request(self, target='/boot.wim', method='GET'):
        proc = subprocess.run([sys.executable, str(SERVER), str(self.manifest)],
            input=f'{method} {target} HTTP/1.0\r\n\r\n'.encode(), capture_output=True, timeout=5)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode())
        headers, body = proc.stdout.split(b'\r\n\r\n', 1)
        event = json.loads((self.root / 'http.jsonl').read_text().splitlines()[-1])
        return headers, body, event

    def test_only_requested_iso_extent_is_served(self):
        headers, body, event = self.request()
        self.assertIn(b'200 OK', headers)
        self.assertEqual(body, b'PAYLOAD')
        self.assertEqual(event['bytes_sent'], 7)
        self.assertTrue(event['completed'])

    def test_missing_and_traversal_paths_are_not_served(self):
        for target in ('/missing.wim', '/../iso', '/%2e%2e/iso'):
            with self.subTest(target=target):
                headers, body, event = self.request(target)
                self.assertIn(b'404', headers)
                self.assertEqual(body, b'')
                self.assertEqual(event['status'], 404)

    def test_head_does_not_count_as_a_download(self):
        headers, body, event = self.request(method='HEAD')
        self.assertIn(b'Content-Length: 7', headers)
        self.assertEqual(body, b'')
        self.assertEqual(event['bytes_sent'], 0)
        self.assertEqual(event['method'], 'HEAD')

    def test_truncated_image_is_not_marked_complete(self):
        (self.root / 'iso').write_bytes(b'prefixBAD')
        _, body, event = self.request()
        self.assertEqual(body, b'BAD')
        self.assertFalse(event['completed'])
        self.assertIsNone(event['sha256'])


if __name__ == '__main__':
    unittest.main()
