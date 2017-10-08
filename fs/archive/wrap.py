# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import itertools
import six

from .. import errors
from ..errors import ResourceNotFound
from ..copy import copy_file
from ..path import abspath, dirname, join, normpath
from ..mode import Mode
from ..opener import open_fs
from ..wrapfs import WrapFS

from .meta import ArchiveMeta
from ._utils import unique, UniversalContainer



def _copy_file_rich(src_fs, src_path, dst_fs, dst_path=None):
    dst_path = src_path if dst_path is None else dst_path
    copy_file(src_fs, src_path, dst_fs, dst_path)
    src_info = src_fs.getinfo(src_path, namespaces=UniversalContainer())
    dst_fs.setinfo(dst_path, src_info.raw)




@six.add_metaclass(ArchiveMeta)
class WrapWritable(WrapFS):
    """A wrapper that makes a read-only FS writable.

    All modifications are discarded once the filesystem is closed.
    """

    def __init__(self, delegate_fs, writable_fs="mem://"):
        super(WrapWritable, self).__init__(delegate_fs)
        self._rfs = delegate_fs
        self._wfs = open_fs(writable_fs)
        self._removed = set()

    def close(self):
        if not self.isclosed():
            self._wfs.close()
            super(WrapWritable, self).close()

    def exists(self, path):
        _path = self.validatepath(path)
        if self._wfs.exists(path):
            return True
        if self._rfs.exists(path) and _path not in self._removed:
            return True
        return False

    def getinfo(self, path, namespaces=None):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if self._wfs.exists(_path):
            return self._wfs.getinfo(_path, namespaces)
        return self._rfs.getinfo(_path, namespaces)

    def isfile(self, path):
        _path = self.validatepath(path)
        if self._wfs.isfile(_path):
            return True
        if self._rfs.isfile(_path) and _path not in self._removed:
            return True
        return False

    def listdir(self, path):
        _path = self.validatepath(path)

        if not self.getinfo(path).is_dir:
            raise errors.DirectoryExpected(path)

        files_it = itertools.chain()
        if self._wfs.isdir(_path):
            files_it = itertools.chain(files_it, self._wfs.listdir(_path))
        if self._rfs.isdir(_path) and _path not in self._removed:
            files_it = itertools.chain(files_it, self._rfs.listdir(_path))

        def was_removed(name):
            return join(_path, name) in self._removed
        return list(unique(six.moves.filterfalse(was_removed, files_it)))

    def makedir(self, path, permissions=None, recreate=False):

        _path = self.validatepath(path)

        if self.exists(_path):
            if not recreate:
                raise errors.DirectoryExists(path)
        elif not self.exists(dirname(_path)):
            raise errors.ResourceNotFound(dirname(path))
        elif self.isfile(dirname(_path)):
            raise errors.DirectoryExpected(dirname(path))

        if _path in self._removed:
            self._removed.remove(_path)

        # FIXME: possible permission mismatch
        self._wfs.makedirs(dirname(_path), recreate=True)
        return self._wfs.makedir(_path, permissions, recreate)

    def openbin(self, path, mode='r', buffering=-1, **options):
        _path = self.validatepath(path)
        _mode = Mode(mode)
        _mode.validate_bin()

        if not self.exists(_path):
            if not self.isdir(dirname(_path)):
                raise ResourceNotFound(dirname(path))
            if _mode.create:
                if _path in self._removed:
                    self._removed.remove(_path)
                self._wfs.makedirs(dirname(_path), recreate=True)
                return self._wfs.openbin(path, mode, buffering, **options)
            else:
                raise ResourceNotFound(path)
        elif self._wfs.exists(_path):
            return self._wfs.openbin(path, mode, buffering, **options)
        elif not _mode.writing:
            return self._rfs.openbin(path, mode, buffering, **options)
        else:
            self._wfs.makedirs(dirname(_path), recreate=True)
            _copy_file_rich(self._rfs, _path, self._wfs)
            return self._wfs.openbin(path, mode, buffering, **options)

    def remove(self, path):
        _path = self.validatepath(path)
        if not self.getinfo(path).is_file:
            raise errors.FileExpected(path)
        self._removed.add(_path)
        if self._wfs.isfile(_path):
            self._wfs.remove(_path)

    def removedir(self, path):
        _path = self.validatepath(path)
        if not self.isempty(_path):
            raise errors.DirectoryNotEmpty(path)
        self._removed.add(_path)
        if self._wfs.isdir(_path):
            self._wfs.removedir(_path)

    def setinfo(self, path, info):
        _path = self.validatepath(path)
        if not self.exists(_path):
            raise errors.ResourceNotFound(path)
        if self._rfs.exists(_path):
            self._wfs.makedirs(dirname(_path), recreate=True)
            _copy_file_rich(self._rfs, _path, self._wfs, _path)
        return self._wfs.setinfo(_path, info)

    def validatepath(self, path):
        super(WrapWritable, self).validatepath(path)
        return abspath(normpath(path))
