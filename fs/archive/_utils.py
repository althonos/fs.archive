# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import sys
import errno
import importlib

from six.moves import filterfalse

__all__ = [
    'unique',
    'import_from_names',
    'writable_path',
    'writable_stream'
]


def unique(iterable, key=None):
        """Yield unique elements, preserving order.
        """
        seen = set()
        seen_add = seen.add
        if key is None:
            for element in filterfalse(seen.__contains__, iterable):
                seen_add(element)
                yield element
        else:
            for element in iterable:
                k = key(element)
                if k not in seen:
                    seen_add(k)
                    yield element


def import_from_names(*names):
    for name in names:
        try:
            return importlib.import_module(name)
        except ImportError:
            continue
    return None


def writable_path(path):
    if os.path.exists(path):
        return os.access(path, os.W_OK)
    try:
        with open(path, 'w'):
            pass
    except (OSError, IOError):
        return False
    else:
        os.remove(path)
        return True


def writable_stream(handle):
    if isinstance(handle, io.IOBase) and sys.version_info >= (3, 5):
        return handle.writable()
    try:
        handle.write(b'')
    except (io.UnsupportedOperation, IOError):
        return False
    else:
        return True
