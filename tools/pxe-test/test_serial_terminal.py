import unittest
from serial_terminal import Terminal


class TerminalTests(unittest.TestCase):
    def test_split_query_and_no_duplicate_response(self):
        t=Terminal()
        self.assertEqual(t.replies(b'boot\x1b['),b'')
        self.assertEqual(t.replies(b'6n'),b'\x1b[24;80R')
        self.assertEqual(t.replies(b'next output'),b'')

    def test_combined_queries(self):
        self.assertEqual(Terminal().replies(b'\x1b[18t\x1b[c'),b'\x1b[8;24;80t\x1b[?1;2c')

    def test_capability_query_falls_back(self):
        self.assertEqual(Terminal().replies(b'\x1bP+q6E616D65\x1b\\'),b'\x1bP0+r6E616D65\x1b\\')

    def test_guest_evidence_is_never_echoed_back(self):
        self.assertEqual(Terminal().replies(b'BMA_HANDOFF_PROOF_PASSED\nUbuntu login:'),b'')

if __name__=='__main__':unittest.main()
