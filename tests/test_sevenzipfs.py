# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import zipfile
import tempfile
import unittest

from six.moves import filterfalse

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases

try:
    import py7zr
except ImportError:
    py7zr = None

try:
    from fs.archive.sevenzipfs import SevenZipReadFS, SevenZipFS, SevenZipSaver
except ImportError:
    SevenZipReadFS = SevenZipFS = SevenZipSaver = None



def sevenzip_compress(handle, source_fs):
    if hasattr(handle, 'seek') and handle.seekable():
        handle.seek(0)
    saver = SevenZipSaver(handle, overwrite=False)
    saver.save(source_fs)


@unittest.skipUnless(py7zr, 'py7zr not available')
class TestSevenZipFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return SevenZipFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile


@unittest.skipUnless(py7zr, 'py7zr not available')
class TestSevenZipReadFS(ArchiveReadTestCases, unittest.TestCase):

    long_names = True
    unicode_names = True

    compress = staticmethod(sevenzip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    _archive_read_fs = SevenZipReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestSevenZipReadFS, self).setUp(handle)


@unittest.skipUnless(py7zr, 'py7zr not available')
class TestSevenZipFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(sevenzip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    load_archive = SevenZipFS
    _archive_fs = SevenZipFS

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
