# coding: utf-8
"""Tar archive filesystems.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import sys
import time
import tarfile
import datetime

import six

from ... import errors
from ...info import Info
from ...mode import Mode
from ...time import datetime_to_epoch
from ...path import basename, relpath, splitext, isbase, parts, frombase
from ...enums import ResourceType
from ...permissions import Permissions

from .. import base
from .._utils import unique

from .iotools import RawWrapper
from .tarfile2 import TarFile


class TarReadFS(base.ArchiveReadFS):
    """A read-only filesystem within a TAR archive.
    """

    _meta = {
        'standard': {
            'case_insensitive': True, # FIXME : is it ?
            'network': False,
            'read_only': True,
            'supports_rename': False,
            'thread_safe': True, # FIXME: is it ?
            'unicode_paths': True,
            'virtual': False,
            'max_path_length': None,
            'max_sys_path_length': None,
            'invalid_path_chars': '\x00\x01',
        },
    }

    _TYPE_MAP = {
        tarfile.BLKTYPE: ResourceType.block_special_file,
        tarfile.CHRTYPE: ResourceType.character,
        tarfile.DIRTYPE: ResourceType.directory,
        tarfile.FIFOTYPE: ResourceType.fifo,
        tarfile.REGTYPE: ResourceType.file,
        tarfile.AREGTYPE: ResourceType.file,
        tarfile.SYMTYPE: ResourceType.symlink,
        tarfile.CONTTYPE: ResourceType.file,
        tarfile.LNKTYPE: ResourceType.symlink,
    }


    if six.PY2:
        def _decode(self, string):
            return string.decode(self._encoding)
    else:
        def _decode(self, string):
            return string

    def __init__(self, handle, **options):  # noqa: D102, D107
        super(TarReadFS, self).__init__(handle, **options)
        if isinstance(handle, io.IOBase):
            self._tar = TarFile.open(fileobj=handle, mode='r')
        else:
            self._tar = TarFile.open(handle, mode='r')

        self._encoding = encoding = options.get('encoding') or \
            sys.getdefaultencoding().replace('ascii', 'utf-8')

        self._members = {
            self._decode(info.name): info
                for info in self._tar.getmembers()
        }

    def exists(self, path):  # noqa: D102
        _path = self.validatepath(path)
        return any(isbase(_path, f) for f in self._members)

    def isdir(self, path):  # noqa: D102
        _path = relpath(self.validatepath(path))
        try:
            return self._members[_path].isdir()
        except KeyError:
            return any(isbase(_path, f) for f in self._members)

    def isfile(self, path):  # noqa: D102
        _path = relpath(self.validatepath(path))
        try:
            return self._members[_path].isfile()
        except KeyError:
            return False

    def listdir(self, path):  # noqa: D102
        _path = relpath(self.validatepath(path))
        if self.gettype(_path) is not ResourceType.directory:
            raise errors.DirectoryExpected(path)
        children = (frombase(_path, n) for n in self._members if isbase(_path, n))
        return list(unique(parts(child)[1] for child in children if relpath(child)))

    def getinfo(self, path, namespaces=None):  # noqa: D102
        namespaces = namespaces or ()
        _path = relpath(self.validatepath(path))

        try:
            _inferred = False
            tar_info = self._members[_path]
        except KeyError:
            if not self.isdir(_path):
                raise errors.ResourceNotFound(path)
            _inferred = True
            tar_info = tarfile.TarInfo(_path)
            tar_info.type = tarfile.DIRTYPE

        info = {'basic': {
            'name': basename(_path),
            'is_dir': tar_info.isdir()
        }}

        if 'details' in namespaces:
            info['details'] = {
                'size': tar_info.size,
                'type': int(self._TYPE_MAP.get(
                    tar_info.type, ResourceType.unknown)),
            }
            if not _inferred:
                info['details']['modified'] = tar_info.mtime

        if not _inferred and 'access' in namespaces:
            info['access'] = {
                'gid': tar_info.gid,
                'group': tar_info.gname,
                'permissions': Permissions(mode=tar_info.mode).dump(),
                'uid': tar_info.uid,
                'user': tar_info.uname,
            }

        if not _inferred and 'tar' in namespaces:
            info['tar'] = tar_info.get_info(self._encoding) \
                          if six.PY2 else tar_info.get_info()
            info['tar'].update({
                k.replace('is', 'is_'):getattr(tar_info, k)()
                for k in dir(tar_info)
                if k.startswith('is')
            })

        return Info(info)

    def openbin(self, path, mode='r', buffering=-1, **options):  # noqa: D102
        _path = relpath(self.validatepath(path))
        _mode = Mode(mode)

        if _mode.writing:
            self._on_modification_attempt(path)
        if self.gettype(path) is not ResourceType.file:
            raise errors.FileExpected(path)

        bin_file = self._tar.extractfile(self._members[_path])
        if six.PY2: bin_file.flush = lambda: None

        return RawWrapper(bin_file)


class TarSaver(base.ArchiveSaver):
    """A TAR archive serializer.
    """

    _compression_map = {
        '.tar': '', '.xz': 'xz', '.txz': 'xz',
        '.gz': 'gz', '.tgz':'gz', '.bz2': 'bz2', '.tbz':'bz2',
    }

    if six.PY2:
        def _encode(self, string):
            return string.encode(self.encoding)
    else:
        def _encode(self, string):
            return string

    def __init__(self, output, overwrite=False, initial_position=0, **options):  # noqa: D102, D107
        super(TarSaver, self).__init__(output, overwrite, initial_position)
        self.encoding = options.pop('encoding', 'utf-8')

        self.compression = options.pop('compression', '')

        if not self.compression and hasattr(output, 'name'):
            if isinstance(output.name, six.binary_type):
                name = output.name.decode(sys.getfilesystemencoding())
            else:
                name = output.name
            _, extension = splitext(name)
            self.compression = self._compression_map.get(extension, '')

        self.buffer_size = options.pop('buffer_size', io.DEFAULT_BUFFER_SIZE)

    def _to(self, handle, fs):  # noqa: D102
        attr_map = {
            'uid': 'uid', 'gid': 'gid', 'uname': 'user', 'gname': 'group'}
        type_map = {
            v:k for k,v in TarReadFS._TYPE_MAP.items()}

        mode = 'w:{}'.format(self.compression or '')
        if isinstance(handle, io.IOBase):
            _tar = TarFile.open(fileobj=handle, mode=mode)
        else:
            _tar = TarFile.open(handle, mode=mode)

        current_time = time.time()

        with _tar:
            for path, info in fs.walk.info(namespaces=('details', 'access', 'stat')):

                tar_info = tarfile.TarInfo(self._encode(relpath(path)))

                if info.has_namespace('stat'):
                    mtime = info.get('stat', 'st_mtime', current_time)
                else:
                    mtime = info.modified or current_time

                if isinstance(mtime, datetime.datetime):
                    mtime = datetime_to_epoch(mtime)
                if isinstance(mtime, float):
                    mtime = int(mtime)
                tar_info.mtime = mtime

                if info.has_namespace('access'):
                    for tarattr, infoattr in attr_map.items():
                        if getattr(info, infoattr) is not None:
                            setattr(tar_info, tarattr, getattr(info, infoattr))
                    tar_info.mode = getattr(info.permissions, 'mode', 0o420)


                tar_info.size = info.size
                tar_info.type = type_map.get(info.type, tarfile.REGTYPE)

                if not info.is_dir:
                    with fs.openbin(path) as bin_file:
                        _tar.addfile(tar_info, bin_file)
                else:
                    _tar.addfile(tar_info)


class TarFS(base.ArchiveFS):
    """A filesystem in a TAR archive.
    """

    _read_fs_cls = TarReadFS
    _saver_cls = TarSaver

    def __init__(self, handle, **options):  # noqa: D102, D107
        options.setdefault('compression', 'gz')
        options.setdefault('encoding', 'utf-8')
        options['proxy'] = options.pop('temp_fs', 'temp://__ziptemp__')
        super(TarFS, self).__init__(handle, **options)
