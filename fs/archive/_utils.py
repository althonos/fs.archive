# coding: utf-8
from __future__ import absolute_import
from __future__ import unicode_literals

import os
import io
import sys
import errno
import importlib


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
