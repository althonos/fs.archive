# coding: utf-8
"""Tar archive filesystems.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import six
import sys
import time
import tarfile
import datetime

from ... import errors
from ...info import Info
from ...mode import Mode
from ...time import datetime_to_epoch
from ...path import dirname, basename, relpath, abspath, splitext
from ...enums import ResourceType
from ..._fscompat import fsdecode, fsencode
from ...permissions import Permissions

from .. import base

from .iotools import RawWrapper
from .tarfile2 import TarFile


class TarReadFS(base.ArchiveReadFS):

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

    def __init__(self, handle, **options):
        super(TarReadFS, self).__init__(handle, **options)
        if isinstance(handle, io.IOBase):
            self._tar = TarFile.open(fileobj=handle, mode='r')
        else:
            self._tar = TarFile.open(handle, mode='r')

        self._encoding = encoding = options.get('encoding') or \
            sys.getdefaultencoding().replace('ascii', 'utf-8')

        self._contents = self._get_contents(self._encoding)

    def _get_contents(self, encoding):
        if six.PY2:
            return {n.decode(encoding) for n in self._tar.getnames()}
        else:
            return set(self._tar.getnames())

    def exists(self, path):
        _path = self.validatepath(path)
        if _path in '/':
            return True
        return relpath(_path) in self._contents

    def isdir(self, path):
        _path = relpath(self.validatepath(path))
        if _path in '/':
            return True
        if _path not in self._contents:
            return False
        if six.PY2:
            _path = _path.encode(self._encoding)
        return self._tar.getmember(_path).isdir()

    def isfile(self, path):
        _path = relpath(self.validatepath(path))
        if _path in '/' or _path not in self._contents:
            return False
        if six.PY2:
            _path = _path.encode(self._encoding)
        return self._tar.getmember(_path).isfile()

    def listdir(self, path):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if not self.isdir(_path):
            raise errors.DirectoryExpected(path)
        return [basename(f) for f in self._contents
                if dirname(abspath(f)) == _path]

    def getinfo(self, path, namespaces=None):
        namespaces = namespaces or ()
        _path = relpath(self.validatepath(path))

        if not self.exists(_path):
            raise errors.ResourceNotFound(path)

        if _path in '/':
            tar_info = tarfile.TarInfo()
            tar_info.type = tarfile.DIRTYPE
        else:
            if six.PY2:
                tar_info = self._tar.getmember(_path.encode(self._encoding))
            else:
                tar_info = self._tar.getmember(_path)

        info = {'basic': {
            'name': basename(_path),
            'is_dir': tar_info.isdir()
        }}

        if 'details' in namespaces:
            if _path in '/':
                info['details'] = {
                    'size': 0,
                    'type': tarfile.DIRTYPE
                }
            else:
                info['details'] = {
                    'size': tar_info.size,
                    'type': int(self._TYPE_MAP.get(
                        tar_info.type, ResourceType.unknown)),
                    'modified': tar_info.mtime
                }
        if 'access' in namespaces and _path not in '/':
            info['access'] = {
                'gid': tar_info.gid,
                'group': tar_info.gname,
                'permissions': Permissions(mode=tar_info.mode).dump(),
                'uid': tar_info.uid,
                'user': tar_info.uname,
            }
        if 'tar' in namespaces and _path not in '/':
            info['tar'] = tar_info.get_info(self._encoding) \
                          if six.PY2 else tar_info.get_info()
            info['tar'].update({
                k.replace('is', 'is_'):getattr(tar_info, k)()
                for k in dir(tar_info)
                if k.startswith('is')
            })

        return Info(info)

    def openbin(self, path, mode='r', buffering=-1, **options):
        _path = relpath(self.validatepath(path))
        _mode = Mode(mode)

        if _mode.writing:
            self._on_modification_attempt(path)
        if not self.exists(path):
            raise errors.ResourceNotFound(path)

        if six.PY2:
            _path = _path.encode(self._encoding)

        tar_info = self._tar.getmember(_path)
        if not tar_info.isfile():
            raise errors.FileExpected(path)

        bin_file = self._tar.extractfile(tar_info)
        if six.PY2: bin_file.flush = lambda: None

        return RawWrapper(bin_file)


class TarSaver(base.ArchiveSaver):

    _compression_map = {
        '.tar': '', '.xz': 'xz', '.txz': 'xz',
        '.gz': 'gz', '.tgz':'gz', '.bz2': 'bz2', '.tbz':'bz2',
    }

    def __init__(self, output, overwrite=False, initial_position=0, **options):
        super(TarSaver, self).__init__(output, overwrite, initial_position)
        self.encoding = options.pop('encoding', 'utf-8')

        self.compression = options.pop('compression', '')

        if not self.compression and hasattr(output, 'name'):
            _, extension = splitext(output.name)
            self.compression = self._compression_map.get(extension, '')


        self.buffer_size = options.pop('buffer_size', io.DEFAULT_BUFFER_SIZE)

    def _to(self, handle, fs):
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
                tar_name = relpath(path)
                if not six.PY3:
                    tar_name = tar_name.encode(self.encoding, 'replace')

                tar_info = tarfile.TarInfo(tar_name)

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
    _read_fs_cls = TarReadFS
    _saver_cls = TarSaver

    def __init__(self, handle, **options):
        options.setdefault('compression', 'gz')
        options.setdefault('encoding', 'utf-8')
        options['proxy'] = options.pop('temp_fs', 'temp://__ziptemp__')
        super(TarFS, self).__init__(handle, **options)
