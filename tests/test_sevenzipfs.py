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
from fs.errors import PermissionDenied, CreateFailed, OperationFailed
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

try:
    import lzma
except ImportError:
    lzma = None

FS_VERSION = tuple(map(int, fs.__version__.split('.')))


def sevenzip_compress(handle, source_fs, **options):
    if hasattr(handle, 'seek') and handle.seekable():
        handle.seek(0)
    saver = SevenZipSaver(handle, overwrite=False, **options)
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

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move(self):
        super(TestSevenZipFS, self).test_move()

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move_file_same_fs(self):
        super(TestSevenZipFS, self).test_move_file_same_fs()


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

    def test_password_protected_file(self):
        buffer = io.BytesIO()
        source_fs = fs.memoryfs.MemoryFS()
        source_fs.settext("foo.txt", "Hello, World")
        sevenzip_compress(buffer, source_fs, password="pwd")

        # test with no password
        buffer.seek(0)
        with SevenZipReadFS(buffer, close_handle=False) as archive:
            self.assertRaises(PermissionDenied, archive.readtext, "foo.txt")
        # test with wrong password
        buffer.seek(0)
        with SevenZipReadFS(buffer, password="password", close_handle=False) as archive:
            self.assertRaises(OperationFailed, archive.readtext, "foo.txt")
        # test with good password
        buffer.seek(0)
        with SevenZipReadFS(buffer, password="pwd", close_handle=False) as archive:
            self.assertEqual(archive.readtext("foo.txt"), "Hello, World")

    def test_password_protected_header(self):
        buffer = io.BytesIO()
        source_fs = fs.memoryfs.MemoryFS()
        source_fs.settext("foo.txt", "Hello, World")
        sevenzip_compress(buffer, source_fs, password="pwd", encrypt_header=True)

        # test with no password
        buffer.seek(0)
        with self.assertRaises(CreateFailed) as ctx:
            archive = SevenZipReadFS(buffer, close_handle=False)
        self.assertIsInstance(ctx.exception.exc, PermissionDenied)
        # test with no password
        buffer.seek(0)
        with self.assertRaises(CreateFailed) as ctx:
            archive = SevenZipReadFS(buffer, password="password", close_handle=False)
        self.assertIsInstance(ctx.exception.exc, (lzma.LZMAError, TypeError))
        # test with good password
        buffer.seek(0)
        with SevenZipReadFS(buffer, password="pwd", close_handle=False) as archive:
            self.assertEqual(archive.readtext("foo.txt"), "Hello, World")

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
