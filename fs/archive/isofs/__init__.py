# coding: utf-8
"""ISO archive read-only filesystem.
"""
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import six
import construct

from ... import errors
from ...enums import Seek
from ...base import FS
from ...info import Info
from ...path import join, recursepath
from ...tempfs import TempFS
from ...memoryfs import MemoryFS
from ..._fscompat import fsdecode, fspath

from .. import base

from . import structs


class ISOReadFile(io.RawIOBase):

    def __init__(self, fs, record):
        self._fs = fs
        self._handle = fs._handle
        self._record = record
        self._start = record['Location of Extent'] * fs._blocksize
        self._end = self._start + record['Data Length']
        self._position = 0

    @property
    def name(self):
        return self._record['File Identifier'].split(b';')[0].decode('utf-8')

    def read1(self, size=-1):
        if size == -1 or size + self._position > len(self):
            size = len(self) - self._position
        with self._fs._lock:
            self._handle.seek(self._start + self._position)
            buffer = self._handle.read(size)
        self._position += size
        return buffer

    def read(self, size=-1):
        return self.read1(size=size)

    def __len__(self):
        return self._record['Data Length']

    def readable(self):
        return True

    def seek(self, offset, whence=Seek.set):

        if whence == Seek.set:
            if offset > len(self):
                offset = len(self)
            elif offset < 0:
                offset = 0
            with self._fs._lock:
                self._handle.seek(self._start + offset)
                self._position = offset

        if whence == Seek.current:
            if offset + self._start + self._position > self._end:
                offset = self._end - self._position - self._start
            elif offset + self._start + self._position < 0:
                offset = - self._start - self._position
            with self._fs._lock:
                self._handle.seek(self._start + self._position + offset)
                self._position += offset

        if whence == Seek.end:
            if offset > 0:
                offset = 0
            elif -offset > len(self):
                offset = -len(self)
            with self._fs._lock:
                self._handle.seek(self._end + offset)
                self._position += offset

        return self._position

    def seekable(self):
        return True

    def tell(self):
        return self._position

    def tellable(self):
        return True

    def writable(self):
        return False


