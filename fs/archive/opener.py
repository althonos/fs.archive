# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import six
import contextlib

from pkg_resources import iter_entry_points, DistributionNotFound
from ..opener import open_fs
from ..opener._errors import Unsupported
from ..path import basename

@contextlib.contextmanager
def open_archive(fs_url, archive):

    it = iter_entry_points('fs.archive.open_archive')
    entry_point = next((ep for ep in it if archive.endswith(ep.name)), None)

    if entry_point is None:
        raise Unsupported(
            'unknown archive extension: {}'.format(archive))

    try:
        archive_opener = entry_point.load()
    except DistributionNotFound as df:
        six.raise_from(Unsupported(
            'extension {} requires {}'.format(entry_point.name, df.req)), None)

    # if not isinstance(archive_fs, base.ArchiveFS):
    #     raise TypeError('bad entry point')

    try:
        fs = open_fs(fs_url)
        binfile = fs.openbin(archive, 'r+' if fs.isfile(archive) else 'w')

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
