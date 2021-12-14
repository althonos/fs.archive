# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import zipfile
import tempfile
import unittest

import py7zr
from six.moves import filterfalse

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs
import fs.archive.sevenzipfs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases


def sevenzip_compress(handle, source_fs):
    if hasattr(handle, 'seek') and handle.seekable():
        handle.seek(0)
    saver = fs.archive.sevenzipfs.SevenZipSaver(handle, overwrite=False)
    saver.save(source_fs)


class TestSevenZipFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return fs.archive.sevenzipfs.SevenZipFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile


class TestSevenZipReadFS(ArchiveReadTestCases, unittest.TestCase):

    long_names = True
    unicode_names = True

    compress = staticmethod(sevenzip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    _archive_read_fs = fs.archive.sevenzipfs.SevenZipReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestSevenZipReadFS, self).setUp(handle)


class TestSevenZipFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(sevenzip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    load_archive = fs.archive.sevenzipfs.SevenZipFS
    _archive_fs = fs.archive.sevenzipfs.SevenZipFS

    @staticmethod
    def iter_files(handle):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
        with py7zr.SevenZipFile(handle) as z:
            for entry in z.files:
                if not entry.is_directory:
                    yield abspath(entry.filename)

    @staticmethod
    def iter_dirs(handle):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
        with py7zr.SevenZipFile(handle) as z:
            for entry in z.files:
                if entry.is_directory:
                    yield abspath(entry.filename)
