# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import six
import contextlib
import pkg_resources

from .. import errors
from ..path import basename
from ..opener import open_fs
from ..opener._errors import Unsupported

from . import base


@contextlib.contextmanager
def open_archive(fs_url, archive):

    it = pkg_resources.iter_entry_points('fs.archive.open_archive')
    entry_point = next((ep for ep in it if archive.endswith(ep.name)), None)

    if entry_point is None:
        raise Unsupported(
            'unknown archive extension: {}'.format(archive))

    try:
        archive_opener = entry_point.load()
    except pkg_resources.DistributionNotFound as df:
        six.raise_from(Unsupported(
            'extension {} requires {}'.format(entry_point.name, df.req)), None)

    # if not isinstance(archive_fs, base.ArchiveFS):
    #     raise TypeError('bad entry point')

    try:
        fs = open_fs(fs_url)

        if issubclass(archive_opener, base.ArchiveFS):
            try:
                binfile = fs.openbin(archive, 'r+')
            except errors.ResourceNotFound:
                binfile = fs.openbin(archive, 'w')
            except errors.ResourceReadOnly:
                binfile = fs.openbin(archive, 'r')
                archive_opener = archive_opener._read_fs_cls

        elif issubclass(archive_opener, base.ArchiveReadFS):
            binfile = fs.openbin(archive, 'r')

        if not hasattr(binfile, 'name'):
            binfile.name = basename(archive)

        archive_fs = archive_opener(binfile)

        yield archive_fs

    except Exception:
        raise

    finally:
        archive_fs.close()
        binfile.close()
        if fs is not fs_url: # close the fs if we opened it
            fs.close()
