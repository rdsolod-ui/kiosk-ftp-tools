import unittest
from pathlib import Path
from kiosk_ftp_tools.app import remote_path, local_path, TRANSFER


class Paths(unittest.TestCase):
    def test_remote_injection_and_traversal(self):
        for value in ['../Windows', '/a/../b', 'x\r\nDELE a', 'C:/x', 'a\\b', '\x00']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                remote_path(value)

    def test_normal_paths(self):
        self.assertEqual(remote_path('folder/file.txt'), '/folder/file.txt')
        self.assertEqual(remote_path('/'), '/')
        with self.assertRaises(ValueError): remote_path('/', file=True)

    def test_local_scope(self):
        for value in ['../outside', 'C:/Windows/test', '.', '/outside']:
            with self.subTest(value=value), self.assertRaises(ValueError): local_path(value)
        self.assertEqual(local_path('sample.txt'), (TRANSFER / 'sample.txt').resolve())


if __name__ == '__main__':
    unittest.main()
