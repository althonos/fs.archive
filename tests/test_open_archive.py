# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import gzip
import lzma
import zipfile
import tarfile
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

        with mem.openbin('myzip.zip') as myzip:
            self.assertTrue(zipfile.is_zipfile(myzip))

    def _test_tar(self, filename, arcfile, opener):

        mem = fs.open_fs('mem://')

        # Check we can write
        with fs.archive.open_archive(mem, filename) as archive:
            print(archive._saver.compression)
            self.assertIsInstance(archive, fs.archive.tarfs.TarFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        # Check the dumped archive is a gzipped file
        with mem.openbin(filename) as mytar:
            arc = arcfile(fileobj=mytar)
            arc.read()

        # Check we can open it normally
        with mem.openbin(filename) as mytar:
            tar = getattr(tarfile.TarFile, opener)(filename, fileobj=mytar)
        with mem.openbin(filename) as mytar:
            tar = tarfile.TarFile.open(filename, fileobj=mytar)

        # Check we can read it with the TarFS
        with fs.archive.open_archive(mem, filename) as archive:
            self.assertEqual(sorted(archive.listdir('/')), ['abc.txt', 'dir'])
            self.assertEqual(archive.gettext('abc.txt'), 'abc')

    def test_tar_gz(self):
        self._test_tar('mytar.tar.gz', gzip.GzipFile, 'gzopen')
        self._test_tar('mytar.tgz', gzip.GzipFile, 'gzopen')

    def test_tar_xz(self):
        self._test_tar('mytar.tar.xz', lzma.LZMAFile, 'xzopen')
        self._test_tar('mytar.txz', lzma.LZMAFile, 'xzopen')



    def test_tar_xz(self):

        mem = fs.open_fs('mem://')

        # Check we can write
        with fs.archive.open_archive(mem, 'mytar.tar.xz') as archive:
            print(archive._saver.compression)
            self.assertIsInstance(archive, fs.archive.tarfs.TarFS)
            archive.settext('abc.txt', 'abc')
            archive.makedir('dir')

        # Check the dumped archive is a gzipped file
        with mem.openbin('mytar.tar.xz') as mytar:
            xz = lzma.LZMAFile(mytar)
            print(xz.read())

        # Check we can open it normally
        with mem.openbin('mytar.tar.xz') as mytar:
            tar = tarfile.TarFile.xzopen('mytar.tar.xz', fileobj=mytar)
        with mem.openbin('mytar.tar.xz') as mytar:
            tar = tarfile.TarFile.open('mytar.tar.xz', fileobj=mytar)

        # Check we can read it with the TarFS
        with fs.archive.open_archive(mem, 'mytar.tar.xz') as archive:
            self.assertEqual(sorted(archive.listdir('/')), ['abc.txt', 'dir'])
            self.assertEqual(archive.gettext('abc.txt'), 'abc')
