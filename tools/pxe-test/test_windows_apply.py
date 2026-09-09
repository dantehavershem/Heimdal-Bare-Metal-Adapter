import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple
import windows_apply

Usage = namedtuple('Usage', 'total used free')


class DiskIsolationTests(unittest.TestCase):
    def test_insufficient_space_does_not_create_disk_or_run_commands(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            with patch.object(windows_apply.shutil, 'disk_usage', return_value=Usage(100, 99, 1)), patch.object(windows_apply, 'execute') as execute:
                with self.assertRaises(ValueError):
                    windows_apply.prepare(root/'run1', root/'payload', root)
                execute.assert_not_called()
                self.assertEqual(list(root.iterdir()), [])

    def test_existing_target_is_never_reused_or_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); target=root/'run1';target.mkdir()
            disk=target/'windows.qcow2';disk.write_bytes(b'preserve existing disk')
            with patch.object(windows_apply.shutil, 'disk_usage', return_value=Usage(100*1024**3,0,100*1024**3)), patch.object(windows_apply, 'execute') as execute:
                with self.assertRaises(FileExistsError):
                    windows_apply.prepare(Path('/output/run1'), Path('/payload'), root)
                execute.assert_not_called()
                self.assertEqual(disk.read_bytes(), b'preserve existing disk')


class FirstBootEvidenceTests(unittest.TestCase):
    def test_identity_does_not_substitute_for_completion_marker(self):
        markers, matched = windows_apply.evidence('BMA_WINDOWS_FIRST_BOOT_run1\r\n', 'run1')
        self.assertTrue(matched)
        self.assertFalse(markers['BMA_WINDOWS_FIRST_BOOT'])

    def test_complete_lines_and_exact_run_identity_are_required(self):
        serial = '\r\n'.join(windows_apply.MARKERS) + '\r\nBMA_WINDOWS_FIRST_BOOT_run1\r\n'
        markers, matched = windows_apply.evidence(serial, 'run1')
        self.assertTrue(all(markers.values()))
        self.assertTrue(matched)
        self.assertFalse(windows_apply.evidence(serial, 'run')[1])


if __name__ == '__main__':
    unittest.main()
