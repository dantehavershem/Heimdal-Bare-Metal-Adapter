import unittest
from clonezilla_lab import MARKERS, reached


class ClonezillaEvidenceTests(unittest.TestCase):
    def test_starting_clonezilla_is_not_a_restore_pass(self):
        self.assertFalse(reached('BMA_CLONEZILLA_STARTED\n', 'current'))

    def test_restored_files_without_target_boot_is_not_a_pass(self):
        self.assertFalse(reached('\n'.join(MARKERS), 'current'))

    def test_previous_run_cannot_satisfy_target_boot(self):
        serial='\n'.join(MARKERS)+'\nBMA_CLONEZILLA_TARGET_BOOT_previous\n'
        self.assertFalse(reached(serial, 'current'))

    def test_full_evidence_requires_exact_lines(self):
        serial='\r\n'.join(MARKERS)+'\r\nBMA_CLONEZILLA_TARGET_BOOT_current\r\n'
        self.assertTrue(reached(serial, 'current'))
        self.assertFalse(reached(serial.replace('BMA_CLONEZILLA_SAVED', 'echo BMA_CLONEZILLA_SAVED'), 'current'))

    def test_firmware_cursor_controls_do_not_hide_exact_boot_identity(self):
        serial='\n'.join(MARKERS)+'\n\x1b[H\x1b[J\x1b[1;1HBMA_CLONEZILLA_TARGET_BOOT_current\n'
        self.assertTrue(reached(serial, 'current'))
        self.assertFalse(reached(serial, 'curr'))
