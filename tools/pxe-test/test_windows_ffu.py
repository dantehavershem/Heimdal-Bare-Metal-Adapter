import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from collections import namedtuple
import windows_apply
import windows_ffu

Usage = namedtuple('Usage', 'total used free')


class FfuEvidenceTests(unittest.TestCase):
    def test_wim_pass_cannot_be_mistaken_for_ffu_pass(self):
        serial = '\n'.join(windows_apply.MARKERS) + '\nBMA_WINDOWS_FIRST_BOOT_current\n'
        markers, matched = windows_ffu.evidence(serial, 'current')
        self.assertTrue(matched)
        self.assertFalse(all(markers.values()))

    def test_capture_and_restore_without_target_boot_is_not_a_pass(self):
        serial = '\n'.join(windows_apply.MARKERS + windows_ffu.MARKERS[:-1])
        serial += '\nBMA_WINDOWS_FIRST_BOOT_current\n'
        markers, matched = windows_ffu.evidence(serial, 'current')
        self.assertTrue(matched)
        self.assertFalse(all(markers.values()))

    def test_complete_evidence_still_requires_correct_run_identity(self):
        serial = '\n'.join(windows_apply.MARKERS + windows_ffu.MARKERS)
        serial += '\nBMA_WINDOWS_FIRST_BOOT_previous\n'
        markers, matched = windows_ffu.evidence(serial, 'current')
        self.assertTrue(all(markers.values()))
        self.assertFalse(matched)
        self.assertTrue(windows_ffu.evidence(serial, 'previous')[1])

    def test_space_gate_precedes_disk_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(windows_ffu.shutil, 'disk_usage', return_value=Usage(100, 90, 10)), patch.object(windows_apply, 'prepare') as prepare:
                with self.assertRaises(ValueError):
                    windows_ffu.prepare(Path(tmp), Path(tmp), Path(tmp))
                prepare.assert_not_called()
