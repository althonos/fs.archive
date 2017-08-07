# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import tarfile
import tempfile
import unittest

from six.moves import filterfalse

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs
import fs.archive.tarfs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases


def tar_compress(handle, source_fs):
    if hasattr(handle, 'seek') and handle.seekable():
        handle.seek(0)
    saver = fs.archive.tarfs.TarSaver(handle, False)
    saver.save(source_fs)


class TestTarFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return fs.archive.tarfs.TarFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile


class TestTarReadFS(ArchiveReadTestCases, unittest.TestCase):

    long_names = True
    unicode_names = True

    compress = staticmethod(tar_compress)
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_read_fs = fs.archive.tarfs.TarReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(TestTarReadFS, self).setUp(handle)

    def test_create_failed(self):
        self.assertRaises(fs.errors.CreateFailed, fs.archive.tarfs.TarFS, 1)


class TestTarFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(tar_compress)
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_fs = fs.archive.tarfs.TarFS

    @staticmethod
    def load_archive(handle):
        return fs.archive.tarfs.TarFS(handle)

    @staticmethod
    def iter_files(handle):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
            kwargs = {'fileobj': handle, 'mode': 'r'}
        else:
            kwargs = {'name': handle, 'mode': 'r'}

        with tarfile.TarFile(**kwargs) as t:
            for member in t.getmembers():
                if member.isfile():
                    yield abspath(member.name)

    @staticmethod
    def iter_dirs(handle):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
            kwargs = {'fileobj': handle, 'mode': 'r'}
        else:
            kwargs = {'name': handle, 'mode': 'r'}

        with tarfile.TarFile(**kwargs) as t:
            for member in t.getmembers():
                if member.isdir():
                    yield abspath(member.name)
