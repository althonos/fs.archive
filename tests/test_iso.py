# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import unittest

import fs.memoryfs
import fs.archive.isofs

from fs.archive.test import ArchiveReadTestCases


class TestISOReadFS(ArchiveReadTestCases, unittest.TestCase):

    long_names = False
    unicode_names = False

    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_read_fs = fs.archive.isofs.ISOReadFS

    def compress(self, handle, source_fs):
        tests_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        resources_path = os.path.join(tests_dir, 'resources')
        with open(os.path.join(resources_path, 'test.iso'), 'rb') as iso_file:
            handle.write(iso_file.read())

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestISOReadFS, self).setUp(handle)


class TestISOReadFS_Joliet(ArchiveReadTestCases, unittest.TestCase):

    long_names = False
    unicode_names = True

    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_read_fs = fs.archive.isofs.ISOReadFS

    def compress(self, handle, source_fs):
        tests_dir = os.path.dirname(os.path.abspath(os.path.realpath(__file__)))
        resources_path = os.path.join(tests_dir, 'resources')
        with open(os.path.join(resources_path, 'test.joliet.iso'), 'rb') as iso_file:
            handle.write(iso_file.read())

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestISOReadFS_Joliet, self).setUp(handle)
