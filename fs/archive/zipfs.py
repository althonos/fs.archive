# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import io
import six
import time
import shutil
import zipfile
import datetime

from .. import errors
from ..info import Info
from ..mode import Mode
from ..time import datetime_to_epoch
from ..path import forcedir, relpath, dirname, basename, abspath
from ..path import iteratepath, recursepath, frombase, join
from ..enums import ResourceType
from ..iotools import RawWrapper


from . import base




class ZipReadFS(base.ArchiveReadFS):

    _meta = {
        'case_insensitive': True,
        'network': False,
        'read_only': True,
        'supports_rename': False,
        'thread_safe': True,
        'unicode_paths': True,
        'virtual': False
    }

    def __init__(self, handle, **options):
        super(ZipReadFS, self).__init__(handle)
        self._zip = zipfile.ZipFile(handle)

        self._namelist = self._zip.namelist()
        self._contents = self._get_contents()

    def _get_contents(self):
        contents = set()
        for name in self._namelist:
            for partial_name in recursepath(name):
                partial_name = relpath(partial_name)
                if partial_name != name:
                    partial_name = forcedir(partial_name)
                if partial_name:
                    contents.add(partial_name)
        return contents

    def getinfo(self, path, namespaces=None):
        namespaces = namespaces or ()
        _path = self.validatepath(path)

        if not self.exists(_path):
            raise errors.ResourceNotFound(path)

        info = {'basic': {
            'name': basename(_path),
            'is_dir': self.isdir(_path),
        }}

        if namespaces:

            try:
                zip_name = relpath(
                    forcedir(_path) if self.isdir(_path) else _path)
                zip_info = self._zip.getinfo(zip_name)
            except KeyError:
                if info['basic']['is_dir']: # Implicit directory
                    info['details'] = {
                        'size': 0,
                        'type': ResourceType.directory,
                    }
            else:
                modified_epoch = datetime_to_epoch(
                    datetime.datetime(*zip_info.date_time)
                )
                info['zip'] = {
                    k: getattr(zip_info, k)
                    for k in dir(zip_info)
                    if (not k.startswith('_') and
                        not callable(getattr(zip_info, k)))
                }
                info['details'] = {
                    'size': zip_info.file_size,
                    'type': int(
                        ResourceType.directory
                        if zip_info.is_dir() else
                        ResourceType.file
                    ),
                    'modified': modified_epoch
                }

        return Info(info)

    def getbytes(self, path):
        _path = self.validatepath(path)

        if self.isdir(_path):
            raise errors.FileExpected(path)
        if not self.isfile(_path):
            raise errors.ResourceNotFound(path)

        zip_bytes = self._zip.read(relpath(_path))
        return zip_bytes

    def isfile(self, path):
        _path = self.validatepath(path).lower()
        return relpath(_path) in self._contents

    def isdir(self, path):
        if path in '/':
            return True
        _path = self.validatepath(path).lower()
        return relpath(forcedir(_path)) in self._contents

    def exists(self, path):
        if path in '/':
            return True
        return self.isdir(path) or self.isfile(path)

    def listdir(self, path):
        return [entry.name for entry in self.scandir(path)]

    def scandir(self, path, namespaces=None, page=None):
        _path = self.validatepath(path)

        if not self.exists(path):
            raise errors.ResourceNotFound(path)
        elif not self.isdir(path):
            raise errors.DirectoryExpected(path)

        seen = set()

        for fullname in self._namelist:
            fullname = abspath(fullname.rstrip('/'))

            if fullname.startswith(_path) and fullname != _path:

                name = iteratepath(relpath(frombase(_path, fullname)))[0]
                fullname = join(_path, name)

                if namespaces is None:
                    info = Info({'basic': {
                        'name': name,
                        'is_dir': self.isdir(fullname)
                    }})
                else:
                    info = self.getinfo(fullname, namespaces=namespaces)

                if fullname not in seen:
                    seen.add(fullname)
                    yield info

    def openbin(self, path, mode='r', buffering=-1, **options):
        _path = self.validatepath(path)
        _mode = Mode(mode)

        if _mode.writing:
            self._on_modification_attempt(path)

        if self.isdir(_path):
            raise errors.FileExpected(path)
        if not self.isfile(_path):
            raise errors.ResourceNotFound(path)

        bin_file = self._zip.open(relpath(path), 'r')
        return RawWrapper(bin_file)

    def close(self):
        if not self.isclosed():
            super(ZipReadFS, self).close()
            self._zip.close()


class ZipSaver(base.ArchiveSaver):

    def __init__(self, output, careful=True, to_stream=True, **options):
        super(ZipSaver, self).__init__(output, careful, to_stream)
        self.encoding = options.pop('encoding', 'utf-8')
        self.compression = options.pop('compression', zipfile.ZIP_DEFLATED)
        self.buffer_size = options.pop('buffer_size', io.DEFAULT_BUFFER_SIZE)
        self.careful = careful

    def _to(self, handle, fs):
        _zip = zipfile.ZipFile(
            handle, mode='w', compression=self.compression, allowZip64=True)

        with _zip:

            for path, info in fs.walk.info(namespaces=('details', 'stat')):

                # Zip names must be relative, directory names must end
                # with a slash.
                zip_name = relpath(forcedir(path) if info.is_dir else path)
                if six.PY2:
                    # Python2 expects bytes filenames
                    zip_name = zip_name.encode(self.encoding, 'replace')

                if info.has_namespace('stat'):
                    # get zip time directory from the stat structure
                    st_mtime = info.get('stat', 'st_mtime', None)
                    _mtime = time.localtime(st_mtime)
                    zip_time = _mtime[0:6]

                else:
                    # use the modified time from details namespace.
                    mt = info.modified or datetime.datetime.utcnow()
                    zip_time = (
                        mt.year, mt.month, mt.day,
                        mt.hour, mt.minute, mt.second
                    )

                # create a custom zip_info
                zip_info = zipfile.ZipInfo(zip_name, zip_time)

                if info.is_dir:
                    # only write empty directories (other are implicit)
                    if next(fs.walk.files(path), None) is None:
                        _zip.writestr(zip_info, b'')
                else:
                    #
                    size = fs.getsize(path)
                    if size is not None and size > 0:
                        zip_info.file_size = size

                    with fs.openbin(path, 'rb') as src_file:
                        with _zip.open(zip_info, 'w') as dst_file:
                            shutil.copyfileobj(src_file, dst_file, self.buffer_size)


class ZipFS(base.ArchiveFS):
    _read_fs_cls = ZipReadFS
    _saver_cls = ZipSaver

    def __init__(self, handle, **options):
        options.setdefault('compression', zipfile.ZIP_DEFLATED)
        options.setdefault('encoding', 'utf-8')
        options['proxy'] = options.pop('temp_fs', 'temp://__ziptemp__')
        super(ZipFS, self).__init__(handle, **options)
