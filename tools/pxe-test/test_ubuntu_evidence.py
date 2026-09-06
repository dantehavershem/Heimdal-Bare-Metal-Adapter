"""Readiness must come from the installer, not merely a boot banner."""
import unittest
from network_winpe import ubuntu_reached


class UbuntuEvidenceTests(unittest.TestCase):
    boot = 'BMA_UBUNTU_GRUB_STARTED\nLinux version 7.0.0\nUbuntu 26.04.1 LTS'
    serial_ui = ('As the installer is running on a serial console\n'
                 '\x1b[0;30;47m[ Continue in rich mode > ]\n'
                 '[ Continue in basic mode > ]')

    def test_banner_and_login_are_insufficient(self):
        self.assertFalse(ubuntu_reached(self.boot + '\nubuntu-server login:'))

    def test_actual_serial_welcome_is_ready(self):
        self.assertTrue(ubuntu_reached(self.boot + self.serial_ui))

    def test_partial_screen_is_insufficient(self):
        self.assertFalse(ubuntu_reached(self.boot + 'Continue in basic mode'))

    def test_ui_requires_kernel_and_boot_chain_marker(self):
        self.assertFalse(ubuntu_reached('Ubuntu' + self.serial_ui))
        self.assertFalse(ubuntu_reached('Linux version 7.0 Ubuntu' + self.serial_ui))

    def test_language_screen_is_ready(self):
        self.assertTrue(ubuntu_reached(self.boot + '\nWelcome!\nEnglish'))


if __name__ == '__main__':
    unittest.main()
