# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

import fs.archive
from fs.archive.zipfs import ZipFS
from fs.archive.tarfs import TarFS
from fs.opener import _errors as errors


class TestOpenArchive(unittest.TestCase):

    def test_open_unknown_archive(self):
        with self.assertRaises(errors.Unsupported):
            with fs.archive.open_archive('mem://', 'not-an-archive.txt'):
                pass

    def test_zip(self):
        mem = fs.open_fs('mem://')
        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertIsInstance(archive, fs.archive.zipfs.ZipFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        with fs.archive.open_archive(mem, 'myzip.zip') as archive:
            self.assertEqual(sorted(archive.listdir('/')), ['abc.txt', 'dir'])
            self.assertEqual(archive.gettext('abc.txt'), 'abc')
