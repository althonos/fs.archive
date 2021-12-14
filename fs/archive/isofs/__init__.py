# coding: utf-8
"""ISO Disk Image filesystems.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import os
import re
import operator
import weakref

import six
import pycdlib

from ... import errors
from ...mode import Mode
from ...info import Info
from ...path import recursepath, iteratepath, join, frombase
from ...enums import ResourceType, Seek

from .. import base

from ._utils import iso_path_slugify


class ISOFile(io.RawIOBase):
    """A read-only, seekable file on an ISO filesystem.
    """

    def __init__(self, fs, entry):  # noqa: D102, D107

        self._fs = fs
        self._cd = cd = fs._cd
        self._entry = entry

        self._handle, self._size = entry.data_fp, entry.data_length

        if entry.original_data_location == entry.DATA_ON_ORIGINAL_ISO:
            self._start = entry.orig_extent_loc * cd.pvd.logical_block_size()
        else:
            self._start = entry.fp_offset
        self._position = 0
        self._end = self._start + self._size

    def readable(self):  # noqa: D102
        return True

    def writable(self):  # noqa: D102
        return False

    def read(self, size=-1):  # noqa: D102
        with self._fs.lock():
            self._handle.seek(self._start + self._position)
            if size == -1 or self._position + size > self._size:
                size = self._size - self._position
            self._position += size
            return self._handle.read(size)

    def seek(self, offset, whence=Seek.set):  # noqa: D102
        if whence == Seek.set:
            if offset < 0:
                raise ValueError("Negative seek position {}".format(offset))
            self._position = min(offset, self._size)
        elif whence == Seek.current:
            self._position = max(min(self._position + offset, self._size), 0)
        elif whence == Seek.end:
            if offset > 0:
                raise ValueError("Positive seek position {}".format(offset))
            self._position = max(0, self._size + offset)
        else:
            raise ValueError(
                "Invalid whence ({}, should be {}, {} or {})".format(
                    whence, Seek.set, Seek.current, Seek.end
                )
            )
        return self._position

    def seekable(self):  # noqa: D102
        return True

    def tell(self):  # noqa: D102
        return self._position


class ISOReadFS(base.ArchiveReadFS):
    """A read-only ISO filesystem.
    """

    _meta = {
        'standard': {
            'case_insensitive': True,
            'network': False,
            'read_only': True,
            'supports_rename': False,
            'thread_safe': True,
            'unicode_paths': True,
            'virtual': False,
            'max_path_length': None,
            'max_sys_path_length': None,
            'invalid_path_chars': '\0',
        },
    }

    def _get_name_from_entry(self, entry):
        if self._cd.has_rock_ridge() and entry.rock_ridge is not None:
            return entry.rock_ridge.name().decode('utf-8')
        else:
            return entry.file_identifier().decode('ascii').lower().rstrip(';1').rstrip('.')

    def _get_cd_entry(self, path):

        # Get the closest parent of the requested path
        for subpath in recursepath(path):
            if subpath in self._path_table:
                entry = self._path_table[subpath]
                _path = frombase(subpath, path)
                break

        # If the actual entry is found, return it directly
        if not _path:
            return entry

        # Else, recurse down from the closest transitive parent entry
        for name in iteratepath(_path):

            # Get the content of the CWD and store each entry in the path table
            for child in entry.children:
                if not child.is_dot() and not child.is_dotdot():
                    child_name = self._get_name_from_entry(child)
                    child_path = join(subpath, child_name)
                    self._path_table[child_path] = child

            # Raise an error if no entry is found with the given name
            entry = self._path_table.get(join(subpath, name), None)
            if entry is None:
                raise errors.ResourceNotFound(path)

            # Raise an error if the non-final entry is not a directory
            if path != join(subpath, name) and not entry.is_dir():
                raise errors.DirectoryExpected(join(subpath, name))

            # Move one level deeper
            subpath = join(subpath, name)

        return entry

    def _get_info_from_entry(self, entry, namespaces=None):
        namespaces = namespaces or ()

        info = {'basic': {
            'name': self._get_name_from_entry(entry),
            'is_dir': entry.is_dir()
        }}

        # TODO: the rest
        if 'details' in namespaces:
            info['details'] = details = {
                'size': entry.data_length,
                'type': ResourceType.directory if entry.is_dir() else ResourceType.file,
            }

            if self._cd.has_rock_ridge() and entry.rock_ridge is not None:
                if entry.rock_ridge.is_symlink():
                    details['type'] = ResourceType.symlink

        return Info(info)

    def __init__(self, handle, **options):  # noqa: D102, D107
        """Create a new ISO reader filesystem.

        Parameters:
            handle (`io.IOBase` or `str`): A filename or a readable
                file-like object storing the archive to read.

        Keyword Arguments:
            close_handle (`boolean`): If ``True``, close the handle
                when the filesystem is closed. **[default: True]**

        """
        super(ISOReadFS, self).__init__(handle, **options)
        self._cd = pycdlib.PyCdlib()

        if isinstance(handle, io.IOBase):
            self._cd.open_fp(handle)
        else:
            self._cd.open(handle)

        self._joliet = self._cd.joliet_vd is not None
        self._rock_ridge = self._cd.rock_ridge is not None
        self._joliet_only = self._joliet and not self._rock_ridge

        self._path_table = {} #weakref.WeakValueDictionary()
        self._path_table['/'] = self._cd.get_record(iso_path='/')

    def getinfo(self, path, namespaces=None):  # noqa: D102
        _path = self.validatepath(path)

        if _path in '/':
            return Info({
                'basic': {'name': '', 'is_dir': True},
                'details': {'size': 0, 'type': ResourceType.directory}
            })
        else:
            entry = self._get_cd_entry(_path)
            return self._get_info_from_entry(entry, namespaces)

    def scandir(self, path, namespaces=None, page=None):  # noqa: D102
        _path = self.validatepath(path)

        entry = self._get_cd_entry(_path)

        if entry.is_file():
            raise errors.DirectoryExpected(path)

        for child in entry.children:
            if not child.is_dot() and not child.is_dotdot():
                yield self._get_info_from_entry(child, namespaces)

    def listdir(self, path):  # noqa: D102
        return [child.name for child in self.scandir(path)]

    def openbin(self, path, mode='r', buffering=-1, **options):  # noqa: D102
        _path = self.validatepath(path)
        _mode = Mode(mode)

        if _mode.writing:
            self._on_modification_attempt(path)

        if self.isdir(_path):
            raise errors.FileExpected(path)
        elif not self.isfile(_path):
            raise errors.ResourceNotFound(path)

        entry = self._get_cd_entry(_path)
        return ISOFile(self, entry)

    def getmeta(self, namespace="standard"):  # noqa: D102
        meta = self._meta.get(namespace, {}).copy()
        if namespace == "standard" and not (self._rock_ridge or self._joliet):
            meta['case_insensitive'] = self._cd.interchange_level < 4
            meta['max_path_length'] = 255
        return meta

    def getsize(self, path):  # noqa: D102
        _path = self.validatepath(path)
        entry = self._get_cd_entry(_path)
        return entry.file_length()


class ISOSaver(base.ArchiveSaver):
    """An ISO-9660 serializer.
    """

    def __init__(self, output, overwrite=False, initial_position=0, **options):  # noqa: D102, D107
        """Create a new archive filesystem.

        Parameters:
            handle (io.IOBase or str): A filename or a stream storing an
                archive and/or in which to write the updated archive.
            proxy (FS): The filesystem to use as to perform temporary
                write operations. Leave to `None` to use the default
                defined in `~fs.archive.wrap.WrapWritable`.
                **[default: `~fs.memoryfs.MemoryFS`]**

        Keyword Arguments:
            close_handle (boolean): If `True`, close the handle
                when the filesystem is closed. **[default: True]**
            joliet (boolean): If `True`, enable Joliet extensions to
                be added to the ISO image. **[default: True]**
            rock_ridge (str): The level of the Rock Ridge extensions to
                add to the ISO image. **[default: "1.12"]**
            interchange_level (int): The ISO interchange level to use
                for the ISO image. **[default: 1]**

        """
        super(ISOSaver, self).__init__(output, overwrite, initial_position)

        self.joliet = options.pop('joliet', False)
        self.rock_ridge = options.pop('rock_ridge', '1.12')
        self.interchange_level = options.pop('interchange_level', 1)
        self.strict = self.interchange_level < 4

    def _to(self, handle, fs):
        _cd = pycdlib.PyCdlib()
        _cd.new(
            interchange_level=self.interchange_level,
            sys_ident='',
            vol_ident='',
            set_size=1,
            seqnum=1,
            log_block_size=2048,
            vol_set_ident=' ',
            pub_ident_str='',
            preparer_ident_str='',
            app_ident_str='PyCdlib (C) 2015-2016 Chris Lalancette',
            copyright_file='',
            abstract_file='',
            bibli_file='',
            vol_expire_date=None,
            app_use='',
            joliet=self.joliet,
            rock_ridge=self.rock_ridge,
            xa=False
        )
        slug_table = {'/': '/'}

        try:
            for parent, dirs, files in fs.walk('/',
                    search='breadth', namespaces=('details', 'access', 'stat')):
                for d in dirs:
                    path = join(parent, d.name)
                    iso_path = \
                        iso_path_slugify(path, slug_table, True, self.strict)
                    _cd.add_directory(
                        iso_path=iso_path,
                        rr_name=d.name if self.rock_ridge else None,
                        joliet_path=path if self.joliet else None,
                    )
                for f in files:
                    path = join(parent, f.name)
                    iso_path = \
                        iso_path_slugify(path, slug_table, strict=self.strict)
                    _cd.add_fp(
                        fp=fs.openbin(path), length=f.size, iso_path=iso_path,
                        rr_name=f.name if self.rock_ridge else None,
                        joliet_path=path if self.joliet else None,
                    )
        finally:
            if isinstance(handle, io.IOBase):
                _cd.write_fp(handle)
            else:
                _cd.write(handle)
            _cd.close()


class ISOFS(base.ArchiveFS):
    """An ISO-9660 filesystem.
    """

    _read_fs_cls = ISOReadFS
    _saver_cls = ISOSaver
