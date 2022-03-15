# coding: utf-8
"""7z archive filesystems.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import collections
import io
import functools
import itertools
import stat

import six
import lzma
import py7zr
import iocursor
from py7zr.helpers import ArchiveTimestamp
from py7zr.py7zr import FILE_ATTRIBUTE_UNIX_EXTENSION
from py7zr.exceptions import Bad7zFile

from ... import errors
from ...info import Info
from ...mode import Mode
from ...osfs import OSFS
from ...path import abspath, dirname, basename, join, relpath
from ...enums import ResourceType
from ...permissions import Permissions

from .. import base


class _Origin(object):
    def __init__(self, fs, path):
        self.fs = fs
        self.path = path
    def open(self, mode="rb"):
        return self.fs.openbin(self.path, mode)


class SevenZipReadFS(base.ArchiveReadFS):
    """A read-only filesystem within a 7z archive.
    """

    _meta = {
        'standard': {
            'case_insensitive': False,
            'network': False,
            'read_only': True,
            'supports_rename': False,
            'thread_safe': True,
            'unicode_paths': True,
            'virtual': False,
            'max_path_length': None,
            'max_sys_path_length': None,
            'invalid_path_chars': '\x00\x01',
        },
    }

    def __init__(self, handle, **options):  # noqa: D102, D107
        """Create a new 7z reader filesystem.

        Parameters:
            handle (`io.IOBase` or `str`): A filename or a readable
                file-like object storing the archive to read.

        Keyword Arguments:
            close_handle (`boolean`): If ``True``, close the handle
                when the filesystem is closed. **[default: True]**
            password (`str`): The password to use for decrypting the
                archive contents. **[default: None]**

        """
        super(SevenZipReadFS, self).__init__(handle, **options)
        self._password = options.get('password')
        self._start_position = self._handle.tell()

        _7z = None
        try:
            _7z = py7zr.SevenZipFile(handle, 'r', password=self._password)
        except py7zr.exceptions.PasswordRequired as exc:
            raise errors.CreateFailed(
                exc=errors.PermissionDenied(msg="7z archive is password protected", exc=exc)
            )
        except (lzma.LZMAError, TypeError, Bad7zFile) as exc:
            raise errors.CreateFailed(exc=exc)
        else:
            self._members = {abspath(info.filename):info for info in _7z.files}
            self._bydir = collections.defaultdict(list)
            for info in _7z.files:
                self._bydir[abspath(dirname(info.filename))].append(info)
        finally:
            if _7z is not None:
                _7z.close()

    def _get_info_from_entry(self, entry, namespaces=None):
        namespaces = namespaces or ()

        info = {
            'basic': {
                'name': basename(entry.filename),
                'is_dir': entry.is_directory,
            }
        }

        if "details" in namespaces:
            properties = entry.file_properties()
            info['details'] = details = {}

            raw_type = entry.st_fmt
            if raw_type is not None:
                details['type'] = OSFS.STAT_TO_RESOURCE_TYPE.get(raw_type, ResourceType.unknown)
            elif properties['is_directory']:
                details['type'] = stat.S_IFDIR
            else:
                details['type'] = stat.S_IFREG

            if "uncompressed" in properties:
                details["size"] = properties["uncompressed"]

            creationtime = properties.get("creationtime")
            if creationtime is not None:
                details['created'] = creationtime.totimestamp()
            lastaccesstime = properties.get("lastaccesstime")
            if lastaccesstime is not None:
                details['accessed'] = lastaccesstime.totimestamp()
            lastwritetime = properties.get("lastwritetime")
            if lastwritetime is not None:
                details['modified'] = lastwritetime.totimestamp()

        # TODO: extract UNIX permissions
        # if "access" in namespaces:
        #     properties = entry.file_properties()
        #     info['access'] = access = {}

        return Info(info)

    def getinfo(self, path, namespaces=None):  # noqa: D102
        _path = abspath(self.validatepath(path))

        if _path == '/':
            return Info({'basic': {'name': '', 'is_dir': True}})

        entry = self._members.get(_path)
        if entry is None:
            raise errors.ResourceNotFound(path)

        return self._get_info_from_entry(entry, namespaces)

    def listdir(self, path):  # noqa: D102
        return [entry.name for entry in self.scandir(path)]

    def scandir(self, path, namespaces=None, page=None):  # noqa: D102
        _path = abspath(self.validatepath(path))

        if _path != '/':
            _info = self._members.get(_path)
            if _info is None:
                raise errors.ResourceNotFound(path)
            elif not _info.is_directory:
                raise errors.DirectoryExpected(path)

        for entry in self._bydir.get(_path, ()):
            yield self._get_info_from_entry(entry, namespaces)

    def openbin(self, path, mode='r', buffering=-1, **options):  # noqa: D102
        _path = abspath(self.validatepath(path))
        _mode = Mode(mode)

        if _mode.writing:
            self._on_modification_attempt(path)

        _info = self._members.get(_path)
        if _info is None:
            raise errors.ResourceNotFound(path)
        elif _info.is_directory:
            raise errors.FileExpected(path)
        elif _info.emptystream:
            return io.BytesIO()

        self._handle.seek(self._start_position)

        _7z = None
        try:
            _7z = py7zr.SevenZipFile(self._handle, 'r', password=self._password)
            decompressed = _7z.read([_path])
        except py7zr.exceptions.PasswordRequired as exc:
            raise errors.PermissionDenied(msg="7z archive is password protected", exc=exc)
        except lzma.LZMAError as exc:
            raise errors.OperationFailed(exc=exc)
        finally:
            if _7z is not None:
                _7z.close()

        return iocursor.Cursor(decompressed[relpath(_path)].getbuffer())

    def isdir(self, path):
        if path in '/':
            return True
        _path = self.validatepath(path)
        info = self._members.get(_path)
        return False if info is None else info.is_directory

    def isfile(self, path):
        if path in '/':
            return False
        _path = self.validatepath(path)
        info = self._members.get(_path)
        return False if info is None else not info.is_directory

    def exists(self, path):
        if path in '/':
            return True
        _path = self.validatepath(path)
        return _path in self._members


class SevenZipSaver(base.ArchiveSaver):
    """A 7z archive saver.
    """

    def __init__(self, output, overwrite=False, initial_position=0, **options):  # noqa: D102, D107
        """Create a new 7z serializer.

        Parameters:
            output (`io.IOBase` or `str`): The filename of the destination
                or a file handle in which to write the archive.
            overwrite (`boolean`): If True, use a temporary file to save
                the contents of the archive. Useful when updating an archive
                file. **[default: False]**
            initial_position (`int`): The initial position of the stream when
                it was seen for the first time. **[default: 0]**

        Keyword Arguments:
            password (`str`): The password to use for encrypting the
                archive contents. **[default: None]**
            encrypt_header (`bool`): Whether or not to encrypt the archive
                header, which contains the file list. **[default: False]**

        """
        self._password = options.get("password")
        self._encrypt_header = options.get("encrypt_header", False)
        super(SevenZipSaver, self).__init__(output, overwrite, initial_position)

    @staticmethod
    def _make_file_info(fs, path, info):
        file_info = {}
        file_info["filename"] = path

        file_info["emptystream"] = empty = info.is_dir or info.size == 0
        file_info["origin"] = None if empty else _Origin(fs, path)

        created = info.get("details", "created")
        if created is not None:
            file_info["creationtime"] = ArchiveTimestamp.from_datetime(created)
        modified = info.get("details", "modified")
        if modified is not None:
            file_info["lastwritetime"] = ArchiveTimestamp.from_datetime(modified)
        accessed = info.get("details", "accessed")
        if created is not None:
            file_info["lastaccesstime"] = ArchiveTimestamp.from_datetime(accessed)

        if info.is_dir:
            file_info["attributes"] = stat.FILE_ATTRIBUTE_DIRECTORY
            file_info["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION
            file_info["attributes"] |= stat.S_IFDIR << 16
        else:
            file_info["attributes"] = stat.FILE_ATTRIBUTE_ARCHIVE
            file_info["attributes"] |= FILE_ATTRIBUTE_UNIX_EXTENSION
            file_info["uncompressed"] = info.size

        permissions = info.get("access", "permissions")
        if permissions is not None:
            file_info["attributes"] |= Permissions.load(permissions).mode << 16

        return file_info

    def _to(self, handle, fs):  # noqa: D102
        with py7zr.SevenZipFile(
                handle,
                mode="w",
                password=self._password,
                header_encryption=self._encrypt_header
        ) as _7z:
            _7z.header.initialize()
            for parent, dirs, files in fs.walk("/", search='breadth', namespaces=["details", "access"]):
                for resource in itertools.chain(dirs, files):
                    path = join(parent, resource.name)
                    file_info = self._make_file_info(fs, path, resource)
                    _7z.header.files_info.files.append(file_info)
                    _7z.header.files_info.emptyfiles.append(file_info["emptystream"])
                    _7z.files.append(file_info)
                    folder = _7z.header.main_streams.unpackinfo.folders[-1]
                    _7z.worker.archive(_7z.fp, _7z.files, folder, deref=_7z.dereference)


class SevenZipFS(base.ArchiveFS):
    """A filesystem within a 7z archive.
    """

    _read_fs_cls = SevenZipReadFS
    _saver_cls = SevenZipSaver
