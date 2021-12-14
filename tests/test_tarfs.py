# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import six
import tarfile
import tempfile
import unittest
import uuid

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs
import fs.archive.tarfs

from fs import ResourceType
from fs.path import join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases
from fs.archive._utils import UniversalContainer


FS_VERSION = tuple(map(int, fs.__version__.split('.')))


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

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move(self):
        super(TestTarFS, self).test_move()

    @unittest.skipIf(FS_VERSION < (2, 4, 15), "fails because of PyFilesystem2#509")
    def test_move_file_same_fs(self):
        super(TestTarFS, self).test_move_file_same_fs()


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


class TestTarFSInferredDirectories(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tmpfs = fs.open_fs("temp://")

    @classmethod
    def tearDownClass(cls):
        cls.tmpfs.close()

    def setUp(self):
        self.tempfile = self.tmpfs.open('test.tar', 'wb+')
        with tarfile.open(mode="w", fileobj=self.tempfile) as tf:
            tf.addfile(tarfile.TarInfo("foo/bar/baz/spam.txt"), io.StringIO())
            tf.addfile(tarfile.TarInfo("foo/eggs.bin"), io.StringIO())
            tf.addfile(tarfile.TarInfo("foo/yolk/beans.txt"), io.StringIO())
            info = tarfile.TarInfo("foo/yolk")
            info.type = tarfile.DIRTYPE
            tf.addfile(info, io.BytesIO())
        self.tempfile.seek(0)
        self.fs = fs.archive.tarfs.TarReadFS(self.tempfile)

    def tearDown(self):
        self.fs.close()
        self.tempfile.close()

    def test_isfile(self):
        self.assertFalse(self.fs.isfile("foo"))
        self.assertFalse(self.fs.isfile("foo/bar"))
        self.assertFalse(self.fs.isfile("foo/bar/baz"))
        self.assertTrue(self.fs.isfile("foo/bar/baz/spam.txt"))
        self.assertTrue(self.fs.isfile("foo/yolk/beans.txt"))
        self.assertTrue(self.fs.isfile("foo/eggs.bin"))
        self.assertFalse(self.fs.isfile("foo/eggs.bin/baz"))

    def test_isdir(self):
        self.assertTrue(self.fs.isdir("foo"))
        self.assertTrue(self.fs.isdir("foo/yolk"))
        self.assertTrue(self.fs.isdir("foo/bar"))
        self.assertTrue(self.fs.isdir("foo/bar/baz"))
        self.assertFalse(self.fs.isdir("foo/bar/baz/spam.txt"))
        self.assertFalse(self.fs.isdir("foo/eggs.bin"))
        self.assertFalse(self.fs.isdir("foo/eggs.bin/baz"))
        self.assertFalse(self.fs.isdir("foo/yolk/beans.txt"))

    def test_listdir(self):
        self.assertEqual(sorted(self.fs.listdir("foo")), ["bar", "eggs.bin", "yolk"])
        self.assertEqual(self.fs.listdir("foo/bar"), ["baz"])
        self.assertEqual(self.fs.listdir("foo/bar/baz"), ["spam.txt"])
        self.assertEqual(self.fs.listdir("foo/yolk"), ["beans.txt"])

    def test_getinfo(self):
        info = self.fs.getinfo("foo/bar/baz", namespaces=UniversalContainer())
        self.assertEqual(info.name, "baz")
        self.assertEqual(info.size, 0)
        self.assertIs(info.type, ResourceType.directory)

        info = self.fs.getinfo("foo", namespaces=UniversalContainer())
        self.assertEqual(info.name, "foo")
        self.assertEqual(info.size, 0)
        self.assertIs(info.type, ResourceType.directory)
