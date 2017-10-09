# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import pycdlib
import tempfile
import unittest

from six.moves import filterfalse
from six.moves.queue import Queue

import fs.test
import fs.wrap
import fs.errors
import fs.memoryfs
import fs.archive.isofs

from fs.path import relpath, join, forcedir, abspath, recursepath
from fs.archive.test import ArchiveReadTestCases, ArchiveIOTestCases


def compress(rr, joliet, il):
    def iso_compress(handle, source_fs):
        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
        saver = fs.archive.isofs.ISOSaver(
            handle, overwrite=False,
            rock_ridge=rr, joliet=joliet,
            interchange_level=il
        )
        saver.save(source_fs)
    return iso_compress


def iso_name(entry, joliet=False, rock_ridge=False):
    if entry.file_identifier() in b'/':
        return '/'
    elif rock_ridge:
        return entry.rock_ridge.name().decode('utf-8').rsplit(';1').rsplit('.')
    elif joliet:
        return entry.file_identifier().decode('utf-16be')
    return entry.file_identifier().decode('ascii')


def iso_path(iso_entry, joliet=False, rock_ridge=False):
    path = iso_name(iso_entry, joliet, rock_ridge)
    while iso_entry.parent is not None:
        path = join(iso_name(iso_entry.parent, joliet, rock_ridge), path)
        iso_entry = iso_entry.parent
    return abspath(path).lower()


### rw FS ###

class TestISOFS(fs.test.FSTestCases, unittest.TestCase):

    def make_fs(self):
        self.tempfile = tempfile.mktemp()
        return fs.archive.isofs.ISOFS(self.tempfile)

    def destroy_fs(self, fs):
        fs.close()
        if os.path.exists(self.tempfile):
            os.remove(self.tempfile)
        del self.tempfile


### ro FS ###

class _TestISOReadFS(ArchiveReadTestCases):

    long_names = False
    unicode_names = False
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_read_fs = fs.archive.isofs.ISOReadFS

    @staticmethod
    def remove_archive(handle):
        handle.close()

    def setUp(self):
        handle = io.BytesIO()
        super(_TestISOReadFS, self).setUp(handle)

    def test_create_failed(self):
        self.assertRaises(fs.errors.CreateFailed, fs.archive.isofs.ISOFS, 1)


class TestISOv1ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 1))


class TestISOv2ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 2))


class TestISOv3ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 3))


class TestISOv4ReadFS(_TestISOReadFS, unittest.TestCase):

    compress = staticmethod(compress(None, False, 4))


class TestISORockRidge112ReadFS(_TestISOReadFS, unittest.TestCase):

    long_names = True
    compress = staticmethod(compress('1.12', False, 1))


class TestISORockRidge109ReadFS(_TestISOReadFS, unittest.TestCase):

    long_names = True
    compress = staticmethod(compress('1.09', False, 1))


class TestISOJolietReadFS(_TestISOReadFS, unittest.TestCase):

    long_name = True
    compress = staticmethod(compress(None, True, 1))



### FS IO ###

class TestISOFSio(ArchiveIOTestCases, unittest.TestCase):

    compress = staticmethod(compress('1.12', False, 1))
    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)
    _archive_fs = fs.archive.isofs.ISOFS

    @staticmethod
    def load_archive(handle):
        return fs.archive.isofs.ISOFS(handle)

    @staticmethod
    def iter_entries(handle):

        cd = pycdlib.PyCdlib()

        if hasattr(handle, 'seek') and handle.seekable():
            handle.seek(0)
            cd.open_fp(handle)
        else:
            cd.open(handle)

        rock_ridge = cd.rock_ridge is not None
        joliet = cd.joliet_vd is not None
        joliet_only = joliet and not rock_ridge

        directories = Queue()
        directories.put(cd.get_entry('/', joliet_only))

        while not directories.empty():
            directory = directories.get()

            for child in directory.children:
                if not child.is_dot() and not child.is_dotdot():
                    if child.is_dir():
                        directories.put(child)
                    yield child

    def iter_files(self, handle):
        for entry in self.iter_entries(handle):
            if entry.is_file():
                yield iso_path(entry)

    def iter_dirs(self, handle):
        for entry in self.iter_entries(handle):
            if entry.is_dir():
                yield iso_path(entry)



### FS Saver ###

class TestISOSaver(unittest.TestCase):

    make_source_fs = staticmethod(fs.memoryfs.MemoryFS)

    def test_unicode_duplicates(self):
        """Check unicode names are not collisioning when slugified.
        """
        source = self.make_source_fs()
        source.makedir('/😋')
        source.settext('/😋/éé.txt', 'some accents in an emoji')
        source.settext('/éé.txt', 'some accents')
        source.settext('/üü.txt', 'some umlauts')
        source.settext('/☭☭.txt', 'some communism')

        stream = io.BytesIO()
        saver = fs.archive.isofs.ISOSaver(stream)
        saver.save(source)

        stream.seek(0)
        iso = fs.archive.isofs.ISOReadFS(stream)
        self.assertEqual(
            sorted(iso.listdir('/')),
            ['éé.txt', 'üü.txt' ,'☭☭.txt', '😋'],
        )
        self.assertEqual(iso.gettext('/éé.txt'), 'some accents')
        self.assertEqual(iso.gettext('/üü.txt'), 'some umlauts')
        self.assertEqual(iso.gettext('/☭☭.txt'), 'some communism')
        self.assertEqual(iso.gettext('/😋/éé.txt'), 'some accents in an emoji')