class ISOReadFS(base.ArchiveReadFS):

    _meta = {
        'standard': {
            'case_insensitive': True, # FIXME : is it ?
            'network': False,
            'read_only': True,
            'supports_rename': False,
            'thread_safe': False, # FIXME: is it ?
            'unicode_paths': False,
            'invalid_path_chars': '\x00\x01',
            'virtual': False,
            'max_path_length': None,
            'max_sys_path_length': None,
        },
        # 'archive': {
        #     # IN LEVEL 1
        #     # 'max_dirname_length': 8
        #     # 'max_filename_length': 12
        #     # IN LEVEL 3
        #     'max_dirname_length': 31   # in
        #     'max_filename_length': 30, # in Level 3
        #     # IN ENHANCED VOLUME DESCRIPTOR
        #     # 'max_filename_length': 207
        #     # 'max_dirname_length': 207
        #     #
        #     'max_depth': 8,
        #     'na'
        # }
    }

    def __init__(self, handle, **options):
        """Create a new read-only filesystem from an ISO image byte stream.
        """

        super(ISOReadFS, self).__init__(handle)

        self._joliet = False
        self._rockridge = False

        try:
            descs = list(self._descriptors())
            pvd = next(d for d in descs if d.type=='PrimaryVolumeDescriptor')
            svd = next(
                (d for d in descs if d.type=='SupplementaryVolumeDescriptor'),
                None,
            )
        except StopIteration:
            raise errors.CreateFailed(
                'could not find primary volume descriptor')
        except construct.core.ConstructError as ce:
            raise errors.CreateFailed(
                'error occured while parsing: {}'.format(ce))

        self._blocksize = pvd['Logical Block Size']

        if svd is not None:
            self._path_table = {'/': svd['Root Directory Record']}
            self._joliet = True
        else:
            self._path_table = {'/': pvd['Root Directory Record']}

    def _descriptors(self):
        """Yield the descriptors of the ISO image.
        """
        # Go to initial descriptor adress
        self._handle.seek(16 * 2048)
        # Read all descriptors until the terminator
        while 'Terminator not encountered':
            # Read the next block
            block = self._handle.read(2048)
            # Peek at the descriptor header,
            meta = construct.Peek(structs.VolumeDescriptorHeader).parse(block)
            # If we could not find a valid descriptor header: stop iteration
            if meta is None:
                break
            # get the struct to use
            desc_parser = getattr(
                structs, meta.type, structs.RawVolumeDescriptor)
            # Yield the right descriptor struct
            yield desc_parser.parse(block)
            # Stop at the terminator
            if meta.type == 'VolumeDescriptorSetTerminator':
                break

    def _directory_records(self, block_id):
        """Yield the records within a directory.

        Note:
            ``.`` and ``..`` (which in the ISO9660 standard are
            defined as ``\x00`` and ``\x01``) are ignored.
        """

        # Get the main directory block
        extent = self._get_block(block_id)
        block = structs.DirectoryBlock(self._blocksize).parse(extent)
        block.records = block.records[2:] # NB: remove '\x01' and '\x02'

        while block.records:
            for record in block.records:
                # Stop iterator if we enter another directory
                if record['File Identifier'] in (b'\x00', b'\x01'):
                    return
                yield record

            # Attempt to explore adjacent block
            extent = self._handle.read(self._blocksize)
            block = structs.DirectoryBlock(self._blocksize).parse(extent)

    def _find(self, path):
        for subpath in recursepath(path):

            record = self._path_table.get(subpath)
            if record is None:
                raise errors.ResourceNotFound(subpath)

            for r in self._directory_records(record["Location of Extent"]):
                record_name = self._make_name(r['File Identifier'])
                record_path = join(subpath, record_name.lower())
                self._path_table[record_path] = r

    def _get_block(self, block_id):
        self._handle.seek(self._blocksize * block_id)
        return self._handle.read(self._blocksize)

    def _get_record(self, path):
        path = path.lower()
        if path not in self._path_table:
            self._find(path)
        return self._path_table[path]

    def _make_info_from_record(self, record, namespaces=None):
        namespaces = namespaces or ()

        name = self._make_name(record['File Identifier'])

        # FIXME: other namespaces
        info = {'basic': {
            'name': name.lower() if name != '\0' else '',
            'is_dir': record['Flags'].is_dir,
        }}

        if 'details' in namespaces:
            info['details'] = {
                'size': record['Data Length'],
            }
        if 'iso' in namespaces:
            info['iso'] = dict(record)

        return Info(info)

    def _make_name(self, name):
        if name in (b'\x00', b'\x01'):
            name = name.decode('ascii')
        elif self._joliet:
            name = name.decode('utf-16-be')
        else:
            name = name.decode('ascii').split(';')[0].rstrip('.').lower()
        return name

    def getmeta(self, namespace="standard"):
        meta = super(ISOReadFS, self).getmeta(namespace)
        if namespace == 'standard':
            meta['unicode_paths'] = self._joliet or self._rockridge
        return meta

    def openbin(self, path, mode='r', buffering=-1, **options):
        if not mode.startswith('r'):
            self._on_modification_attempt(path)

        _path = self.validatepath(path)
        record = self._get_record(_path)

        if record['Flags'].is_dir:
            raise errors.FileExpected(path)

        return ISOReadFile(self, record)

    def scandir(self, path, namespaces=None, page=None):
        _path = self.validatepath(path)
        record = self._get_record(_path)

        if not record['Flags'].is_dir:
            raise errors.DirectoryExpected(path)

        for record in self._directory_records(record["Location of Extent"]):
            name = self._make_name(record['File Identifier'])
            self._path_table[join(_path, name)] = record
            yield self._make_info_from_record(record, namespaces)

    def listdir(self, path):
        return [entry.name for entry in self.scandir(path)]

    def getinfo(self, path, namespaces=None):
        _path = self.validatepath(path)
        record = self._get_record(_path)

        return self._make_info_from_record(record, namespaces)
