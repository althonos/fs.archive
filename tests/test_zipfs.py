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
import fs.archive.zipfs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases


FS_VERSION = tuple(map(int, fs.__version__.split('.')))


def zip_compress(handle, source_fs):
    if hasattr(handle, 'seek') and handle.seekable():
        handle.seek(0)
    saver = fs.archive.zipfs.ZipSaver(handle, False)
    saver.save(source_fs)


class TestZipFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return fs.archive.zipfs.ZipFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move(self):
        super(TestZipFS, self).test_move()

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move_file_same_fs(self):
        super(TestZipFS, self).test_move_file_same_fs()


class TestZipReadFS(ArchiveReadTestCases, unittest.TestCase):

    long_names = True
    unicode_names = True

    compress = staticmethod(zip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    _archive_read_fs = fs.archive.zipfs.ZipReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestZipReadFS, self).setUp(handle)


class TestZipFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(zip_compress)
    make_source_fs = fs.memoryfs.MemoryFS
    load_archive = fs.archive.zipfs.ZipFS
    _archive_fs = fs.archive.zipfs.ZipFS

    @staticmethod
    def iter_files(handle):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
        with zipfile.ZipFile(handle) as z:
            for name in filter(None, z.namelist()):
                if not name.endswith('/'):
                    yield abspath(name)

    @staticmethod
    def iter_dirs(handle):
        zipname = lambda n: abspath(n).rstrip('/')
        seen = set()
        root_filter = '/'.__contains__

        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)

        with zipfile.ZipFile(handle) as z:
            for name in z.namelist():
                # directory defined in the zipfile
                if name.endswith('/'):
                    seen.add(name)
                    yield zipname(name)
                # implicit directory
                else:
                    for path in filterfalse(root_filter, recursepath(name)):
                        if path != abspath(name) and not path in seen:
                            seen.add(path)
                            yield zipname(path)
